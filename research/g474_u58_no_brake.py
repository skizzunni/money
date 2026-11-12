"""G474 (docs/NINJATRADER_V38.md): the 50K's U58 with the brake at 0.25 (G473) against no brake. G415's fresh starts,
then G372's development / unseen starts (G386's runner).

    python research/g474_u58_no_brake.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

V = {"U58, brake 0.25": {**U58, "giveback_brake": 0.25}, "U58, no brake": {**U58, "giveback_brake": 0.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
