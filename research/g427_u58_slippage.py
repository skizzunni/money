"""G427 (docs/NINJATRADER_V38.md): U58 against U48 with one more tick of slippage on every market and stop fill (2 in
all). G415's fresh starts, then G372's development / unseen starts.

    python research/g427_u58_slippage.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U48": {}, "U58": U58, "U48, 2 ticks": {"slippage_ticks": 2}, "U58, 2 ticks": {**U58, "slippage_ticks": 2}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
