"""Noise-area intraday momentum, exactly as pine/mnq_noise_momentum.pine trades it.

From Zarattini, Aziz & Barbon (2024), "Beat the Market: An Effective Intraday Momentum Strategy
for S&P500 ETF (SPY)", run with the paper's settings: 14-day noise area, half-hourly checks, no
VWAP stop (the variant tested in research/published_lab.py as S2a).

Rules, New York time, on any chart whose bar length divides 30 minutes:
  * Day open = open of the 09:30 bar. Previous close = close of the previous session's last RTH bar.
  * At each check (the close of the bars ending 10:00, 10:30, ..., 15:30), record
    move = |close / day open - 1| for that time of day.
  * sigma = average of that time of day's move over the last 14 complete sessions
    (a session is complete when it reached 16:00 with all 12 checks).
  * Upper = max(day open, previous close) * (1 + sigma); lower = min(day open, previous close) * (1 - sigma).
  * Flat: buy if close > upper, sell short if close < lower.
    Long: if close < upper, exit, or reverse to short if close < lower. Short: the mirror image.
  * Orders are market orders filled at the next bar's open.
  * Everything is closed at the 16:00 close. If a session ends early (half day, data gap), a position
    still open is closed at the close of the first bar outside 09:30-16:00 or of the next 09:30 bar.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .data import NY

N_CHECKS = 12
FIRST_CHECK, LAST_CHECK, STEP = 600, 930, 30  # minutes after midnight: 10:00 .. 15:30
RTH_OPEN, RTH_CLOSE = 570, 960  # 09:30, 16:00


@dataclass
class NoiseConfig:
    lookback: int = 14  # sessions in the noise average
    qty: int = 1  # contracts
    tick: float = 0.25
    point_value: float = 2.0  # MNQ
    commission_per_side: float = 0.62  # $ per contract
    slippage_ticks: int = 1  # on every market fill


@dataclass
class NoiseTrade:
    direction: int
    qty: int
    entry_bar: int
    entry_time: pd.Timestamp
    entry: float
    exit_bar: int
    exit_time: pd.Timestamp
    exit: float
    reason: str
    pnl: float


@dataclass
class NoiseResult:
    trades: list[NoiseTrade]
    events: list[tuple[int, str]]  # (bar, action) for every alert: BUY, SELL, EXIT, REVERSE, FLAT
    bands: list[tuple[int, float, float]] = field(default_factory=list)  # (check bar, upper, lower)

    def trades_frame(self) -> pd.DataFrame:
        return pd.DataFrame([t.__dict__ for t in self.trades])


def bar_minutes(bars: pd.DataFrame) -> int:
    step = pd.Series(bars.index).diff().dropna().min()
    return int(step.total_seconds() // 60)


def run(bars: pd.DataFrame, cfg: NoiseConfig | None = None, minutes: int | None = None) -> NoiseResult:
    cfg = cfg or NoiseConfig()
    minutes = minutes or bar_minutes(bars)
    if 30 % minutes:
        raise ValueError(f"bar length {minutes} min must divide 30")
    idx = bars.index.tz_convert(NY)
    o, c = bars["open"].to_numpy(float), bars["close"].to_numpy(float)
    slip = cfg.slippage_ticks * cfg.tick
    lb_n = cfg.lookback

    ring = np.full(lb_n * N_CHECKS, np.nan)
    today = [math.nan] * N_CHECKS
    filled = slot = 0
    day_open = prev_close = last_rth_close = math.nan
    pos = 0
    entry_px, entry_bar = 0.0, 0
    pending: tuple[str, int] | None = None  # ("entry", direction) or ("close", 0), filled at the next open
    trades: list[NoiseTrade] = []
    events: list[tuple[int, str]] = []
    bands: list[tuple[int, float, float]] = []

    def open_pos(i: int, d: int) -> None:
        nonlocal pos, entry_px, entry_bar
        pos, entry_px, entry_bar = d, o[i] + d * slip, i

    def close_pos(i: int, price: float, reason: str) -> None:
        nonlocal pos
        pnl = pos * (price - entry_px) * cfg.qty * cfg.point_value - 2 * cfg.commission_per_side * cfg.qty
        trades.append(NoiseTrade(pos, cfg.qty, entry_bar, idx[entry_bar], entry_px, i, idx[i], price, reason, pnl))
        pos = 0

    for i in range(len(bars)):
        t = idx[i]
        t_min = t.hour * 60 + t.minute
        end = t_min + minutes
        in_rth = t_min >= RTH_OPEN and end <= RTH_CLOSE

        # market orders from the previous bar fill at this bar's open
        if pending is not None:
            kind, d = pending
            pending = None
            if kind == "close" and pos:
                close_pos(i, o[i] - pos * slip, "Back inside")
            elif kind == "entry":
                if pos == -d:
                    close_pos(i, o[i] - pos * slip, "reversed")
                if pos == 0:
                    open_pos(i, d)

        if pos and (not in_rth or t_min == RTH_OPEN):  # a session ended early (half day, data gap)
            close_pos(i, c[i] - pos * slip, "Session ended")
            events.append((i, "EXIT"))

        if t_min == RTH_OPEN:
            prev_close = last_rth_close
            day_open = o[i]
            today = [math.nan] * N_CHECKS
        if in_rth:
            last_rth_close = c[i]

        if in_rth and not math.isnan(day_open) and FIRST_CHECK <= end <= LAST_CHECK and (end - FIRST_CHECK) % STEP == 0:
            k = (end - FIRST_CHECK) // STEP
            today[k] = abs(c[i] / day_open - 1)
            if filled >= lb_n and not math.isnan(prev_close):
                s = 0.0
                for d in range(lb_n):  # same summation order as the Pine loop
                    s += ring[d * N_CHECKS + k]
                sigma = s / lb_n
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                bands.append((i, upper, lower))
                if pos > 0 and c[i] < upper:
                    pending = ("entry", -1) if c[i] < lower else ("close", 0)
                    events.append((i, "REVERSE" if c[i] < lower else "EXIT"))
                elif pos < 0 and c[i] > lower:
                    pending = ("entry", 1) if c[i] > upper else ("close", 0)
                    events.append((i, "REVERSE" if c[i] > upper else "EXIT"))
                elif pos == 0 and c[i] > upper:
                    pending = ("entry", 1)
                    events.append((i, "BUY"))
                elif pos == 0 and c[i] < lower:
                    pending = ("entry", -1)
                    events.append((i, "SELL"))

        if in_rth and end == RTH_CLOSE:
            if pos:
                close_pos(i, c[i] - pos * slip, "16:00 close")
                events.append((i, "FLAT"))
            if not math.isnan(day_open) and not any(math.isnan(x) for x in today):
                ring[slot * N_CHECKS : (slot + 1) * N_CHECKS] = today
                slot = (slot + 1) % lb_n
                filled += 1
            day_open = math.nan

    return NoiseResult(trades, events, bands)
