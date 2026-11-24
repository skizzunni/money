# ruff: noqa
import sys, pickle, warnings; sys.path.insert(0,'zoo'); warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import harness as H, strats as S, bench, mk_search as K
sets=pickle.load(open(bench.PK,'rb'))
d,s=sets['unseen_nq']
t=H.trades_of(S.everyday,d,s,legs=(("gap_go",bench.GAP),("noise",bench.BAND)))
t['add']=(bench._stretch(d,t,1.0)>=1.5).astype(int)
G5=pickle.load(open('/tmp/claude-0/-home-user-money/a932a565-3474-5ea9-80d7-5853e3bebb0c/scratchpad/data/gold5.pkl','rb'))
for g in G5:
    for k in ('o','h','l','c'): g[k]=np.round(np.asarray(g[k]),1)
gr={}
for i in range(15,len(G5)):
    for side,kc,e,x,why,xb in K.carry(G5,i,0.1): gr.setdefault(G5[i]['d'],[]).append((x-e)*side*10-1.24)
bm={k:list(zip(g.usd,g['add'])) for k,g in t.groupby('d')}
days=[x for x in d if pd.Timestamp(x['d'])<=pd.Timestamp('2025-03-21')]
DAYS=[(bm.get(x['d'],[]), gr.get(x['d'],[]), x['news'][0]) for x in days]
rng=np.random.default_rng(1)
def run(start, n=252):
    bal=start; high=max(50000.0,start); low=start
    for k in rng.integers(0,len(DAYS),n):
        nq_tr, g_tr, v = DAYS[k]
        prof=bal-50000; floor=min(high-2000,50000); cush=bal-floor
        on=cush<1500
        q=3 if prof>=3500 else 2 if prof>=2000 else 1
        mild=v==v and 2<=v<3
        if v==v and v>=6: q=min(q+1,3)
        maxc,ds=(1,max(100.0,min(600.0,0.25*cush))) if on else (3,600.0)
        q=min(q,maxc); gq=min(3 if prof>=3500 else 2 if prof>=2000 else 1, maxc); dp=0.0
        if not on:
            for u in g_tr:
                dp+=u*gq
                if bal+dp<=floor: return True, bal+dp-start, low
        nq=0.0
        if not mild:
            for u,a in nq_tr:
                if (on and nq<=-ds) or nq<=-600: break
                nq+=u*min(q+a,maxc)
                if bal+dp+nq<=floor: return True, bal+dp+nq-start, low
        bal+=dp+nq; high=max(high,bal); low=min(low,bal)
    return False, bal-start, low
for start in (50000.0, 48806.5, 48997.5):
    R=[run(start) for _ in range(2000)]
    lost=np.mean([r[0] for r in R]); pr=np.array([r[1] for r in R]); low=np.array([r[2] for r in R])
    print(f"start ${start:,.0f}: blown {lost:.1%} of 2,000 shuffled years | 12-month result median ${np.median(pr):,.0f}, worst 10% ${np.percentile(pr,10):,.0f} | lowest balance median ${np.median(low):,.0f}, worst 5% ${np.percentile(low,5):,.0f}")
