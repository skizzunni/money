"""G502 (docs/NINJATRADER_V38.md), a measurement for the user's real set-up: two 50K accounts started together on the
same signals make twice one account, so the pair reaches +$25,000 when one account reaches +$12,500. G495's table with
that goal: U58 (Funded growth), Funded growth plus, Funded aggressive. A lost account loses both (same trades).

    python research/g502_two_accounts.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

G.GOAL = 12500.0
V = {"U58 (Funded growth)": {**U58, "giveback_brake": 0.25},
     "Funded growth plus": {**U58, "giveback_brake": 0.25, "profit_step": 1250.0},
     "Funded aggressive": {**U58, "giveback_brake": 0.0, "profit_step": 1000.0, "early_daily_loss": 1000.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
