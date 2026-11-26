"""Research (2026-11-26, docs section 179): a third guard tier deep near the floor. Under $1,000 the shipped guard
takes strong breaks (1.5 sigma) and the gap trade at 1 contract with a quarter-cushion day stop; under $500 one hard
stop ($200) is 40% of what is left. Variants under `low` ($300 / $500 / $700): the gap trade only (stop at most 30
points, $60), or no trade at all. Shuffled years (2,000 runs of 252 days from each period, near_floor_tiers.shuffled's
loop) from $50,000 / $48,500 / $48,806 / $48,998 against a $48,000 floor; lost share and median profit.
Run from research/: python zoo/deep_tier.py
"""
import pickle
import sys
import warnings

import numpy as np

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import harness as H  # noqa: E402
import strats as S  # noqa: E402

STARTS = (50000.0, 48500.0, 48806.0, 48998.0)


def shuffled(t, st, deep, d, low=0.0, n_runs=2000, seed=1, share=0.25, guard=1500.0, below=1000.0):
    by = {k: (g.usd.to_numpy(), g["add"].to_numpy()) for k, g in t.groupby("d")}
    sb = {k: g.usd.to_numpy() for k, g in st.groupby("d")}
    db = {k: g.usd.to_numpy() for k, g in deep.groupby("d")} if deep is not None else {}
    nf = B._news(d)
    days = [x["d"] for x in d]
    out = {}
    for start in STARTS:
        rng = np.random.default_rng(seed)
        lost, prof = 0, []
        for _ in range(n_runs):
            bal, high = start, max(50000.0, start)
            for k in rng.integers(0, len(days), 252):
                day = days[k]
                floor = min(high - 2000.0, 50000.0)
                cush = bal - floor
                on = cush < guard
                if on and cush < low:
                    g, ad = db.get(day, np.zeros(0)), None
                elif on and cush < below:
                    g, ad = sb.get(day, np.zeros(0)), None
                else:
                    g, ad = by.get(day, (np.zeros(0), None))
                q = 1
                for lim, qq in B.STEPS:
                    if bal - 50000.0 >= lim:
                        q = qq
                q = nf(day, q)
                if q <= 0:
                    g = np.zeros(0)
                q = min(q, 1) if on else q
                ds = max(100.0, min(600.0, share * cush)) if on else 600.0
                pl, dead = 0.0, False
                for j, u in enumerate(g):
                    if pl <= -ds:
                        break
                    a = int(ad[j]) if ad is not None and not on else 0
                    pl += u * min(q + a, max(q, 3))
                    if bal + pl <= floor:
                        dead = True
                        break
                bal += pl
                if dead or bal <= floor:
                    lost += 1
                    break
                high = max(high, bal)
            else:
                prof.append(bal - start)
        out[start] = (lost / n_runs, np.median(prof) if prof else np.nan)
    return out


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25")):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
        st = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, "min_stretch": 1.5})))
        gap_only, none = st[st.bar <= 1], st.iloc[0:0]
        rows = [("shipped (no third tier)", None, 0.0)]
        rows += [(f"under ${lo:,.0f}: {nm}", ds, lo) for lo in (300.0, 500.0, 700.0)
                 for nm, ds in (("the gap trade only", gap_only), ("no trade", none))]
        print(lab, flush=True)
        for nm, ds, lo in rows:
            r = shuffled(t, st, ds, d, low=lo)
            print(f"  {nm}: " + " | ".join(f"${k:,.0f} {v[0]:.1%} / ${v[1]:,.0f}" for k, v in r.items()), flush=True)


if __name__ == "__main__":
    main()
