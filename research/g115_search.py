"""G115 (docs/NINJATRADER_V38.md): 32 random combinations of nine settings around U29, the chart's execution, 5-minute.

    python research/g115_search.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

U29 = {"gap_go": True, "gap_go_exit": 595, "gap_go_max_qty": 1, "gap_go_locked_qty": 10, "gap_go_small_k": 0.0,
       "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True, "fill_min_room": 3000.0,
       "size_slip_pts": 4.0, "fill_qty2_room": 6000.0, "giveback_brake": 0.5, "size_up_to": 20}


def combos(n: int = 32) -> list[dict]:
    rng = random.Random(115)
    out = []
    for _ in range(n):
        out.append({"lock_at": round(rng.uniform(0.28, 0.45), 2), "lock_plus": round(rng.uniform(1.5, 4.0) * 4) / 4,
                    "take_profit": round(rng.uniform(1.8, 2.4), 2), "stop_buffer": round(rng.uniform(0.20, 0.28), 2),
                    "time_stop": rng.choice([50, 55, 60, 65, 70, 75]),
                    "fill_min_room": float(rng.choice([2500, 3000, 3500, 4000])),
                    "fill_qty2_room": float(rng.choice([5000, 6000, 7000, 8000])),
                    "gap_go_locked_qty": rng.choice([8, 9, 10, 11, 12]),
                    "giveback_brake": rng.choice([0.4, 0.5, 0.6])})
    return out


def one(k: int) -> dict:
    kw = combos()[k]
    out = {"k": k, **kw}
    for name, (bars, first, skip) in S.D.items():
        if name == "win":
            continue
        cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                             "gap_go_skip_month_first": name != "proxy", **U29, **kw})
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
        for r in ex.map(one, range(32)):
            print(json.dumps(r), flush=True)
    _ = np  # numpy kept for the shared imports
