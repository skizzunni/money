"""G535b (docs/NINJATRADER_V38.md): the user trades a fixed 3 MNQ from now on (2026-11-23). Funded growth at 3 MNQ with
less loss per trade and per day, on G495's measure (the floor and the day budget as the 50K's).

    python research/g535_three_contracts.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V41 = {**FG, "lock_at": 0.75, "stop_buffer": 0.5, "entry_k": 0.9, "max_loss_per_trade": 250.0, "max_losers": 3}
V = {"Funded growth (G511, 1 MNQ growing)": FG, "C3 Funded growth, at most 3 MNQ": {**FG, "size_up_to": 3},
     "C3b at most 3, 2 from $1,000": {**FG, "size_up_to": 3, "profit_step": 1000.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
