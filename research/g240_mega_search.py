"""G240 (docs/NINJATRADER_V38.md): 1,000 random combinations around U44, each on the window, NQ and the index (the
chart's execution); G195's runner. Each line is printed as it finishes, so a stopped run keeps its results.

    python research/g240_mega_search.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file> [first k] [last k]
"""
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor

import g195_wide as G
import v24_scan as S

G.U41 = {**G.U41, "max_losers": 3, "early_daily_loss": 750.0, "time_stop": 45, "range_pos_min": 0.7,
         "gap_go_k": 0.6, "profit_step_fast": 650.0, "profit_step_fast_from": 8000.0,
         "fill_qty3_room": 8000.0, "fill_qty2_room": 4000.0, "size_up_to": 75}  # U44
SPACE = {
    # entries and filters
    "lookback": [12, 13, 15, 16], "entry_k": [0.95, 1.05, 1.1], "range_pos_min": [0.65, 0.68, 0.72, 0.75],
    "calm_k": [0.6, 0.65, 0.75, 0.8], "big_day_k": [1.3, 1.4, 1.6, 1.7], "squeeze_min": [15.0, 18.0, 22.0, 25.0],
    "trend_n": [40, 45, 55, 60, 75], "last_entry_end": [870, 930], "skip_checks": ["780", "870", "750,780,870", ""],
    # exits
    "take_profit": [1.75, 1.9, 2.1, 2.25], "lock_at": [0.3, 0.33, 0.38, 0.4], "lock_plus": [1.0, 2.0, 3.5, 5.0],
    "time_stop": [35, 40, 50, 55], "time_lock": [30, 45, 60], "late_lock_from": [840, 870, 900],
    "max_loss_per_trade": [175.0, 180.0, 195.0, 200.0],
    # sizing and budget
    "profit_step": [1400.0, 1450.0, 1550.0, 1600.0], "profit_step_fast": [600.0, 625.0, 675.0, 700.0],
    "profit_step_fast_from": [7000.0, 7500.0, 8500.0, 9000.0], "size_slip_pts": [4.0, 4.5, 5.5, 6.0],
    "budget_frac": [0.95, 0.98], "early_daily_loss": [650.0, 700.0, 800.0], "max_losers": [2, 4],
    # survival
    "giveback_brake": [0.45, 0.55], "fill_min_room": [2250.0, 2750.0], "after_loss_ml_mult5": [0.95, 1.05],
    "after_loss_ml_locked": [0.95, 1.05],
    # gap slot and fill-ins
    "gap_go_k": [0.55, 0.65, 0.7], "gap_go_k_locked": [0.55, 0.65], "gap_go_locked_qty": [8, 9],
    "gap_go_drive_k": [0.5, 0.55, 0.65, 0.7], "fill_qty2_room": [3500.0, 4500.0, 5000.0],
    "fill_qty3_room": [7000.0, 7500.0, 8500.0, 9000.0], "gap_go_be": [0.75, 1.0, 1.5],
}
rng = random.Random(240)
G.VARIANTS = [{}]
while len(G.VARIANTS) < 1001:
    n = rng.choice([1, 2, 2, 3, 3, 4, 5])
    keys = rng.sample(sorted(SPACE), n)
    v = {k: rng.choice(SPACE[k]) for k in keys}
    if v not in G.VARIANTS:
        G.VARIANTS.append(v)

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    lo = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    hi = int(sys.argv[5]) if len(sys.argv) > 5 else len(G.VARIANTS) - 1
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(G.one, [(k, ["proxy", "nq", "index"]) for k in range(lo, hi + 1)]):
            print(json.dumps(r), flush=True)
