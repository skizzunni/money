"""Research (2026-11-25, docs section 126): a stricter last guard tier under $1,000 above the floor, per period.

Under $1,000 the shipped guard trades strong breaks (1.5 sigma) and the gap trade only (section 50). Variants for
those days: no gap trade, or the first trade of the day only. Calendar starts (bad_runs.runs, the guard on) from
$50,000 / $48,806 / $48,998 against a $48,000 floor; then shuffled years (2,000 runs of 252 days drawn from each
period, the same daily rules). MNQ alone. Run from research/: python zoo/near_floor_tiers.py [--share]
(--share, docs 127: the guard's day stop at 0.15-0.35 of the cushion instead.)
"""
import pickle
import sys
import warnings

import numpy as np

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bad_runs as BR  # noqa: E402
import bench as B  # noqa: E402
import harness as H  # noqa: E402
import strats as S  # noqa: E402

STARTS = (50000.0, 48806.0, 48998.0)


def shuffled(t, st, d, n_runs=2000, seed=1, share=0.25):
    """252 days drawn at random (with replacement), the shipped guard as bad_runs.runs; lost share and median."""
    by = {k: (g.usd.to_numpy(), g["add"].to_numpy()) for k, g in t.groupby("d")}
    sb = {k: g.usd.to_numpy() for k, g in st.groupby("d")}
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
                on = cush < 1500.0
                g, ad = (sb.get(day, np.zeros(0)), None) if on and cush < 1000.0 else by.get(day, (np.zeros(0), None))
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
        tiers = (("shipped (strong breaks + the gap trade)", st, 0.25),
                 ("strong breaks, no gap trade", st[st.bar > 1], 0.25),
                 ("strong breaks + gap, first trade a day only", st.groupby("d").head(1), 0.25))
        if "--share" in sys.argv:  # docs 127: the guard's day stop as this share of the cushion ($100-600)
            tiers = tuple((f"day stop {x} x the cushion", st, x) for x in (0.15, 0.2, 0.25, 0.3, 0.35))
        for name, tier, share in tiers:
            cal = []
            for start in STARTS:
                r = BR.runs(t, d, B.STEPS, 600.0, B._news(d), strong=tier, guard=1500.0, strong_below=1000.0,
                            start=start, share=share)
                cal.append(f"${start:,.0f} {r.lost.mean():.1%} / ${r.profit.median():,.0f}")
            sh = shuffled(t, tier, d, share=share)
            shs = " ".join(f"${k:,.0f} {v[0]:.1%} / ${v[1]:,.0f}" for k, v in sh.items())
            print(f"{lab} {name}:\n   calendar (lost / median 12-month profit): {' | '.join(cal)}\n"
                  f"   shuffled years: {shs}", flush=True)


if __name__ == "__main__":
    main()
