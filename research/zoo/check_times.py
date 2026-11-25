"""Research (2026-11-25, docs section 158): the band's trades by entry check (10:00 ... 14:00), by period and year.

Analysis only (1 contract): the entry bar is the one after the check (bar 6 = the 10:00 check), so the check is
the end of the bar before the entry (read from the day's own bar times: a day with missing bars,
e.g. 2020-03-12 with 76, shifts the bar index). Per period the trades, PF and $ per check; per check the years up
(NQ dev + unseen + live).
Run from research/: python zoo/check_times.py
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
    allb = []
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("live", "live 2026")):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        b = t[t.bar > 1].copy()
        idx = {x["d"]: i for i, x in enumerate(d)}
        m = [int(d[idx[day]]["mm"][bar - 1]) + 5 for day, bar in zip(b.d, b.bar, strict=True)]  # the day's own bars
        b["check"] = [f"{x // 60}:{x % 60:02d}" for x in m]
        b["y"] = pd.to_datetime(b.d).dt.year
        print(f"{lab}: " + " | ".join(f"{c} {len(g)} PF {pf(g.usd):.2f} ${g.usd.sum():,.0f}"
                                      for c, g in b.groupby("check", sort=True)))
        allb.append(b)
    b = pd.concat(allb)
    tab = b.pivot_table(index="y", columns="check", values="usd", aggfunc="sum").fillna(0).round(0).astype(int)
    print("\nthe band by entry check and year, 1 contract:\n" + tab.to_string())
    print("years up per check: " + ", ".join(f"{c} {int((tab[c] > 0).sum())} of {len(tab)}" for c in tab.columns))


if __name__ == "__main__":
    main()
