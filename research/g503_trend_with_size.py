"""G503 (docs/NINJATRADER_V38.md): Funded growth plus with bigger trades on the trend's side: a trade with the
45-session trend (U58's trend_n) takes trend_with_mult x the contracts (the same stop in points, so x the max loss;
still cut to the day's budget and the room above the floor). W1 1.5x, W2 2x. G495's measure.

    python research/g503_trend_with_size.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import g495_reach_25k as G
import pandas as pd
from g423_wide_when_wild import U58

P = {**U58, "giveback_brake": 0.25, "profit_step": 1250.0}
V = {"Funded growth plus": P, "W1 1.5x with the trend": {**P, "trend_with_mult": 1.5},
     "W2 2x with the trend": {**P, "trend_with_mult": 2.0}}

if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = G.table
    pd.set_option("display.width", 250)
    M.main()
