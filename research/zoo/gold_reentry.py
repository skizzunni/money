"""Research (2026-11-25, docs section 111): gold in again once after an early stop, each period on its own.

After the shipped trade (mk_search.carry) is stopped out, the first 5-minute close past the signal close (the move
resumed) before `until` (New York 09:00 / 09:30 / 10:00) re-enters once its way at the next bar's open + a tick. The
stop: "orig" the first trade's stop price again, or "swing" a tick past the extreme since the stop-out; out at the
14:15 exit (the first bar from 14:10 on closes, out at the next open) or the stop, filled a tick worse. $1.24 a
contract a round trip. Per period (2009-17, 2018 - Mar 2025): the re-entries alone and the first trade plus them.
Run from research/: python zoo/gold_reentry.py PATH/gold5.pkl
"""
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "zoo")
import mk_search as K  # noqa: E402

OFF, TICK, EXIT = 360, 0.1, 1215  # the gold bars' clock is New York + 6 hours; 1215 = 14:15
PERIODS = (("2009-17", "2009-01-01", "2017-12-31"), ("2018-25", "2018-01-01", "2025-12-31"))


def again(d, first, until, mode):
    side, kc, _e, _x, why, xb = first
    if why != "stop":
        return None
    sig = d["c"][kc - 1]
    ko = K.at(d, 860)
    stop0 = np.round((d["o"][ko] + 0.6 * (sig - d["o"][ko]) - side * TICK) / TICK) * TICK
    for b in range(xb + 1, len(d["o"]) - 1):
        if d["mm"][b] + 5 > until + OFF:
            return None
        if side * (d["c"][b] - sig) > 0:
            e = d["o"][b + 1] + side * TICK
            if mode == "orig":
                stop = stop0
            else:
                seg = slice(xb, b + 1)
                stop = (d["l"][seg].min() - TICK) if side > 0 else (d["h"][seg].max() + TICK)
            if side * (e - stop) <= 0:
                return None
            for j in range(b + 1, len(d["o"])):
                if (side > 0 and d["l"][j] <= stop) or (side < 0 and d["h"][j] >= stop):
                    x = (min(d["o"][j], stop) if side > 0 else max(d["o"][j], stop)) - side * TICK
                    return (x - e) * side * 10 - 1.24
                if d["mm"][j] >= EXIT - 5 and j + 1 < len(d["o"]):
                    return (d["o"][j + 1] - side * TICK - e) * side * 10 - 1.24
            return None
    return None


def stats(s, a, b):
    p = s[(s.index >= pd.Timestamp(a)) & (s.index <= pd.Timestamp(b))]
    yrs = (min(s.index.max(), pd.Timestamp(b)) - pd.Timestamp(a)).days / 365.25
    pf = p[p > 0].sum() / -p[p < 0].sum() if (p < 0).any() else np.inf
    up = np.mean(p.groupby(p.index.year).sum() > 0) if len(p) else np.nan
    worst = p.min() if len(p) else 0.0
    return f"{len(p) / yrs:.0f}/yr ${p.sum() / yrs:+,.0f}/yr PF {pf:.2f} worst ${worst:,.0f} years up {up:.0%}"


def main():
    G = pickle.load(open(sys.argv[1], "rb"))
    for g in G:
        for k in ("o", "h", "l", "c"):
            g[k] = np.round(np.asarray(g[k]), 1)
    base, extra = {}, {}
    for i in range(15, len(G)):
        for tr in K.carry(G, i, TICK):
            base[pd.Timestamp(G[i]["d"])] = (tr[3] - tr[2]) * tr[0] * 10 - 1.24
            for until in (540, 570, 600):
                for mode in ("orig", "swing"):
                    r = again(G[i], tr, until, mode)
                    if r is not None:
                        extra.setdefault((until, mode), {})[pd.Timestamp(G[i]["d"])] = r
    b = pd.Series(base).sort_index()
    print("shipped: " + " | ".join(f"{lab} {stats(b, a, z)}" for lab, a, z in PERIODS))
    for (until, mode), x in sorted(extra.items()):
        x = pd.Series(x).sort_index()
        both = b.add(x, fill_value=0.0)
        print(f"again by {until // 60}:{until % 60:02d}, {mode} stop: re-entries "
              + " | ".join(f"{lab} {stats(x, a, z)}" for lab, a, z in PERIODS))
        print("    with the first trades: " + " | ".join(f"{lab} {stats(both, a, z)}" for lab, a, z in PERIODS),
              flush=True)


if __name__ == "__main__":
    main()
