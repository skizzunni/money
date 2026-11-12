"""G493 (docs/NINJATRADER_V38.md): Funded green days (G481) with a loser limit: days with 4 or more trades end green
11-34% of the time (G489), so their later trades mostly add to the loss. M1 no new entries after 2 losing trades today
(max_losers 2), M2 after 3 (U58: no limit). G415's fresh starts (green traded days), then G372's development / unseen.

    python research/g493_green_days_losers.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

GD = {**U58, "giveback_brake": 0.25, "day_stop_late_from": 660, "day_stop_late": 1.0}
V = {"Funded green days (G481)": GD, "M1 2 losers a day": {**GD, "max_losers": 2},
     "M2 3 losers a day": {**GD, "max_losers": 3}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
