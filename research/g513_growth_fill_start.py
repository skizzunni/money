"""G513 (docs/NINJATRADER_V38.md): Funded growth (U58 + G511's fill-in steps) with its 1-MNQ fill-ins starting at
another distance above the floor: now $2,750 (G241). C1 $2,250, C2 $3,250. G495's measure against the current
Funded growth.

    python research/g513_growth_fill_start.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V = {"Funded growth (G511)": FG, "C1 fill-ins from $2,250": {**FG, "fill_min_room": 2250.0},
     "C2 fill-ins from $3,250": {**FG, "fill_min_room": 3250.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
