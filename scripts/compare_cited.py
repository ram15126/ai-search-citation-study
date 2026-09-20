"""Which page features go with being cited by Perplexity?
A) All cited pages vs uncited Google top-10 pages (raw comparison).
B) Within Google top-10 only, logistic regression per feature controlling for Google position,
   so 'ranks higher' is not mistaken for 'has feature X'.
"""
import json, os, math, statistics as st
import numpy as np
from scipy.stats import mannwhitneyu, fisher_exact, false_discovery_control
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = lambda n: os.path.join(HERE, '..', 'data', n)
d = json.load(open(DATA('page_features.json')))
C = [f for f in d if f["cited"]]; U = [f for f in d if not f["cited"]]
print(f"measured: cited={len(C)}  uncited top-10={len(U)}\n")
BOOL = ["slug_match", "title_match", "h1_match", "first120_match", "definition_early", "toc", "key_takeaways",
        "faq_section", "schema_faq", "schema_article", "schema_breadcrumb", "byline", "visible_date", "visible_updated",
        "reading_time", "author_bio_box", "inline_cta"]
NUM = ["words", "h2", "question_h2", "lists", "tables", "images", "numbers_per1k", "external_links", "internal_links",
       "mod_age_months"]
res = []
print("A) cited vs uncited top-10 (raw)")
for k in BOOL:
    a = sum(bool(f[k]) for f in C); b = sum(bool(f[k]) for f in U)
    p = fisher_exact([[a, len(C) - a], [b, len(U) - b]]).pvalue
    res.append((k, f"{a/len(C):.0%}", f"{b/len(U):.0%}", p))
for k in NUM:
    a = [f[k] for f in C if f.get(k) is not None]; b = [f[k] for f in U if f.get(k) is not None]
    p = mannwhitneyu(a, b).pvalue
    res.append((k, f"{st.median(a):.0f}", f"{st.median(b):.0f}", p))
adj = false_discovery_control([r[3] for r in res])
for (k, a, b, p), q in zip(res, adj):
    print(f"  {k:18s} cited={a:>6s} uncited={b:>6s}  p={p:.4f} adj={q:.3f}{'  *' if q < 0.05 else ''}")

# B) within top-10: logistic regression cited ~ feature + log(position)
T = [f for f in d if f["gpos"]]
print(f"\nB) within Google top-10 only (n={len(T)}, cited={sum(f['cited'] for f in T)}), controlling for position")
def logit(X, y, iters=50):
    X = np.column_stack([np.ones(len(y)), X]); w = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ w)); W = p * (1 - p) + 1e-9
        H = X.T @ (X * W[:, None]) + 1e-6 * np.eye(X.shape[1]); w += np.linalg.solve(H, X.T @ (y - p))
    cov = np.linalg.inv(H); return w, np.sqrt(np.diag(cov))
from scipy.stats import norm
out = []
y = np.array([f["cited"] for f in T], float)
pos = np.log([f["gpos"] for f in T])
w, se = logit(pos[:, None], y)
print(f"  position alone: coef(log pos)={w[1]:.2f} (z={w[1]/se[1]:.1f})")
for k in BOOL + NUM:
    rows = [(f, f.get(k)) for f in T if f.get(k) is not None]
    x = np.array([float(v) for _, v in rows]); yy = np.array([f["cited"] for f, _ in rows], float)
    pp = np.log([f["gpos"] for f, _ in rows])
    if x.std() == 0: continue
    if k in NUM: x = (x - x.mean()) / x.std()  # per 1 SD
    w, se = logit(np.column_stack([x, pp]), yy)
    z = w[1] / se[1]; p = 2 * (1 - norm.cdf(abs(z)))
    out.append((k, math.exp(w[1]), p, len(rows)))
adj = false_discovery_control([o[2] for o in out])
for (k, orr, p, n), q in sorted(zip(out, adj), key=lambda t: t[0][2]):
    unit = "per SD" if k in NUM else ""
    print(f"  {k:18s} OR={orr:5.2f} {unit:6s} p={p:.4f} adj={q:.3f} n={n}{'  *' if q < 0.05 else ''}")
