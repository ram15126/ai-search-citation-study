# What actually goes with being cited by AI search

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23194290.svg)](https://doi.org/10.5281/zenodo.23194290)

Measured on **19–20 September 2026** by [Ramakrishnan S](https://www.growwithram.in). This
repository is the working: every citation as collected, the measurement of all 438 pages, and the
scripts that turn one into the other.

Write-up: **https://www.growwithram.in/blog/what-gets-cited-by-ai-search**

## The finding

Perplexity was asked **30 B2B and technical questions, twice each**, logged out, with every source
recorded from the answer's own source list: **60 answers, 603 citations, 319 unique URLs.** The
comparison group is the ordinary web-search top ten for the same questions. Then **438 pages** —
cited and uncited — were measured by one script that records the same features on each.

**Ranking is the biggest lever.** A page ranked first in web search was cited 63% of the time; a
page ranked ninth, 7%.

| Web-search position | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Cited | **63%** | 41% | 38% | 31% | 31% | 20% | 17% | 20% | 7% | 10% |

**But three-quarters of cited pages were not in the top ten at all** (210 of 276) — they were long
guides, a median of 2,924 words, on sites that rank for the topic generally.

**82% of everything cited was a company blog or resource page** (261 of 319). Wikipedia was 1%.

### Page features, with ranking held constant

The comparison that matters is between pages *at the same web-search position*, so "this page
ranks better" cannot masquerade as "this page has a table of contents". n = 228, of which 66 were
cited, corrected for testing many features at once.

| Feature | Odds ratio | Verdict |
|---|---|---|
| **Table of contents** | **3.50** | **Holds up** (adj. p = 0.003) |
| **Visible "Updated" date** | **3.09** | **Holds up** (adj. p = 0.017) |
| Named author byline | 2.80 | Directional (adj. p = 0.06) |
| Query words in the first 120 words | 2.51 | Directional |
| Key-takeaways box | 2.22 | Directional |
| FAQ section | 1.66 | No effect |
| Word count | 0.88 per SD | No effect |
| **FAQPage schema** | **0.74** | **No effect — if anything slightly negative** |
| Article schema, visible date, reading time, images, author bio, CTA, question headings | ~1.0 | No effect |

**The raw comparison is the trap.** Compare cited pages with uncited ones and far more looks
significant: table of contents 66% vs 33%, FAQ 43% vs 27%, "Updated" 36% vs 18%, longer (2,760 vs
2,391 words). Most of that gap is ranking, not the feature. That is how "+340% citations from FAQ
schema" gets published in good faith.

### How stable are AI citations?

Asked twice, minutes apart, the same question returned **the same set of sources 25 times out of
30** (mean Jaccard overlap 0.93). One question swung hard (overlap 0.19). So a change in citations
for a fixed prompt is probably real rather than noise — within a session. Day-to-day drift was not
tested.

## Limits — where this could be wrong

1. **Correlation, not cause.** Nobody added a table of contents to these pages to see what
   happened. A table of contents may simply mark a big, maintained, well-resourced page, and that
   may be what is really being cited. The honest claim is "goes with", not "causes".
2. **One engine, one day.** Perplexity, logged out, no personalisation, 19 September 2026. ChatGPT
   and Google AI Mode may weight sources differently.
3. **No authority metric.** Measured on a free stack, so there is no Domain Rating to control for.
   Ranking position partly stands in for it, imperfectly.
4. **Table-of-contents detection undercounts** JavaScript-built ones — it missed about 1 in 8 when
   tested. That biases toward *missing* the effect, so the real one is probably no weaker.
5. **The comparison SERP is a web-search API's top ten**, not a logged Google SERP for the same
   moment, so "top 10" is approximate.
6. **30 English B2B and technical questions.** Nothing here covers local, India-specific, health,
   finance or e-commerce queries.
7. **438 of 532 candidate pages** could be measured; the rest blocked fetching or were too thin.
   Blocked sites skew toward large enterprise domains.

## What the platforms say

- [Google, AI features and your website](https://developers.google.com/search/docs/appearance/ai-features):
  there are no additional requirements to appear in AI Overviews or AI Mode, and no special
  optimisations necessary; a page must be indexed and eligible to be shown with a snippet. Google
  also describes AI Mode using a "query fan-out" technique, issuing several related searches.
- [Perplexity, bots](https://docs.perplexity.ai/guides/bots): PerplexityBot "is designed to surface
  and link websites in search results on Perplexity. It is not used to crawl content for AI
  foundation models." Blocking a *training* bot does not remove you from AI search; blocking a
  *search* bot does.

## The data

| File | What it holds |
|---|---|
| [`data/perplexity_citations.json`](data/perplexity_citations.json) | All 60 runs and 603 citations, as collected |
| [`data/cited_union.json`](data/cited_union.json) | Unique cited URLs per question |
| [`data/page_features.json`](data/page_features.json) | Every measurement for all 438 pages |
| [`data/serp_sample.json`](data/serp_sample.json), [`data/serp_excluded.json`](data/serp_excluded.json) | The web-search top ten used as the comparison group |
| [`data/overlap_output.txt`](data/overlap_output.txt), [`data/compare_cited_output.txt`](data/compare_cited_output.txt) | The script output behind the tables above |

The citation list was hashed inside the browser as it was collected and the saved file re-hashed
on disk before use, so nothing was lost in transcription.

## Re-run it

```bash
pip install requests beautifulsoup4 numpy scipy

python scripts/overlap.py         # stability, ranking overlap, source mix (no internet needed)
python scripts/compare_cited.py   # the feature tables above (no internet needed)
python scripts/page_features.py   # refetches all 532 pages and re-measures (~10 minutes)
```

The first two run entirely on the published data, so every number in the write-up can be checked
in one command.

**If you re-run this and get different numbers, please open an issue.**

## Check your own site

```bash
# Can the AI search crawlers reach you at all?
curl -s https://yoursite.com/robots.txt | grep -iE "OAI-SearchBot|PerplexityBot|Claude-SearchBot"

# Is your text in the HTML before any JavaScript runs?
curl -s https://yoursite.com/ | sed -e 's/<[^>]*>/ /g' | tr -s ' \n' ' ' | wc -w
```

Under 50 words from the second command means an AI crawler receives nothing to read, whatever else
you do. That is [a separate study](https://github.com/ram15126/ai-crawler-visibility-study).

## Licence

Scripts: MIT (see [LICENSE](LICENSE)). The measurements are factual observations of public pages;
reuse them freely, and a link back to the write-up is appreciated.
