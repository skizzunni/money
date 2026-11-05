"""G245 (docs/NINJATRADER_V38.md): support and resistance, breakout and retest (the user's video, 2026-11-05). A measurement.

5-minute RTH bars, 1 MNQ, $1.24 commission and a tick each way per round trip:
  levels: a pivot high (low) is a bar whose high (low) is at least (at most) the 3 bars on each side; it is known only
    3 bars later. A resistance (support) is a confirmed pivot high (low) with an earlier pivot high (low) of the same
    session within 0.05% of its price (the market turned there at least twice). Each level is traded once.
  breakout: a close above a resistance (below a support), from 09:45;
  retest: within the next 12 bars, a bar whose low (high) comes back to the level and closes back beyond it: enter long
    (short) at that close, 09:45-15:30, one trade at a time;
  exit: a stop 11 points and a target 12.5 points at 24,500 (the video's $132 / $150 on 6 MNQ), scaled with the price
    (0.0449% / 0.0510%); both in one bar counts the stop; out at the 15:55 bar's close otherwise.
Per set: trades, net per MNQ, win %, years up; split by whether U47 trades that day.

    PACK_JSON='{...}' python research/g245_sr_retest.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
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
SL, TP, TOL, K, WAIT = 11 / 24500, 12.5 / 24500, 0.0005, 3, 12


def day_trades(g: pd.DataFrame) -> list[float]:
    gm = (g.index.hour * 60 + g.index.minute).to_numpy()
    o, h, lo, c = (g[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(g)
    piv_h, piv_l = [], []  # (bar, price) confirmed pivots
    levels = []  # [side, price, state, broke_at]; side +1 resistance, -1 support; state 0 new, 1 broken, 2 used
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
        j = i - K  # a pivot at j is known at i
        if j >= K:
            if h[j] >= h[j - K:j + K + 1].max():
                if any(abs(p - h[j]) <= TOL * h[j] for _, p in piv_h):
                    levels.append([1, h[j], 0, -1])
                piv_h.append((j, h[j]))
            if lo[j] <= lo[j - K:j + K + 1].min():
                if any(abs(p - lo[j]) <= TOL * lo[j] for _, p in piv_l):
                    levels.append([-1, lo[j], 0, -1])
                piv_l.append((j, lo[j]))
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
    for day, g in rth.groupby(rth.index.date):
        for p in day_trades(g):
            rows.append({"y": day.year, "u47": day in traded, "pnl": p})
    df = pd.DataFrame(rows)
    yr = df.groupby("y").pnl.sum().round(0)
    idle = df[~df.u47]
    yi = idle.groupby("y").pnl.sum().round(0)
    print(f"\n{name}: {len(df)} trades, net ${df.pnl.sum():,.0f} per MNQ, win {100 * (df.pnl > 0).mean():.1f}%, "
          f"years up {(yr > 0).sum()} of {len(yr)}; U47 days ${df[df.u47].pnl.sum():,.0f} ({int(df.u47.sum())}), "
          f"idle days ${idle.pnl.sum():,.0f} ({len(idle)}, years up {(yi > 0).sum()} of {len(yi)})")
    print(pd.DataFrame({"net": yr, "U47 days": df[df.u47].groupby("y").pnl.sum().round(0), "idle days": yi}).to_string(),
          flush=True)
