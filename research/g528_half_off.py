"""G528 (docs/NINJATRADER_V38.md): Funded growth taking half the position off at 1.0 / 1.5 / 2.0 R (R: the max loss a
contract; the rest keeps the stop, lock, target and 16:00 exit), on G495's measure.

    python research/g528_half_off.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V41 = {**FG, "lock_at": 0.75, "stop_buffer": 0.5, "entry_k": 0.9, "max_loss_per_trade": 250.0, "max_losers": 3}
V = {"Funded growth (G511)": FG, "P1 half off at 1.0R": {**FG, "partial_at": 1.0},
     "P2 half off at 1.5R": {**FG, "partial_at": 1.5}, "P3 half off at 2.0R": {**FG, "partial_at": 2.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
