"""G426 (docs/NINJATRADER_V38.md): U58 with its calm-stretch filter (no trades when the last 10 sessions' average range
is under calm_k x the last 40's; U58 0.7) off or at 0.6. G415's fresh starts, then G372's development / unseen starts.

    python research/g426_u58_calm_filter.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, calm filter off": {**U58, "calm_k": 0.0}, "U58, calm filter 0.6": {**U58, "calm_k": 0.6}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
