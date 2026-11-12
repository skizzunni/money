"""G486 (docs/NINJATRADER_V38.md): the stop-once-green time between G480's all day (55%) and G481's 11:00 (50.5%):
G1 from 10:30, G2 from 10:00, inside Funded green days; and C1, U58 (Funded growth) with calm_k 0.8 (G485's D1
was better on two sets inside Funded green days; G426 tested U58 only at 0 and 0.6). G415's fresh starts, then
G372's development / unseen starts.

    python research/g486_green_from_1030.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

GROW = {**U58, "giveback_brake": 0.25}
GD = {**GROW, "day_stop_late_from": 660, "day_stop_late": 1.0}
V = {"U58 (Funded growth)": GROW, "C1 U58 calm 0.8": {**GROW, "calm_k": 0.8},
     "Funded green days (G481)": GD, "G1 green stop from 10:30": {**GD, "day_stop_late_from": 630},
     "G2 green stop from 10:00": {**GD, "day_stop_late_from": 600}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
