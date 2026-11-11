"""G460 (docs/NINJATRADER_V38.md): U58 with its calm stretch judged against the last 30 or 60 sessions' average range
(calm_long; U58 40), for both the calm-day filter and the narrow calm-stretch lines. G415's fresh starts, then G372's
development / unseen starts (G386's runner).

    python research/g460_u58_calm_window.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, calm against 30 sessions": {**U58, "calm_long": 30},
     "U58, calm against 60 sessions": {**U58, "calm_long": 60}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
