"""G510 (docs/NINJATRADER_V38.md): Funded growth plus with entries as a limit a little back toward the line instead of
at the market (G509: a tick of slippage costs 15-25%): the check's close minus limit_entry_frac x (close - line),
working until the next check. Earlier tests used 0.5 (G137 / G333-era: missed the best breakouts); here L1 0.05,
L2 0.1, L3 0.2. G495's measure.

    python research/g510_small_limit_entry.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

P = {**U58, "giveback_brake": 0.25, "profit_step": 1250.0}
V = {"Funded growth plus": P, "L1 limit 0.05 back": {**P, "limit_entry_frac": 0.05},
     "L2 limit 0.1 back": {**P, "limit_entry_frac": 0.1}, "L3 limit 0.2 back": {**P, "limit_entry_frac": 0.2}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
