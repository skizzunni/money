"""G38 (docs/NINJATRADER_V38.md): trapped buyers (sellers) at a new high (low) of the day, from NQ futures' volume.

    python research/g38_trapped.py <nq1m_scaled.pkl> [out.csv]

Rules are in the doc, fixed before running. Per 1 MNQ ($2 a point), $1.24 fees, 1 tick of slippage per market fill.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from g12_overnight_inflection import stats

TICK, PV, FEES, SLIP = 0.25, 2.0, 1.24, 0.25


def five_minute(path: str) -> pd.DataFrame:
    b = pd.read_pickle(path)
    b.index = b.index.tz_convert("America/New_York")
    t = b.index
    b = b[(t.hour * 60 + t.minute >= 570) & (t.hour * 60 + t.minute < 960)]  # the regular session
    return b.resample("5min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()


def trades(b: pd.DataFrame) -> pd.DataFrame:
    t = b.index
    mins = np.asarray(t.hour * 60 + t.minute)
    o, h, low, c, v = (b[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    vavg = pd.Series(v).rolling(20).mean().shift(1).to_numpy()  # the 20 bars before
    out = []
    dates = np.asarray(t.date)
    starts = np.flatnonzero(np.r_[True, dates[1:] != dates[:-1]])
    ends = np.r_[starts[1:], len(dates)]
    for a, e in zip(starts, ends, strict=True):
        if e - a < 70:  # a short session
            continue
        done = {1: False, -1: False}
        for k in range(a + 1, e - 2):
            if not 600 <= mins[k] + 5 <= 900:  # the trap bar closes 10:00-15:00
                continue
            hi, lo = h[a:k].max(), low[a:k].min()  # the day so far, before the trap bar
            rng = h[k] - low[k]
            if rng <= 0 or np.isnan(vavg[k]) or v[k] < 1.5 * vavg[k]:
                continue
            for d in (-1, 1):  # -1: trapped buyers at a new high (a short); 1: trapped sellers at a new low
                if done[d]:
                    continue
                if d < 0:
                    trap = h[k] > hi and (c[k] - low[k]) <= 0.5 * rng and (h[k] - max(o[k], c[k])) >= 0.5 * rng
                    confirm = c[k + 1] < low[k]
                else:
                    trap = low[k] < lo and (h[k] - c[k]) <= 0.5 * rng and (min(o[k], c[k]) - low[k]) >= 0.5 * rng
                    confirm = c[k + 1] > h[k]
                if not (trap and confirm):
                    continue
                done[d] = True
                en = k + 2
                entry = o[en] + d * SLIP
                stop = (h[k] + TICK) if d < 0 else (low[k] - TICK)
                risk = d * (entry - stop)
                if not 4.0 <= risk <= 40.0:
                    continue
                day_ext = low[a:en].min() if d < 0 else h[a:en].max()  # the day's low (high) at the entry
                tp = day_ext if d * (day_ext - entry) >= risk else entry + d * risk
                last = e - 1
                exit_px, why = c[last] - d * SLIP, "close"
                for j in range(en, e):
                    if (h[j] >= stop) if d < 0 else (low[j] <= stop):
                        fill = max(o[j], stop) if d < 0 else min(o[j], stop)
                        exit_px, why = fill - d * SLIP, "stop"
                        break
                    if (low[j] <= tp) if d < 0 else (h[j] >= tp):
                        exit_px, why = tp, "target"
                        break
                pnl = d * (exit_px - entry) * PV - FEES
                out.append({"day": pd.Timestamp(dates[a]), "side": d, "entry": entry, "stop": stop, "risk pts": risk,
                            "target": tp, "exit": exit_px, "why": why, "pnl": pnl, "R": pnl / (risk * PV + FEES)})
    return pd.DataFrame(out)


def main() -> None:
    tf = trades(five_minute(sys.argv[1]))
    rows = []
    for label, a, b in (("NQ 2015-2018", "2015-01-01", "2019-01-01"), ("NQ 2019-2021", "2019-01-01", "2022-01-01"),
                        ("NQ 2022-Jul 2025", "2022-01-01", "2025-08-01")):
        x = tf[(tf.day >= a) & (tf.day < b)]
        n_days = len(pd.bdate_range(a, min(pd.Timestamp(b), tf.day.max() + pd.Timedelta(days=1))))
        r = stats(x, n_days, label)
        r["target %"] = round(100 * float((x.why == "target").mean()), 1)
        r["shorts $"] = round(float(x[x.side < 0].pnl.sum()))
        r["longs $"] = round(float(x[x.side > 0].pnl.sum()))
        rows.append(r)
        print(r, flush=True)
    if len(sys.argv) > 2:
        pd.DataFrame(rows).to_csv(sys.argv[2], index=False)
        tf.to_csv(sys.argv[2].replace(".csv", "_trades.csv"), index=False)


if __name__ == "__main__":
    main()
