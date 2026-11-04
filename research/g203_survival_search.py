"""G203 (docs/NINJATRADER_V38.md): 40 random combinations of the survival settings around U41, on the 263 starts on the
1st. Writes one VARIANT_JSON per line (tag, json) for g35_start_dates.py.

    python research/g203_survival_search.py <U41 JS json file>
"""
import json
import random
import sys

SPACE = {"giveback_brake": [0.4, 0.6, 0.7], "fill_min_room": [2000.0, 3000.0, 3500.0],
         "early_daily_loss": [500.0, 600.0, 750.0], "early_ml": [150.0, 170.0], "profit_step": [1250.0, 1750.0, 2000.0],
         "size_slip_pts": [4.0, 6.0, 8.0], "max_losers": [2, 3], "skip_checks": ["780", "780,870,900", "750,780,870"],
         "lock_at": [0.3, 0.45], "take_profit": [1.75, 2.25], "time_stop": [45, 90], "trend_n": [40, 75],
         "calm_k": [0.6, 0.8], "big_day_k": [1.3, 1.7], "range_pos_min": [0.6, 0.7], "gap_go_k": [0.4, 0.6, 0.75],
         "fill_qty2_room": [5000.0, 8000.0], "after_loss_ml_mult5": [0.9, 1.1]}
base = json.load(open(sys.argv[1]))
rng = random.Random(203)
seen = []
while len(seen) < 40:
    v = {k: rng.choice(c) for k, c in SPACE.items() if rng.random() < 0.25}
    if v and v not in seen:
        seen.append(v)
for i, v in enumerate(seen, 1):
    print(f"k{i}", json.dumps({**base, **v}))
