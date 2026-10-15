"""Afternoon trend: does the 13:30 position of price predict the move to the close? One clean test.

    python research/afternoon.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Where the idea came from: in discovery.py's 2011-2022 results, "distance from the day's average price"
and "move from the open" at 13:30 lined up with the move to the close in both 2011-2018 and 2019-2022
(t about 3.3-3.7 each), though they missed the false-discovery cut. 2023 - Sep 2026 was not used.

Fixed before running:
  * Candidates, each one trade a day at 13:30, held to the 16:00 close, 1 MNQ at today's price and costs:
      A1 direction of price vs the day's time-weighted average price (TWAP) since 09:30
      A2 direction of price vs the 09:30 open
      A3 only when A1 and A2 agree
  * Pick the best 2011-2022 t-stat of daily P&L; it must be at least 2.5.
  * Final test on 2023 - Sep 2026, run once: it passes at t >= 2.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import discovery as D  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

K = D.CHECKS.index(240)  # 13:30


def main() -> None:
    raw = load_histdata(sys.argv[1])
    ref = float(raw.close.iloc[-1])
    notional, cost = ref * 2.0, 2 * 0.25 * 2.0 + 1.24
    feats, targets, meta = D.build(raw)
    y = targets["close"][:, K]
    twap_side = np.sign(feats["distance_from_twap"][:, K])
    open_side = np.sign(feats["move_from_open"][:, K])
    rules = {"A1": twap_side, "A2": open_side, "A3": np.where(twap_side == open_side, twap_side, 0.0)}
    fit = np.flatnonzero(meta.ok & (meta.year >= 2011) & (meta.year < 2023))
    test = np.flatnonzero(meta.ok & (meta.year >= 2023))

    def daily(pos, rows):
        p = np.nan_to_num(pos[rows])
        r = np.nan_to_num(y[rows])
        day = p * r * notional - np.abs(p) * cost
        return day, day.mean() / day.std(ddof=1) * math.sqrt(len(day))

    best, best_t = None, -math.inf
    for name, pos in rules.items():
        day, t = daily(pos, fit)
        share = 100 * np.mean(pos[fit] != 0)
        print(f"{name}: 2011-2022 ${day.mean():+.2f}/day, t {t:+.2f}, trades on {share:.0f}% of days")
        if t > best_t:
            best, best_t = name, t
    if best_t < 2.5:
        print(f"Best {best} t {best_t:.2f} < 2.5: nothing goes to the final test.")
        return
    day, t = daily(rules[best], test)
    years = pd.Series(day, index=meta.year.to_numpy()[test]).groupby(level=0).sum().round(0).astype(int)
    wins = np.mean(day[rules[best][test] != 0] > 0)
    print(f"\nPicked {best}. FINAL TEST 2023 - Sep 2026: {len(day)} sessions, ${day.mean():+.2f}/day, t {t:+.2f}, "
          f"win {100 * wins:.0f}%, by year {years.to_dict()} -> {'PASS' if t >= 2 else 'FAIL'}")


if __name__ == "__main__":
    main()
