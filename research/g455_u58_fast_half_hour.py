"""G455 (docs/NINJATRADER_V38.md): U58 on the funded account with new entries only out of a fast half hour (G362's
thrust_k 0.5 or 0.75). G415's fresh starts, then G372's development / unseen starts (G386's runner).

    python research/g455_u58_fast_half_hour.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, fast half hour 0.5": {**U58, "thrust_k": 0.5},
     "U58, fast half hour 0.75": {**U58, "thrust_k": 0.75}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
