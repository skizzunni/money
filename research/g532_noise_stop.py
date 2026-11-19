"""G532 (docs/NINJATRADER_V38.md): Funded growth with the max loss set by the market's noise (cap_sigma x the check's
noise x the price, a contract) instead of a fixed $187.50: tighter in calm markets, wider in wild ones.

    python research/g532_noise_stop.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

FG = {**U58, "giveback_brake": 0.25, "fill_qty2_room": 4000.0, "fill_qty3_room": 6500.0}
V41 = {**FG, "lock_at": 0.75, "stop_buffer": 0.5, "entry_k": 0.9, "max_loss_per_trade": 250.0, "max_losers": 3}
V = {"Funded growth (G511)": FG, "V1 stop 0.4 noise": {**FG, "cap_sigma": 0.4},
     "V2 stop 0.6 noise": {**FG, "cap_sigma": 0.6}, "V3 stop 0.8 noise": {**FG, "cap_sigma": 0.8}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
