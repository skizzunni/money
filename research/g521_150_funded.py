"""G521 (docs/NINJATRADER_V38.md): Pine v4.3's $150 a trade on the funded account, on G495's measure: Funded growth
against $150 a trade alone and with the lock at 0.75 / 0.25 and 3 losers a day.

    python research/g521_150_funded.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V41 = {**FG, "lock_at": 0.75, "stop_buffer": 0.5, "entry_k": 0.9, "max_loss_per_trade": 250.0, "max_losers": 3}
V = {"Funded growth (G511)": FG, "E $150 a trade": {**FG, "max_loss_per_trade": 150.0},
     "F $150 + lock 0.75 + 3 losers": {**FG, "max_loss_per_trade": 150.0, "lock_at": 0.75, "max_losers": 3},
     "G $150 + 3 losers": {**FG, "max_loss_per_trade": 150.0, "max_losers": 3},
     "H $150 + lock 0.25": {**FG, "max_loss_per_trade": 150.0, "lock_at": 0.25}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
