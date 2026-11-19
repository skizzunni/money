"""G529 (docs/NINJATRADER_V38.md): Funded growth with a small day lock: once today's P/L (closed + open) reaches
day_lock_at, the stop goes no lower than where today's P/L is day_lock_keep. On G495's measure.

    python research/g529_small_day_lock.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V41 = {**FG, "lock_at": 0.75, "stop_buffer": 0.5, "entry_k": 0.9, "max_loss_per_trade": 250.0, "max_losers": 3}
V = {"Funded growth (G511)": FG, "L1 lock $300 keep $100": {**FG, "day_lock_at": 300.0, "day_lock_keep": 100.0},
     "L2 lock $500 keep $200": {**FG, "day_lock_at": 500.0, "day_lock_keep": 200.0},
     "L3 lock $400 keep $0": {**FG, "day_lock_at": 400.0, "day_lock_keep": 0.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
