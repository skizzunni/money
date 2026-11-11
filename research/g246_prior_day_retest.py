"""G246 (docs/NINJATRADER_V38.md): G245 with the prior session's high and low as the levels and a 2:1 target. A
measurement.

5-minute RTH bars, 1 MNQ, $1.24 commission and a tick each way per round trip:
  levels: the prior RTH session's high (resistance) and low (support), each traded once a day;
  breakout, retest and entry as G245 (a close beyond the level from 09:45; within 12 bars a bar back to the level that
    closes beyond it again; enter at that close, 09:45-15:30, one trade at a time);
  exit: a stop 11 points and a target 22 points at 24,500 (2:1), scaled with the price; both in one bar counts the
    stop; out at the 15:55 bar's close otherwise.
Per set: trades, net per MNQ, win %, years up; split by whether U47 trades that day.

    PACK_JSON='{...}' python research/g246_prior_day_retest.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import os
import sys

import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

S.init({}, *sys.argv[1:4])
PACK = json.loads(os.environ["PACK_JSON"])
NY = "America/New_York"
COST = 2 * 0.62 + 2 * 0.25 * 2.0
SL, TP, WAIT = 11 / 24500, 22 / 24500, 12
PRIOR = None


def day_trades(g: pd.DataFrame) -> list[float]:
    gm = (g.index.hour * 60 + g.index.minute).to_numpy()
    o, h, lo, c = (g[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(g)
    levels = [[1, PRIOR[0], 0, -1], [-1, PRIOR[1], 0, -1]] if PRIOR else []  # the prior session's high and low
    out, pos = [], None
    for i in range(n):
        if pos is not None:  # manage the open trade on this bar
            side, entry, stop, tgt = pos
            hit_s = lo[i] <= stop if side > 0 else h[i] >= stop
            hit_t = h[i] >= tgt if side > 0 else lo[i] <= tgt
            if hit_s or hit_t or gm[i] >= 955:
                px = stop if hit_s else tgt if hit_t else c[i]
                out.append(side * (px - entry) * 2.0 - COST)
                pos = None
            continue
        if gm[i] < 585 or gm[i] > 930:
            continue
        for lv in levels:
            side, p, st, b = lv
            if st == 0 and (c[i] > p if side > 0 else c[i] < p):
                lv[2], lv[3] = 1, i
            elif st == 1 and i > b:
                if i - b > WAIT:
                    lv[2] = 2
                elif (lo[i] <= p and c[i] > p) if side > 0 else (h[i] >= p and c[i] < p):
                    lv[2] = 2
                    e = c[i]
                    pos = (side, e, e * (1 - side * SL), e * (1 + side * TP))
                    break
    if pos is not None:
        side, entry, _, _ = pos
        out.append(side * (c[-1] - entry) * 2.0 - COST)
    return out


for name, (bars, first, skip) in S.D.items():
    if name == "win":
        continue
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                         "gap_go_skip_month_first": name != "proxy", **PACK})
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    if first:
        cfg.trail_from = first
    tf = run(bars, cfg, minutes=5).trades_frame()
    traded = set(tf.entry_time.dt.tz_convert(NY).dt.date)
    b = bars.copy()
    b.index = b.index.tz_convert(NY)
    if first:
        b = b[b.index >= pd.Timestamp(first, tz=NY)]
    m = b.index.hour * 60 + b.index.minute
    rth = b[(m >= 570) & (m < 960)]
    rows = []
    PRIOR = None
    for day, g in rth.groupby(rth.index.date):
        for p in day_trades(g):
            rows.append({"y": day.year, "u47": day in traded, "pnl": p})
        PRIOR = (g.high.max(), g.low.min())
    df = pd.DataFrame(rows)
    yr = df.groupby("y").pnl.sum().round(0)
    idle = df[~df.u47]
    yi = idle.groupby("y").pnl.sum().round(0)
    print(f"\n{name}: {len(df)} trades, net ${df.pnl.sum():,.0f} per MNQ, win {100 * (df.pnl > 0).mean():.1f}%, "
          f"years up {(yr > 0).sum()} of {len(yr)}; U47 days ${df[df.u47].pnl.sum():,.0f} ({int(df.u47.sum())}), "
          f"idle days ${idle.pnl.sum():,.0f} ({len(idle)}, years up {(yi > 0).sum()} of {len(yi)})")
    print(pd.DataFrame({"net": yr, "U47 days": df[df.u47].groupby("y").pnl.sum().round(0),
        "idle days": yi}).to_string(),
          flush=True)
