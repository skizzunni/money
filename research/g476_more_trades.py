"""G476 (docs/NINJATRADER_V38.md): more trades on the 50K. U58 (brake 0.25) against T1 entry checks every 15 minutes
(check_step 15), T2 the 0.8 entry lines every day (entry_k 0.8; U58 only on calm stretches), T3 both. G415's fresh
starts, then G372's development / unseen starts (G386's runner).

    python research/g476_more_trades.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

B = {**U58, "giveback_brake": 0.25}
V = {"U58 (brake 0.25)": B, "T1 checks every 15 min": {**B, "check_step": 15},
     "T2 0.8 lines every day": {**B, "entry_k": 0.8}, "T3 both": {**B, "check_step": 15, "entry_k": 0.8}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
