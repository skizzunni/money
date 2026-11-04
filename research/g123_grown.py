"""G123 (docs/NINJATRADER_V38.md), a measurement: U32's trades once the account is $10,000 up.

    python research/g123_grown.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import sys

import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

U32 = {"gap_go": True, "gap_go_exit": 595, "gap_go_max_qty": 1, "gap_go_locked_qty": 10, "gap_go_small_k": 0.0,
       "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True, "fill_min_room": 3000.0,
       "size_slip_pts": 4.0, "fill_qty2_room": 6000.0, "giveback_brake": 0.5, "size_up_to": 50,
       "after_loss_ml_locked": 1.0}

S.init({}, *sys.argv[1:4])
for name in ("nq", "index"):
    bars, first, skip = S.D[name]
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                         "gap_go_skip_month_first": True, **U32})
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    tf = run(bars, cfg, minutes=5).trades_frame()
    tf["before"] = tf.pnl.cumsum().shift(1, fill_value=0.0)
    g = tf[tf.before >= 10000].copy()
    et = g.entry_time.dt.tz_convert("America/New_York")
    g["slot"] = (et.dt.hour * 60 + et.dt.minute) // 30 * 30
    g["slot"] = g.slot.map(lambda m: f"{m // 60:02d}:{m % 60:02d}")
    g["gap"] = g.reason.str.startswith("Gap")
    g["day_n"] = g.groupby(et.dt.date).cumcount() + 1
    print(name, "grown trades", len(g), "qty quantiles", g.qty.quantile([.1, .5, .9]).tolist())
    print("losers' P/L quantiles", g.pnl[g.pnl < 0].quantile([.1, .5, .9]).round().tolist())
    for col in ("slot", "gap", "day_n", "direction", "reason"):
        print(g.groupby(col).pnl.agg(["count", "sum", "mean"]).round().to_string(), "\n", flush=True)
    dayp = g.groupby(et.dt.date).pnl.sum()
    print("days", len(dayp), "mean", round(dayp.mean()), "share of days at <= -800", round((dayp <= -800).mean(), 3),
          "days >= +1500", round((dayp >= 1500).mean(), 3), flush=True)
