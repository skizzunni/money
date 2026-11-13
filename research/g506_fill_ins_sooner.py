"""G506 (docs/NINJATRADER_V38.md): Funded growth plus with the 1-MNQ fill-in trades (small gaps, drives, shorts against
the trend) sooner and bigger, for more trading days early: F1 fill-ins from $2,000 above the floor (now $2,750), F2 at
2 MNQ from $3,500 and 3 from $6,000 (now $5,000 / $8,000), F3 both. G495's measure.

    python research/g506_fill_ins_sooner.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

P = {**U58, "giveback_brake": 0.25, "profit_step": 1250.0}
F2 = {"fill_qty2_room": 3500.0, "fill_qty3_room": 6000.0}
V = {"Funded growth plus": P, "F1 fill-ins from $2,000": {**P, "fill_min_room": 2000.0},
     "F2 2 MNQ from $3,500, 3 from $6,000": {**P, **F2}, "F3 both": {**P, "fill_min_room": 2000.0, **F2}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
