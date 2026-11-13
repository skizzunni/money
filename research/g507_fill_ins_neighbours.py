"""G507 (docs/NINJATRADER_V38.md): G506's F2 (fill-ins at 2 MNQ from $3,500 above the floor, 3 from $6,000) and its
neighbours, inside Funded growth plus: E1 2 from $3,000 / 3 from $5,000, E2 2 from $4,000 / 3 from $6,500, E3 2 from
$3,500 / 3 from $8,000 (only the 2-MNQ step moved). G495's measure.

    python research/g507_fill_ins_neighbours.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

P = {**U58, "giveback_brake": 0.25, "profit_step": 1250.0}


def f(q2, q3):
    return {**P, "fill_qty2_room": q2, "fill_qty3_room": q3}


V = {"Funded growth plus": P, "F2 $3,500 / $6,000": f(3500.0, 6000.0), "E1 $3,000 / $5,000": f(3000.0, 5000.0),
     "E2 $4,000 / $6,500": f(4000.0, 6500.0), "E3 $3,500 / $8,000": f(3500.0, 8000.0)}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
