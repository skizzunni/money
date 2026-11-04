"""G145 (docs/NINJATRADER_V38.md): 24 random combinations of the growth-phase settings around U34; G135's screen.

    python research/g145_search.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

G.U33 = {**G.U33, "profit_step_fast": 750.0}  # U34
rng = random.Random(145)
G.VARIANTS = [{}] + [{"profit_step": float(rng.choice([1250, 1500, 1750])),
                      "profit_step_fast": float(rng.choice([600, 750, 900])),
                      "profit_step_fast_from": float(rng.choice([8000, 10000, 12000])),
                      "gap_go_locked_qty": rng.choice([8, 10, 12]),
                      "fill_qty2_room": float(rng.choice([5000, 6000, 7000])),
                      "giveback_brake": rng.choice([0.4, 0.5, 0.6]),
                      "fill_min_room": float(rng.choice([2500, 3000, 3500]))} for _ in range(23)]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps(r), flush=True)
