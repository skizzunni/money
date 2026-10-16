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
  * Exit, exit_mode "stop" (default): once in a trade a stop order rests stop_buffer noise units past
    the current line (below the upper line for a long: upper * (1 - stop_buffer * sigma); above the lower
    line for a short) and moves with it at each check. It fills at the stop, or at the bar's open if the
    open is already past it (the line moved past the price, or a gap). On the bar the entry fills, it
    fills at the stop or the open, whichever is worse. stop_buffer = 0 puts the stop on the line itself.
    A second stop sits max_loss_per_trade dollars (for the whole position) from the entry fill, from the
    bar after the fill on; whichever stop is closer is the one in force ("Max loss" when it is the cap).
    A take-profit limit sits take_profit noise units from the entry fill (entry x (1 +/- take_profit x the
    current sigma)), from the bar after the fill; it fills at the limit once price trades a tick through it,
    and only if the stop didn't fill on the same bar ("Target").
    exit_mode "check": the paper's rule. Long: if a check closes below upper, exit, or reverse to short
    if it closes below lower. Short: the mirror image.
  * Entries and check-mode exits are market orders filled at the next bar's open.
  * No new trades on the dates in skip_dates (holidays and half days by default).
  * Fed days (fed_dates, the scheduled FOMC announcement days): no short entries from the checks before
    14:00 (10:00-13:30), when fed_no_shorts is on. In check mode a reversal to short there is a plain exit.
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
# US market holidays and half days, when MNQ trades a short session (closed or halted by about 13:00 ET).
# The 16-year test only traded full sessions, so the bot sits these out. Same list as the Pine input.
SKIP_DATES = (
    "2026-01-01,2026-01-19,2026-02-16,2026-04-03,2026-05-25,2026-06-19,2026-07-03,2026-09-07,"
    "2026-11-26,2026-11-27,2026-12-24,2026-12-25,2027-01-01,2027-01-18,2027-02-15,2027-03-26,"
    "2027-05-31,2027-06-18,2027-07-05,2027-09-06,2027-11-25,2027-11-26,2027-12-24"
)
# Scheduled FOMC announcement days (statement at 14:00 New York time), from federalreserve.gov. Same list as
# the Pine input; research/fomc_dates.csv has 2011-2026.
FED_DATES = (
    "2026-01-28,2026-03-18,2026-04-29,2026-06-17,2026-07-29,2026-09-16,2026-10-28,2026-12-09,"
    "2027-01-27,2027-03-17,2027-04-28,2027-06-09,2027-07-28,2027-09-15,2027-10-27,2027-12-08"
)
FED_CUTOFF = 840  # 14:00: no shorts from the checks before this on Fed days


@dataclass
class NoiseConfig:
    lookback: int = 14  # sessions in the noise average
    qty: int = 1  # contracts
    tick: float = 0.25
    point_value: float = 2.0  # MNQ
    commission_per_side: float = 0.62  # $ per contract
    slippage_ticks: int = 1  # on every market fill
    skip_dates: str = SKIP_DATES  # "YYYY-MM-DD,..." sessions with no new trades
    exit_mode: str = "stop"  # "stop": resting stop past the current line; "check": exit only at the half hours
    stop_buffer: float = 0.24  # the stop sits this many noise units (sigma) past the line; 0 = on the line
    max_loss_per_trade: float = 350.0  # $ for the whole position: a second stop this far from the entry; 0 = off
    fed_dates: str = FED_DATES  # "YYYY-MM-DD,..." scheduled Fed announcement days
    fed_no_shorts: bool = True  # on those days, no short entries before 14:00 (round twenty-four)
    take_profit: float = 1.5  # noise units from the entry fill for a take-profit limit, stop mode only; 0 = off


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
    events: list[tuple[int, str]]  # (bar, action) for every alert: BUY, SELL, EXIT, TARGET, REVERSE, FLAT
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
    h, l = bars["high"].to_numpy(float), bars["low"].to_numpy(float)
    use_stop = cfg.exit_mode == "stop"
    if cfg.exit_mode not in ("stop", "check"):
        raise ValueError(f"exit_mode must be 'stop' or 'check', not {cfg.exit_mode!r}")
    slip = cfg.slippage_ticks * cfg.tick
    lb_n = cfg.lookback

    ring = np.full(lb_n * N_CHECKS, np.nan)
    today = [math.nan] * N_CHECKS
    filled = slot = 0
    day_open = prev_close = last_rth_close = math.nan
    upper = lower = sigma = math.nan  # the current noise lines and noise, set at each check
    skip_today = fed_today = False
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

        # the resting stop at the line (checked before the script-side logic, like the broker)
        if use_stop and pos and not math.isnan(upper):
            line = upper * (1 - cfg.stop_buffer * sigma) if pos > 0 else lower * (1 + cfg.stop_buffer * sigma)
            reason = "Back inside"
            if cfg.max_loss_per_trade > 0 and entry_bar != i:  # the cap needs the fill price: it starts the bar after
                cap = entry_px - pos * cfg.max_loss_per_trade / cfg.qty / cfg.point_value
                if (pos > 0 and cap > line) or (pos < 0 and cap < line):
                    line, reason = cap, "Max loss"
            if entry_bar == i:  # a stop attached to the entry can fill on the fill bar itself
                hit = l[i] <= line if pos > 0 else h[i] >= line
                price = (min(o[i], line) if pos > 0 else max(o[i], line)) - pos * slip
            elif (pos > 0 and o[i] <= line) or (pos < 0 and o[i] >= line):  # the line moved past the price, or a gap
                hit, price = True, o[i] - pos * slip
            else:
                hit = l[i] <= line if pos > 0 else h[i] >= line
                price = line - pos * slip
            if hit:
                close_pos(i, price, reason)
                events.append((i, "EXIT"))
            elif cfg.take_profit > 0 and entry_bar != i:  # the take-profit limit, from the bar after the fill
                tp = entry_px * (1 + pos * cfg.take_profit * sigma)
                if (pos > 0 and h[i] >= tp + cfg.tick) or (pos < 0 and l[i] <= tp - cfg.tick):
                    close_pos(i, tp, "Target")
                    events.append((i, "TARGET"))

        if pos and (not in_rth or t_min == RTH_OPEN):  # a session ended early (half day, data gap)
            close_pos(i, c[i] - pos * slip, "Session ended")
            events.append((i, "EXIT"))

        if t_min == RTH_OPEN:
            prev_close = last_rth_close
            day_open = o[i]
            upper = lower = sigma = math.nan
            today = [math.nan] * N_CHECKS
            skip_today = t.strftime("%Y-%m-%d") in cfg.skip_dates  # substring test, like Pine's str.contains
            fed_today = cfg.fed_no_shorts and t.strftime("%Y-%m-%d") in cfg.fed_dates
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
                short_ok = not (fed_today and end < FED_CUTOFF)
                if skip_today:
                    pass
                elif use_stop and pos:
                    pass  # exits are the resting stop's job
                elif pos > 0 and c[i] < upper:
                    rev = c[i] < lower and short_ok
                    pending = ("entry", -1) if rev else ("close", 0)
                    events.append((i, "REVERSE" if rev else "EXIT"))
                elif pos < 0 and c[i] > lower:
                    pending = ("entry", 1) if c[i] > upper else ("close", 0)
                    events.append((i, "REVERSE" if c[i] > upper else "EXIT"))
                elif pos == 0 and c[i] > upper:
                    pending = ("entry", 1)
                    events.append((i, "BUY"))
                elif pos == 0 and c[i] < lower and short_ok:
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
