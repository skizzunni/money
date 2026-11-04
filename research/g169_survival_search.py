"""G169 (docs/NINJATRADER_V38.md): 20 random combinations of the survival settings around U37, on 263 monthly starts.

    python research/g169_survival_search.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
Prints one line per combination: its settings and the lost-or-frozen count (NQ + index).
"""
import json
import os
import random
import re
import subprocess
import sys

U34 = {"gap_go": True, "gap_go_skip_month_first": True, "gap_go_max_qty": 1, "gap_go_locked_qty": 10,
       "gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
       "fill_min_room": 3000.0, "size_slip_pts": 4.0, "fill_qty2_room": 6000.0, "giveback_brake": 0.5,
       "after_loss_ml_locked": 1.0, "size_up_to": 50, "skip_checks": "780,870", "skip_checks_early": True,
       "profit_step_fast": 750.0, "after_loss_ml_mult5": 1.0}  # U37
rng = random.Random(169)
COMBOS = [{"profit_step": float(rng.choice([1500, 1750, 2000])),
           "size_slip_pts": rng.choice([3.0, 4.0, 5.0, 6.0]),
           "giveback_brake": rng.choice([0.45, 0.5, 0.55]),
           "fill_min_room": float(rng.choice([2500, 3000, 3500])),
           "skip_checks": rng.choice(["780,870", "870", "780"])} for _ in range(20)]

if __name__ == "__main__":
    for k, c in enumerate(COMBOS):
        env = {**os.environ, "START_FREQ": "MS", "VARIANT_JSON": json.dumps({**U34, **c}), "VARIANT_TAG": f"g169_{k}"}
        r = subprocess.run([sys.executable, "research/g35_start_dates.py", *sys.argv[1:4], "json"], env=env,
                           capture_output=True, text=True)
        dead = [int(m) for m in re.findall(r"dead \(lost or frozen\) (\d+)", r.stdout)]
        med = [int(m) for m in re.findall(r"median net (-?\d+)", r.stdout)]
        print(json.dumps({"k": k, **c, "dead": sum(dead), "dead by set": dead, "medians": med}), flush=True)
