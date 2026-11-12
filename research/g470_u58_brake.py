"""G470 (docs/NINJATRADER_V38.md): U58 on the 50K with the giveback brake at 0.35 or 0.25 (U58 0.45; the 100K took 0.35
in G469). G415's fresh starts, then G372's development / unseen starts (G386's runner).

    python research/g470_u58_brake.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58": U58, "U58, brake 0.35": {**U58, "giveback_brake": 0.35},
     "U58, brake 0.25": {**U58, "giveback_brake": 0.25}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
