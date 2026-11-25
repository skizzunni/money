"""Research (2026-11-25, docs section 147): the shipped strategy year by year (1 contract), each leg on its own.

Per year: the band's and the gap trade's trades, PF, $ and worst month; the market that year (the NQ's move over the
year, its average daily high-low range as % of the close, and the share of sessions that closed beyond the 20-session
average the same way as the day before: trend persistence). Analysis only.
Run from research/: python zoo/year_profile.py
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
    trades, mk = [], []
    for n in ("dev", "unseen_nq", "live"):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        trades.append(t)
        c = np.array([x["c"][-1] / x["s"] for x in d])  # closes on one scale (the set is back-adjusted by s)
        sma = pd.Series(c).rolling(20).mean().shift(1).to_numpy()
        side = np.sign(c - sma)
        for i, x in enumerate(d):
            mk.append((pd.Timestamp(x["d"]), c[i], (np.max(x["h"]) - np.min(x["l"])) / x["c"][-1],
                       i > 20 and side[i] == side[i - 1]))
    t = pd.concat(trades)
    t["d"] = pd.to_datetime(t.d)
    m = pd.DataFrame(mk, columns=["d", "c", "rng", "persist"]).drop_duplicates("d").set_index("d")
    rows = []
    for y, g in t.groupby(t.d.dt.year):
        my = m[m.index.year == y]
        out = {"year": y, "NQ move": f"{my.c.iloc[-1] / my.c.iloc[0] - 1:+.0%}", "day range": f"{my.rng.mean():.2%}",
               "trend days": f"{my.persist.mean():.0%}"}
        for leg, sel in (("band", g.bar > 1), ("gap", g.bar <= 1)):
            u = g[sel]
            mon = u.groupby(u.d.dt.month).usd.sum()
            out[f"{leg} n"] = len(u)
            out[f"{leg} PF"] = round(pf(u.usd), 2)
            out[f"{leg} $"] = int(u.usd.sum())
            out[f"{leg} worst month"] = int(mon.min()) if len(mon) else 0
        rows.append(out)
    print(pd.DataFrame(rows).set_index("year").to_string())


if __name__ == "__main__":
    main()
