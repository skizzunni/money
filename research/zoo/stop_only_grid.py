"""Research (2026-11-25, docs section 153): the grid around section 152's scaled stop, by period, and its years.

noise hard_stop_only: the hard stop at hard_vol x the 14-day average range within lo-hi points; break-even, the target
and the stop step on the $200 unit. --grid: hard_vol 0.2 / 0.25 / 0.3 x lo 70 / 75 / 80 x hi 140 / 150 / 160, fresh
50K starts per period. --years: 0.25 / 75-150 against the shipped at 1 contract by year (NQ dev + unseen + live).
Run from research/: python zoo/stop_only_grid.py --grid | --years
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


def cell(hv, lo, hi):
    return {"hard_vol": hv, "hard_lo": lo, "hard_hi": hi, "hard_stop_only": True}


def score(sets, n, band):
    d, s = sets[n]
    t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, **band})))
    t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
    r = H.account(t, d, steps=B.STEPS, day_stop=600.0, day_qty=B._news(d))
    p = np.array([x[1] for x in r])
    return np.mean([x[0] for x in r]), np.median(p), np.percentile(p, 25)


def main():
    sets = pickle.load(open(B.PK, "rb"))
    if "--grid" in sys.argv:
        base = {n: score(sets, n, {}) for n in ("dev", "unseen_nq")}
        print("shipped: " + " | ".join(f"{n} lost {v[0]:.1%} median ${v[1]:,.0f} p25 ${v[2]:,.0f}"
                                       for n, v in base.items()))
        for hv in (0.2, 0.25, 0.3):
            for lo in (70.0, 75.0, 80.0):
                for hi in (140.0, 150.0, 160.0):
                    parts = []
                    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25")):
                        v = score(sets, n, cell(hv, lo, hi))
                        parts.append(f"{lab} lost {v[0]:.1%} median {v[1] - base[n][1]:+,.0f} "
                                     f"p25 {v[2] - base[n][2]:+,.0f}")
                    print(f"{hv} x range, {lo:.0f}-{hi:.0f}: " + " | ".join(parts), flush=True)
    if "--years" in sys.argv:
        cols = {}
        for lab, band in (("shipped", {}), ("0.25x, 75-150", cell(0.25, 75.0, 150.0))):
            ys = []
            for n in ("dev", "unseen_nq", "live"):
                d, s = sets[n]
                t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, **band})))
                ys.append(t.groupby(pd.to_datetime(t.d).dt.year).usd.sum())
            cols[lab] = pd.concat(ys).groupby(level=0).sum()
        df = pd.DataFrame(cols).round(0)
        df["diff"] = df.iloc[:, 1] - df.iloc[:, 0]
        print(df.astype(int).to_string())
        print(f"up in {int((df['diff'] > 0).sum())} of {len(df)} years, total {df['diff'].sum():+,.0f}, "
              f"the largest year {df['diff'].idxmax()} {df['diff'].max():+,.0f}")


if __name__ == "__main__":
    main()
