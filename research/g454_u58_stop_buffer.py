"""G454 (docs/NINJATRADER_V38.md): U58 with the stop buffer at 0.18 or 0.30 (U58 0.24). G415's fresh starts, then
G372's development / unseen starts (G386's runner).

    python research/g454_u58_stop_buffer.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, stop buffer 0.18": {**U58, "stop_buffer": 0.18},
     "U58, stop buffer 0.30": {**U58, "stop_buffer": 0.30}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
