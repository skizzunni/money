"""G450 (docs/NINJATRADER_V38.md): U58 on the funded account with its take-profit at 1.5 or 2.5 noise units (U58 2.0).
G415's fresh starts, then G372's development / unseen starts (G386's runner).

    python research/g450_u58_take_profit.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, take-profit 1.5": {**U58, "take_profit": 1.5},
     "U58, take-profit 2.5": {**U58, "take_profit": 2.5}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
