"""Research (2026-11-25, docs section 108): gold's move threshold, confirmation and exit, each period on its own.

Gold alone (mk_search.carry as MgcOvernightCarry trades it: the 60% stop, out at 14:15, $1.24 a contract round trip),
one setting moved at a time from the shipped k 1.5 / confirm 15 / exit 14:15: per period (2009-17, 2018 - Mar 2025)
the trades a year, $ a year a contract, PF, worst trade and the share of years up.
Needs the 5-minute gold bars (the gold5.pkl the stress tests use): python zoo/gold_recheck.py PATH/gold5.pkl
--stop (docs section 109): the stop 0-80% of the way to the signal close, and the move from another bar's close.
--pairs (docs section 144): the move x the stop, and the confirmation x the exit, 3 x 3 each.
"""
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "zoo")
import mk_search as K  # noqa: E402

PERIODS = (("2009-17", "2009-01-01", "2017-12-31"), ("2018-25", "2018-01-01", "2025-12-31"))


def trades(G, **kw):
    out = []
    for i in range(15, len(G)):
        for side, _e, e, x, _w, _x in K.carry(G, i, 0.1, **kw):
            out.append((pd.Timestamp(G[i]["d"]), (x - e) * side * 10 - 1.24))
    return pd.DataFrame(out, columns=["d", "usd"])


def line(t):
    parts = []
    for lab, a, b in PERIODS:
        p = t[(t.d >= a) & (t.d <= b)]
        yrs = p.groupby(p.d.dt.year).usd.sum()
        n_yrs = (min(t.d.max(), pd.Timestamp(b)) - pd.Timestamp(a)).days / 365.25
        pf = p.usd[p.usd > 0].sum() / -p.usd[p.usd < 0].sum()
        parts.append(f"{lab} {len(p) / n_yrs:.0f}/yr ${p.usd.sum() / n_yrs:+,.0f}/yr PF {pf:.2f} "
                     f"worst ${p.usd.min():,.0f} years up {np.mean(yrs > 0):.0%}")
    return " | ".join(parts)


def main():
    G = pickle.load(open(sys.argv[1], "rb"))
    for g in G:
        for k in ("o", "h", "l", "c"):
            g[k] = np.round(np.asarray(g[k]), 1)
    rows = [("shipped (1.5x, 15 min, 14:15)", {})]
    rows += [(f"move {k}x", {"k": k}) for k in (1.25, 1.35, 1.65, 1.75, 2.0)]
    rows += [(f"confirm {c} min", {"confirm": c}) for c in (10, 20)]
    exits = (1185, 1200, 1230, 1245)  # the gold bars' clock is New York + 6 hours (1215 = 14:15)
    rows += [(f"out {(m - 360) // 60}:{(m - 360) % 60:02d}", {"exit_m": m}) for m in exits]
    if "--stop" in sys.argv:  # docs section 109: the stop and the move's reference bar
        rows = [("shipped (stop 60%, from the 13:25 close)", {})]
        rows += [(f"stop {int(a * 100)}%", {"stop_at": a}) for a in (0.0, 0.4, 0.5, 0.7, 0.75, 0.8)]
        refs = (1160, 1165, 1175, 1185)  # settle m: the close of the bar starting at m - 5 (New York m - 365)
        rows += [(f"from the {(m - 365) // 60}:{(m - 365) % 60:02d} close", {"settle": m}) for m in refs]
    if "--pairs" in sys.argv:  # docs 144: two settings at once, 3 x 3, the shipped cell in the middle
        rows = [(f"move {k}x, stop {int(a * 100)}%", {"k": k, "stop_at": a}) for k in (1.35, 1.5, 1.65)
                for a in (0.5, 0.6, 0.7)]
        rows += [(f"confirm {c} min, out {(m - 360) // 60}:{(m - 360) % 60:02d}", {"confirm": c, "exit_m": m})
                 for c in (10, 15, 20) for m in (1200, 1215, 1230)]
    for lab, kw in rows:
        print(f"{lab}: {line(trades(G, **kw))}", flush=True)


if __name__ == "__main__":
    main()
