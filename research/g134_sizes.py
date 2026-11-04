"""G134 (docs/NINJATRADER_V38.md), a measurement: U33's grown-phase trades by contracts and per contract.

    python research/g134_sizes.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import sys

import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

U33 = {"gap_go": True, "gap_go_exit": 595, "gap_go_max_qty": 1, "gap_go_locked_qty": 10, "gap_go_small_k": 0.0,
       "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True, "fill_min_room": 3000.0,
       "size_slip_pts": 4.0, "fill_qty2_room": 6000.0, "giveback_brake": 0.5, "size_up_to": 50,
       "after_loss_ml_locked": 1.0, "skip_checks": "780,870", "skip_checks_early": True}

S.init({}, *sys.argv[1:4])
for name in ("proxy", "index"):
    bars, first, skip = S.D[name]
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                         "gap_go_skip_month_first": name != "proxy", **U33})
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    if first:
        cfg.trail_from = first
    tf = run(bars, cfg, minutes=5).trades_frame()
    tf["before"] = tf.pnl.cumsum().shift(1, fill_value=0.0)
    g = tf[tf.before >= 10000].copy()
    g["gap"] = g.reason.str.startswith("Gap")
    g["bucket"] = pd.cut(g.qty, [0, 1, 2, 4, 8, 16, 60])
    g["per_c"] = g.pnl / g.qty
    print(name, len(g))
    print(g.groupby(["gap", "bucket"], observed=True).agg(n=("pnl", "size"), sum=("pnl", "sum"), mean=("pnl", "mean"),
                                                          per_c=("per_c", "mean")).round().to_string(), flush=True)
