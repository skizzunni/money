"""G535 (docs/NINJATRADER_V38.md): the user trades a fixed 3 MNQ from now on (2026-11-23). Funded growth at 3 MNQ with
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
F3 = {**FG, "qty": 3, "profit_step": 0.0, "size_up_to": 3}
V = {"Funded growth (G511, 1 MNQ growing)": FG,
     "T1 3 MNQ, $562.50 a trade": {**F3, "max_loss_per_trade": 562.5},
     "T2 3 MNQ, $375 a trade": {**F3, "max_loss_per_trade": 375.0},
     "T3 3 MNQ, $562.50, $600 a day": {**F3, "max_loss_per_trade": 562.5, "early_daily_loss": 600.0, "daily_loss_limit": 600.0},
     "T4 3 MNQ, $375, 2 losers a day": {**F3, "max_loss_per_trade": 375.0, "max_losers": 2},
     "T5 3 MNQ, $375, lock 0.25": {**F3, "max_loss_per_trade": 375.0, "lock_at": 0.25}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
