"""G195/G196 (docs/NINJATRADER_V38.md): a wide random search around U41, 300 combinations of about 30 settings.

G195 (ORDER=window): stage 1 every combination on the window (the chart's execution), stage 2 the 15 best on the window
(no -$1,000 day, at least U41's net) on NQ and the index. G196 (ORDER=long, SEED=196): stage 1 on NQ and the index,
stage 2 the 15 best there (both at least U41's, no -$1,000 day) on the window. The output lists both stages; stage 3 (NinjaTrader's execution and the 526
starts) is run separately for those passing stage 2.

    python research/g195_wide.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

U41 = {"gap_go": True, "gap_go_exit": 595, "gap_go_max_qty": 1, "gap_go_locked_qty": 10, "gap_go_small_k": 0.0,
       "trend_small": True, "gap_go_drive_k": 0.6, "fill_after_lock": True, "fill_min_room": 2500.0,
       "size_slip_pts": 5.0, "fill_qty2_room": 6000.0, "giveback_brake": 0.5, "size_up_to": 50,
       "after_loss_ml_locked": 1.0, "skip_checks": "780,870", "skip_checks_early": True, "profit_step_fast": 750.0,
       "after_loss_ml_mult5": 1.0, "gap_skip_braked": True}
SPACE = {"lookback": [10, 12, 16, 20], "take_profit": [1.5, 1.75, 2.25, 2.5, 3.0], "lock_at": [0.25, 0.3, 0.45, 0.5],
         "lock_plus": [1.0, 5.0, 10.0], "entry_k": [0.9, 1.1, 1.2, 1.3], "max_loss_per_trade": [150.0, 170.0, 210.0],
         "big_day_k": [1.3, 1.7, 2.0], "calm_k": [0.6, 0.8, 0.9], "range_pos_min": [0.55, 0.6, 0.7, 0.75],
         "trend_n": [30, 40, 75, 100], "time_stop": [30, 45, 90, 120, 0], "last_entry_end": [870, 930],
         "squeeze_min": [10.0, 15.0, 25.0, 30.0], "max_losers": [2, 3, 4], "profit_step": [1250.0, 1750.0, 2000.0],
         "profit_step_fast": [600.0, 900.0], "giveback_brake": [0.4, 0.6, 0.7], "gap_go_k": [0.4, 0.6, 0.75],
         "gap_go_locked_qty": [5, 8, 12, 15], "gap_go_be": [0.5, 1.0], "partial_at": [1.0, 1.5],
         "side_cooldown": [1, 2], "time_lock": [30, 60], "late_lock_from": [840, 900], "short_mult": [0.5, 1.5],
         "fill_min_room": [2000.0, 3000.0], "size_slip_pts": [3.0, 4.0, 6.0], "big_day_against_tp": [0.5, 1.0],
         "after_loss_tp": [1.0, 1.5], "day_keep": [0.25, 0.5]}
rng = random.Random(int(os.environ.get("SEED", "195")))
LONG = os.environ.get("ORDER", "window") == "long"
VARIANTS = [{}]
while len(VARIANTS) < 300:
    v = {k: rng.choice(c) for k, c in SPACE.items() if rng.random() < 0.25}
    if v and v not in VARIANTS:
        VARIANTS.append(v)


def one(job) -> dict:
    k, sets = job
    out = {"k": k, **VARIANTS[k]}
    for name in sets:
        bars, first, skip = S.D[name]
        cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                             "gap_go_skip_month_first": name != "proxy", **U41, **VARIANTS[k]})
        if isinstance(skip, str):
            cfg.skip_dates, cfg.fed_dates = skip, ""
        if first:
            cfg.trail_from = first
        tf = run(bars, cfg, minutes=5).trades_frame()
        if first:
            tf = tf[tf.entry_time >= pd.Timestamp(first, tz="America/New_York")]
        dayp = tf.groupby(tf.exit_time.dt.date).pnl.sum()
        S.TRAIL = cfg.trail_dd
        out[f"{name} net"] = round(float(tf.pnl.sum()))
        out[f"{name} d1000"] = int((dayp <= -1000).sum())
        out[f"{name} floor"] = int(S.trail_stats(name, tf)[f"{name} tb0"])
    return out


if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        first, second = (["nq", "index"], ["proxy"]) if LONG else (["proxy"], ["nq", "index"])
        st1 = list(ex.map(one, [(k, first) for k in range(len(VARIANTS))], chunksize=4))
        for r in st1:
            print("S1", json.dumps(r), flush=True)
        b = st1[0]
        ok = [r for r in st1[1:] if all(r[f"{n} d1000"] == 0 and r[f"{n} floor"] == 0 and r[f"{n} net"] >= b[f"{n} net"]
                                        for n in first)]
        top = sorted(ok, key=lambda r: -sum(r[f"{n} net"] / b[f"{n} net"] for n in first))[:15]
        for r in ex.map(one, [(k, second) for k in [0] + [t["k"] for t in top]]):
            print("S2", json.dumps(r), flush=True)
