"""Research (2026-11-25, docs section 149): the band trades in calm and wild markets, each period on its own.

Analysis: per band trade the band's width in points at the 12:00 check (the 14-session sigma there x the day's open),
against the 100-point hard stop ($200 a contract), in terciles per period; per tercile the trades, win rate, PF,
$ a trade a contract and the share out at the full hard stop (a loss of $190 or more).
Run from research/: python zoo/calm_band.py
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
    return u[u > 0].sum() / -u[u < 0].sum() if (u < 0).any() else np.inf


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25")):
        d, s = sets[n]
        idx = {x["d"]: i for i, x in enumerate(d)}
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        b = t[t.bar > 1].copy()
        b["width"] = [np.mean([S._moves(d, j).get(720, np.nan) for j in range(idx[day] - 14, idx[day])])
                      * d[idx[day]]["o"][0] for day in b.d]
        b["q"] = pd.qcut(b.width, 3, labels=["calm", "mid", "wild"])
        cuts = b.width.quantile([1 / 3, 2 / 3]).round(0).tolist()
        print(f"{lab}: the band's width at 12:00 in points, terciles cut at {cuts} (the hard stop is 100 points)")
        for q, g in b.groupby("q", observed=True):
            u = g.usd
            yrs = pd.to_datetime(g.d).dt.year.value_counts().sort_index().to_dict()
            print(f"   {q}: {len(u)} trades, win {np.mean(u > 0):.0%}, PF {pf(u):.2f}, ${u.mean():.1f} a trade, at the "
                  f"hard stop {np.mean(u <= -190):.0%}; trades by year {yrs}", flush=True)


if __name__ == "__main__":
    main()
