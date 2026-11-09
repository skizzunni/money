"""G414 (docs/NINJATRADER_V38.md): the user: "search every and all markets". G413 on seven more: the FTSE 100, the
CAC 40, Brent, the pound, the Australian and New Zealand dollars and the dollar index (HistData UKXGBP, FRXEUR, BCOUSD,
GBPUSD, AUDUSD, NZDUSD, UDXUSD). G413: Round 68's engine
(research/other_markets.run_market) on silver, crude, the euro (CME micros SIL / MCL / M6E, round 68's sessions), the
DAX (Eurex micro FDXS, EUR 1 a point ~ $1.08, tick 1, session 03:00-11:30 NY, checks 03:30-11:00) and the Euro Stoxx 50
(micro FSXE, EUR 1 a point ~ $1.08, tick 1, same hours), at 1 or 2 contracts and $100 / $200 / $300 of max loss a
contract. HistData 1-minute data rescaled to the Sep 2026 level. Per market, variant and period: $ a day, t, trades a
week, winners.

    python research/g414_more_markets.py <scratchpad>
"""
import itertools
import math
import sys

import pandas as pd
import other_markets as O

EXTRA = {
    "ftse": O.Spec("ftse", "UKXGBP", 180, 690, 210, 660, 1.27, 0.5, 0.50, 2.0),
    "cac": O.Spec("cac", "FRXEUR", 180, 690, 210, 660, 1.08, 0.5, 0.50, 2.0),
    "brent": O.Spec("brent", "BCOUSD", 540, 870, 570, 840, 100.0, 0.01, 0.75, 0.02),
    "pound": O.Spec("pound", "GBPUSD", 500, 900, 540, 870, 6250.0, 0.0001, 0.62, 0.0002),
    "aussie": O.Spec("aussie", "AUDUSD", 500, 900, 540, 870, 10000.0, 0.0001, 0.62, 0.0002),
    "kiwi": O.Spec("kiwi", "NZDUSD", 500, 900, 540, 870, 10000.0, 0.0001, 0.62, 0.0002),
    "dollar index": O.Spec("dollar index", "UDXUSD", 500, 900, 540, 870, 1000.0, 0.005, 1.00, 0.01),
}


def main() -> None:
    rows = []
    for name in EXTRA:
        spec = EXTRA[name]
        bars = O.market_bars(sys.argv[1], spec)
        days = pd.Index(sorted(set(bars.index.tz_localize(None).normalize())))
        for q, mlc in itertools.product((1, 2), (100.0, 200.0, 300.0)):
            df = pd.DataFrame(O.run_market(bars, spec, q, mlc * q, 3),
                              columns=["dir", "eb", "ep", "xb", "xp", "pnl", "why"])
            df["day"] = bars.index[df.xb].tz_localize(None).normalize()
            for per, y0, y1 in O.PERIODS:
                dd = days[(days.year >= y0) & (days.year <= y1)]
                if not len(dd):
                    continue
                x = df[(df.day.dt.year >= y0) & (df.day.dt.year <= y1)]
                daily = x.groupby("day").pnl.sum().reindex(dd, fill_value=0.0)
                t = daily.mean() / (daily.std(ddof=1) / math.sqrt(len(daily))) if daily.std() > 0 else 0.0
                rows.append({"market": name, "contracts": q, "max loss a contract": mlc, "period": per,
                             "$ a day": round(daily.mean(), 2), "t": round(t, 2),
                             "trades a week": round(len(x) / (len(dd) / 5), 1), "winners": round((x.pnl > 0).mean(), 3)})
        print(name, "done", flush=True)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
