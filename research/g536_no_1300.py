"""G536 (docs/NINJATRADER_V38.md): the user's live setup (Funded growth, the gap cap, at most 3 MNQ) without the 13:00
check, whose entries lose on NQ 2015-2025 (-$1,891, 224 trades) and break even on the index (-$142, 306 trades) while
every other check makes money on both. On G495's measure.

    python research/g536_no_1300.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
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
V = {"Live (Funded growth, gap cap, at most 3)": LIVE, "R1 no 13:00 check": {**LIVE, "skip_checks": "780"}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
