"""G484 (docs/NINJATRADER_V38.md): Funded green days (G481) with more money, its green rule unchanged: P1 +1 MNQ per
$1,250 (G478), P2 no small-gap fill-in (G479 V1), P3 both. G415's fresh starts (green traded days), then G372's
development / unseen starts.

    python research/g484_green_days_more_money.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

GD = {**U58, "giveback_brake": 0.25, "day_stop_late_from": 660, "day_stop_late": 1.0}
V = {"Funded green days (G481)": GD, "P1 +1 per $1,250": {**GD, "profit_step": 1250.0},
     "P2 no small-gap fill-in": {**GD, "gap_go_small_k": -1.0},
     "P3 both": {**GD, "profit_step": 1250.0, "gap_go_small_k": -1.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
