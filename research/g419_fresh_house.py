"""G419 (docs/NINJATRADER_V38.md): G409's fresh-start check for G418's pick (house money x2 from $2,000 of profit)
against U48: G415's starts, measure and table.

    python research/g419_fresh_house.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import g415_final_pick as F

F.VARIANTS.clear()
F.VARIANTS["U48"] = {}
F.VARIANTS["G418 pick: day up x2 from $2000"] = {"day_up_mult": 2.0, "day_up_from": 2000.0}

if __name__ == "__main__":
    F.main()
