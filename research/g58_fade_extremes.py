"""G58 (docs/NINJATRADER_V38.md): the user's own style as rules: fade a stretched one-hour move at the edge of the
two-hour range, 24 hours a day, a 0.16% stop and a 0.38% target, out after 4 hours.

    python research/g58_fade_extremes.py <data dir>
"""
import sys

import numpy as np
import pandas as pd

NY = "America/New_York"
D = sys.argv[1]
TICK, PV, FEES = 0.25, 2.0, 1.24
STOP, TARGET, MOVE, EXTREME, HOLD = 0.0016, 0.0038, 0.0013, 0.05, 48  # 48 bars = 4 hours


def trades(b: pd.DataFrame, with_trend: bool) -> pd.DataFrame:
    o, h, lo, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    idx = b.index
    gap = np.r_[False, np.diff(idx.asi8) > 30 * 60 * 10**9]  # a break of over 30 minutes (the daily halt, weekends)
    hh = pd.Series(h).rolling(24).max().to_numpy()
    ll = pd.Series(lo).rolling(24).min().to_numpy()
    c12 = pd.Series(c).shift(12).to_numpy()
    e50 = pd.Series(c).ewm(span=50, adjust=False).mean().to_numpy()
    e200 = pd.Series(c).ewm(span=200, adjust=False).mean().to_numpy()
    seg = np.cumsum(gap)  # no window may span a break
    seg24 = pd.Series(seg).shift(23).to_numpy()
    out = []
    i, n = 200, len(c)
    while i < n - 1:
        ok = seg24[i] == seg[i] and seg[i + 1] == seg[i] and hh[i] > ll[i]
        d = 0
        if ok:
            pos = (c[i] - ll[i]) / (hh[i] - ll[i])
            move = c[i] / c12[i] - 1
            if pos >= 1 - EXTREME and move >= MOVE and (not with_trend or e50[i] < e200[i]):
                d = -1
            elif pos <= EXTREME and move <= -MOVE and (not with_trend or e50[i] > e200[i]):
                d = 1
        if not d:
            i += 1
            continue
        e = i + 1
        entry = o[e] + d * TICK
        stop = entry * (1 - d * STOP)
        tgt = entry * (1 + d * TARGET)
        x_px, why, j = None, "time", e
        for j in range(e, min(n, e + HOLD)):
            if j > e and seg[j] != seg[e]:  # the session broke: out at the last price before it
                x_px, why, j = c[j - 1] - d * TICK, "break", j - 1
                break
            if (lo[j] <= stop) if d > 0 else (h[j] >= stop):
                x_px = (min(o[j], stop) if d > 0 else max(o[j], stop)) - d * TICK
                why = "stop"
                break
            if (h[j] >= tgt) if d > 0 else (lo[j] <= tgt):
                x_px, why = tgt, "target"
                break
        if x_px is None:
            x_px = c[j] - d * TICK
        out.append({"time": idx[e], "side": d, "pnl": d * (x_px - entry) * PV - FEES, "why": why})
        i = j + 1
    return pd.DataFrame(out)


def stats(tf, first, last, label):
    x = tf[(tf.time >= pd.Timestamp(first, tz=NY)) & (tf.time < pd.Timestamp(last, tz=NY))]
    p = x.pnl.to_numpy()
    t = p.mean() / p.std(ddof=1) * np.sqrt(len(p)) if len(p) > 1 else np.nan
    weeks = (pd.Timestamp(last) - pd.Timestamp(first)).days / 7
    return {"set": label, "period": f"{first[:4]}-{last[:4]}", "trades": len(p), "a week": round(len(p) / weeks, 1),
            "net $": round(float(p.sum())), "$ a trade": round(float(p.mean()), 2), "t": round(float(t), 2),
            "win %": round(100 * float((p > 0).mean()), 1),
            "pf": round(float(p[p > 0].sum() / -p[p <= 0].sum()), 2),
            "targets %": round(100 * float((x.why == "target").mean()), 1)}


SETS = (("nq", f"{D}/nq5m_scaled.pkl", (("2015-01-01", "2020-01-01"), ("2020-01-01", "2025-08-01"))),
        ("index", f"{D}/bars5_scaled.pkl", (("2011-01-01", "2019-01-01"), ("2019-01-01", "2026-10-01"))))
for with_trend in (True, False):
    for name, path, halves in SETS:
        b = pd.read_pickle(path)[["open", "high", "low", "close"]].dropna()
        tf = trades(b, with_trend)
        for first, last in halves:
            print({"variant": "A with the trend" if with_trend else "B both sides", **stats(tf, first, last, name)},
                  flush=True)
