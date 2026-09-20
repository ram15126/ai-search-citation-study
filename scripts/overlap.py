import json, re, collections, os
from urllib.parse import urlparse
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = lambda n: os.path.join(HERE, '..', 'data', n)

def _tpl(name):
    """The web-search top-10 sample, collected for the companion template study."""
    return DATA(name)

def norm(u):
    u=re.sub(r'^https?://(www\.)?','',u.strip()); u=re.sub(r'[#?].*$','',u); return u.rstrip('/').lower()
runs=json.load(open(DATA('perplexity_citations.json')))['runs']
cit=collections.defaultdict(lambda: {1:set(),2:set()})
for q,r,links in runs: cit[q][r]=set(norm(u) for u in links)
# 1 stability
jac=[len(v[1]&v[2])/len(v[1]|v[2]) for v in cit.values()]
same_top=[1 for v in cit.values()]
print(f"Run-to-run Jaccard: mean {sum(jac)/len(jac):.2f}, min {min(jac):.2f}, identical sets {sum(j==1 for j in jac)}/30")
# 2 overlap with Google top 10
g=collections.defaultdict(dict)
for r in json.load(open(_tpl('serp_sample.json')))+json.load(open(_tpl('serp_excluded.json'))):
    g[r['query']][norm(r['url'])]=r['position']
tot=inG=0; gcited=0; gtot=0
for q,v in cit.items():
    allc=v[1]|v[2]
    tot+=len(allc); inG+=len(allc & set(g[q]))
    gtot+=len(g[q]); gcited+=len(allc & set(g[q]))
print(f"AI-cited URLs (union of runs): {tot}; also in Google top-10 for same query: {inG} ({inG/tot:.0%})")
print(f"Google top-10 URLs cited by AI: {gcited}/{gtot} ({gcited/gtot:.0%})")
# by Google position
pos=collections.Counter(); posc=collections.Counter()
for q in cit:
    allc=cit[q][1]|cit[q][2]
    for u,p in g[q].items():
        pos[p]+=1; posc[p]+= u in allc
print("cited share by Google position:", {p:f"{posc[p]}/{pos[p]}" for p in sorted(pos)})
# domain-level overlap (same site, different page)
dom=lambda u: '.'.join(u.split('/')[0].split('.')[-2:])
dm=0
for q,v in cit.items():
    gd=set(dom(u) for u in g[q]); dm+=sum(dom(u) in gd for u in (v[1]|v[2]))
print(f"AI-cited URLs whose DOMAIN is in Google top-10: {dm}/{tot} ({dm/tot:.0%})")
# 3 source types
def kind(u):
    d=u.split('/')[0]
    if 'wikipedia' in d: return 'wikipedia'
    if any(x in d for x in ['reddit','quora','youtube','linkedin.com/top-content']) or 'linkedin.com/top-content' in u: return 'ugc/social'
    if d.endswith('.edu') or '.edu/' in u or d.endswith('.gov') or 'library.' in d: return 'edu/gov'
    if any(x in d for x in ['forbes','searchengineland','searchenginejournal','cio.com','techtarget','pcmag','hbr.org','businessnewsdaily','cmswire','socialmediaexaminer','business.org']): return 'media/publisher'
    if any(x in d for x in ['coursera','indeed','geeksforgeeks','wikihow','ixdf','contentmarketinginstitute','nngroup']): return 'education/reference site'
    if any(x in u for x in ['/docs/','developer.','learn.microsoft','kubernetes.io','help.']): return 'official docs'
    return 'company blog/resource'
k=collections.Counter(kind(u) for q,v in cit.items() for u in (v[1]|v[2]))
print("source types:", k.most_common())
json.dump({q:sorted(v[1]|v[2]) for q,v in cit.items()}, open(DATA('cited_union.json'),'w'), indent=1)
