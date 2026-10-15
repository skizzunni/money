"""Can noise-area momentum trade more often without losing its edge? Set up so it can't fool itself.

    python research/noise_tuning.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Fixed before running:
  * Variants: check every 30, 15 or 5 minutes (first check 10:00, last check 16:00 minus the interval),
    times a noise-band multiplier of 0.8, 1.0 or 1.2 (1.0 is the paper's). Nine variants; 30 minutes
    x 1.0 is the current strategy.
  * Data: Nov 2010 - Sep 2026 1-minute NSXUSD, full sessions with no missing minutes. 1 MNQ at the last
    price in the data, with today's costs ($1.24 fees + 1 tick each way), as in noise_eval.py.
  * Tuning period 2010-2019, unseen test period 2020 - Sep 2026.
  * Rule: pick the variant with the highest tuning-period t-stat of daily P&L. Adopt it only if its
    test-period t-stat is at least the current strategy's; otherwise keep the current strategy.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import published_lab as L  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

from mnqbot.config import PropRules  # noqa: E402
from mnqbot.report import run_eval  # noqa: E402

INTERVALS = (30, 15, 5)
MULTIPLIERS = (0.8, 1.0, 1.2)
CURRENT = (30, 1.0)
TUNING_END = 2020  # tuning: years before this; test: this year onward
COST = 2 * 0.25 * 2.0 + 1.24  # $ per round trip per MNQ: 1 tick each way + fees


def checks_for(interval: int) -> list[int]:
    """Check times as minutes after 09:30: 10:00 first, 16:00 minus the interval last."""
    return list(range(30, L.MINUTES - interval + 1, interval))


def noise_sigma(days: L.Days, checks: list[int], lookback: int = L.LOOKBACK) -> np.ndarray:
    move = np.abs(days.cf[:, [m - 1 for m in checks]] / days.o[:, [0]] - 1)
    sigma = np.full_like(move, np.nan)
    full = np.flatnonzero(days.full)
    for j in range(lookback, len(full)):
        sigma[full[j]] = np.nanmean(move[full[j - lookback : j]], axis=0)
    return sigma


def session(days: L.Days, i: int, sigma: np.ndarray, checks: list[int], mult: float, notional: float):
    """One session for 1 MNQ at today's price: (P&L, worst intraday dip, trades, wins)."""
    o0, pc = days.o[i, 0], days.prev_close[i]
    pos, entry, entry_min = 0, 0.0, 0
    realized = worst = 0.0
    n = wins = 0

    def close(m_exit: int, px: float) -> None:
        nonlocal realized, worst, n, wins, pos
        seg = slice(entry_min, m_exit + 1)
        adverse = (np.nanmin(days.l[i, seg]) - entry) if pos > 0 else (entry - np.nanmax(days.h[i, seg]))
        worst = min(worst, realized + notional * adverse / entry - COST)
        pnl = notional * pos * (px - entry) / entry - COST
        realized += pnl
        worst = min(worst, realized)
        n, wins, pos = n + 1, wins + (pnl > 0), 0

    for k, m in enumerate(checks):
        p = days.cf[i, m - 1]
        ub = max(o0, pc) * (1 + mult * sigma[i, k])
        lb = min(o0, pc) * (1 - mult * sigma[i, k])
        exited = 0
        if pos == 1 and p < ub or pos == -1 and p > lb:
            exited = pos
            close(m, days.o[i, m])
        if pos == 0:
            want = 1 if p > ub else -1 if p < lb else 0
            if want and want != exited:
                pos, entry, entry_min = want, days.o[i, m], m
    if pos:
        close(L.MINUTES - 1, days.c[i, L.MINUTES - 1])
    return realized, worst, n, wins


def evaluate(df: pd.DataFrame) -> dict:
    t = df.pnl.mean() / df.pnl.std() * math.sqrt(len(df)) if df.pnl.std() > 0 else 0.0
    return {"days": len(df), "avg": df.pnl.mean(), "sd": df.pnl.std(), "t": t, "trades_per_day": df.trades.mean(),
            "win_rate": df.wins.sum() / max(df.trades.sum(), 1), "worst_dip": df.worst.min(),
            "max_dd": (df.pnl.cumsum().cummax() - df.pnl.cumsum()).max()}


def eval_odds(df: pd.DataFrame, horizon: int = 125) -> tuple[float, float]:
    recs = list(zip(df.pnl, df.worst, df.trades > 0, strict=True))
    res = [run_eval(recs[s : s + horizon], PropRules())[0] for s in range(len(recs) - horizon)]
    return res.count("passed") / len(res), res.count("failed") / len(res)


def main() -> None:
    raw = load_histdata(sys.argv[1])
    notional = float(raw.close.iloc[-1]) * 2.0
    days = L.Days(raw)
    clean = [i for i in np.flatnonzero(days.full) if not days.missing[i, : days.last[i] + 1].any()
             and days.last[i] == L.MINUTES - 1 and not np.isnan(days.prev_close[i])]
    results = {}
    for interval in INTERVALS:
        checks = checks_for(interval)
        sigma = noise_sigma(days, checks)
        ok = [i for i in clean if not np.isnan(sigma[i]).any()]
        for mult in MULTIPLIERS:
            rows = [(days.dates[i], *session(days, i, sigma, checks, mult, notional)) for i in ok]
            df = pd.DataFrame(rows, columns=["day", "pnl", "worst", "trades", "wins"]).set_index("day")
            results[(interval, mult)] = df
    common = sorted(set.intersection(*(set(df.index) for df in results.values())))  # same sessions for all
    year = pd.Index(common).map(lambda d: d.year)
    tune_days = [d for d, y in zip(common, year, strict=True) if y < TUNING_END]
    test_days = [d for d, y in zip(common, year, strict=True) if y >= TUNING_END]
    print(f"{len(common)} sessions: tuning {len(tune_days)} ({common[0]} ..), test {len(test_days)} (2020 ..)")
    print(f"\n{'variant':16s} {'trades/day':>10s} {'win%':>5s} | {'tuning $/day':>12s} {'t':>5s} | "
          f"{'test $/day':>10s} {'t':>5s} | {'full t':>6s} {'worst dip':>9s} {'max DD':>8s} | "
          f"{'eval pass/fail (test)':>21s}")
    stats = {}
    for key, df in results.items():
        df = df.loc[common]
        a, b, f = evaluate(df.loc[tune_days]), evaluate(df.loc[test_days]), evaluate(df)
        p, q = eval_odds(df.loc[test_days])
        stats[key] = (a, b, f)
        name = f"{key[0]:2d} min x {key[1]:.1f}" + ("  (now)" if key == CURRENT else "")
        print(f"{name:16s} {f['trades_per_day']:>10.2f} {100 * f['win_rate']:>4.0f}% | "
              f"{a['avg']:>+12.2f} {a['t']:>5.2f} | {b['avg']:>+10.2f} {b['t']:>5.2f} | "
              f"{f['t']:>6.2f} {f['worst_dip']:>9,.0f} {f['max_dd']:>8,.0f} | {100 * p:>9.0f}% / {100 * q:.0f}%")
    pick = max(stats, key=lambda k: stats[k][0]["t"])
    if pick == CURRENT:
        verdict = "that is the current strategy: keep it"
    elif stats[pick][1]["t"] >= stats[CURRENT][1]["t"]:
        verdict = "it also beats the current strategy on the test period: adopt it"
    else:
        verdict = "it does worse than the current strategy on the test period: keep the current strategy"
    print(f"\nPicked on the tuning period: {pick[0]} min x {pick[1]} (test t {stats[pick][1]['t']:.2f}, "
          f"current {stats[CURRENT][1]['t']:.2f}); {verdict}")
    by_year = results[pick].loc[common].pnl.groupby(year).sum().round(0).astype(int).to_dict()
    print(f"Pick $ by year: {by_year}")


if __name__ == "__main__":
    main()
