"""G177 (docs/NINJATRADER_V38.md): 23 random combinations of the growth-phase sizing settings around U38; G135's screen.

    python research/g177_search.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

G.U33 = {**G.U33, "profit_step_fast": 750.0, "after_loss_ml_mult5": 1.0, "size_slip_pts": 5.0}  # U38
rng = random.Random(177)
G.VARIANTS = [{}] + [{"profit_step_fast": float(rng.choice([600, 700, 750, 850])),
                      "profit_step_fast_from": float(rng.choice([8000, 10000, 12000, 15000])),
                      "fill_qty2_room": float(rng.choice([5000, 6000, 7000])),
                      "gap_go_locked_qty": rng.choice([9, 10, 11]),
                      "gap_go_drive_k": rng.choice([0.4, 0.5, 0.6])} for _ in range(23)]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps(r), flush=True)
