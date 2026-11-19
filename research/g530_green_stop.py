"""G530 (docs/NINJATRADER_V38.md): Funded growth with no new entries once today's P/L is up (or up $150) from 10:30 /
11:00 (Funded green days, G481) / 12:00 / 13:00, on G495's measure.

    python research/g530_green_stop.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V41 = {**FG, "lock_at": 0.75, "stop_buffer": 0.5, "entry_k": 0.9, "max_loss_per_trade": 250.0, "max_losers": 3}
V = {"Funded growth (G511)": FG,
     "D0 green stop from 11:00 (the mode)": {**FG, "day_stop_late_from": 660, "day_stop_late": 1.0},
     "D1 green stop from 10:30": {**FG, "day_stop_late_from": 630, "day_stop_late": 1.0},
     "D2 green stop from 12:00": {**FG, "day_stop_late_from": 720, "day_stop_late": 1.0},
     "D3 green stop from 13:00": {**FG, "day_stop_late_from": 780, "day_stop_late": 1.0},
     "D4 up $150 from 12:00": {**FG, "day_stop_late_from": 720, "day_stop_late": 150.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
