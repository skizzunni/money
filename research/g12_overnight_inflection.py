"""G12 (docs/NINJATRADER_V38.md): the overnight "inflection", a sweep of the Asian range, then a reversal.

    python research/g12_overnight_inflection.py <nsx1m_scaled.pkl> <nq1m_scaled.pkl> [out.csv]

Rules are in the doc, fixed before running. Per 1 MNQ ($2 a point), $1.24 fees, 2 ticks of slippage per fill.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

TICK, PV, FEES, SLIP = 0.25, 2.0, 1.24, 0.5  # SLIP: 2 ticks, in points


def day_trades(bars: pd.DataFrame) -> pd.DataFrame:
    t = bars.index.tz_convert("America/New_York")
    mins = t.hour * 60 + t.minute
    # the session day: bars from 18:00 belong to the next day's session
    day = (t + pd.to_timedelta(np.where(mins >= 18 * 60, 1, 0), unit="D")).date
    o, h, low, c = (bars[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    out = []
    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    ends = np.r_[starts[1:], len(day)]
    for a, b in zip(starts, ends, strict=True):
        m = mins[a:b]
        asia = (m >= 18 * 60) | (m < 3 * 60)
        if asia.sum() < 300:  # a holiday or a gap: no proper Asian session
            continue
        hi, lo = h[a:b][asia].max(), low[a:b][asia].min()
        win = np.flatnonzero((m >= 3 * 60) & (m <= 9 * 60 + 25)) + a
        close_i = np.flatnonzero(m == 15 * 60 + 59)
        if not len(win) or not len(close_i):
            continue
        last = close_i[0] + a
        trade = None
        for i in win:
            for d, level, swept in ((1, lo, low[i] < lo), (-1, hi, h[i] > hi)):
                if not swept:
                    continue
                ext = low[i] if d > 0 else h[i]
                for j in range(i, min(i + 5, last)):
                    ext = min(ext, low[j]) if d > 0 else max(ext, h[j])
                    if (c[j] > level) if d > 0 else (c[j] < level):
                        trade = (d, j + 1, ext - d * TICK)
                        break
                if trade:
                    break
            if trade:
                break
        if not trade:
            continue
        d, e, stop = trade
        entry = o[e] + d * SLIP
        risk = d * (entry - stop)
        if not 2.0 <= risk <= 30.0:
            continue
        exit_px, why = c[last] - d * SLIP, "16:00"
        for k in range(e, last + 1):
            if (low[k] <= stop) if d > 0 else (h[k] >= stop):
                fill = min(o[k], stop) if d > 0 else max(o[k], stop)
                exit_px, why = fill - d * SLIP, "stop"
                break
        pnl = d * (exit_px - entry) * PV - FEES
        out.append({"day": pd.Timestamp(day[a]), "side": d, "entry": entry, "stop": stop, "risk pts": risk,
                    "exit": exit_px, "why": why, "pnl": pnl, "R": pnl / (risk * PV + FEES)})
    return pd.DataFrame(out)


def stats(tf: pd.DataFrame, days: int, label: str) -> dict:
    p = tf.pnl.to_numpy()
    daily = np.zeros(days)
    daily[: len(p)] = p  # one trade a day at most: the other days are $0
    t = daily.mean() / daily.std(ddof=1) * np.sqrt(days) if days > 1 and daily.std() > 0 else float("nan")
    return {"set": label, "trades": len(p), "win %": round(100 * float((p > 0).mean()), 1),
            "$ / trade": round(float(p.mean()), 2), "$ / day": round(float(daily.mean()), 2),
            "t": round(float(t), 2), "avg R": round(float(tf.R.mean()), 3), "best R": round(float(tf.R.max()), 1),
            "stopped %": round(100 * float((tf.why == "stop").mean()), 1),
            "avg risk pts": round(float(tf["risk pts"].mean()), 1)}


def main() -> None:
    rows = []
    for path, sets in ((sys.argv[1], (("index 2011-2018", "2011-01-01", "2019-01-01"),
                                      ("index 2019-2022", "2019-01-01", "2023-01-01"),
                                      ("index 2023-Sep 2026", "2023-01-01", "2026-10-01"))),
                       (sys.argv[2], (("NQ 2015-2025", "2015-01-01", "2025-08-01"),))):
        tf = day_trades(pd.read_pickle(path))
        for label, a, b in sets:
            x = tf[(tf.day >= a) & (tf.day < b)]
            n_days = len(pd.bdate_range(a, min(pd.Timestamp(b), tf.day.max() + pd.Timedelta(days=1))))
            rows.append(stats(x, n_days, label))
            print(rows[-1], flush=True)
    if len(sys.argv) > 3:
        pd.DataFrame(rows).to_csv(sys.argv[3], index=False)


if __name__ == "__main__":
    main()
