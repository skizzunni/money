"""G495 (docs/NINJATRADER_V38.md), a measurement toward the user's goal: a fresh 50K account at +$25,000 net within
its first 12 months. For each start (G415's fresh, G372's development / unseen): the 12-month net (a lost start counts
its net up to the loss), the share of starts at +$25,000 or more, the median, and the share lost. U58 (Funded growth),
P +1 MNQ per $1,250 (Funded growth plus), A1 (Funded aggressive), A1 + a $1,500 day budget once the floor stops,
A1 + a contract per $750, A1 + faster steps (+1 per $400 from $5,000).

    python research/g495_reach_25k.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import pandas as pd
from g423_wide_when_wild import U58

GROW = {**U58, "giveback_brake": 0.25}
A1 = {**U58, "giveback_brake": 0.0, "profit_step": 1000.0, "early_daily_loss": 1000.0}
V = {"U58 (Funded growth)": GROW, "P +1 per $1,250 (plus)": {**GROW, "profit_step": 1250.0},
     "A1 (Funded aggressive)": A1, "A1 + $1,500 day once locked": {**A1, "daily_loss_limit": 1500.0},
     "A1 + 1 per $750": {**A1, "profit_step": 750.0},
     "A1 + 1 per $400 from $5,000": {**A1, "profit_step_fast": 400.0, "profit_step_fast_from": 5000.0}}
GOAL = 25000.0


def table(d):
    y = d.groupby(["tag", "set", "start"]).agg(net=("pnl", "sum"), lost=("lost", "any")).reset_index()
    out = y.groupby("tag").agg(starts=("net", "size"), reach_25k=("net", lambda s: (s >= GOAL).mean()),
                               median_12m=("net", "median"), p25_12m=("net", lambda s: s.quantile(0.25)),
                               best_12m=("net", "max"), lost=("lost", "mean"))
    return out.join(d.groupby("tag").pnl.mean().rename("per_session")).sort_values("reach_25k", ascending=False)


if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = table
    pd.set_option("display.width", 250)
    M.main()
