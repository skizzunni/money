"""G499 (docs/NINJATRADER_V38.md): G498's sprint start with a defence, so fewer accounts are lost: while the room above
the trailing floor is under sprint_low_room, the sprint takes 1 MNQ. L1 2 MNQ x 20 sessions; L2 3 MNQ x 20 sessions
with 1 MNQ under $1,500 of room; L3 4 MNQ x 10 sessions with 1 MNQ under $1,500. G495's measure.

    python research/g499_plus_safe_sprint.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

P = {**U58, "giveback_brake": 0.25, "profit_step": 1250.0}
LOW = {"sprint_low_room": 1500.0, "sprint_low_qty": 1}
V = {"Funded growth plus": P, "L1 2 MNQ x 20": {**P, "sprint_qty": 2, "sprint_days": 20},
     "L2 3 MNQ x 20, 1 under $1,500": {**P, "sprint_qty": 3, "sprint_days": 20, **LOW},
     "L3 4 MNQ x 10, 1 under $1,500": {**P, "sprint_qty": 4, "sprint_days": 10, **LOW}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
