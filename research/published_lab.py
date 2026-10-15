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

  Pass bar: after costs, mean daily P&L t-stat >= 2.5 over the whole period, positive in each era
  that has data (2010-2016, 2017-2022, 2023-2026), and positive in at least 75% of the calendar
  years with 100+ tested days. (The first run, on 2023-2026 only, used: positive in both 2023-2024
  and 2025-2026 and in 3 of 4 years. Same idea, extended when 2010-2022 data arrived.)
  S1 is scored in R. S2 and S3 are scored in % of price per trade (constant notional), so the
  2010s, when the index was near 2,000, count as much as 2026, when it was near 25,000.

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


ERAS = (("2010-2016", 0, 2017), ("2017-2022", 2017, 2023), ("2023-2026", 2023, 9999))
MIN_DAYS_PER_YEAR = 100  # a calendar year counts toward "years up" only with this many tested days


def evaluate(name: str, trades: list[Trade], eligible: pd.Index, unit: str = "$") -> dict:
    """Daily P&L, with days that had a trade across missing minutes left out.

    unit "$": dollars as sized. "R": each trade's P&L over its risk (1R = stop loss plus costs).
    "%": each trade's net move as a percent of its entry price, i.e. constant notional, so years
    with a low index level weigh the same as years with a high one.
    """
    tf = pd.DataFrame([{**t.__dict__, "pnl": t.pnl, "gross_pts": t.direction * (t.exit - t.entry) + 2 * SLIP}
                       for t in trades])
    if unit == "R":
        tf["pnl"] = tf.pnl / (tf.qty * (tf.risk_pts * PV + SLIP * PV + FEE_RT))
    elif unit == "%":
        tf["pnl"] = 100 * (tf.direction * (tf.exit - tf.entry) - FEE_RT / PV) / tf.entry
    bad_days = set(tf.loc[tf.hole, "day"]) if len(tf) else set()
    clean = tf[~tf.day.isin(bad_days)] if len(tf) else tf
    days = eligible.difference(pd.Index(sorted(bad_days)))
    daily = clean.groupby("day").pnl.sum().reindex(days, fill_value=0.0) if len(clean) else pd.Series(0.0, days)
    year = daily.index.map(lambda d: d.year)
    years = daily.groupby(year).sum()
    counted = daily.groupby(year).size() >= MIN_DAYS_PER_YEAR
    in_era = {label: (year >= a) & (year < b) for label, a, b in ERAS}
    eras = {label: float(daily[m].sum()) for label, m in in_era.items() if m.any()}
    t = daily.mean() / daily.std(ddof=1) * math.sqrt(len(daily)) if daily.std(ddof=1) > 0 else 0.0
    years_up, years_counted = int((years[counted] > 0).sum()), int(counted.sum())
    passed = t >= 2.5 and all(v > 0 for v in eras.values()) and years_up >= 0.75 * years_counted
    sized_r = len(clean) and unit == "$" and (clean.risk_pts > 0).all()
    r = clean.pnl / (clean.qty * (clean.risk_pts * PV + SLIP * PV + FEE_RT)) if sized_r else None
    return {
        "name": name, "unit": unit, "days": len(daily), "trades": len(clean), "left_out_days": len(bad_days),
        "win_rate": float((clean.pnl > 0).mean()) if len(clean) else 0.0,
        "avg_trade": float(clean.pnl.mean()) if len(clean) else 0.0,
        "avg_gross_pts": float(clean.gross_pts.mean()) if len(clean) else 0.0,  # per contract, before costs
        "avg_r": float(r.mean()) if r is not None else None,
        "net": float(daily.sum()), "t": float(t), "eras": eras,
        "years_up": years_up, "years_counted": years_counted,
        "by_year": {int(y): round(float(v), 2) for y, v in years.items()},
        "worst_day": float(daily.min()), "best_day": float(daily.max()),
        "max_dd": float((daily.cumsum().cummax() - daily.cumsum()).max()),
        "pass": bool(passed), "trades_frame": clean, "daily": daily,
    }


def run_all(raw: pd.DataFrame) -> list[dict]:
    days = Days(raw)
    sigma = noise_sigma(days)
    full = np.flatnonzero(days.full)
    has_sigma = [i for i in full if not np.isnan(sigma[i]).any() and not np.isnan(days.prev_close[i])]
    has_prev = [i for i in full if not np.isnan(days.prev_close[i])]
    specs = [  # name, trades for day i, unit, eligible days
        ("S1 5-min opening range, 10R, every signal", lambda i: s1_orb(days, i, sized=False), "R", list(full)),
        ("S1 5-min opening range, 10R, $150 risk", lambda i: s1_orb(days, i), "$", list(full)),
        ("S2a noise area", lambda i: s2_noise(days, i, sigma, use_twap=False), "%", has_sigma),
        ("S2b noise area + TWAP stop", lambda i: s2_noise(days, i, sigma, use_twap=True), "%", has_sigma),
        ("S3 last half hour", lambda i: s3_last_half_hour(days, i), "%", has_prev),
    ]
    out = []
    for name, fn, unit, elig in specs:
        trades = [t for i in elig for t in fn(i)]
        out.append(evaluate(name, trades, pd.Index([days.dates[i] for i in elig]), unit))
    return out


def cost_check(raw: pd.DataFrame) -> list[str]:
    """Added after seeing the 2010-2026 result: the same trades under three cost models.

    points: today's MNQ costs in index points at every price level (the declared test above)
    scaled: today's costs as a share of price, using the last price in the data. In 2011 the index
            was near 2,300, so 1 tick plus fees was about ten times today's cost as a share of price.
    gross:  no costs at all
    """
    global SLIP, FEE_RT
    saved = SLIP, FEE_RT
    SLIP, FEE_RT = 0.0, 0.0  # raw fills; costs are applied per trade below
    try:
        ref = float(raw.close.iloc[-1])
        days = Days(raw)
        sigma = noise_sigma(days)
        full = np.flatnonzero(days.full)
        has_sigma = [i for i in full if not np.isnan(sigma[i]).any() and not np.isnan(days.prev_close[i])]
        has_prev = [i for i in full if not np.isnan(days.prev_close[i])]
        specs = [
            ("S1 opening range", lambda i: s1_orb(days, i, sized=False), "R", list(full)),
            ("S2a noise area", lambda i: s2_noise(days, i, sigma, use_twap=False), "%", has_sigma),
            ("S2b noise area + TWAP stop", lambda i: s2_noise(days, i, sigma, use_twap=True), "%", has_sigma),
            ("S3 last half hour", lambda i: s3_last_half_hour(days, i), "%", has_prev),
        ]
        fee_pts = saved[1] / PV
        lines = [f"reference price for 'scaled': {ref:,.0f}"]
        for name, fn, unit, elig in specs:
            tf = pd.DataFrame([t.__dict__ for i in elig for t in fn(i)])
            bad = set(tf.loc[tf.hole, "day"])
            tf = tf[~tf.day.isin(bad)]
            all_days = pd.Index([days.dates[i] for i in elig]).difference(pd.Index(sorted(bad)))
            move = tf.direction * (tf.exit - tf.entry)
            for model in ("points", "scaled", "gross"):
                scale = 1.0 if model == "points" else tf.entry / ref if model == "scaled" else 0.0
                slip = saved[0] * scale
                cost = slip + slip * (tf.reason != "target") + fee_pts * scale
                net = move - cost
                val = net / (tf.risk_pts + slip + fee_pts * scale) if unit == "R" else 100 * net / tf.entry
                daily = val.groupby(tf.day).sum().reindex(all_days, fill_value=0.0)
                year = daily.index.map(lambda d: d.year)
                yrs = daily.groupby(year).sum()
                counted = daily.groupby(year).size() >= MIN_DAYS_PER_YEAR
                eras = [daily[(year >= a) & (year < b)].sum() for _, a, b in ERAS]
                t = daily.mean() / daily.std(ddof=1) * math.sqrt(len(daily))
                up, n = int((yrs[counted] > 0).sum()), int(counted.sum())
                ok = t >= 2.5 and all(v > 0 for v in eras) and up >= 0.75 * n
                era_text = " ".join(f"{v:+8.2f}" for v in eras)
                lines.append(f"{name:28s} {model:6s} avg {val.mean():+.4f}{unit}/trade  t={t:+.2f}  "
                             f"eras {era_text}  years up {up}/{n}  {'PASS' if ok else 'fail'}")
        return lines
    finally:
        SLIP, FEE_RT = saved


def main() -> None:
    raw = load_histdata(sys.argv[1])
    print(f"{len(raw):,} 1-minute bars, {raw.index[0]} .. {raw.index[-1]}")
    for r in run_all(raw):
        u = r["unit"]
        avg_r = f" ({r['avg_r']:+.3f}R)" if r["avg_r"] is not None else ""
        eras = ", ".join(f"{k} {v:+,.2f}" for k, v in r["eras"].items())
        print(f"\n{r['name']}  [{u}]  ->  {'PASS' if r['pass'] else 'fail'}")
        print(f"  {r['trades']} trades on {r['days']} days ({r['left_out_days']} days left out for missing data), "
              f"win {100 * r['win_rate']:.1f}%, avg {r['avg_trade']:+.4f} {u}/trade{avg_r}, "
              f"avg {r['avg_gross_pts']:+.2f} pts/contract before costs")
        print(f"  net {r['net']:+,.2f} {u}, t = {r['t']:+.2f}, eras: {eras}, "
              f"years up {r['years_up']} of {r['years_counted']}")
        print(f"  by year {r['by_year']}")
        print(f"  worst day {r['worst_day']:+,.2f}, best day {r['best_day']:+,.2f}, "
              f"max drawdown {r['max_dd']:,.2f} ({u})")
    print("\nCost check, added after seeing the results above (eras: " + ", ".join(e[0] for e in ERAS) + ")")
    for line in cost_check(raw):
        print("  " + line)


if __name__ == "__main__":
    main()
