"""G515 (docs/NINJATRADER_V38.md): G514's P1 (a contract per $1,400) with the gentle start (steps_after_lock: no
contract steps until the trailing floor has stopped), to keep P1's gains without its lost development start; also
the gentle start on the current Funded growth alone. G495's measure against the current Funded growth (G511).

    python research/g515_step_1400_gentle.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V = {"Funded growth (G511)": FG, "P1 per $1,400 (G514)": {**FG, "profit_step": 1400.0},
     "Q1 P1 + gentle start": {**FG, "profit_step": 1400.0, "steps_after_lock": True},
     "Q2 gentle start alone": {**FG, "steps_after_lock": True}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
