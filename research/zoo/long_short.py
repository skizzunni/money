"""Research (2026-11-25, docs section 155): long against short, each leg, by period and by year (1 contract).

Analysis only: the band's and the gap trade's longs and shorts, trades, PF and $ per period (2015-19 / 2020-25 / ES
2020-24 / live 2026) and the band's longs / shorts $ by year (NQ dev + unseen + live).
Run from research/: python zoo/long_short.py
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
    years = []
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("unseen_es", "ES 2020-24"), ("live", "live 2026")):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        t["d"] = pd.to_datetime(t.d)
        parts = []
        for leg, m in (("band", t.bar > 1), ("gap", t.bar <= 1)):
            for side, nm in ((1, "long"), (-1, "short")):
                u = t.usd[m & (t.side == side)]
                parts.append(f"{leg} {nm} {len(u)} PF {pf(u):.2f} ${u.sum():,.0f}")
        print(f"{lab}: " + " | ".join(parts))
        if n != "unseen_es":
            b = t[t.bar > 1]
            years.append(b.groupby([b.d.dt.year, b.side]).usd.sum().unstack())
    y = pd.concat(years).groupby(level=0).sum().round(0).astype(int)
    y.columns = ["short $", "long $"]
    print("\nthe band by year, 1 contract:\n" + y.to_string())
    print(f"longs up in {int((y['long $'] > 0).sum())} of {len(y)} years, shorts in {int((y['short $'] > 0).sum())}")


if __name__ == "__main__":
    main()
