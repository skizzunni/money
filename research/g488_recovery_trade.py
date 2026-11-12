"""G488 (docs/NINJATRADER_V38.md): a recovery trade inside Funded green days (G481): the trade after a losing trade
takes a nearer take-profit, so a red morning more often turns green: R1 after_loss_tp 0.75, R2 1.0 noise units
(U58 2.0), R3 R1 with twice the contracts (after_loss_qty_div 0.5; still within the day's budget and the floor).
G415's fresh starts (green traded days), then G372's development / unseen starts.

    python research/g488_recovery_trade.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

GD = {**U58, "giveback_brake": 0.25, "day_stop_late_from": 660, "day_stop_late": 1.0}
V = {"Funded green days (G481)": GD, "R1 after a loser target 0.75": {**GD, "after_loss_tp": 0.75},
     "R2 after a loser target 1.0": {**GD, "after_loss_tp": 1.0},
     "R3 R1 with twice the contracts": {**GD, "after_loss_tp": 0.75, "after_loss_qty_div": 0.5}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
