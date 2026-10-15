"""Test published intraday strategies on Nasdaq-100 1-minute data, with their authors' settings.

    python research/published_lab.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Fixed before looking at any results:

  S1   5-minute opening range (Zarattini & Aziz 2023, "Can Day Trading Really Be Profitable?"):
       trade in the direction of the 09:30-09:35 candle (none on a doji) at the 09:35 open, stop at
       that candle's far end, target 10R, otherwise out at the 16:00 close. $150 risk per trade.
  S2a  Noise-area momentum (Zarattini, Aziz & Barbon 2024, "Beat the Market"): every half hour from
       10:00 to 15:30, go long above / short below the noise area; exit when price is back inside
       it (or reverse if it's through the other side); out at 16:00. 1 contract.
  S2b  Same, with the paper's VWAP trailing stop. The data has no volume, so a time-weighted
       average price (TWAP) stands in for VWAP.
  S3   Last-half-hour momentum (Gao, Han, Li & Zhou 2018, "Market Intraday Momentum"): at 15:30 go
       in the direction of the return from the previous 16:00 close to 10:00; out at 16:00. 1 contract.

  Pass bar (all three): after costs, mean daily P&L t-stat >= 2.5 over the whole period, positive in
  both 2023-2024 and 2025-2026, and positive in at least 3 of the 4 calendar years.

Fills and costs follow the repo's cautious defaults: market orders fill at the next 1-minute open plus
1 tick of slippage, stops fill at the stop (or at the open if price gaps past it) minus 1 tick, a
target needs price 1 tick through it and never fills on the entry bar, a stop wins if both are hit in
the same bar, and fees are $0.62 per contract per side. Trades open across missing minutes in the free
data are left out, together with their day.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nsx_study import load_histdata  # noqa: E402

TICK = 0.25
SLIP = TICK  # points, per market or stop fill
PV = 2.0  # MNQ $ per point
FEE_RT = 1.24  # $ per contract round trip
RISK = 150.0  # $ per trade for S1
MAX_QTY = 15
MINUTES = 390  # 09:30 .. 15:59 bar-open times
CHECKS = list(range(30, 361, 30))  # 10:00, 10:30, ..., 15:30 as minutes after 09:30
LOOKBACK = 14  # days, noise area


@dataclass
class Trade:
    day: pd.Timestamp
    direction: int
    entry_min: int
    exit_min: int
    entry: float
    exit: float
    qty: int
    risk_pts: float  # 0 when the strategy has no fixed stop
    reason: str
    hole: bool

    @property
    def pnl(self) -> float:
        return self.qty * (self.direction * (self.exit - self.entry) * PV - FEE_RT)


class Days:
    """RTH 1-minute bars as (day, minute) matrices, NaN where a minute is missing."""

    def __init__(self, raw: pd.DataFrame):
        idx = raw.index
        minute = idx.hour * 60 + idx.minute - (9 * 60 + 30)
        rth = (minute >= 0) & (minute < MINUTES)
        all_dates = pd.Index(idx.date)
        r, m, d = raw[rth], minute[rth], all_dates[rth]
        self.dates = pd.Index(sorted(set(d)))
        row = self.dates.get_indexer(d)
        shape = (len(self.dates), MINUTES)
        self.o, self.h, self.l, self.c = (np.full(shape, np.nan) for _ in range(4))
        for arr, col in ((self.o, "open"), (self.h, "high"), (self.l, "low"), (self.c, "close")):
            arr[row, m] = r[col].values
        self.missing = np.isnan(self.o)
        self.cf = pd.DataFrame(self.c).ffill(axis=1).values  # last close at or before each minute
        # full sessions only: a 09:30 bar and a bar at 15:55 or later. That drops holidays, half days and
        # the weeks when the US and European clock changes differ, when this data's session ends at 15:15.
        self.full = ~self.missing[:, 0] & ~self.missing[:, MINUTES - 5 :].all(axis=1)
        self.last = np.where(self.full, MINUTES - 1 - np.argmax(~self.missing[:, ::-1], axis=1), -1)
        # previous session's last close (half days count), if within 5 calendar days
        last = pd.DataFrame(self.c).ffill(axis=1).values[:, -1]
        self.prev_close = np.full(len(self.dates), np.nan)
        for i in range(1, len(self.dates)):
            if (self.dates[i] - self.dates[i - 1]).days <= 5:
                self.prev_close[i] = last[i - 1]

    def open_at(self, i: int, m: int) -> tuple[float, int]:
        """Open of minute m, or of the first available minute after it."""
        while m < MINUTES and self.missing[i, m]:
            m += 1
        return (self.o[i, m], m) if m < MINUTES else (self.cf[i, -1], MINUTES - 1)

    def hole(self, i: int, a: int, b: int) -> bool:
        return bool(self.missing[i, a : b + 1].any())


def close_out(days: Days, i: int, d: int) -> tuple[float, int]:
    """Market exit at the session's last close."""
    return days.cf[i, MINUTES - 1] - d * SLIP, int(days.last[i])


def s1_orb(days: Days, i: int, sized: bool = True) -> list[Trade]:
    """sized=False takes every signal with 1 contract, to be scored in R as the paper does."""
    if days.missing[i, :6].any():
        return []
    o, h, l, c = days.o[i], days.h[i], days.l[i], days.c[i]
    first_open, first_close = o[0], c[4]
    d = int(np.sign(first_close - first_open))
    if d == 0:
        return []
    entry = o[5] + d * SLIP
    stop = l[:5].min() if d > 0 else h[:5].max()
    risk = d * (entry - stop)
    if risk <= 0:
        return []
    qty = min(MAX_QTY, math.floor(RISK / (risk * PV + SLIP * PV + FEE_RT))) if sized else 1
    if qty < 1:
        return []
    target = entry + d * 10 * risk
    for m in range(5, int(days.last[i]) + 1):
        if days.missing[i, m]:
            continue
        if (l[m] <= stop) if d > 0 else (h[m] >= stop):
            fill = (min(o[m], stop) if d > 0 else max(o[m], stop)) - d * SLIP
            return [Trade(days.dates[i], d, 5, m, entry, fill, qty, risk, "stop", days.hole(i, 5, m))]
        if m > 5 and ((h[m] >= target + TICK) if d > 0 else (l[m] <= target - TICK)):
            return [Trade(days.dates[i], d, 5, m, entry, target, qty, risk, "target", days.hole(i, 5, m))]
    px, m = close_out(days, i, d)
    return [Trade(days.dates[i], d, 5, m, entry, px, qty, risk, "close", days.hole(i, 5, m))]


def noise_sigma(days: Days) -> np.ndarray:
    """sigma[i, k]: mean |close at check k / 09:30 open - 1| over the previous LOOKBACK full sessions."""
    move = np.full((len(days.dates), len(CHECKS)), np.nan)
    for k, m in enumerate(CHECKS):
        move[:, k] = np.abs(days.cf[:, m - 1] / days.o[:, 0] - 1)
    sigma = np.full_like(move, np.nan)
    full = np.flatnonzero(days.full)
    for j in range(LOOKBACK, len(full)):
        sigma[full[j]] = np.nanmean(move[full[j - LOOKBACK : j]], axis=0)
    return sigma


def s2_noise(days: Days, i: int, sigma: np.ndarray, use_twap: bool) -> list[Trade]:
    pc, o0 = days.prev_close[i], days.o[i, 0]
    if np.isnan(sigma[i]).any() or np.isnan(pc):
        return []
    typical = (days.h[i] + days.l[i] + days.c[i]) / 3
    twap = np.nancumsum(typical) / np.cumsum(~np.isnan(typical))
    trades, pos, entry, entry_min = [], 0, 0.0, 0

    def close(m_exit: int, px: float, reason: str) -> None:
        trades.append(Trade(days.dates[i], pos, entry_min, m_exit, entry, px, 1, 0.0, reason,
                            days.hole(i, entry_min, m_exit)))

    for k, m in enumerate(CHECKS):
        p = days.cf[i, m - 1]
        ub = max(o0, pc) * (1 + sigma[i, k])
        lb = min(o0, pc) * (1 - sigma[i, k])
        long_stop = max(ub, twap[m - 1]) if use_twap else ub
        short_stop = min(lb, twap[m - 1]) if use_twap else lb
        if pos == 1 and p < long_stop or pos == -1 and p > short_stop:
            px, mm = days.open_at(i, m)
            close(mm, px - pos * SLIP, "back inside")
            exited, pos = pos, 0
        else:
            exited = 0
        if pos == 0:
            want = 1 if p > long_stop else -1 if p < short_stop else 0
            if want and want != exited:
                px, entry_min = days.open_at(i, m)
                pos, entry = want, px + want * SLIP
    if pos:
        px, mm = close_out(days, i, pos)
        close(mm, px, "close")
    return trades


def s3_last_half_hour(days: Days, i: int) -> list[Trade]:
    pc = days.prev_close[i]
    if np.isnan(pc):
        return []
    d = int(np.sign(days.cf[i, 29] / pc - 1))
    if d == 0:
        return []
    px, m = days.open_at(i, 360)
    entry = px + d * SLIP
    exit_px, mx = close_out(days, i, d)
    return [Trade(days.dates[i], d, m, mx, entry, exit_px, 1, 0.0, "close", days.hole(i, m, mx))]


def evaluate(name: str, trades: list[Trade], eligible: pd.Index, in_r: bool = False) -> dict:
    """Daily P&L in $ (or in R when in_r), with days that had a trade across missing minutes left out."""
    tf = pd.DataFrame([{**t.__dict__, "pnl": t.pnl, "gross_pts": t.direction * (t.exit - t.entry) + 2 * SLIP}
                       for t in trades])
    if in_r:
        tf["pnl"] = tf.pnl / (tf.qty * (tf.risk_pts * PV + SLIP * PV + FEE_RT))
    bad_days = set(tf.loc[tf.hole, "day"]) if len(tf) else set()
    clean = tf[~tf.day.isin(bad_days)] if len(tf) else tf
    days = eligible.difference(pd.Index(sorted(bad_days)))
    daily = clean.groupby("day").pnl.sum().reindex(days, fill_value=0.0) if len(clean) else pd.Series(0.0, days)
    years = daily.groupby(daily.index.map(lambda d: d.year)).sum()
    half1 = daily[daily.index < pd.Timestamp("2025-01-01").date()].sum()
    half2 = daily[daily.index >= pd.Timestamp("2025-01-01").date()].sum()
    t = daily.mean() / daily.std(ddof=1) * math.sqrt(len(daily)) if daily.std(ddof=1) > 0 else 0.0
    passed = t >= 2.5 and half1 > 0 and half2 > 0 and (years > 0).sum() >= 3
    sized_r = len(clean) and not in_r and (clean.risk_pts > 0).all()
    r = clean.pnl / (clean.qty * (clean.risk_pts * PV + SLIP * PV + FEE_RT)) if sized_r else clean.pnl if in_r else None
    return {
        "name": name, "unit": "R" if in_r else "$", "days": len(daily), "trades": len(clean),
        "left_out_days": len(bad_days),
        "win_rate": float((clean.pnl > 0).mean()) if len(clean) else 0.0,
        "avg_trade": float(clean.pnl.mean()) if len(clean) else 0.0,
        "avg_gross_pts": float(clean.gross_pts.mean()) if len(clean) else 0.0,  # per contract, before costs
        "avg_r": float(r.mean()) if r is not None else None,
        "net": float(daily.sum()), "t": float(t), "half_2023_24": float(half1), "half_2025_26": float(half2),
        "by_year": {int(y): round(float(v), 2) for y, v in years.items()},
        "worst_day": float(daily.min()), "best_day": float(daily.max()),
        "max_dd": float((daily.cumsum().cummax() - daily.cumsum()).max()),
        "pass": bool(passed), "trades_frame": clean, "daily": daily,
    }


def run_all(raw: pd.DataFrame) -> list[dict]:
    days = Days(raw)
    sigma = noise_sigma(days)
    full = np.flatnonzero(days.full)
    out = []
    specs = {
        "S1 5-min opening range, 10R, every signal (in R)": lambda i: s1_orb(days, i, sized=False),
        "S1 5-min opening range, 10R, $150 risk (skips too-wide stops)": lambda i: s1_orb(days, i),
        "S2a noise area": lambda i: s2_noise(days, i, sigma, use_twap=False),
        "S2b noise area + TWAP stop": lambda i: s2_noise(days, i, sigma, use_twap=True),
        "S3 last half hour": lambda i: s3_last_half_hour(days, i),
    }
    for name, fn in specs.items():
        if name.startswith("S2"):
            elig = [i for i in full if not np.isnan(sigma[i]).any() and not np.isnan(days.prev_close[i])]
        elif name.startswith("S3"):
            elig = [i for i in full if not np.isnan(days.prev_close[i])]
        else:
            elig = list(full)
        trades = [t for i in elig for t in fn(i)]
        out.append(evaluate(name, trades, pd.Index([days.dates[i] for i in elig]), in_r="(in R)" in name))
    return out


def main() -> None:
    raw = load_histdata(sys.argv[1])
    for r in run_all(raw):
        u = r["unit"]
        avg_r = f"  avg {r['avg_r']:+.3f}R" if r["avg_r"] is not None and u == "$" else ""
        print(f"\n{r['name']}  ->  {'PASS' if r['pass'] else 'fail'}")
        print(f"  {r['trades']} trades on {r['days']} days ({r['left_out_days']} days left out for missing data), "
              f"win {100 * r['win_rate']:.1f}%, avg {r['avg_trade']:+.3f} {u}/trade{avg_r}, "
              f"avg {r['avg_gross_pts']:+.2f} pts/contract before costs")
        print(f"  net {r['net']:+,.1f} {u}, t = {r['t']:+.2f}, 2023-24 {r['half_2023_24']:+,.1f}, "
              f"2025-26 {r['half_2025_26']:+,.1f}, by year {r['by_year']}")
        print(f"  worst day {r['worst_day']:+,.1f}, best day {r['best_day']:+,.1f}, "
              f"max drawdown {r['max_dd']:,.1f} ({u})")


if __name__ == "__main__":
    main()
