"""G538 (docs/NINJATRADER_V38.md): the live setup without the gap trade on gaps over 3x / 2x the 14-session average
(those gap trades: NQ -$35 / $7 a trade, the index $1 / $4, against $18-50 / $12-33 below 2x). On G495's measure.

    python research/g538_big_gaps.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V41 = {**FG, "lock_at": 0.75, "stop_buffer": 0.5, "entry_k": 0.9, "max_loss_per_trade": 250.0, "max_losers": 3}
LIVE = {**FG, "gap_go_cap": True, "size_up_to": 3}  # what the user runs: U59 and the cap at 3 (G535)
V = {"Live (Funded growth, gap cap, at most 3)": LIVE, "X3 no gap trade over 3x": {**LIVE, "gap_go_max_k": 3.0},
     "X2 no gap trade over 2x": {**LIVE, "gap_go_max_k": 2.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
