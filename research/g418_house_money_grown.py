"""G418 (docs/NINJATRADER_V38.md): G417's house money (entries x day_up_mult while today's closed P/L is above 0) only
once the account's closed profit is at least day_up_from. G372's 12-month measure (G386's runner).

    python research/g418_house_money_grown.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import g386_funded_chop_pause as R

R.VARIANTS.clear()
R.VARIANTS["U48"] = {}
for u in (1.5, 2.0):
    for f in (2000.0, 4000.0, 6000.0):
        R.VARIANTS[f"day up x{u} from ${f:.0f} profit"] = {"day_up_mult": u, "day_up_from": f}

if __name__ == "__main__":
    R.main()
