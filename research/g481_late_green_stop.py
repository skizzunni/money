"""G481 (docs/NINJATRADER_V38.md): stop once green, only from a time of day (morning trades as usual). U58 (brake 0.25)
against no new entries once today's P/L is above $0 from 11:00, 12:00 or 13:00 (day_stop_late_from / day_stop_late $1).
G415's fresh starts (green days), then G372's development / unseen starts.

    python research/g481_late_green_stop.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

B = {**U58, "giveback_brake": 0.25}
V = {"U58 (brake 0.25)": B, **{f"stop once green from {h}:00": {**B, "day_stop_late_from": h * 60, "day_stop_late": 1.0}
                               for h in (11, 12, 13)}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
