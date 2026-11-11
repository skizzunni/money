"""G446 (docs/NINJATRADER_V38.md): U58 with its time stop at 30 or 60 minutes (U58 45, from G204). G415's fresh starts,
then G372's development / unseen starts (G386's runner).

    python research/g446_u58_time_stop.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, time stop 30": {**U58, "time_stop": 30}, "U58, time stop 60": {**U58, "time_stop": 60}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
