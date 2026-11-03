"""G60 (docs/NINJATRADER_V38.md): gap and go in 09:30-10:00, beside the day bot.

    python research/g60_gap_go.py <data dir>
"""
import sys

import numpy as np
import pandas as pd
import v24_scan as S

NY = "America/New_York"
D = sys.argv[1]
TICK, PV, FEES = 0.25, 2.0, 1.24


def trades(path: str, skip: set) -> pd.DataFrame:
    b = pd.read_pickle(path)[["open", "high", "low", "close"]].dropna()
    t = b.index.tz_convert(NY)
    b = b.assign(day=t.strftime("%Y-%m-%d"), m=t.hour * 60 + t.minute)
    rth = b[(b.m >= 570) & (b.m < 960)]
    out, gaps, prev_close, prev_month = [], [], None, None
    for day, x in rth.groupby("day", sort=True):
        x = x.set_index("m")
        month = day[:7]
        ok = 570 in x.index and 955 in x.index and len(x) >= 70 and day not in skip
        if ok and prev_close is not None and month == prev_month:
            gap = x.loc[570, "open"] - prev_close
            avg = np.mean(gaps[-14:]) if len(gaps) >= 10 else None
            if avg and abs(gap) >= 0.5 * avg and all(k in x.index for k in (575, 580, 585, 590, 595, 600)):
                d = 1 if gap > 0 else -1
                if d * (x.loc[570, "close"] - x.loc[570, "open"]) > 0:
                    entry, stop = x.loc[575, "open"] + d * TICK, x.loc[570, "open"]
                    exit_px, why = x.loc[600, "open"] - d * TICK, "10:00"
                    for m in (575, 580, 585, 590, 595):
                        hit = x.loc[m, "low"] <= stop if d > 0 else x.loc[m, "high"] >= stop
                        if hit:
                            exit_px = (min(x.loc[m, "open"], stop) if d > 0 else max(x.loc[m, "open"], stop)) - d * TICK
                            why = "stop"
                            break
                    out.append({"day": day, "side": d, "pnl": d * (exit_px - entry) * PV - FEES, "why": why})
            gaps.append(abs(gap))
        if ok:
            prev_close = x.loc[955, "close"]
        prev_month = month
    return pd.DataFrame(out)


def t_stat(p):
    return float(p.mean() / p.std(ddof=1) * np.sqrt(len(p))) if len(p) > 1 else float("nan")


SETS = (("nq", f"{D}/nq5m_scaled.pkl", (("2015-01-01", "2020-01-01"), ("2020-01-01", "2025-08-01"))),
        ("index", f"{D}/bars5_scaled.pkl", (("2011-01-01", "2019-01-01"), ("2019-01-01", "2026-10-01"))))
pooled = []
for name, path, halves in SETS:
    skip = set(S.CLOSURES.split(","))
    tf = trades(path, skip)
    for first, last in halves:
        x = tf[(tf.day >= first) & (tf.day < last)]
        p = x.pnl.to_numpy()
        pooled.append(p)
        weeks = (pd.Timestamp(last) - pd.Timestamp(first)).days / 7
        print({"set": name, "period": f"{first[:4]}-{last[:4]}", "trades": len(p), "a week": round(len(p) / weeks, 2),
               "net $": round(float(p.sum())), "$ a trade": round(float(p.mean()), 2), "t": round(t_stat(p), 2),
               "win %": round(100 * float((p > 0).mean()), 1),
               "pf": round(float(p[p > 0].sum() / -p[p <= 0].sum()), 2)}, flush=True)
    tf.to_csv(f"verification/noise_v2/g60_gap_go_{name}.csv", index=False)
allp = np.concatenate(pooled)
print({"pooled trades": len(allp), "net $": round(float(allp.sum())), "t": round(t_stat(allp), 2)})
