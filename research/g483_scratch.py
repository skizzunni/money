"""G483 (docs/NINJATRADER_V38.md): scratch instead of lose. U58 (brake 0.25) and Funded green days (G481) against the
lock armed sooner with a smaller cushion: S1 lock at 0.15 max losses to entry +1 point (U58 0.35 / +2.5), S2 0.10 / +1,
S3 S1 in Funded green days. G415's fresh starts (green traded days), then G372's development / unseen starts.

    python research/g483_scratch.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

B = {**U58, "giveback_brake": 0.25}
GD = {**B, "day_stop_late_from": 660, "day_stop_late": 1.0}
V = {"U58 (brake 0.25)": B, "Funded green days (G481)": GD,
     "S1 lock 0.15, +1 point": {**B, "lock_at": 0.15, "lock_plus": 1.0},
     "S2 lock 0.10, +1 point": {**B, "lock_at": 0.10, "lock_plus": 1.0},
     "S3 S1 in Funded green days": {**GD, "lock_at": 0.15, "lock_plus": 1.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
