"""G537 (docs/NINJATRADER_V38.md): the live setup trading smaller after a losing trade (until a winner): the trade after
a loss makes half as much as the others on NQ 2015-2025 ($13 against $26, 1,093 trades) and the index ($14 against $26,
1,435), for the same risk. On G495's measure.

    python research/g537_smaller_after_loss.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
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
V = {"Live (Funded growth, gap cap, at most 3)": LIVE, "A1 1 MNQ after a loss": {**LIVE, "after_loss_qty_cap": 1},
     "A2 at most 2 after a loss": {**LIVE, "after_loss_qty_cap": 2}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
