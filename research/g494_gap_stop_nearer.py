"""G494 (docs/NINJATRADER_V38.md): the gap trade's stop nearer, inside Funded green days (G481): it sits at the 09:30
open (G489: 60% of the red days start with it hit); here gap_go_stop_frac of the way from the 09:30 open toward the
09:30 bar's close: S1 0.25, S2 0.5. G415's fresh starts (green traded days), then G372's development / unseen.

    python research/g494_gap_stop_nearer.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

GD = {**U58, "giveback_brake": 0.25, "day_stop_late_from": 660, "day_stop_late": 1.0}
V = {"Funded green days (G481)": GD, "S1 gap stop 0.25 nearer": {**GD, "gap_go_stop_frac": 0.25},
     "S2 gap stop 0.5 nearer": {**GD, "gap_go_stop_frac": 0.5}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
