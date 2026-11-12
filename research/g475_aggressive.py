"""G475 (docs/NINJATRADER_V38.md): a measurement for the user, aggressive 50K funded variants of U58 (brake 0.25):
A1 no brake, +1 MNQ per $1,000, a $1,000 early day budget; A2 A1 with the take-profit at 2.5; A3 A1 starting at 2 MNQ.
G415's fresh starts, then G372's development / unseen starts (G386's runner).

    python research/g475_aggressive.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

A1 = {**U58, "giveback_brake": 0.0, "profit_step": 1000.0, "early_daily_loss": 1000.0}
V = {"U58 (brake 0.25)": {**U58, "giveback_brake": 0.25}, "A1 aggressive": A1,
     "A2 = A1 + take-profit 2.5": {**A1, "take_profit": 2.5},
     "A3 = A1 + start 2 MNQ": {**A1, "qty": 2, "max_loss_per_trade": 375.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
