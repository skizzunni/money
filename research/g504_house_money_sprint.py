"""G504 (docs/NINJATRADER_V38.md): a sprint start that sizes up only once ahead ("house money"): the first 20 sessions
(until +$3,000) at sprint_qty contracts, and at sprint_push_qty while the profit since the start is at least
sprint_push_min; 1 MNQ while under $1,500 above the floor (G499's defence). H1 2 MNQ, 4 once +$500; H2 1 MNQ, 3 once
+$500; H3 2 MNQ, 4 once +$1,000. G495's measure against Funded growth plus.

    python research/g504_house_money_sprint.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

P = {**U58, "giveback_brake": 0.25, "profit_step": 1250.0}
S = {**P, "sprint_days": 20, "sprint_push_from": 1, "sprint_low_room": 1500.0, "sprint_low_qty": 1}
V = {"Funded growth plus": P,
     "H1 2 MNQ, 4 once +$500": {**S, "sprint_qty": 2, "sprint_push_qty": 4, "sprint_push_min": 500.0},
     "H2 1 MNQ, 3 once +$500": {**S, "sprint_qty": 1, "sprint_push_qty": 3, "sprint_push_min": 500.0},
     "H3 2 MNQ, 4 once +$1,000": {**S, "sprint_qty": 2, "sprint_push_qty": 4, "sprint_push_min": 1000.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
