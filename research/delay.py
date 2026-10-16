"""Round thirty-five: what does each minute of entry delay cost? Measured on 1-minute bars.

    python research/delay.py nsx_1m_scaled.pkl nq_1m_scaled.pkl

Reasoning, written before running. The 5-minute stress test (round thirty) found that entering one bar late
roughly halves the profit. A trader working by hand from a TradingView alert enters some seconds to minutes after
the check; an automated order (alert -> webhook -> broker) enters within seconds. This round measures the cost
minute by minute, so the choice between hand and automation rests on a number.
Method: the bot as it trades (line stop 0.24 noise units past the line, max loss live from the fill, 1.5-unit
take-profit from the bar after the fill, flat at 16:00) on 1-minute bars, entries filling at the open of the
first minute after the check (delay 0, what an automated order gets), or d = 1, 2, 3, 5 minutes later at that
minute's open plus a tick, the max loss then measured from the real fill. 1 contract, $1.24 fees, 1 tick
slippage, prices at today's level. Both max losses: $116.67 a contract (the tested level) and $35 ($350 over
10 MNQ, the user's setting). Both datasets: the index (2011 - Sep 2026) and NQ futures (2015 - Jul 2025).
Also the 5-minute run next to the 1-minute one at delay 0, to show how much the bar length of the backtest
itself moves the result (stops and targets resolved inside a 5-minute bar vs inside 1-minute bars).
This is a measurement, not a rule change: nothing in the bot changes from it. It decides whether to build
automation (a webhook alert format) as the next step: worth it if 1-3 minutes of delay cost 15% or more of the
$ per day.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import more_trades as MT  # noqa: E402
import profit_levers as P  # noqa: E402
import stress as S  # noqa: E402

CAPS = {"$117": 350.0 / 3 / 2.0, "$35": 35.0 / 2.0}
DELAYS = (0, 1, 2, 3, 5)


def five(bars: pd.DataFrame) -> pd.DataFrame:
    return bars.resample("5min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()


def _job(args):
    path, cap, d = args
    bars = pd.read_pickle(path)
    kw = dict(target=1.5, target_on_fill_bar=False, cap_on_fill_bar=True, cap_pts=CAPS[cap])
    if d == "5m":
        return (path, cap, d), P.simulate(five(bars), **kw)
    return (path, cap, d), P.simulate(bars, minutes=1, entry_delay=d, **kw)


def main() -> None:
    paths = {"index 2011-26": sys.argv[1], "NQ futures 2015-25": sys.argv[2]}
    jobs = [(p, cap, d) for p in paths.values() for cap in CAPS for d in ("5m", *DELAYS)]
    with ProcessPoolExecutor(max_workers=4) as ex:
        runs = dict(ex.map(_job, jobs))
    rows = []
    for label, path in paths.items():
        sessions, first = S.sessions_of(five(pd.read_pickle(path)))
        start = "2011-01-01" if label.startswith("index") else "2015-03-01"
        sessions = sessions[sessions >= start]
        for cap in CAPS:
            stats = {}
            for d in ("5m", *DELAYS):
                tf = MT.clean(runs[(path, cap, d)], first)
                stats[d] = MT.stats(tf[tf.entry_time.dt.tz_localize(None) >= sessions[0]], sessions)
            for d, s in stats.items():
                rows.append((label, cap, "5-min bars" if d == "5m" else f"{d} min late", s["trades/day"],
                             s["win %"], s["$/day"], s["t"], s["worst stretch"],
                             100 * s["$/day"] / stats[0]["$/day"]))
    df = pd.DataFrame(rows, columns=["data", "max loss", "entry", "trades/day", "win %", "$/day", "t",
                                     "worst stretch", "% of on-time $"])
    pd.set_option("display.width", 200)
    print(df.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
