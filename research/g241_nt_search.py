"""G241 / G242 (docs/NINJATRADER_V38.md): 10,000 random combinations around U44, screened in NinjaTrader's execution (as
g69_days.py with NT_EXEC=1) on the window, NQ and the index. Resumable: rows already in the output file are skipped.

    python research/g241_nt_search.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file> <U44 J json> <output file>
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


def with_1600(bars: pd.DataFrame, m: int) -> pd.DataFrame:
    """A 16:00 bar at the last price where a session's data stops at 16:00 (as research/g69_days.py)."""
    t = bars.index.tz_convert("America/New_York")
    mins = t.hour * 60 + t.minute
    last = (mins + m == 960) & ~pd.Series(mins == 960).shift(-1, fill_value=False).to_numpy()
    add = bars[last].copy()
    add.index = add.index + pd.Timedelta(minutes=m)
    for k in ("open", "high", "low"):
        add[k] = add["close"]
    return pd.concat([bars, add]).sort_index()

SPACE = {
    "lookback": [12, 13, 15, 16], "entry_k": [0.95, 1.05, 1.1], "range_pos_min": [0.65, 0.68, 0.72, 0.75],
    "calm_k": [0.6, 0.65, 0.75, 0.8], "big_day_k": [1.3, 1.4, 1.6, 1.7], "squeeze_min": [15.0, 18.0, 22.0, 25.0],
    "trend_n": [40, 45, 55, 60, 75], "last_entry_end": [870, 930], "skip_checks": ["780", "870", "750,780,870", ""],
    "take_profit": [1.75, 1.9, 2.1, 2.25], "lock_at": [0.3, 0.33, 0.38, 0.4], "lock_plus": [1.0, 2.0, 3.5, 5.0],
    "time_stop": [35, 40, 50, 55], "time_lock": [30, 45, 60], "late_lock_from": [840, 870, 900],
    "max_loss_per_trade": [175.0, 180.0, 195.0, 200.0],
    "profit_step": [1400.0, 1450.0, 1550.0, 1600.0], "profit_step_fast": [600.0, 625.0, 675.0, 700.0],
    "profit_step_fast_from": [7000.0, 7500.0, 8500.0, 9000.0], "size_slip_pts": [4.0, 4.5, 5.5, 6.0],
    "budget_frac": [0.95, 0.98], "early_daily_loss": [650.0, 700.0, 800.0], "max_losers": [2, 4],
    "giveback_brake": [0.45, 0.55], "fill_min_room": [2250.0, 2750.0], "after_loss_ml_mult5": [0.95, 1.05],
    "after_loss_ml_locked": [0.95, 1.05],
    "gap_go_k": [0.55, 0.65, 0.7], "gap_go_k_locked": [0.55, 0.65], "gap_go_locked_qty": [8, 9],
    "gap_go_drive_k": [0.5, 0.55, 0.65, 0.7], "fill_qty2_room": [3500.0, 4500.0, 5000.0],
    "fill_qty3_room": [7000.0, 7500.0, 8500.0, 9000.0], "gap_go_be": [0.75, 1.0, 1.5],
}
rng = random.Random(int(os.environ.get("SEED", "241")))  # G242: SEED=242 around U45
VARIANTS = [{}]
seen = {"{}"}
while len(VARIANTS) < 10001:
    keys = rng.sample(sorted(SPACE), rng.choice([1, 2, 2, 3, 3, 4, 5]))
    v = {k: rng.choice(SPACE[k]) for k in keys}
    key = json.dumps(v, sort_keys=True)
    if key not in seen:
        seen.add(key)
        VARIANTS.append(v)
BASE: dict = {}
WINDOW_FIRST = float(os.environ.get("WINDOW_FIRST", "0"))  # the base's window net: screen the window first (G244 on)


def one(k: int) -> dict:
    out = {"k": k, **VARIANTS[k]}
    for name in ("proxy", "nq", "index"):
        bars, first, skip = S.D[name]
        cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                             "gap_go": True, "gap_go_skip_month_first": name != "proxy", "gap_go_exit": 595,
                             "gap_go_max_qty": 1, "gap_go_locked_qty": 3, **BASE, **VARIANTS[k]})
        cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
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
        if WINDOW_FIRST and k and name == "proxy" and not (out["proxy net"] > WINDOW_FIRST and out["proxy d1000"] == 0
                                                           and out["proxy floor"] == 0):
            break  # it can't pass stage 1: NQ and the index are skipped (the outcome is the same, about 5x faster)
    return out


if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    S.D = {k: (with_1600(b, S.MIN[0]), first, skip) for k, (b, first, skip) in S.D.items() if k != "win"}
    BASE.update(json.load(open(sys.argv[4])))
    path = sys.argv[5]
    done = set()
    if os.path.exists(path):
        done = {json.loads(line)["k"] for line in open(path) if line.startswith("{")}
    todo = [k for k in range(len(VARIANTS)) if k not in done]
    with ProcessPoolExecutor(4) as ex, open(path, "a") as f:
        for r in ex.map(one, todo, chunksize=2):
            f.write(json.dumps(r) + "\n")
            f.flush()
