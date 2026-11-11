"""G447 (docs/NINJATRADER_V38.md): U58 with its calm-stretch entry lines at 0.7 or 0.9 noise (U58 0.8, G421 / G422).
G415's fresh starts, then G372's development / unseen starts (G386's runner).

    python research/g447_calm_width.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, calm lines 0.7": {**U58, "entry_k_regime": 0.7},
     "U58, calm lines 0.9": {**U58, "entry_k_regime": 0.9}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
