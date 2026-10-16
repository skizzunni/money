"""Round twenty-one: contracts that follow the account, on the $50K evaluation.

    python research/sizing.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Twenty rounds of entry and exit ideas leave the bot at about $23 a day per contract. A prop account is
lost or passed on its path, not its average, so this round changes only how many contracts the bot trades
each day, from the account's profit so far (known at the start of the day). Every size stays within the
$350-per-trade rule: at most 3 contracts with the $116.67-per-contract max loss.
Variants, fixed before running:
  fixed 2; fixed 3;
  build up: 2, then 3 once up $750, 1 if down $750;
  earn the size: 1, then 2 once up $500, 3 once up $1,500;
  back off: 3, then 2 if down $500, 1 if down $1,000.
Take Profit Trader's $50K Test as reviews describe it: $3,000 target, $2,000 end-of-day trailing drawdown,
best day under half the profit, at least 5 trading days. Every start day, 125 sessions.
Pass bar: a higher pass rate than fixed 2 and a fail rate no higher. The variant with the largest pass minus
fail on 2011-2018 that passes there goes on; the same test on 2019-2022; then 2023 - Sep 2026, once.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval50k as E  # noqa: E402
import more_trades as MT  # noqa: E402

from mnqbot.data import NY  # noqa: E402

TARGET, DD, FRAC, MIN_DAYS, HORIZON = 3000.0, 2000.0, 0.5, 5, 125


def fixed(n):
    return lambda profit: n


def build_up(profit):
    return 3 if profit >= 750 else 1 if profit <= -750 else 2


def earn(profit):
    return 3 if profit >= 1500 else 2 if profit >= 500 else 1


def back_off(profit):
    return 1 if profit <= -1000 else 2 if profit <= -500 else 3


VARIANTS = {"fixed 2": fixed(2), "fixed 3": fixed(3), "build up": build_up, "earn the size": earn,
            "back off": back_off}


def attempt(pnl: np.ndarray, traded: np.ndarray, size) -> str:
    rel = peak = 0.0
    days, best = 0, -np.inf
    for p, t in zip(pnl, traded, strict=True):
        day = p * size(rel)
        rel += day
        peak = max(peak, rel)
        if t:
            days += 1
            best = max(best, day)
        if rel <= min(peak - DD, 0.0):  # end-of-day trailing drawdown, stops trailing at the start balance
            return "failed"
        if rel >= TARGET and days >= MIN_DAYS and best < FRAC * rel:
            return "passed"
    return "open"


def odds(d: pd.DataFrame, size) -> tuple[float, float]:
    pnl, traded = d.pnl.to_numpy(), d.traded.to_numpy()
    res = [attempt(pnl[s : s + HORIZON], traded[s : s + HORIZON], size) for s in range(len(d) - HORIZON)]
    return res.count("passed") / len(res), res.count("failed") / len(res)


def main() -> None:
    bars = MT._bars(sys.argv[1])
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == 570].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2011-01-01") & ~sessions.isin(list(first_sessions))]
    d = E.daily(MT.clean(MT.simulate(bars, 30, 1.0), first_sessions), sessions)
    table = {}
    for label, y0, y1 in (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022)):
        dd = d[(d.index.year >= y0) & (d.index.year <= y1)]
        for name, size in VARIANTS.items():
            table[(name, label)] = odds(dd, size)
            p, f = table[(name, label)]
            print(f"{label} {name:14s} pass {100 * p:5.1f}%  fail {100 * f:5.1f}%")

    def passes(name, label):
        (p, f), (p0, f0) = table[(name, label)], table[("fixed 2", label)]
        return p > p0 and f <= f0

    cands = [n for n in VARIANTS if n != "fixed 2" and passes(n, "2011-2018")]
    print(f"\nDiscovery 2011-2018: {cands or 'none pass'}")
    if not cands:
        return
    best = max(cands, key=lambda n: table[(n, "2011-2018")][0] - table[(n, "2011-2018")][1])
    ok = passes(best, "2019-2022")
    print(f"Best: {best}. Confirmation 2019-2022: {'PASS' if ok else 'FAIL'}")
    if ok:
        dd = d[d.index.year >= 2023]
        for name in ("fixed 2", best):
            table[(name, "2023-2026")] = odds(dd, VARIANTS[name])
            p, f = table[(name, "2023-2026")]
            print(f"2023-2026 {name:14s} pass {100 * p:5.1f}%  fail {100 * f:5.1f}%")
        print(f"FINAL TEST 2023 - Sep 2026: {'PASS' if passes(best, '2023-2026') else 'FAIL'}")


if __name__ == "__main__":
    main()
