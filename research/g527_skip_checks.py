"""G527 (docs/NINJATRADER_V38.md): Funded growth without its weakest entry checks (11:00, 11:30, 15:00), on G495's
measure. Pass: no more accounts lost on both sets and a higher 12-month median on both.

    python research/g527_skip_checks.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V41 = {**FG, "lock_at": 0.75, "stop_buffer": 0.5, "entry_k": 0.9, "max_loss_per_trade": 250.0, "max_losers": 3}
V = {"Funded growth (G511)": FG, "S1 no 11:00 check": {**FG, "skip_checks": "660"},
     "S2 no 11:00 / 11:30": {**FG, "skip_checks": "660,690"}, "S3 no 15:00": {**FG, "skip_checks": "900"},
     "S4 no 11:00 / 15:00": {**FG, "skip_checks": "660,900"}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
