"""G220 (docs/NINJATRADER_V38.md): 30 random combinations of the exit settings around U44; G195's runner (the chart's execution on the window, NQ and the index).

    python research/g209_grown_search.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
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
SPACE = {"take_profit": [1.75, 2.25, 2.5], "lock_at": [0.25, 0.3, 0.45], "lock_plus": [1.0, 5.0],
         "time_stop": [30, 40, 50, 60], "late_lock_from": [840, 900], "time_lock": [30, 60]}
rng = random.Random(220)
G.VARIANTS = [{}]
while len(G.VARIANTS) < 31:
    v = {k: rng.choice(c) for k, c in SPACE.items() if rng.random() < 0.35}
    if v and v not in G.VARIANTS:
        G.VARIANTS.append(v)

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(G.one, [(k, ["proxy", "nq", "index"]) for k in range(len(G.VARIANTS))]):
            print(json.dumps(r), flush=True)
