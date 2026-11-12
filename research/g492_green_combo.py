"""G492 (docs/NINJATRADER_V38.md): the small green-day gains found so far, together, inside Funded green days (G481):
C1 G490's B2 (gap stop to entry + 2.5 points at 0.75x risk) + G485's D1 (calm_k 0.8); C2 C1 + G487's K2 (day lock at
+$150 keeping $1). G415's fresh starts (green traded days), then G372's development / unseen starts.

    python research/g492_green_combo.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

GD = {**U58, "giveback_brake": 0.25, "day_stop_late_from": 660, "day_stop_late": 1.0}
C1 = {**GD, "gap_go_be": 0.75, "gap_go_be_plus": 2.5, "calm_k": 0.8}
V = {"Funded green days (G481)": GD, "C1 B2 + calm 0.8": C1,
     "C2 C1 + day lock $150": {**C1, "day_lock_at": 150.0, "day_lock_keep": 1.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
