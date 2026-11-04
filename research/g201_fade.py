"""G201 (docs/NINJATRADER_V38.md): the morning fade as it could be traded. A measurement.

Every session: at 10:00 (the 09:55 bar's close), 1 MNQ against the 09:30-10:00 move; out at 16:00 (the 15:55 bar's
close) or at U41's first entry of the day at or after 10:00 (that trade's entry price), whichever first. Per MNQ after
commission and a tick each way, per year, split by whether U41 traded after 10:00 that day.

    PACK_JSON='{...}' python research/g201_fade.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
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
    et = tf.entry_time.dt.tz_convert(NY)
    bot = tf[(et.dt.hour * 60 + et.dt.minute) >= 600].assign(day=et.dt.date)
    first_entry = bot.sort_values("entry_time").groupby("day").first()
    b = bars.copy()
    b.index = b.index.tz_convert(NY)
    if first:
        b = b[b.index >= pd.Timestamp(first, tz=NY)]
    m = b.index.hour * 60 + b.index.minute
    rth = b[(m >= 570) & (m < 960)]
    rows = []
    for day, g in rth.groupby(rth.index.date):
        gm = g.index.hour * 60 + g.index.minute
        if not ((gm == 570).any() and (gm == 595).any() and (gm == 955).any()):
            continue
        o930, c1000, c1600 = g.open[gm == 570].iloc[0], g.close[gm == 595].iloc[0], g.close[gm == 955].iloc[0]
        if c1000 == o930:
            continue
        side = -1 if c1000 > o930 else 1
        traded = day in first_entry.index
        out = float(first_entry.loc[day, "entry"]) if traded else c1600
        rows.append({"y": day.year, "traded": traded, "pnl": side * (out - c1000) * 2.0 - COST})
    df = pd.DataFrame(rows)
    yr = df.groupby("y").pnl.sum().round(0)
    print(f"\n{name}: {len(df)} sessions, net ${df.pnl.sum():,.0f} per MNQ, win {100 * (df.pnl > 0).mean():.1f}%, "
          f"years up {(yr > 0).sum()} of {len(yr)}; U41 days ${df[df.traded].pnl.sum():,.0f} "
          f"({int(df.traded.sum())}), other days ${df[~df.traded].pnl.sum():,.0f} ({int((~df.traded).sum())})")
    print(pd.DataFrame({"net": yr, "U41 days": df[df.traded].groupby("y").pnl.sum().round(0),
                        "other days": df[~df.traded].groupby("y").pnl.sum().round(0)}).to_string(), flush=True)
