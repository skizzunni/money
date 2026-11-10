"""G425 (docs/NINJATRADER_V38.md): U58 with a nearer take-profit on a calm stretch (the last 10 sessions' average range
below the last 40's): 1.0 or 1.25 noise units (U58: 1.5). G415's fresh starts, then G372's development / unseen starts.

    python research/g425_calm_target.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, target 1.0 when calm": {**U58, "tp_calm": 1.0},
     "U58, target 1.25 when calm": {**U58, "tp_calm": 1.25}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
