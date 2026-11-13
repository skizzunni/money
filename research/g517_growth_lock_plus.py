"""G517 (docs/NINJATRADER_V38.md): Funded growth (G511) with the lock's cushion bigger: once a trade is 0.35 max
losses in profit its stop goes to the entry + lock_plus points (now 2.5). K1 5 points, K2 10 points. G495's measure
against the current Funded growth.

    python research/g517_growth_lock_plus.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V = {"Funded growth (G511)": FG, "K1 lock + 5 points": {**FG, "lock_plus": 5.0},
     "K2 lock + 10 points": {**FG, "lock_plus": 10.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
