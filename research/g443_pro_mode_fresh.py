"""G443 (docs/NINJATRADER_V38.md): the cost of the PRO mode (G440: trail_intraday, pro_guard $100) on U58 over the 16
recent 12-month starts (G409 / G415): $ a session, starts lost (G415's floor-touch check, end-of-day floor), green
months. A measurement for the user's choice.

    python research/g443_pro_mode_fresh.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import g415_final_pick as F
from g423_wide_when_wild import U58

if __name__ == "__main__":
    F.VARIANTS.clear()
    F.VARIANTS.update({"U58": U58, "U58 + PRO mode": {**U58, "trail_intraday": True, "pro_guard": 100.0}})
    F.main()
