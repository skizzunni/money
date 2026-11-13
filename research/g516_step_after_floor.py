"""G516 (docs/NINJATRADER_V38.md): Funded growth (G511) at $1,500 a contract until the trailing floor stops, then a
smaller step (profit_step_locked): R1 $1,400, R2 $1,300. G514's $1,400 throughout lost one development start (the early
phase); G501's much smaller locked steps ($1,000 / $750) lost many. G495's measure against the current Funded growth.

    python research/g516_step_after_floor.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V = {"Funded growth (G511)": FG, "R1 then $1,400": {**FG, "profit_step_locked": 1400.0},
     "R2 then $1,300": {**FG, "profit_step_locked": 1300.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
