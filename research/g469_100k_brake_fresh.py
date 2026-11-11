"""G469 (docs/NINJATRADER_V38.md): the 100K funded mode ($2,000 steps) with the giveback brake at 0.35 or 0.55 (U58
0.45), on G415's fresh starts (each account's own floor).

    python research/g469_100k_brake_fresh.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import g415_final_pick as F
from g423_wide_when_wild import U58

K100 = {"trail_dd": 3000.0, "daily_loss_limit": 1800.0, "early_daily_loss": 1500.0, "profit_step": 2000.0}

if __name__ == "__main__":
    F.VARIANTS.clear()
    F.VARIANTS.update({"100K funded": {**U58, **K100}, "brake 0.35": {**U58, **K100, "giveback_brake": 0.35},
                       "brake 0.55": {**U58, **K100, "giveback_brake": 0.55}})
    F.main()
