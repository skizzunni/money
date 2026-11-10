"""G417 (docs/NINJATRADER_V38.md): the funded account (U48) sized within the day by today's closed P/L: entries while
it is above 0 x day_up_mult, below 0 x day_down_mult (at least 1 contract). G372's 12-month measure (G386's runner).

    python research/g417_house_money.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import g386_funded_chop_pause as R

R.VARIANTS.clear()
R.VARIANTS["U48"] = {}
for u, dn in ((1.5, 1.0), (2.0, 1.0), (1.0, 0.5), (1.0, 1.5), (1.5, 0.5), (0.5, 1.0)):
    R.VARIANTS[f"day up x{u}, day down x{dn}"] = {"day_up_mult": u, "day_down_mult": dn}

if __name__ == "__main__":
    R.main()
