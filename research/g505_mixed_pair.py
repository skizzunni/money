"""G505 (docs/NINJATRADER_V38.md), a measurement: the user's two accounts in different modes. Per start, the pair's
12-month net is the sum of the two accounts' (each counts up to its own loss). Pairs: plus + plus (G502), plus + H1
(G504), plus + L3 (G499), plus + Funded aggressive. Reported: the share of starts where the pair is at +$25,000, the
pair's median, the share with at least one account lost, and with both lost.

    python research/g505_mixed_pair.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json> fresh|unseen
"""
import sys

import g386_funded_chop_pause as R
import g415_final_pick as F
import pandas as pd
from g423_wide_when_wild import U58

P = {**U58, "giveback_brake": 0.25, "profit_step": 1250.0}
SPR = {"sprint_days": 20, "sprint_push_from": 1, "sprint_low_room": 1500.0, "sprint_low_qty": 1}
V = {"plus": P, "H1": {**P, **SPR, "sprint_qty": 2, "sprint_push_qty": 4, "sprint_push_min": 500.0},
     "L3": {**P, "sprint_qty": 4, "sprint_days": 10, "sprint_low_room": 1500.0, "sprint_low_qty": 1},
     "aggressive": {**U58, "giveback_brake": 0.0, "profit_step": 1000.0, "early_daily_loss": 1000.0}}


def table(d):
    y = d.groupby(["tag", "set", "start"]).agg(net=("pnl", "sum"), lost=("lost", "any")).reset_index()
    w = y.pivot_table(index=["set", "start"], columns="tag", values=["net", "lost"], aggfunc="first")
    rows = {}
    for b in ("plus", "H1", "L3", "aggressive"):
        net = w["net"]["plus"] + w["net"][b]
        la, lb = w["lost"]["plus"].astype(bool), w["lost"][b].astype(bool)
        rows[f"plus + {b}"] = {"starts": len(net), "pair_reach_25k": (net >= 25000).mean(),
                               "pair_median": net.median(), "pair_p25": net.quantile(0.25),
                               "one_lost": (la | lb).mean(), "both_lost": (la & lb).mean()}
    return pd.DataFrame(rows).T


if __name__ == "__main__":
    M = F if sys.argv.pop(5) == "fresh" else R
    M.VARIANTS.clear()
    M.VARIANTS.update(V)
    M.table = table
    pd.set_option("display.width", 250)
    M.main()
