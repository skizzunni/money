"""G14 (docs/NINJATRADER_V38.md): a liquidity sweep of the previous session's high/low and an inversion fair value
gap on 1-minute bars, in the evening session (19:00-02:00 New York), 2R target, flat by 09:25.

    python research/g14_sweep_ifvg.py <nsx1m_scaled.pkl> <nq1m_scaled.pkl> [out.csv]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from g12_overnight_inflection import FEES, PV, SLIP, TICK, stats


def night_trades(bars: pd.DataFrame) -> pd.DataFrame:
    t = bars.index.tz_convert("America/New_York")
    mins = np.asarray(t.hour * 60 + t.minute)
    dates = np.asarray(t.date)
    o, h, low, c = (bars[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    rth = (mins >= 570) & (mins < 960)
    sess = pd.DataFrame({"d": dates[rth], "h": h[rth], "l": low[rth]}).groupby("d")
    sess = sess.agg(hi=("h", "max"), lo=("l", "min")).sort_index()
    out = []
    starts = np.flatnonzero(mins == 19 * 60)  # each night's 19:00 bar
    for s in starts:
        d0 = dates[s]
        k0 = sess.index.searchsorted(d0, side="right") - 1  # the latest regular session on or before (Sunday: Friday)
        if k0 < 0 or (pd.Timestamp(d0) - pd.Timestamp(sess.index[k0])).days > 4:
            continue
        hi, lo = sess.iloc[k0]["hi"], sess.iloc[k0]["lo"]
        # the night: from 19:00 to the 09:25 bar of the next morning (at most 15 hours of bars)
        end = s
        while end + 1 < len(mins) and end - s < 900 and not (mins[end] == 9 * 60 + 25 and dates[end] != d0):
            end += 1
        if mins[end] != 9 * 60 + 25:
            continue
        trade = None
        sweep = {1: None, -1: None}
        for i in range(s, end):
            if mins[i] >= 2 * 60 and mins[i] < 19 * 60:  # entries until 02:00
                break
            for d in (1, -1):
                if sweep[d] is None and ((low[i] < lo) if d > 0 else (h[i] > hi)):
                    sweep[d] = i
                sw = sweep[d]
                if sw is None or i - sw > 30 or i < 2:
                    continue
                gap = None  # the most recent opposite fair value gap, formed from 30 bars before the sweep to i-1
                for k in range(i - 1, max(sw - 30, s + 2) - 1, -1):
                    if d > 0 and h[k] < low[k - 2]:
                        gap = low[k - 2]
                        break
                    if d < 0 and low[k] > h[k - 2]:
                        gap = h[k - 2]
                        break
                if gap is None or not ((c[i] > gap) if d > 0 else (c[i] < gap)):
                    continue
                ext = low[sw:i + 1].min() if d > 0 else h[sw:i + 1].max()
                trade = (d, i + 1, ext - d * TICK)
                break
            if trade:
                break
        if not trade:
            continue
        d, e, stop = trade
        entry = o[e] + d * SLIP
        risk = d * (entry - stop)
        if not 3.0 <= risk <= 40.0:
            continue
        tp = entry + d * 2 * risk
        exit_px, why = c[end] - d * SLIP, "09:25"
        for k in range(e, end + 1):
            if (low[k] <= stop) if d > 0 else (h[k] >= stop):
                fill = min(o[k], stop) if d > 0 else max(o[k], stop)
                exit_px, why = fill - d * SLIP, "stop"
                break
            if (h[k] >= tp) if d > 0 else (low[k] <= tp):
                exit_px, why = tp, "target"
                break
        pnl = d * (exit_px - entry) * PV - FEES
        out.append({"day": pd.Timestamp(d0), "side": d, "entry": entry, "stop": stop, "risk pts": risk,
                    "exit": exit_px, "why": why, "pnl": pnl, "R": pnl / (risk * PV + FEES)})
    return pd.DataFrame(out)


def main() -> None:
    rows = []
    for path, sets in ((sys.argv[1], (("index 2011-2018", "2011-01-01", "2019-01-01"),
                                      ("index 2019-2022", "2019-01-01", "2023-01-01"),
                                      ("index 2023-Sep 2026", "2023-01-01", "2026-10-01"))),
                       (sys.argv[2], (("NQ 2015-2025", "2015-01-01", "2025-08-01"),))):
        tf = night_trades(pd.read_pickle(path))
        for label, a, b in sets:
            x = tf[(tf.day >= a) & (tf.day < b)]
            n_days = len(pd.bdate_range(a, min(pd.Timestamp(b), tf.day.max() + pd.Timedelta(days=1))))
            r = stats(x, n_days, label)
            r["target %"] = round(100 * float((x.why == "target").mean()), 1)
            rows.append(r)
            print(r, flush=True)
    if len(sys.argv) > 3:
        pd.DataFrame(rows).to_csv(sys.argv[3], index=False)


if __name__ == "__main__":
    main()
