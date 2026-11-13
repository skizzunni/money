"""G497 (docs/NINJATRADER_V38.md): Funded growth plus toward +$25,000 a year with the two changes that made more money
in the green-days rounds: R1 the gap trade's stop halfway from the 09:30 open to its close (gap_go_stop_frac 0.5; G494
S2: +29% unseen), R2 calm_k 0.8 (G485 D1 / G492), R3 both. G495's measure.

    python research/g497_plus_gap_stop.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

P = {**U58, "giveback_brake": 0.25, "profit_step": 1250.0}
V = {"Funded growth plus": P, "R1 gap stop halfway": {**P, "gap_go_stop_frac": 0.5},
     "R2 calm 0.8": {**P, "calm_k": 0.8}, "R3 both": {**P, "gap_go_stop_frac": 0.5, "calm_k": 0.8}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
