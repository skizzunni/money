"""G534 (docs/NINJATRADER_V38.md): the gap trade after Nov 19-20 (two gap stops, $290 and $322): Funded growth with
no gap trade, with its stop capped at the bot's $187.50 a contract, or with the stop half way up the 09:30 bar.

    python research/g534_gap_trade.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V41 = {**FG, "lock_at": 0.75, "stop_buffer": 0.5, "entry_k": 0.9, "max_loss_per_trade": 250.0, "max_losers": 3}
V = {"Funded growth (G511)": FG, "N1 no gap trade": {**FG, "gap_go": False},
     "N2 gap stop capped at $187.50": {**FG, "gap_go_cap": True},
     "N3 gap stop half way up the 09:30 bar": {**FG, "gap_go_stop_frac": 0.5}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
