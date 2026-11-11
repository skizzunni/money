"""G412 (docs/NINJATRADER_V38.md): the user's gold chart: the noise-area breakout on gold (XAUUSD 1-minute, HistData,
rescaled to the Sep 2026 level as research/other_markets.py does; MGC $10 a point), at 1 or 2 MGC and a max loss of
$100, $200 or $300 a contract, with round 68's engine (research/other_markets.run_market: session 08:20-13:30 NY,
checks 09:00-13:00, 14-session noise, take-profit 1.5 noise, lock at +1 max loss, 3 losers a day). Per variant and
period: $ a day (every session), t on daily P/L, trades a week, winners.

    python research/g412_gold.py <scratchpad>
"""
import itertools
import math
import sys

import other_markets as O
import pandas as pd


def main() -> None:
    spec = O.SPECS["gold"]
    bars = O.market_bars(sys.argv[1], spec)
    days = pd.Index(sorted(set(bars.index.tz_localize(None).normalize())))
    rows = []
    for q, mlc in itertools.product((1, 2), (100.0, 200.0, 300.0)):
        tr = O.run_market(bars, spec, q, mlc * q, 3)
        df = pd.DataFrame(tr, columns=["dir", "eb", "ep", "xb", "xp", "pnl", "why"])
        df["day"] = bars.index[df.xb].tz_localize(None).normalize()
        for name, y0, y1 in O.PERIODS:
            dd = days[(days.year >= y0) & (days.year <= y1)]
            x = df[(df.day.dt.year >= y0) & (df.day.dt.year <= y1)]
            daily = x.groupby("day").pnl.sum().reindex(dd, fill_value=0.0)
            t = daily.mean() / (daily.std(ddof=1) / math.sqrt(len(daily))) if daily.std() > 0 else 0.0
            rows.append({"MGC": q, "max loss a contract": mlc, "period": name, "$ a day": round(daily.mean(), 2),
                         "t": round(t, 2), "trades a week": round(len(x) / (len(dd) / 5), 1),
                         "winners": round((x.pnl > 0).mean(), 3)})
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
