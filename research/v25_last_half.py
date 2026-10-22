"""The last half hour in the direction of the first (Gao, Han, Li & Zhou 2018), at 10 MNQ: at 15:30 (or 15:00) take
the sign of the return from the previous close to 10:00 (or the day so far), hold to 16:00. On the v2.4 stand-in from
2025 (research/v24_proxy.py), NQ futures 2015-2025 and the index 2011-2026 (docs/RESULTS.md, v2.5: no edge).

    python research/v25_last_half.py <data dir> <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v18_scan as V  # noqa: E402

S, SEP, DEC = sys.argv[1:4]
V.init([SEP, DEC, f"{S}/nq5m_scaled.pkl", f"{S}/bars5_scaled.pkl"])
sets = {"proxy": pd.read_pickle(f"{S}/proxy_5m.pkl"), "nq": V.DATA["nq"][0], "index": V.DATA["index"][0]}
for name, b in sets.items():
    t = b.index.tz_convert("America/New_York")
    b = b.copy()
    b["d"] = t.date
    b["m"] = t.hour * 60 + t.minute
    g = b.groupby("d")
    o, cl = g.open.first(), g.close.last()

    def px_at(m, b=b):  # close of the bar ending at minute m
        return b[b.m == m - 5].set_index("d").close
    c10, c1530, c1500, c1400 = px_at(600), px_at(930), px_at(900), px_at(840)
    df = pd.DataFrame({"o": o, "cl": cl, "c10": c10, "c1530": c1530, "c1500": c1500, "c1400": c1400}).dropna()
    df["pc"] = df.cl.shift(1)
    df = df.dropna()
    if name == "proxy":
        df = df[df.index >= pd.Timestamp("2025-01-02").date()]
    r1 = df.c10 / df.pc - 1
    for lab, entry, rule in (("1530 by r1", df.c1530, np.sign(r1)), ("1500 by r1", df.c1500, np.sign(r1)),
                             ("1530 by day", df.c1530, np.sign(df.c1530 / df.pc - 1)),
                             ("1530 by r1 big", df.c1530, np.sign(r1) * (abs(r1) > r1.abs().rolling(50).median()))):
        pts = rule * (df.cl - entry)
        pnl = pts * 2 * 10 - 12.4 * (rule != 0) - 2 * 0.25 * 2 * 10 * (rule != 0)
        e = pnl.cumsum()
        dd = (e.cummax() - e).max()
        n = int((rule != 0).sum())
        win = 100 * (pnl > 0).sum() / max(1, n)
        print(f"{name:6s} {lab:14s} n={n:5d} net={pnl.sum():10.0f} dd={dd:8.0f} win={win:5.1f} "
              f"pf={pnl[pnl > 0].sum() / -pnl[pnl < 0].sum():.3f}")
