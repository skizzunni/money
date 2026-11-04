"""G207 (docs/NINJATRADER_V38.md): 40 random combinations of the survival settings around U42, on the 263 starts on the
1st. Writes one VARIANT_JSON per line (tag, json) for g35_start_dates.py.

    python research/g207_survival_search.py <U42 JS json file>
"""
import json
import random
import sys

SPACE = {"giveback_brake": [0.4, 0.6], "fill_min_room": [2000.0, 3000.0], "early_daily_loss": [600.0, 850.0, 0.0],
         "early_ml": [150.0, 170.0], "profit_step": [1250.0, 1750.0], "size_slip_pts": [4.0, 6.0],
         "max_losers": [2, 4, 0], "skip_checks": ["780", "780,870,900"], "lock_at": [0.3, 0.45],
         "take_profit": [1.75, 2.25], "time_stop": [30, 60, 90], "trend_n": [40, 75], "calm_k": [0.6, 0.8],
         "big_day_k": [1.3, 1.7], "range_pos_min": [0.65, 0.75], "gap_go_k": [0.5, 0.75],
         "fill_qty2_room": [5000.0, 8000.0], "after_loss_ml_mult5": [0.9, 1.1]}
base = json.load(open(sys.argv[1]))
rng = random.Random(207)
seen = []
while len(seen) < 40:
    v = {k: rng.choice(c) for k, c in SPACE.items() if rng.random() < 0.25}
    if v and v not in seen:
        seen.append(v)
for i, v in enumerate(seen, 1):
    print(f"k{i}", json.dumps({**base, **v}))
