"""G160 (docs/NINJATRADER_V38.md), a measurement: U29 and U34 year by year on the index and NQ, the chart's execution.

    python research/g160_by_year.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import sys

import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

U29 = {"gap_go": True, "gap_go_exit": 595, "gap_go_max_qty": 1, "gap_go_locked_qty": 10, "gap_go_small_k": 0.0,
       "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True, "fill_min_room": 3000.0,
       "size_slip_pts": 4.0, "fill_qty2_room": 6000.0, "giveback_brake": 0.5, "size_up_to": 20}
U34 = {**U29, "size_up_to": 50, "after_loss_ml_locked": 1.0, "skip_checks": "780,870", "skip_checks_early": True,
       "profit_step_fast": 750.0}
S.init({}, *sys.argv[1:4])
rows = {}
for name in ("nq", "index"):
    bars, first, skip = S.D[name]
    for tag, extra in (("U29", U29), ("U34", U34)):
        cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                             "gap_go_skip_month_first": True, **extra})
        if isinstance(skip, str):
            cfg.skip_dates, cfg.fed_dates = skip, ""
        tf = run(bars, cfg, minutes=5).trades_frame()
        rows[(name, tag)] = tf.groupby(tf.exit_time.dt.year).pnl.sum().round()
out = pd.DataFrame(rows).fillna(0).astype(int)
out[("nq", "U34-U29")] = out[("nq", "U34")] - out[("nq", "U29")]
out[("index", "U34-U29")] = out[("index", "U34")] - out[("index", "U29")]
print(out.to_string())
out.to_csv("../verification/noise_v2/g160_by_year.csv")
