"""Noise-area momentum (S2a) on a $25K / $1,500 evaluation, at today's price level.

    python research/noise_eval.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

1. Checks that the bot's 5-minute reference (mnqbot/noise.py) makes the same trades as the
   1-minute research version (published_lab.s2_noise) on full sessions with no missing minutes.
2. Turns every session into 1 MNQ at the last price in the data: each trade's move as a share of
   price times today's contract value, minus today's costs ($1.24 fees + 1 tick each way).
   Also the worst intraday dip, from each trade's worst price while open.
3. Runs Take Profit Trader-style evaluation rules (mnqbot.config.PropRules) starting on every
   historical day, so bad stretches stay together, for 60 / 125 / 250 sessions.
4. Repeats 2-3 with the bot's existing $300 daily loss limit, the one rail tested.
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

from mnqbot import noise  # noqa: E402
from mnqbot.config import PropRules  # noqa: E402
from mnqbot.data import resample  # noqa: E402
from mnqbot.report import run_eval  # noqa: E402

TICK_D, FEE_D = 0.25 * 2.0, 1.24  # $ per MNQ: one tick of slippage, round-trip fees


def crosscheck(raw: pd.DataFrame, days: L.Days, sigma: np.ndarray, elig: list[int]) -> tuple[int, int]:
    lab = {}
    for i in elig:
        if days.missing[i, : days.last[i] + 1].any():
            continue
        lab[days.dates[i]] = [(t.direction, 570 + t.entry_min, 570 + t.exit_min, round(t.entry, 3), round(t.exit, 3))
                              for t in L.s2_noise(days, i, sigma, use_twap=False)]
    lab = {d: v for d, v in lab.items() if v}
    mine: dict = {}
    for t in noise.run(resample(raw, "5min"), minutes=5).trades:
        d = t.entry_time.date()
        if d in lab:
            exit_min = t.exit_time.hour * 60 + t.exit_time.minute + (4 if t.reason == "16:00 close" else 0)
            mine.setdefault(d, []).append((t.direction, t.entry_time.hour * 60 + t.entry_time.minute, exit_min,
                                           round(t.entry, 3), round(t.exit, 3)))
    return sum(mine.get(d) == v for d, v in lab.items()), len(lab)


def sessions(days: L.Days, sigma: np.ndarray, elig: list[int], notional: float, limit: float | None) -> pd.DataFrame:
    rows = []
    for i in elig:
        trades = L.s2_noise(days, i, sigma, use_twap=False)
        if any(t.hole for t in trades):
            continue
        realized, worst = 0.0, 0.0
        for t in trades:
            d, e = t.direction, t.entry
            base = realized - TICK_D - FEE_D  # after entry slippage and fees
            seg = slice(t.entry_min, t.exit_min + 1)
            if limit is not None:  # flat for the day once the day's P&L reaches -limit
                p_stop = e * (1 + d * (-limit - base) / notional)
                hit = (days.l[i, seg] <= p_stop) if d > 0 else (days.h[i, seg] >= p_stop)
                if np.nanmax(hit, initial=0):
                    m = t.entry_min + int(np.argmax(hit))
                    fill = min(days.o[i, m], p_stop) if d > 0 else max(days.o[i, m], p_stop)
                    realized = base + notional * d * (fill - e) / e - TICK_D
                    worst = min(worst, realized)
                    break
            adverse = (np.nanmin(days.l[i, seg]) - e) if d > 0 else (e - np.nanmax(days.h[i, seg]))
            worst = min(worst, base + notional * adverse / e)
            realized = base + notional * d * (t.exit - e) / e - TICK_D
            worst = min(worst, realized)
        rows.append((days.dates[i], realized, worst, len(trades) > 0))
    return pd.DataFrame(rows, columns=["day", "pnl", "worst", "traded"]).set_index("day")


def eval_odds(df: pd.DataFrame, horizon: int, prop: PropRules) -> dict:
    recs = list(zip(df.pnl, df.worst, df.traded, strict=True))
    res = [run_eval(recs[s : s + horizon], prop) for s in range(len(recs) - horizon)]
    out = pd.Series([r[0] for r in res]).value_counts(normalize=True)
    to_pass = [r[1] for r in res if r[0] == "passed"]
    return {"pass": out.get("passed", 0.0), "fail": out.get("failed", 0.0), "open": out.get("timeout", 0.0),
            "median_days_to_pass": float(np.median(to_pass)) if to_pass else math.nan}


def main() -> None:
    raw = load_histdata(sys.argv[1])
    ref = float(raw.close.iloc[-1])
    notional = ref * 2.0
    saved = L.SLIP, L.FEE_RT
    L.SLIP, L.FEE_RT = 0.0, 0.0  # raw fills; today's costs are applied in sessions()
    days = L.Days(raw)
    sigma = L.noise_sigma(days)
    full = np.flatnonzero(days.full)
    elig = [i for i in full if not np.isnan(sigma[i]).any() and not np.isnan(days.prev_close[i])]
    L.SLIP, L.FEE_RT = saved
    same, total = crosscheck(raw, days, sigma, elig)
    print(f"bot reference vs research version: identical trades on {same} of {total} clean sessions with trades")
    L.SLIP, L.FEE_RT = 0.0, 0.0
    prop = PropRules()
    for limit in (None, 300.0):
        df = sessions(days, sigma, elig, notional, limit)
        year = df.index.map(lambda d: d.year)
        t = df.pnl.mean() / df.pnl.std() * math.sqrt(len(df))
        dd = (df.pnl.cumsum().cummax() - df.pnl.cumsum()).max()
        print(f"\n1 MNQ at {ref:,.0f}, daily loss limit {limit}: {len(df)} sessions, avg ${df.pnl.mean():+.2f}/day, "
              f"sd ${df.pnl.std():.0f}, t = {t:+.2f}, max drawdown ${dd:,.0f}, "
              f"worst intraday dip ${df.worst.min():,.0f}")
        print("  $ by year:", {int(k): int(v) for k, v in df.pnl.groupby(year).sum().items()})
        for horizon in (60, 125, 250):
            o = eval_odds(df, horizon, prop)
            print(f"  eval, {horizon} sessions from every start day: pass {o['pass']:.1%}, fail {o['fail']:.1%}, "
                  f"still going {o['open']:.1%}, median {o['median_days_to_pass']:.0f} sessions to pass")
        o = eval_odds(df[year >= 2023], 125, prop)
        print(f"  eval, 125 sessions, 2023-2026 starts only: pass {o['pass']:.1%}, fail {o['fail']:.1%}, "
              f"still going {o['open']:.1%}")


if __name__ == "__main__":
    main()
