"""G466 (docs/NINJATRADER_V38.md): slower contract steps on the funded account, +1 MNQ per $2,000 (U58 $1,500).
50K: U58 against it, G415's fresh starts then G372's development / unseen (G386's runner). 100K-style ($3,000 floor,
$1,800 / $1,500 day budgets): the same pair on G415's fresh starts only (G386's runner judges losses at the 50K's $2,000
floor; G415's uses each account's own).

    python research/g466_slower_steps.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> <part>

part: 50k-fresh, 50k-unseen or 100k-fresh.
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
from g423_wide_when_wild import U58

K100 = {"trail_dd": 3000.0, "daily_loss_limit": 1800.0, "early_daily_loss": 1500.0}

if __name__ == "__main__":
    part = sys.argv.pop(5)
    if part == "100k-fresh":
        V = {"100K U58": {**U58, **K100}, "100K, +1 per $2,000": {**U58, **K100, "profit_step": 2000.0}}
    else:
        V = {"U58": U58, "U58, +1 per $2,000": {**U58, "profit_step": 2000.0}}
    M = R if part == "50k-unseen" else F
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.main()
