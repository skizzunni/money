"""G144 (docs/NINJATRADER_V38.md), a measurement: U34's weekly P/L by the account's profit at the week's start.

    python research/g122_weekly.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import sys

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

U34 = {"gap_go": True, "gap_go_exit": 595, "gap_go_max_qty": 1, "gap_go_locked_qty": 10, "gap_go_small_k": 0.0,
       "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True, "fill_min_room": 3000.0,
       "size_slip_pts": 4.0, "fill_qty2_room": 6000.0, "giveback_brake": 0.5, "size_up_to": 50,
       "after_loss_ml_locked": 1.0, "skip_checks": "780,870", "skip_checks_early": True,
       "profit_step_fast": 750.0}
BANDS = [(-1e9, 10000), (10000, 30000), (30000, 75000), (75000, 1e12)]

S.init({}, *sys.argv[1:4])
rows = []
for name, (bars, first, skip) in S.D.items():
    if name == "win":
        continue
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                         "gap_go_skip_month_first": name != "proxy", **U34})
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    if first:
        cfg.trail_from = first
    tf = run(bars, cfg, minutes=5).trades_frame()
    if first:
        tf = tf[tf.entry_time >= pd.Timestamp(first, tz="America/New_York")]
    t = bars.index.tz_convert("America/New_York")
    t = t[t >= pd.Timestamp(first, tz="America/New_York")] if first else t
    weeks = pd.Series(0.0, index=pd.Index(sorted({d.to_period("W-FRI") for d in t.normalize().unique()})))
    wk = tf.groupby(tf.exit_time.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.to_period("W-FRI")).pnl.sum()
    weeks = weeks.add(wk, fill_value=0.0)
    start = weeks.cumsum().shift(1, fill_value=0.0)  # the profit at each week's start
    for lo, hi in BANDS:
        w = weeks[(start >= lo) & (start < hi)]
        if len(w):
            rows.append({"set": name, "profit at the week's start": f"{lo:,.0f}..{hi:,.0f}", "weeks": len(w),
                         "average week $": round(float(w.mean())), "median week $": round(float(w.median())),
                         "weeks >= $3,000 %": round(100 * float((w >= 3000).mean()), 1),
                         "weeks < 0 %": round(100 * float((w < 0).mean()), 1)})
    print(pd.DataFrame([r for r in rows if r["set"] == name]).to_string(index=False), flush=True)
pd.DataFrame(rows).to_csv("verification/noise_v2/g144_weekly_u34.csv", index=False)
_ = np
