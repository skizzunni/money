"""The user's first NinjaTrader run (Strategy Analyzer, MNQ DEC26, 1 minute, 18 Aug - 17 Oct 2026, slippage 1,
commission on, default settings): the trade list checked against the rules, and the trades replayed through the
Apex 50K intraday-trail evaluation (close at $3,000 + $25; within a trade, its worst point first, then its best).

    python research/nt_run_check.py data/nt_strategy_analyzer_2026-08-18_10-17.csv
"""
from __future__ import annotations

import sys

import pandas as pd


def money(s):
    return float(str(s).replace("$", "").replace(",", "").replace("(", "-").replace(")", ""))


def evaluation(trades):
    cum = peak = 0.0
    for _, t in trades.iterrows():
        if cum - t.MAE <= peak - 2000:
            return "bust", t["Exit time"]
        if cum + t.MFE >= 3025:
            return "pass", t["Exit time"]
        peak = max(peak, cum + t.MFE, cum + t.Profit)
        cum += t.Profit
    return "unfinished", None


def main() -> None:
    d = pd.read_csv(sys.argv[1])
    for c in ("Profit", "MAE", "MFE"):
        d[c] = d[c].map(money)
    d["Entry time"], d["Exit time"] = pd.to_datetime(d["Entry time"]), pd.to_datetime(d["Exit time"])
    d["day"] = d["Entry time"].dt.date
    bot = d[d["Entry name"].isin(["Long", "Short"])]
    w = d[~d.index.isin(bot.index)]
    print(f"{len(d)} trades ({len(bot)} bot, {len(w)} breakout), net ${d.Profit.sum():,.2f}, "
          f"{100 * (d.Profit > 0).mean():.1f}% winners")
    print("bot contracts", sorted(bot.Qty.unique()), "| bot losing stops", sorted(set(bot[bot.Profit < 0].Profit)))
    print("breakout contracts", sorted(w.Qty.unique()), "| worst breakout", w.Profit.min())
    print("latest exit", d["Exit time"].dt.time.max(), "| earliest entry", d["Entry time"].dt.time.min())
    print("evaluation from the first day:", evaluation(d))
    outs = [(str(s), evaluation(d[d.day >= s])[0]) for s in sorted(d.day.unique())]
    print("started on each day:", outs)


if __name__ == "__main__":
    main()
