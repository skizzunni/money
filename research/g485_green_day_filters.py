"""G485 (docs/NINJATRADER_V38.md): Funded green days (G481) with a day filter, so fewer days are traded where the
bot tends to end red: D1 calm_k 0.8, D2 calm_k 0.9 (no entries after a calmer stretch; U58 0.7), D3 gap_block 0.005
(no entries against a 0.5%+ opening gap), D4 drive_filter_k 0.25 (no entries against the 09:30-10:00 drive).
G415's fresh starts (green traded days), then G372's development / unseen starts.

    python research/g485_green_day_filters.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

GD = {**U58, "giveback_brake": 0.25, "day_stop_late_from": 660, "day_stop_late": 1.0}
V = {"Funded green days (G481)": GD, "D1 calm 0.8": {**GD, "calm_k": 0.8}, "D2 calm 0.9": {**GD, "calm_k": 0.9},
     "D3 not against a 0.5% gap": {**GD, "gap_block": 0.005},
     "D4 not against the drive": {**GD, "drive_filter_k": 0.25}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
