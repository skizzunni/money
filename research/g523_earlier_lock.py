"""G523 (docs/NINJATRADER_V38.md): Funded growth with an earlier lock (0.30 / 0.25 / 0.20 max losses; 0.35 now) for
more winning trades, nothing else changed, on G495's measure.

    python research/g523_earlier_lock.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V41 = {**FG, "lock_at": 0.75, "stop_buffer": 0.5, "entry_k": 0.9, "max_loss_per_trade": 250.0, "max_losers": 3}
V = {"Funded growth (G511)": FG, "lock 0.30": {**FG, "lock_at": 0.30}, "lock 0.25": {**FG, "lock_at": 0.25},
     "lock 0.20": {**FG, "lock_at": 0.20}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
