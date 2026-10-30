"""X1, pre-registered in docs/CANDIDATE_X1.md: simplified hourly noise momentum, identical on NQ, ES, YM and RTY futures
(Yahoo Finance hourly bars, Jun 2024 - Oct 2026), 1 micro contract each.

    python research/x1_markets.py <dir with y_NQ_60m.json, y_ES_60m.json, y_YM_60m.json, y_RTY_60m.json> <out.csv>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

NY = "America/New_York"
FEE = 0.62
SPEC = {"NQ": (2.0, 0.25), "ES": (5.0, 0.25), "YM": (0.5, 1.0), "RTY": (5.0, 0.1)}  # micro $ a point, tick
HOURS = [10, 11, 12, 13, 14, 15]  # the regular-hours hourly bars used; checks at the closes of 10:00-14:00


def load(path: Path) -> pd.DataFrame:
    j = json.load(open(path))["chart"]["result"][0]
    t = pd.to_datetime(j["timestamp"], unit="s", utc=True).tz_convert(NY)
    q = j["indicators"]["quote"][0]
    df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")}, index=t).dropna()
    df = df[(df.index.minute == 0) & df.index.hour.isin(HOURS)]
    df["day"] = df.index.strftime("%Y-%m-%d")
    df["h"] = df.index.hour
    full = df.groupby("day").h.count() == len(HOURS)
    return df[df.day.isin(full[full].index)]


def run(df: pd.DataFrame, pv: float, tick: float) -> pd.DataFrame:
    days = sorted(df.day.unique())
    o = df.pivot(index="day", columns="h", values="open").loc[days]
    c = df.pivot(index="day", columns="h", values="close").loc[days]
    day_open = o[10]
    move = (c.div(day_open, axis=0) - 1).abs()
    sig = move.rolling(14).mean().shift(1)
    prev_close = c[15].shift(1)
    rows = []
    for i, d in enumerate(days):
        if i < 15 or not np.isfinite(sig.iloc[i][14]):
            continue
        up = max(day_open.iloc[i], prev_close.iloc[i])
        dn = min(day_open.iloc[i], prev_close.iloc[i])
        pos, entry, pnl, n = 0, 0.0, 0.0, 0
        for h in [10, 11, 12, 13, 14]:
            cl = c.iloc[i][h]
            s = sig.iloc[i][h]
            want = 1 if cl > up * (1 + s) else -1 if cl < dn * (1 - s) else 0
            if want != pos:
                fill = o.iloc[i][h + 1]
                if pos:
                    px = fill - pos * tick
                    pnl += pos * (px - entry) * pv - 2 * FEE
                    rows.append({"day": d, "pnl": pos * (px - entry) * pv - 2 * FEE})
                    n += 1
                if want:
                    entry = fill + want * tick
                pos = want
        if pos:
            px = c.iloc[i][15] - pos * tick
            rows.append({"day": d, "pnl": pos * (px - entry) * pv - 2 * FEE})
    return pd.DataFrame(rows)


def main() -> None:
    src, out = Path(sys.argv[1]), sys.argv[2]
    res, daily = [], {}
    for m, (pv, tick) in SPEC.items():
        tf = run(load(src / f"y_{m}_60m.json"), pv, tick)
        p = tf.pnl.to_numpy()
        daily[m] = tf.groupby("day").pnl.sum()
        e = np.r_[0.0, np.cumsum(p)]
        res.append({"market": m, "trades": len(p), "net $": round(float(p.sum())),
                    "net $/trade": round(float(p.mean()), 2),
                    "t": round(float(p.mean() / (p.std(ddof=1) / np.sqrt(len(p)))), 2),
                    "win %": round(100 * float((p > 0).mean()), 1),
                    "pf": round(float(p[p > 0].sum() / -p[p <= 0].sum()), 3),
                    "closed dd $": round(float((np.maximum.accumulate(e) - e).max())), "from": tf.day.min(),
                    "to": tf.day.max()})
    dd = pd.DataFrame(daily).fillna(0.0)
    for r in res:
        r["corr with NQ"] = round(float(dd[r["market"]].corr(dd["NQ"])), 2)
        r["qualifies"] = r["market"] != "NQ" and r["pf"] >= 1.2 and r["t"] >= 1.5 and r["corr with NQ"] < 0.5
    d = pd.DataFrame(res)
    d.to_csv(out, index=False)
    print(d.to_string(index=False))


if __name__ == "__main__":
    main()
