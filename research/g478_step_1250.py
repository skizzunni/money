"""G478 (docs/NINJATRADER_V38.md): the 50K's U58 (brake 0.25) with a contract per $1,250 of profit (U58 $1,500). G415's
fresh starts, then G372's development / unseen starts (G386's runner).

    python research/g478_step_1250.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

B = {**U58, "giveback_brake": 0.25}
V = {"U58 (brake 0.25)": B, "+1 per $1,250": {**B, "profit_step": 1250.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
