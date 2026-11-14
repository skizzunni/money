"""G518 (docs/NINJATRADER_V38.md): Funded growth (G511) with the take-profit at T1 1.75 or T2 2.25 noise units (now
2.0; G450 tested 1.5 / 2.5 on U58 by $ a session, before G511 and before the $25K measure). G495's measure against the
current Funded growth.

    python research/g518_growth_target.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V = {"Funded growth (G511)": FG, "T1 target 1.75": {**FG, "take_profit": 1.75},
     "T2 target 2.25": {**FG, "take_profit": 2.25}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
