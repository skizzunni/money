"""G501 (docs/NINJATRADER_V38.md): careful before the trailing floor stops, faster after: a contract per profit_step
until the floor stops, then per profit_step_locked. N1 $1,500 then $1,000, N2 $1,500 then $750, N3 $1,250 then $750.
G495's measure against Funded growth plus ($1,250 throughout).

    python research/g501_locked_steps.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

B = {**U58, "giveback_brake": 0.25}
P = {**B, "profit_step": 1250.0}
V = {"Funded growth plus": P, "N1 $1,500 then $1,000": {**B, "profit_step": 1500.0, "profit_step_locked": 1000.0},
     "N2 $1,500 then $750": {**B, "profit_step": 1500.0, "profit_step_locked": 750.0},
     "N3 $1,250 then $750": {**P, "profit_step_locked": 750.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
