"""G209 (docs/NINJATRADER_V38.md): 30 random combinations of the settings that act only once the floor has stopped,
around U42; G195's runner (the chart's execution on the window, NQ and the index).

    python research/g209_grown_search.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor

import g195_wide as G
import v24_scan as S

G.U41 = {**G.U41, "max_losers": 3, "early_daily_loss": 750.0, "time_stop": 45, "range_pos_min": 0.7,
         "gap_go_k": 0.6}  # U42
SPACE = {"profit_step_fast": [600.0, 700.0, 850.0], "profit_step_fast_from": [8000.0, 12000.0, 15000.0],
         "gap_go_locked_qty": [8, 12, 15], "fill_qty2_room": [5000.0, 7000.0], "fill_qty3_room": [9000.0, 12000.0],
         "gap_go_k_locked": [0.5, 0.75, 1.0], "after_loss_ml_locked": [0.9, 1.1]}
rng = random.Random(209)
G.VARIANTS = [{}]
while len(G.VARIANTS) < 31:
    v = {k: rng.choice(c) for k, c in SPACE.items() if rng.random() < 0.4}
    if v and v not in G.VARIANTS:
        G.VARIANTS.append(v)

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(G.one, [(k, ["proxy", "nq", "index"]) for k in range(len(G.VARIANTS))]):
            print(json.dumps(r), flush=True)
