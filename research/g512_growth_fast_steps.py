"""G512 (docs/NINJATRADER_V38.md): Funded growth (U58 + G511's fill-in steps) with its fast contract steps sooner or
smaller: now +1 MNQ per $650 above $9,000 of profit (G243). S1 per $650 above $7,000, S2 per $500 above $9,000.
G495's measure against the current Funded growth.

    python research/g512_growth_fast_steps.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V = {"Funded growth (G511)": FG, "S1 $650 above $7,000": {**FG, "profit_step_fast_from": 7000.0},
     "S2 $500 above $9,000": {**FG, "profit_step_fast": 500.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
