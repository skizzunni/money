"""Research (2026-11-25, docs section 157): the gap trade with / against the 20-session trend, long / short, by year.

Analysis only (1 contract): the gap trade's side against the prior close versus the 20-session average of closes
(known before the open), per period and per year (NQ dev + unseen + live), and its longs / shorts per year.
Section 28 split it by trend among others before sections 61 / 87. Run from research/: python zoo/gap_sides.py
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
    rows = []
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("unseen_es", "ES 2020-24"), ("live", "live 2026")):
        d, s = sets[n]
        idx = {x["d"]: i for i, x in enumerate(d)}
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        g = t[t.bar <= 1].copy()

        def trend(day, d=d, idx=idx):
            i = idx[day]
            if i < 21:
                return np.nan
            pc = [d[j]["c"][-1] * d[i]["s"] / d[j]["s"] for j in range(i - 20, i)]
            return np.sign(pc[-1] - np.mean(pc))
        g["with"] = [side * trend(day) > 0 for side, day in zip(g.side, g.d, strict=True)]
        w, a = g.usd[g["with"]], g.usd[~g["with"]]
        print(f"{lab}: with the trend {len(w)} PF {pf(w):.2f} ${w.sum():,.0f} | against {len(a)} PF {pf(a):.2f} "
              f"${a.sum():,.0f}")
        if n != "unseen_es":
            g["y"] = pd.to_datetime(g.d).dt.year
            rows.append(g)
    g = pd.concat(rows)
    by = {"with $": g["with"], "against $": ~g["with"], "long $": g.side > 0, "short $": g.side < 0}
    tab = pd.DataFrame({k: g[m].groupby("y").usd.sum() for k, m in by.items()})
    print("\nthe gap trade by year, 1 contract:\n" + tab.fillna(0).round(0).astype(int).to_string())
    for c in tab.columns:
        print(f"{c} up in {int((tab[c].fillna(0) > 0).sum())} of {len(tab)} years, total ${tab[c].sum():,.0f}")


if __name__ == "__main__":
    main()
