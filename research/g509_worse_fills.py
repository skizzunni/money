"""G509 (docs/NINJATRADER_V38.md), a measurement: G495's measure with worse fills (2 ticks of slippage on every market
fill instead of 1, the live risk), for U58 (Funded growth) and Funded growth plus, both accounts' modes.

    python research/g509_worse_fills.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

GR = {**U58, "giveback_brake": 0.25}
P = {**GR, "profit_step": 1250.0}
V = {"U58 (Funded growth)": GR, "U58, 2 ticks slippage": {**GR, "slippage_ticks": 2},
     "Funded growth plus": P, "plus, 2 ticks slippage": {**P, "slippage_ticks": 2}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
