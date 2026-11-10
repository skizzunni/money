"""G424 (docs/NINJATRADER_V38.md): U58 sized up faster: a contract more per $1,200 or $1,000 of profit (U58 $1,500), and
the fast steps ($650) from $6,000 instead of $9,000. G415's fresh starts, then G372's development / unseen starts.

    python research/g424_u58_steps.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, +1 per $1,200": {**U58, "profit_step": 1200.0},
     "U58, +1 per $1,000": {**U58, "profit_step": 1000.0},
     "U58, fast steps from $6,000": {**U58, "profit_step_fast_from": 6000.0}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
