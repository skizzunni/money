"""G500 (docs/NINJATRADER_V38.md): G499's L3 sprint (4 MNQ for the first 10 sessions, 1 MNQ under $1,500 of room) with
a stronger defence, to lose fewer accounts: M1 the gap trade at 1 MNQ during the sprint (sprint_gap_qty 1), M2 1 MNQ
under $1,800 of room, M3 both. G495's measure.

    python research/g500_sprint_defence.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

P = {**U58, "giveback_brake": 0.25, "profit_step": 1250.0}
L3 = {**P, "sprint_qty": 4, "sprint_days": 10, "sprint_low_room": 1500.0, "sprint_low_qty": 1}
V = {"Funded growth plus": P, "L3 (G499)": L3, "M1 L3 + gap 1 MNQ in the sprint": {**L3, "sprint_gap_qty": 1},
     "M2 L3, 1 MNQ under $1,800": {**L3, "sprint_low_room": 1800.0},
     "M3 both": {**L3, "sprint_gap_qty": 1, "sprint_low_room": 1800.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
