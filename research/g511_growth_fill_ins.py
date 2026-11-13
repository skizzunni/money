"""G511 (docs/NINJATRADER_V38.md): G506's F2 fill-ins (2 MNQ from $3,500 above the floor, 3 from $6,000) and E2
($4,000 / $6,500) in Funded growth (U58, what the user runs) instead of plus. G495's measure against U58.

    python research/g511_growth_fill_ins.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

GR = {**U58, "giveback_brake": 0.25}
V = {"U58 (Funded growth)": GR, "U58 + F2 $3,500 / $6,000": {**GR, "fill_qty2_room": 3500.0, "fill_qty3_room": 6000.0},
     "U58 + E2 $4,000 / $6,500": {**GR, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
