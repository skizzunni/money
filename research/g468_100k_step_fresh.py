"""G468 (docs/NINJATRADER_V38.md): the 100K funded mode's contract step at $1,750 or $2,500 (G466's mode $2,000), on
G415's fresh starts (each account's own floor).

    python research/g468_100k_step_fresh.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import g415_final_pick as F
from g423_wide_when_wild import U58

K100 = {"trail_dd": 3000.0, "daily_loss_limit": 1800.0, "early_daily_loss": 1500.0}

if __name__ == "__main__":
    F.VARIANTS.clear()
    F.VARIANTS.update({f"100K, +1 per ${s:,}": {**U58, **K100, "profit_step": float(s)} for s in (2000, 1750, 2500)})
    F.main()
