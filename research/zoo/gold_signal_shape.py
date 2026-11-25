"""Research (2026-11-25, docs section 112): the gold signal's shape, each period on its own.

Known when the order goes (the 08:30 bar's close; the 08:35 open is the fill, so it cannot filter): (a) how far the
first 15 minutes ran (the signal close less the 08:20 open) against the overnight move, and (b) where the signal close
sits in the 08:20-08:35 high-low range (1 = at its extreme the trade's way). The shipped trades (mk_search.carry,
$1.24 a contract a round trip) by tercile of each, per period (2009-17, 2018 - Mar 2025).
Run from research/: python zoo/gold_signal_shape.py PATH/gold5.pkl
"""
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "zoo")
import mk_search as K  # noqa: E402


def main():
    G = pickle.load(open(sys.argv[1], "rb"))
    for g in G:
        for k in ("o", "h", "l", "c"):
            g[k] = np.round(np.asarray(g[k]), 1)
    rows = []
    for i in range(15, len(G)):
        for side, kc, e, x, _w, _b in K.carry(G, i, 0.1):
            d, p = G[i], G[i - 1]
            ko, kp = K.at(d, 860), K.at(p, 1165)
            mv = abs(d["o"][ko] - p["c"][kp])
            run = side * (d["c"][kc - 1] - d["o"][ko])
            hi, lo = d["h"][ko:kc].max(), d["l"][ko:kc].min()
            pos = (d["c"][kc - 1] - lo) / (hi - lo) if hi > lo else 0.5
            rows.append((pd.Timestamp(d["d"]), (x - e) * side * 10 - 1.24, run / mv, pos if side > 0 else 1 - pos))
    t = pd.DataFrame(rows, columns=["d", "usd", "run", "pos"])
    t["per"] = np.where(t.d.dt.year <= 2017, "2009-17", "2018-25")
    for col, lab in (("run", "first 15 minutes / overnight move"), ("pos", "signal close in the 08:20-08:35 range")):
        t["q"] = pd.qcut(t[col], 3, labels=["low", "mid", "high"])
        edges = t[col].quantile([1 / 3, 2 / 3]).round(2).tolist()
        print(f"{lab} (terciles cut at {edges}):")
        g = t.groupby(["per", "q"], observed=True).usd
        out = pd.DataFrame({"n": g.size(), "mean $": g.mean().round(1),
                            "PF": g.apply(lambda s: s[s > 0].sum() / -s[s < 0].sum()).round(2),
                            "win": g.apply(lambda s: np.mean(s > 0)).round(2)})
        print(out.to_string(), flush=True)


if __name__ == "__main__":
    main()
