"""G524 (docs/NINJATRADER_V38.md): G520's "lock 0.75 + 3 losers" (more profit, more accounts lost) with more early
protection: the gentle start (no contract steps until the floor stops), a $600 day budget until then, a 0.35 brake.

    python research/g524_protected_lock.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V41 = {**FG, "lock_at": 0.75, "stop_buffer": 0.5, "entry_k": 0.9, "max_loss_per_trade": 250.0, "max_losers": 3}
A = {**FG, "lock_at": 0.75, "max_losers": 3}
V = {"Funded growth (G511)": FG, "A lock 0.75 + 3 losers": A, "B A + gentle start": {**A, "steps_after_lock": True},
     "C A + $600 early day": {**A, "early_daily_loss": 600.0}, "D A + brake 0.35": {**A, "giveback_brake": 0.35},
     "E A + gentle + $600": {**A, "steps_after_lock": True, "early_daily_loss": 600.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
