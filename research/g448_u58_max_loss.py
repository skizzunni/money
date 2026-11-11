"""G448 (docs/NINJATRADER_V38.md): U58 on the funded account with its max loss at $150 or $250 a contract (U58 $187.50).
G415's fresh starts, then G372's development / unseen starts (G386's runner).

    python research/g448_u58_max_loss.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, max loss $150": {**U58, "max_loss_per_trade": 150.0},
     "U58, max loss $250": {**U58, "max_loss_per_trade": 250.0}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
