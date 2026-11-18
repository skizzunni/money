"""G520 (docs/V4_SEARCH.md): Funded growth against "Funded growth v4" (v4.1: the lock at 0.75, the stop 0.5 noise units
out, entry lines 0.9, $250 a trade, 3 losers a day) on G495's measure (+$25,000 within 12 months of a fresh 50K start).

    python research/g520_v41_reach_25k.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V41 = {**FG, "lock_at": 0.75, "stop_buffer": 0.5, "entry_k": 0.9, "max_loss_per_trade": 250.0, "max_losers": 3}
V = {"Funded growth (G511)": FG, "A lock 0.75 + 3 losers": {**FG, "lock_at": 0.75, "max_losers": 3},
     "B A + stop 0.5": {**FG, "lock_at": 0.75, "max_losers": 3, "stop_buffer": 0.5},
     "C A + entry 0.9": {**FG, "lock_at": 0.75, "max_losers": 3, "entry_k": 0.9},
     "D A + $250": {**FG, "lock_at": 0.75, "max_losers": 3, "max_loss_per_trade": 250.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
