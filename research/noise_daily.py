"""Can noise-area momentum trade on most days and keep its edge?

    python research/noise_daily.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Fixed before running:
  * Variants: half-hourly checks with the noise band at 0.0x, 0.25x and 0.5x (0.0 = the lines sit at
    the day's open and previous close, so nearly every day trades), next to the current 1.0x.
  * Same data, sessions, costs and periods as noise_tuning.py.
  * Bar for a "trades most days" version: a trade on at least 80% of days; t >= 2 in both 2010-2019 and
    2020 - Sep 2026; and an evaluation pass rate (125 sessions, 2020-2026 starts) no lower than the
    current version's.

Added after the first run, because 0.5x met that bar but looked worse in ways it didn't cover: the
full-period line (losing years, worst losing stretch, 2025-2026, evaluation odds from every start).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import noise_tuning as T  # noqa: E402
import published_lab as L  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

MULTIPLIERS = (1.0, 0.5, 0.25, 0.0)  # 1.0 is the current strategy


def main() -> None:
    raw = load_histdata(sys.argv[1])
    notional = float(raw.close.iloc[-1]) * 2.0
    days = L.Days(raw)
    checks = T.checks_for(30)
    sigma = T.noise_sigma(days, checks)
    ok = [i for i in np.flatnonzero(days.full)
          if not days.missing[i, : days.last[i] + 1].any() and days.last[i] == L.MINUTES - 1
          and not np.isnan(days.prev_close[i]) and not np.isnan(sigma[i]).any()]
    year = pd.Index([days.dates[i].year for i in ok])
    tune, test = year < T.TUNING_END, year >= T.TUNING_END
    rows = {}
    for mult in MULTIPLIERS:
        recs = [(days.dates[i], *T.session(days, i, sigma, checks, mult, notional)) for i in ok]
        df = pd.DataFrame(recs, columns=["day", "pnl", "worst", "trades", "wins"]).set_index("day")
        a, b = T.evaluate(df[tune]), T.evaluate(df[test])
        p, q = T.eval_odds(df[test])
        rows[mult] = (df, a, b, p, q)
    base_pass = rows[1.0][3]
    print(f"{len(ok)} sessions.  band | days with a trade | trades/day | win% | 2010-19 $/day (t) | "
          f"2020-26 $/day (t) | worst dip | eval pass/fail 2020-26 | meets the bar")
    for mult, (df, a, b, p, q) in rows.items():
        traded = (df.trades > 0).mean()
        ok_bar = traded >= 0.8 and a["t"] >= 2 and b["t"] >= 2 and p >= base_pass
        win = 100 * df.wins.sum() / df.trades.sum()
        print(f"  {mult:.2f}x | {100 * traded:5.0f}% | {df.trades.mean():.2f} | {win:.0f}% | "
              f"{a['avg']:+.2f} ({a['t']:.2f}) | {b['avg']:+.2f} ({b['t']:.2f}) | {df.worst.min():,.0f} | "
              f"{100 * p:.0f}% / {100 * q:.0f}% | {'current' if mult == 1.0 else 'YES' if ok_bar else 'no'}")
    print("\nFull period: band | $/day | losing years | worst losing stretch | 2025-26 total | "
          "eval pass/fail (all starts)")
    for mult, (df, *_rest) in rows.items():
        yr = df.pnl.groupby(year).sum()
        stretch = (df.pnl.cumsum().cummax() - df.pnl.cumsum()).max()
        p, q = T.eval_odds(df)
        print(f"  {mult:.2f}x | {df.pnl.mean():+.2f} | {(yr < 0).sum()} of {len(yr)} | ${stretch:,.0f} | "
              f"${yr[yr.index >= 2025].sum():+,.0f} | {100 * p:.0f}% / {100 * q:.0f}%")


if __name__ == "__main__":
    main()
