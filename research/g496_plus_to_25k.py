"""G496 (docs/NINJATRADER_V38.md): Funded growth plus (U58, +1 MNQ per $1,250) pushed toward +$25,000 in a fresh
50K's first year: Q1 + a $1,500 day budget once the floor stops, Q2 + $1,250, Q3 + faster steps (+1 per $400 from
$5,000), Q4 no giveback brake. G495's measure (share of starts at +$25,000 in 12 months, median, lost).

    python research/g496_plus_to_25k.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

P = {**U58, "giveback_brake": 0.25, "profit_step": 1250.0}
V = {"Funded growth plus": P, "Q1 + $1,500 day once locked": {**P, "daily_loss_limit": 1500.0},
     "Q2 + $1,250 day once locked": {**P, "daily_loss_limit": 1250.0},
     "Q3 + 1 per $400 from $5,000": {**P, "profit_step_fast": 400.0, "profit_step_fast_from": 5000.0},
     "Q4 no brake": {**P, "giveback_brake": 0.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
