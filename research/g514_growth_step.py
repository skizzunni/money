"""G514 (docs/NINJATRADER_V38.md): Funded growth (U58 + G511's fill-in steps) with a contract per $1,400 or $1,350 of
profit instead of $1,500 (plus's $1,250 with these fill-ins lost one more development start, G507 E2). G495's
measure against the current Funded growth.

    python research/g514_growth_step.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V = {"Funded growth (G511)": FG, "P1 per $1,400": {**FG, "profit_step": 1400.0},
     "P2 per $1,350": {**FG, "profit_step": 1350.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
