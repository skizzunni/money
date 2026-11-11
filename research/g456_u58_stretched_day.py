"""G456 (docs/NINJATRADER_V38.md): U58 on the funded account with no new entries once the day's range is already
1.25 or 1.5 x the last 10 sessions' average range (G360's exhaust_k). G415's fresh starts, then G372's development /
unseen starts (G386's runner).

    python research/g456_u58_stretched_day.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, no entries past 1.25x range": {**U58, "exhaust_k": 1.25},
     "U58, no entries past 1.5x range": {**U58, "exhaust_k": 1.5}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
