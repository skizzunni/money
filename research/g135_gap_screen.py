"""G135 (docs/NINJATRADER_V38.md): the gap trade's trigger and size re-checked on U33, the chart's execution.

    python research/g135_gap_screen.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

U33 = {"gap_go": True, "gap_go_exit": 595, "gap_go_max_qty": 1, "gap_go_locked_qty": 10, "gap_go_small_k": 0.0,
       "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True, "fill_min_room": 3000.0,
       "size_slip_pts": 4.0, "fill_qty2_room": 6000.0, "giveback_brake": 0.5, "size_up_to": 50,
       "after_loss_ml_locked": 1.0, "skip_checks": "780,870", "skip_checks_early": True}
VARIANTS = [{}, {"gap_go_k": 0.6}, {"gap_go_k": 0.75}, {"gap_go_k": 1.0}, {"gap_go_locked_qty": 5},
            {"gap_go_locked_qty": 15}, {"gap_go_drive_k": 0.7}, {"gap_go_small_k": 0.2}]


def one(k: int) -> dict:
    out = {"k": k, **VARIANTS[k]}
    for name, (bars, first, skip) in S.D.items():
        if name == "win":
            continue
        cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                             "gap_go_skip_month_first": name != "proxy", **U33, **VARIANTS[k]})
        if isinstance(skip, str):
            cfg.skip_dates, cfg.fed_dates = skip, ""
        if first:
            cfg.trail_from = first
        tf = run(bars, cfg, minutes=5).trades_frame()
        if first:
            tf = tf[tf.entry_time >= pd.Timestamp(first, tz="America/New_York")]
        dayp = tf.groupby(tf.exit_time.dt.date).pnl.sum()
        out[f"{name} net"] = round(float(tf.pnl.sum()))
        out[f"{name} d1000"] = int((dayp <= -1000).sum())
    return out


if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(one, range(len(VARIANTS))):
            print(json.dumps(r), flush=True)
