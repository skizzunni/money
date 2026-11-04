"""G221 (docs/NINJATRADER_V38.md): 30 random combinations of the entry filters around U44; G195's runner (the chart's execution on the window, NQ and the index).

    python research/g221_filter_search.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
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
SPACE = {"calm_k": [0.6, 0.65, 0.75, 0.8], "big_day_k": [1.3, 1.4, 1.6, 1.7], "range_pos_min": [0.65, 0.75],
         "squeeze_min": [15.0, 25.0], "entry_k": [0.95, 1.05, 1.1], "lookback": [12, 16], "gap_go_k": [0.55, 0.7]}
rng = random.Random(221)
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
