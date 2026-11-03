"""G60 (docs/NINJATRADER_V38.md), stage 2: the day bot (Funded growth, 5-minute, the chart's execution) plus gap and go
at 1 MNQ on the same account: the days traded, the net, and the room above the $2,000 end-of-day trailing floor.

    python research/g60_combined.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import sys

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

S.init({}, *sys.argv[1:4])
for name in ("proxy", "nq", "index"):
    bars, first, skip = S.D[name]
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60})
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    if first:
        cfg.trail_from = first
    tf = run(bars, cfg, minutes=5).trades_frame()
    if first:
        tf = tf[tf.entry_time >= pd.Timestamp(first, tz="America/New_York")]
    bot = tf.groupby(tf.exit_time.dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")).pnl.sum()
    src = {"proxy": None, "nq": "nq", "index": "index"}[name]
    if src is None:
        continue
    gg = pd.read_csv(f"verification/noise_v2/g60_gap_go_{src}.csv").groupby("day").pnl.sum()
    t = bars.index.tz_convert("America/New_York")
    sess = sorted(set(t[(t.hour == 9) & (t.minute == 30)].strftime("%Y-%m-%d")))
    days = pd.DataFrame(index=sess).assign(bot=bot, gap=gg).fillna(0.0)

    def floor_room(pl):
        e = np.r_[0.0, np.cumsum(pl)]
        peak = np.maximum.accumulate(e)
        return float((e - np.minimum(peak - 2000.0, 0.0)).min())

    both = days.bot + days.gap
    print({"set": name, "sessions": len(days),
           "bot: days traded %": round(100 * float((days.bot != 0).mean()), 1),
           "bot + gap: days traded %": round(100 * float(((days.bot != 0) | (days.gap != 0)).mean()), 1),
           "bot net $": round(float(days.bot.sum())), "gap net $": round(float(days.gap.sum())),
           "together $": round(float(both.sum())), "bot lowest room $": round(floor_room(days.bot)),
           "together lowest room $": round(floor_room(both)), "worst day together $": round(float(both.min()))},
          flush=True)
