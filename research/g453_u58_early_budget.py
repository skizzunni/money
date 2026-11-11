"""G453 (docs/NINJATRADER_V38.md): U58 on the funded account with its early day budget at $500 or $1,000 (U58 $750).
G415's fresh starts, then G372's development / unseen starts (G386's runner).

    python research/g453_u58_early_budget.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, early budget $500": {**U58, "early_daily_loss": 500.0},
     "U58, early budget $1,000": {**U58, "early_daily_loss": 1000.0}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
