"""G467 (docs/NINJATRADER_V38.md): the 100K funded mode ($2,000 steps, G466) with up to 2 gap contracts before the floor
stops (gap_go_max_qty 2; U58 1), on G415's fresh starts (each account's own floor).

    python research/g467_100k_gap_early_fresh.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import g415_final_pick as F
from g423_wide_when_wild import U58

K100 = {"trail_dd": 3000.0, "daily_loss_limit": 1800.0, "early_daily_loss": 1500.0, "profit_step": 2000.0}

if __name__ == "__main__":
    F.VARIANTS.clear()
    F.VARIANTS.update({"100K funded": {**U58, **K100},
                       "100K funded, gap 2 early": {**U58, **K100, "gap_go_max_qty": 2}})
    F.main()
