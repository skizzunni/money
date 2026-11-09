"""G413 (docs/NINJATRADER_V38.md): the user: "explore diff markets for my goals". Round 68's engine
(research/other_markets.run_market) on silver, crude, the euro (CME micros SIL / MCL / M6E, round 68's sessions), the
DAX (Eurex micro FDXS, EUR 1 a point ~ $1.08, tick 1, session 03:00-11:30 NY, checks 03:30-11:00) and the Euro Stoxx 50
(micro FSXE, EUR 1 a point ~ $1.08, tick 1, same hours), at 1 or 2 contracts and $100 / $200 / $300 of max loss a
contract. HistData 1-minute data rescaled to the Sep 2026 level. Per market, variant and period: $ a day, t, trades a
week, winners.

    python research/g413_markets.py <scratchpad>
"""
import itertools
import math
import sys

import pandas as pd
import other_markets as O

EXTRA = {
    "dax": O.Spec("dax", "GRXEUR", 180, 690, 210, 660, 1.08, 1.0, 0.50, 2.0),
    "stoxx": O.Spec("stoxx", "ETXEUR", 180, 690, 210, 660, 1.08, 1.0, 0.50, 2.0),
}


def main() -> None:
    rows = []
    for name in ("silver", "crude", "euro", "dax", "stoxx"):
        spec = O.SPECS.get(name) or EXTRA[name]
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
