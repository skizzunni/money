"""G147 (docs/NINJATRADER_V38.md): 23 random combinations of the exit settings around U34; G135's screen.

    python research/g147_search.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

G.U33 = {**G.U33, "profit_step_fast": 750.0}  # U34
rng = random.Random(147)
G.VARIANTS = [{}] + [{"lock_at": round(rng.uniform(0.30, 0.40), 2), "lock_plus": rng.choice([2.0, 2.25, 2.5, 2.75,
    3.0]),
                      "take_profit": round(rng.uniform(1.9, 2.15), 2), "stop_buffer": rng.choice([0.22, 0.23, 0.24,
                          0.25, 0.26]),
                      "time_stop": rng.choice([55, 60, 65]),
                      "max_loss_per_trade": rng.choice([162.5, 175.0, 187.5, 200.0])} for _ in range(23)]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps(r), flush=True)
