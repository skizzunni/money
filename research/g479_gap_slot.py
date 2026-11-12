"""G479 (docs/NINJATRADER_V38.md): the 09:30-09:55 gap slot, the main source of red days. U58 (brake 0.25) against
V1 no small-gap fill-in (gap_go_small_k -1), V2 no opening-drive fill-in (gap_go_drive_k 0), V3 a stricter gap trigger
(gap_go_k 0.8), V4 = V1 + V2. G415's fresh starts (green days reported), then G372's development / unseen starts.

    python research/g479_gap_slot.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

B = {**U58, "giveback_brake": 0.25}
V = {"U58 (brake 0.25)": B, "V1 no small-gap fill-in": {**B, "gap_go_small_k": -1.0},
     "V2 no drive fill-in": {**B, "gap_go_drive_k": 0.0}, "V3 gap trigger 0.8": {**B, "gap_go_k": 0.8},
     "V4 no fill-ins": {**B, "gap_go_small_k": -1.0, "gap_go_drive_k": 0.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
