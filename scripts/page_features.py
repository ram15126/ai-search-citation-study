"""Fetch AI-cited pages + uncited Google top-10 pages and measure them identically."""
import json, re, os, sys, datetime, collections
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = lambda n: os.path.join(HERE, '..', 'data', n)
sys.path.insert(0, HERE)   # extract.py sits beside this file
from extract import fetch, features, pick_body
from bs4 import BeautifulSoup

def _tpl(name):
    """The web-search top-10 sample, collected for the companion template study."""
    return DATA(name)
STOP={'what','is','a','an','the','how','to','of','for','best','guide','examples','tips'}
def norm(u):
    u=re.sub(r'^https?://(www\.)?','',u.strip()); u=re.sub(r'[#?].*$','',u); return u.rstrip('/').lower()
cited=json.load(open(DATA('cited_union.json')))
g=collections.defaultdict(dict)
for r in json.load(open(_tpl('serp_sample.json')))+json.load(open(_tpl('serp_excluded.json'))):
    g[r['query']][norm(r['url'])]=(r['position'], r['url'])
rows=[]
for q in cited:
    cs=set(cited[q])
    for u in cs: rows.append({'query':q,'url':'https://'+u,'cited':1,'gpos':g[q].get(u,(None,))[0]})
    for u,(p,raw) in g[q].items():
        if u not in cs: rows.append({'query':q,'url':raw,'cited':0,'gpos':p})
def kw(q): return [w for w in re.findall(r'[a-z]+',q.lower()) if w not in STOP]
def stem(w): return w[:5]
def extra(row, html):
    s=BeautifulSoup(html,'html.parser')
    title=(s.title.get_text(" ",strip=True) if s.title else '').lower()
    h1=(s.find('h1').get_text(" ",strip=True) if s.find('h1') else '').lower()
    for t in s(["script","style","noscript","nav","footer","header","form","aside"]): t.decompose()
    b=pick_body(s)
    txt=" ".join(e.get_text(" ",strip=True) for e in b.find_all(['p','li']) if len(e.get_text().split())>=4)
    first=" ".join(txt.split()[:120]).lower()
    k=[stem(w) for w in kw(row['query'])]
    path=row['url'].lower()
    has=lambda t: all(x in t for x in k)
    n=max(1,len(txt.split()))
    head=row['query'].lower().replace('what is ','').replace('how to ','')
    core=[w for w in kw(row['query'])][:2]
    defn=bool(re.search(r"\b(" + "|".join(re.escape(w) for w in core) + r")[a-z]*\)?\s+(is|are|refers to|means)\b", first)) if core else False
    return {'slug_match':has(path),'title_match':has(title),'h1_match':has(h1),'first120_match':has(first),
            'definition_early':defn,'numbers_per1k':round(1000*len(re.findall(r"(?<![a-z])\d[\d,.]*%?",txt))/n,1),
            'body_words':n}
def run(row):
    html,st=fetch(row['url'])
    if not html or len(html)<5000: return None
    try:
        f=features(row['url'],html)
    except Exception: return None
    if f['words']<250: return None
    f.update(extra(row,html)); f.update({k:row[k] for k in ('query','cited','gpos')})
    d=f.get('date_modified') or f.get('date_published') or ''
    m=re.match(r'(\d{4})-(\d{2})',str(d))
    f['mod_age_months']=((2026-int(m[1]))*12+(9-int(m[2]))) if m else None
    return f
res=[]
with ThreadPoolExecutor(6) as ex:
    for i,r in enumerate(ex.map(run,rows)):
        res.append(r)
        if i%50==0: print('...',i,flush=True)
ok=[r for r in res if r]
json.dump(ok,open(DATA('page_features.json'),'w'),indent=1)
print('rows',len(rows),'measured',len(ok),'cited',sum(r['cited'] for r in ok),'uncited',sum(1-r['cited'] for r in ok))
