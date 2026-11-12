"""G480 (docs/NINJATRADER_V38.md): exits for green days. U58 (brake 0.25) against E1-E3 take-profit 0.5 / 0.75 / 1.0
noise units (U58 2.0), E4 0.5 with the lock at 0.15 max losses (U58 0.35), E5 no new entries once the day is green
(day_stop_profit $1), E6 0.75 + E5, E7 E4 + E5. G415's fresh starts (green days = share of traded days with a profit),
then G372's development / unseen starts.

    python research/g480_green_exits.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

B = {**U58, "giveback_brake": 0.25}
G = {"day_stop_profit": 1.0}
V = {"U58 (brake 0.25)": B, "E1 target 0.5": {**B, "take_profit": 0.5}, "E2 target 0.75": {**B, "take_profit": 0.75},
     "E3 target 1.0": {**B, "take_profit": 1.0}, "E4 target 0.5, lock 0.15": {**B, "take_profit": 0.5, "lock_at": 0.15},
     "E5 stop once green": {**B, **G}, "E6 target 0.75 + stop once green": {**B, "take_profit": 0.75, **G},
     "E7 E4 + stop once green": {**B, "take_profit": 0.5, "lock_at": 0.15, **G}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
