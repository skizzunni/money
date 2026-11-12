"""G491 (docs/NINJATRADER_V38.md): the gap trade out sooner, inside Funded green days (G481): gap trades that reach
their 09:55 exit win 80% of the time, the ones stopped before it all lose (G479, G489), so a shorter hold leaves less
time for the stop: X1 out at the 09:45 bar's open (gap_go_exit 585), X2 09:50 (590); and U58 + X2 for Funded growth.
G415's fresh starts (green traded days), then G372's development / unseen starts.

    python research/g491_gap_exit_green.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

GROW = {**U58, "giveback_brake": 0.25}
GD = {**GROW, "day_stop_late_from": 660, "day_stop_late": 1.0}
V = {"U58 (Funded growth)": GROW, "U58 + X2 out 09:50": {**GROW, "gap_go_exit": 590},
     "Funded green days (G481)": GD, "X1 gap out 09:45": {**GD, "gap_go_exit": 585},
     "X2 gap out 09:50": {**GD, "gap_go_exit": 590}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
