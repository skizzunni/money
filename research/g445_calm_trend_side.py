"""G445 (docs/NINJATRADER_V38.md): U58 with its narrow calm-stretch entry lines (0.8) only on the side of the 45-session
trend (regime_trend_side). G415's fresh starts, then G372's development / unseen starts.

    python research/g445_calm_trend_side.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, narrow lines on the trend side only": {**U58, "regime_trend_side": True}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
