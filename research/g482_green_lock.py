"""G482 (docs/NINJATRADER_V38.md): lock the green instead of stopping. U58 (brake 0.25) and Funded green days (G481)
against the day lock at small levels (day_lock_at / day_lock_keep): L1 +$150 keep $1, L2 +$300 keep $1, L3 +$300 keep
$100, L4 L2 without the small-gap fill-in, L5 L2 + stop once green from 13:00. G415's fresh starts (green traded days),
then G372's development / unseen starts.

    python research/g482_green_lock.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

B = {**U58, "giveback_brake": 0.25}
L2 = {**B, "day_lock_at": 300.0, "day_lock_keep": 1.0}
V = {"U58 (brake 0.25)": B, "Funded green days (G481)": {**B, "day_stop_late_from": 660, "day_stop_late": 1.0},
     "L1 lock +$150 keep $1": {**B, "day_lock_at": 150.0, "day_lock_keep": 1.0}, "L2 lock +$300 keep $1": L2,
     "L3 lock +$300 keep $100": {**B, "day_lock_at": 300.0, "day_lock_keep": 100.0},
     "L4 L2, no small-gap fill-in": {**L2, "gap_go_small_k": -1.0},
     "L5 L2 + stop once green from 13:00": {**L2, "day_stop_late_from": 780, "day_stop_late": 1.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
