"""Fetch blog post HTML and extract template/design features.

Usage: python extract.py serp_sample.json  -> writes html/<n>.html and features.json
Re-run with --offline to re-parse saved HTML without refetching.
"""
import json, re, sys, os, hashlib
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(HERE, "html")
os.makedirs(HTML_DIR, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")


def fname(url):
    return os.path.join(HTML_DIR, hashlib.md5(url.encode()).hexdigest()[:12] + ".html")


def fetch(url):
    p = fname(url)
    if os.path.exists(p) and os.path.getsize(p) > 5000:
        return open(p, encoding="utf-8", errors="ignore").read(), "cached"
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
                         timeout=30)
        html = r.text
        status = r.status_code
    except Exception as e:
        return "", f"error {e.__class__.__name__}"
    if status == 200:
        open(p, "w", encoding="utf-8").write(html)
    return html, status


def jsonld_types(soup):
    types, authors, dp, dm = set(), [], None, None
    def walk(o):
        nonlocal dp, dm
        if isinstance(o, list):
            for i in o: walk(i)
        elif isinstance(o, dict):
            t = o.get("@type")
            for tt in (t if isinstance(t, list) else [t]):
                if tt: types.add(str(tt))
            if o.get("datePublished") and not dp: dp = o["datePublished"]
            if o.get("dateModified") and not dm: dm = o["dateModified"]
            a = o.get("author")
            if a and any(x in str(t) for x in ("Article", "BlogPosting", "NewsArticle", "WebPage")):
                authors.append(a)
            for v in o.values(): walk(v)
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            walk(json.loads(s.string or s.get_text() or "{}"))
        except Exception:
            pass
    return types, authors, dp, dm


def cls_id(el):
    return (" ".join(el.get("class") or []) + " " + (el.get("id") or "")).lower()


def any_cls(soup, pat):
    rx = re.compile(pat, re.I)
    for el in soup.find_all(True):
        if rx.search(cls_id(el)):
            return True
    return False


def pick_body(soup):
    """Pick the smallest container holding ~all of the article's paragraph text."""
    def pw(el):
        return sum(len(p.get_text(" ", strip=True).split()) for p in el.find_all("p"))
    cands = soup.find_all(["article", "main", "section", "div"])
    scored = []
    for c in cands:
        p = pw(c)
        if p < 200: continue
        scored.append((p, len(c.get_text(" ", strip=True).split()), c))
    if not scored:
        return soup.body or soup
    maxp = max(x[0] for x in scored)
    ok = [x for x in scored if x[0] >= 0.85 * maxp]
    ok.sort(key=lambda x: x[1])
    best = ok[0][2]
    # make sure the main headings are inside; climb while h2s sit outside
    while best.parent is not None and len(best.find_all("h2")) < 2 and best.parent.name not in ("body", "html"):
        if len(best.parent.get_text(" ", strip=True).split()) > 1.6 * ok[0][1]: break
        best = best.parent
    return best


def features(url, html):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "svg"]):
        if t.name == "script" and t.get("type") == "application/ld+json":
            continue
    types, ld_authors, dp, dm = jsonld_types(soup)
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    text_all = soup.get_text(" ", strip=True)
    low = text_all.lower()
    body = pick_body(soup)
    btext = body.get_text(" ", strip=True)
    words = len(btext.split())
    h1s = soup.find_all("h1")
    h2s = body.find_all("h2")
    h3s = body.find_all("h3")
    host = urlparse(url).netloc.replace("www.", "")

    # intro words before first h2
    intro = 0
    if h2s:
        for el in h2s[0].find_all_previous("p"):
            if body in el.parents:
                intro += len(el.get_text(" ", strip=True).split())

    links = body.find_all("a", href=True)
    internal = external = 0
    for a in links:
        href = a["href"]
        if href.startswith("#") or href.startswith("mailto"): continue
        h = urlparse(urljoin(url, href)).netloc.replace("www.", "")
        if host.split(".")[-2] in h: internal += 1
        else: external += 1

    meta = lambda **kw: (soup.find("meta", attrs=kw) or {}).get("content") if soup.find("meta", attrs=kw) else None
    pub = meta(property="article:published_time") or dp
    mod = meta(property="article:modified_time") or dm
    labels = [h.get_text(" ", strip=True).lower() for h in soup.find_all(["h2", "h3", "h4", "h5", "h6", "p", "div", "span", "strong", "b", "summary", "button", "nav"]) if 0 < len(h.get_text(" ", strip=True)) < 40]

    f = {
        "url": url, "domain": host, "words": words,
        "title_len": len(soup.title.get_text(strip=True)) if soup.title else 0,
        "meta_desc_len": len(meta(name="description") or ""),
        "h1_count": len(h1s),
        "h1_words": len(h1s[0].get_text(" ", strip=True).split()) if h1s else 0,
        "h2": len(h2s), "h3": len(h3s),
        "words_per_h2": round(words / len(h2s)) if h2s else None,
        "intro_words": intro,
        "h2_has_id": sum(1 for h in h2s if h.get("id") or h.find(id=True)) ,
        "question_h2": sum(1 for h in h2s if h.get_text().strip().endswith("?") or re.match(r"^(what|how|why|when|which|who|is|can|do|does|should)\b", h.get_text().strip().lower())),
        "numbered_h2": sum(1 for h in h2s if re.match(r"^\s*(\d+[\.\):]|step \d)", h.get_text().strip().lower())),
        "images": len(body.find_all("img")),
        "figcaption": len(body.find_all("figcaption")),
        "video_embed": len([i for i in body.find_all(["iframe", "video"]) if re.search(r"youtube|vimeo|wistia|loom|video", str(i.get("src", "")) + i.name)]),
        "tables": len(body.find_all("table")),
        "lists": len(body.find_all(["ul", "ol"])),
        "blockquotes": len(body.find_all("blockquote")),
        "code_blocks": len(body.find_all("pre")),
        "internal_links": internal, "external_links": external,
        "schema_types": sorted(types),
        "schema_article": bool(types & {"Article", "BlogPosting", "NewsArticle", "TechArticle"}),
        "schema_breadcrumb": "BreadcrumbList" in types,
        "schema_faq": "FAQPage" in types,
        "schema_howto": "HowTo" in types,
        "schema_person": "Person" in types or any("Person" in str(a) for a in ld_authors),
        "schema_org": "Organization" in types,
        "og_image": bool(soup.find("meta", property="og:image")),
        "canonical": bool(soup.find("link", rel="canonical")),
        "date_published": pub, "date_modified": mod,
        "visible_updated": bool(re.search(r"\b(updated|last updated|modified)\b[^.]{0,20}(on\s)?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{1,2}[/\-.])", low)),
        "visible_date": bool(soup.find("time")) or bool(re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2},? 20\d\d\b|\b\d{1,2} (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* 20\d\d\b", low)),
        "reading_time": bool(re.search(r"\b\d{1,2}\s?(-|\s)?min(ute)?s?\s?(read|reading)\b|\bread(ing)? time\b", low)),
        "byline": bool(ld_authors) or bool(soup.find("meta", attrs={"name": "author"})) or bool(soup.find("a", rel="author")) or bool(re.search(r"\b(written )?by [A-Z][a-z]+ [A-Z]", text_all[:6000])),
        "byline_person": ("Person" in types) or any("Person" in str(a) or (isinstance(a, dict) and a.get("name") and not re.search(r"team|staff|editor|inc|llc|\.com", str(a.get("name")), re.I)) for a in (ld_authors if isinstance(ld_authors, list) else [])) or bool(re.search(r"\b(written |posted |published )?by\s+[A-Z][a-z]+\s+[A-Z][a-z]+", text_all[:8000])),
        "author_bio_box": any_cls(body.parent or soup, r"author[-_ ]?(bio|box|card|info|profile|about)|about[-_]the[-_]author|post[-_]author") or bool(re.search(r"about the author", low)),
        "reviewer": bool(re.search(r"\b(reviewed by|fact[- ]checked by|edited by|expert reviewed)\b", low)),
        "breadcrumb_visible": any_cls(soup, r"breadcrumb") or bool(soup.find(attrs={"aria-label": re.compile("breadcrumb", re.I)})),
        "toc": any_cls(soup, r"(^|[-_ ])toc([-_ ]|$)|table[-_]?of[-_]?contents|on[-_]this[-_]page|jump[-_]?link|article[-_]nav|sidebar[-_]nav|anchor[-_]nav") or any(re.match(r"^(table of contents|contents|in this article|on this page|jump to|in this guide|in this post|article contents|what.s inside)\b", l) for l in labels),
        "key_takeaways": any(re.match(r"^(key takeaways?|tl;?dr|the short answer|quick answer|summary|article summary|at a glance|key points|the gist|in brief|what you.ll learn|the bottom line)\b", l) for l in labels),
        "faq_section": any(re.search(r"faq|frequently asked", h.get_text().lower()) for h in soup.find_all(["h2", "h3"])),
        "conclusion_h2": any(re.search(r"conclusion|final thoughts|wrapping up|bottom line|next steps|summary|get started|start (your|using|today)|ready to|in closing|takeaway", h.get_text().lower()) for h in h2s),
        "sources_section": any(re.match(r"^(sources|references|citations|works cited|bibliography)\b", h.get_text(" ", strip=True).lower()) for h in body.find_all(["h2", "h3", "h4", "strong", "p"])),
        "inline_cta": any_cls(body, r"(^|[-_ ])cta([-_ ]|$)|call[-_]to[-_]action|banner|promo|signup|sign-up|trial|demo"),
        "newsletter": bool(soup.find("input", attrs={"type": "email"})) or bool(re.search(r"subscribe|newsletter", low)),
        "related_posts": bool(re.search(r"related (posts|articles|reading|resources|content)|you (may|might) also (like|enjoy)|more (from|articles|posts|on this)|read (more|next)|recommended (for you|reading|articles)|keep reading|further reading", low)),
        "share_buttons": bool(re.search(r"facebook\.com/sharer|twitter\.com/intent|x\.com/intent|linkedin\.com/share|sharearticle", html, re.I)),
        "comments": any_cls(soup, r"comment") and bool(re.search(r"\bcomments?\b|leave a (reply|comment)", low)),
        "category_tag": any_cls(soup, r"(^|[-_ ])(category|tag|topic|eyebrow|kicker)([-_ ]|$)"),
    }
    return f


def main():
    src = sys.argv[1]
    offline = "--offline" in sys.argv
    sample = json.load(open(src, encoding="utf-8"))
    seen, out, fails = set(), [], []
    for row in sample:
        url = row["url"]
        if url in seen: continue
        seen.add(url)
        if offline:
            p = fname(url)
            html, st = (open(p, encoding="utf-8", errors="ignore").read(), "cached") if os.path.exists(p) else ("", "missing")
        else:
            html, st = fetch(url)
        if not html or len(html) < 5000 or (st not in (200, "cached")):
            fails.append({"url": url, "status": str(st), "len": len(html)})
            print("FAIL", st, url); continue
        try:
            f = features(url, html)
        except Exception as e:
            fails.append({"url": url, "status": f"parse {e}"}); continue
        f["query"], f["position"] = row.get("query"), row.get("position")
        f["fetch"] = str(st)
        # JS-shell detection: too few words means the static HTML is not the article
        if f["words"] < 400:
            fails.append({"url": url, "status": f"thin static html ({f['words']} words)"})
            print("THIN", f["words"], url); continue
        out.append(f)
        print("OK", f["words"], url)
    json.dump(out, open(os.path.join(HERE, "features.json"), "w"), indent=1)
    json.dump(fails, open(os.path.join(HERE, "fails.json"), "w"), indent=1)
    print(len(out), "ok /", len(fails), "failed")


if __name__ == "__main__":
    main()
