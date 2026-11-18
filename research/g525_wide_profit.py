"""G525 (docs/NINJATRADER_V38.md): a wide search for more profit on the 50K at no more accounts lost. 48 random
combinations of Funded growth's profit levers (the contract step, the lock, losers a day, the take-profit, the time
stop, the giveback brake) on G495's measure. A pass: lost no more than Funded growth on both sets (development 3.2%,
unseen 1.7%) and a higher 12-month median on both.

    python research/g525_wide_profit.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import json
import random
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
SPACE = {"profit_step": [1250.0, 1400.0, 1500.0, 1750.0], "lock_at": [0.3, 0.35, 0.5, 0.75],
         "max_losers": [0, 3, 4], "take_profit": [1.75, 2.0, 2.25], "time_stop": [40, 45, 60],
         "giveback_brake": [0.2, 0.25, 0.35]}
rng = random.Random(525)
V = {"Funded growth (G511)": FG}
seen = set()
while len(V) < 49:
    v = {k: rng.choice(x) for k, x in SPACE.items()}
    key = json.dumps(v, sort_keys=True)
    if key in seen or all(FG.get(k, None) == x for k, x in v.items()):
        continue
    seen.add(key)
    V["v" + str(len(V)) + " " + key] = {**FG, **v}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 400)
    pd.set_option("display.max_colwidth", 200)
    pd.set_option("display.max_rows", 200)
    M.main()
