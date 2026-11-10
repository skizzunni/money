"""G423 (docs/NINJATRADER_V38.md): U58 (G422) with wider entry lines on stretches that are not calm: 1.1 or 1.2 x the
noise area. G415's fresh starts, then G372's development / unseen starts (G386's runner).

    python research/g423_wide_when_wild.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F

U58 = {"skip_checks": "", "range_pos_min": 0.0, "max_losers": 0, "entry_k_regime": 0.8}
V = {"U48": {}, "U58": U58, "U58, lines 1.1 when not calm": {**U58, "entry_k_wild": 1.1},
     "U58, lines 1.2 when not calm": {**U58, "entry_k_wild": 1.2}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
