"""G451 (docs/NINJATRADER_V38.md): U58 with its trend over the last 30 or 60 sessions (U58 45, from G241). G415's fresh
starts, then G372's development / unseen starts (G386's runner).

    python research/g451_u58_trend_len.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, trend 30 sessions": {**U58, "trend_n": 30}, "U58, trend 60 sessions": {**U58, "trend_n": 60}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
