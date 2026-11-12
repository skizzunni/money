"""G490 (docs/NINJATRADER_V38.md): the gap trade protected sooner, with a cushion, so a gap trade that went its way
ends green instead of at its stop (G489: 60% of Funded green days' red days start with a stopped gap trade). The gap
trade's stop goes to its entry + gap_go_be_plus points once a bar closes gap_go_be x its risk its way (now 1.5, + a
tick): B1 0.5 + 2.5 points, B2 0.75 + 2.5 points, B3 0.5 + a tick; inside Funded green days (G481) and B1 in U58.
G415's fresh starts (green traded days), then G372's development / unseen starts.

    python research/g490_gap_green.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

GROW = {**U58, "giveback_brake": 0.25}
GD = {**GROW, "day_stop_late_from": 660, "day_stop_late": 1.0}
B1 = {"gap_go_be": 0.5, "gap_go_be_plus": 2.5}
V = {"U58 (Funded growth)": GROW, "U58 + B1": {**GROW, **B1}, "Funded green days (G481)": GD,
     "B1 gap to +2.5 at 0.5x risk": {**GD, **B1}, "B2 gap to +2.5 at 0.75x": {**GD, "gap_go_be": 0.75,
                                                                              "gap_go_be_plus": 2.5},
     "B3 gap to +1 tick at 0.5x": {**GD, "gap_go_be": 0.5}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
