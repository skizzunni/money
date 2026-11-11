"""G458 (docs/NINJATRADER_V38.md): U58 on the funded account without its first (10:00) or its last (15:30) entry check,
always (skip_checks_early off). G415's fresh starts, then G372's development / unseen starts (G386's runner).

    python research/g458_u58_first_last_check.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58 without the 10:00 check": {**U58, "skip_checks": "600", "skip_checks_early": False},
     "U58 without the 15:30 check": {**U58, "skip_checks": "930", "skip_checks_early": False}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
