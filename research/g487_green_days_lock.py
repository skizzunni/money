"""G487 (docs/NINJATRADER_V38.md): Funded green days (G481, stop once green from 11:00) with G482's day lock, so a
morning that is up keeps its green while the trade runs: K1 lock at +$300 keeping $1, K2 lock at +$150 keeping $1.
G415's fresh starts (green traded days), then G372's development / unseen starts.

    python research/g487_green_days_lock.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

GD = {**U58, "giveback_brake": 0.25, "day_stop_late_from": 660, "day_stop_late": 1.0}
V = {"Funded green days (G481)": GD,
     "K1 + lock +$300 keep $1": {**GD, "day_lock_at": 300.0, "day_lock_keep": 1.0},
     "K2 + lock +$150 keep $1": {**GD, "day_lock_at": 150.0, "day_lock_keep": 1.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
