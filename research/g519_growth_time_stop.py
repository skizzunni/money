"""G519 (docs/NINJATRADER_V38.md): Funded growth (G511) with the time stop at S1 35 or S2 60 minutes (now 45; G446
kept 45 on U58 by $ a session, before G511 and the $25K measure). G495's measure against the current Funded growth.

    python research/g519_growth_time_stop.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V = {"Funded growth (G511)": FG, "S1 time stop 35": {**FG, "time_stop": 35}, "S2 time stop 60": {**FG, "time_stop": 60}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
