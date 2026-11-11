"""G457 (docs/NINJATRADER_V38.md): U58 on the funded account without the gap-and-go trade (gap_go off; its fill-ins
that need it go with it). G415's fresh starts, then G372's development / unseen starts (G386's runner).

    python research/g457_u58_no_gap_trade.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58 without the gap trade": {**U58, "gap_go": False}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
