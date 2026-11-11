"""G449 (docs/NINJATRADER_V38.md): U58 with the trade lock later, at 0.45 or 0.55 max losses (U58 0.35). G415's fresh
starts, then G372's development / unseen starts (G386's runner).

    python research/g449_u58_later_lock.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, lock at 0.45": {**U58, "lock_at": 0.45}, "U58, lock at 0.55": {**U58, "lock_at": 0.55}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
