"""G498 (docs/NINJATRADER_V38.md): Funded growth plus with a sprint start, so a fresh 50K gets past its trailing
floor (and onto bigger sizes) sooner: the first sprint_days sessions at sprint_qty contracts until +$3,000 (cut to the
day's budget and the room above the floor), then plus's sizing. K1 3 MNQ for 10 sessions, K2 4 MNQ for 10, K3 3 MNQ
for 20. G495's measure.

    python research/g498_plus_sprint_start.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

P = {**U58, "giveback_brake": 0.25, "profit_step": 1250.0}
V = {"Funded growth plus": P, "K1 3 MNQ x 10 sessions": {**P, "sprint_qty": 3, "sprint_days": 10},
     "K2 4 MNQ x 10 sessions": {**P, "sprint_qty": 4, "sprint_days": 10},
     "K3 3 MNQ x 20 sessions": {**P, "sprint_qty": 3, "sprint_days": 20}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
