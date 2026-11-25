"""Research (2026-11-25, docs section 136): recompute every number in docs "The result" from the final code.

The pooled fresh 50K starts, the per-period medians, the per-set table (band / gap trades, win, PF, net 1 MNQ, days
traded), the by-year figures and the TradingView window, from bench.run / harness with the shipped defaults.
Run from research/: python zoo/verify_result.py
"""
import pickle
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import harness as H  # noqa: E402
import strats as S  # noqa: E402


def pf(u):
    return u[u > 0].sum() / -u[u < 0].sum()


def main():
    r = B.run()
    print(B.line("shipped", r))
    sets = pickle.load(open(B.PK, "rb"))
    pool, yr = [], {}
    for n in ("dev", "unseen_nq", "unseen_es", "live"):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
        band, gap = t[t.bar > 1].usd, t[t.bar <= 1].usd
        print(f"{n}: {len(d):,} sessions | band {len(band)} ({np.mean(band > 0):.0%}, {pf(band):.2f}, "
              f"${band.sum():,.0f}) | gap {len(gap)} ({pf(gap):.2f}, ${gap.sum():,.0f}) | "
              f"days traded {t.d.nunique() / len(d):.0%}")
        for y, u in t.groupby(pd.to_datetime(t.d).dt.year).usd:
            if n != "unseen_es":  # the by-year figures are NQ / MNQ only
                yr[y] = yr.get(y, 0.0) + u.sum()
        if n in ("dev", "unseen_nq"):
            res = H.account(t, d, steps=B.STEPS, day_stop=600.0, day_qty=B._news(d))
            p = np.array([x[1] for x in res])
            print(f"   {n} starts: {len(res)}, lost {sum(x[0] for x in res)}, median ${np.median(p):,.0f}, "
                  f"p25 ${np.percentile(p, 25):,.0f}")
            pool += res
    p = np.array([x[1] for x in pool])
    g = sum(x[2] for x in pool) / sum(x[3] for x in pool)
    print(f"pooled {len(pool)} starts: lost {sum(x[0] for x in pool)}, median ${np.median(p):,.0f}, p25 "
          f"${np.percentile(p, 25):,.0f}, p10 ${np.percentile(p, 10):,.0f}, worst ${p.min():,.0f}, "
          f"best ${p.max():,.0f}; "
          f"reach $10k {np.mean(p >= 10000):.0%}, $15k {np.mean(p >= 15000):.0%}, $20k {np.mean(p >= 20000):.0%}, "
          f"$25k {np.mean(p >= 25000):.0%}; green traded days {g:.0%}")
    print("by year (1 contract, all trades, NQ / MNQ sets): "
          + ", ".join(f"{y} ${v:,.0f}" for y, v in sorted(yr.items())))


if __name__ == "__main__":
    main()
