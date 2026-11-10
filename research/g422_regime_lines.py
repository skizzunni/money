"""G422 (docs/NINJATRADER_V38.md): G421's C (every check, no range filter, no loser limit) with entry lines at 0.8 noise
only in calm markets (the last 10 sessions' average range below the last 60's) or only in wild ones; and U48 with the
same. G415's fresh starts, then G372's development / unseen starts (G386's runner).

    python research/g422_regime_lines.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g421_trade_more import C

V = {"U48": {}, "C": C,
     "C, lines 0.8 when calm": {**C, "entry_k_regime": 0.8, "regime_calm": True},
     "C, lines 0.8 when wild": {**C, "entry_k_regime": 0.8, "regime_calm": False},
     "U48, lines 0.8 when calm": {"entry_k_regime": 0.8, "regime_calm": True},
     "U48, lines 0.8 when wild": {"entry_k_regime": 0.8, "regime_calm": False}}

if __name__ == "__main__":
    if sys.argv.pop(5) == "fresh":
        F.VARIANTS.clear()
        F.VARIANTS.update(V)
        F.main()
    else:
        R.VARIANTS.clear()
        R.VARIANTS.update(V)
        R.main()
