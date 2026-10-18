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
    A second stop sits max_loss_per_trade dollars (for the whole position) from the entry fill; whichever stop
    is closer is the one in force ("Max loss" when it is the cap). On the fill bar it is measured from the
    expected fill (the signal close plus slippage), as a bracket order placed with the entry would be.
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
    lock_at: float = 1.0  # once the trade has been this many max losses in profit, the stop moves to entry + lock_plus
    lock_plus: float = 2.5  # points; with lock_at 0 or no max loss, no lock (round thirty-seven)
    max_losers: int = 4  # no new entries today after this many losing trades today; 0 = no limit (round thirty-eight)
    tighten_only: bool = False  # webhook mode: in a trade the stop never moves away from the price (round thirty-five)
    # the take-profit also works on the fill bar, from the expected fill, as a bracket sent with the entry does
    # (the NinjaTrader strategy); off: from the bar after the fill, as the Pine script places it
    target_on_fill_bar: bool = False
    # research only (round 116), not in the Pine script or NinjaTrader: the paper's VWAP trailing stop. "checks": the
    # stop is also never looser than the day's VWAP as of the last check (long: max(stop, VWAP)); "bars": as of the
    # last bar's close. Volume-weighted typical price from 09:30; time-weighted where the data has no volume.
    vwap_stop: str = ""


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
    # (signal bar, direction, expected fill, stop, take-profit) for every entry: the bracket sent with it (nan: none)
    orders: list[tuple[int, int, float, float, float]] = field(default_factory=list)
    # (bar, direction) five minutes before a check, when flat and the close is already past that check's line
    headsups: list[tuple[int, int]] = field(default_factory=list)

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
    est_px = math.nan  # expected fill of the pending entry
    losers_today = 0  # losing trades closed today
    locked = False  # the trade has reached the lock trigger (a broker's auto-breakeven)
    held, held_why = math.nan, ""  # tighten_only: the tightest stop so far in this trade, and what set it
    vol = bars["volume"].to_numpy(float) if "volume" in bars else np.zeros(len(bars))
    pv_sum = v_sum = 0.0  # today's volume-weighted (or time-weighted) typical price, from 09:30
    vwap_now = vwap_used = math.nan
    pending: tuple[str, int] | None = None  # ("entry", direction) or ("close", 0), filled at the next open
    trades: list[NoiseTrade] = []
    events: list[tuple[int, str]] = []
    bands: list[tuple[int, float, float]] = []
    orders: list[tuple[int, int, float, float, float]] = []
    headsups: list[tuple[int, int]] = []

    def open_pos(i: int, d: int) -> None:
        nonlocal pos, entry_px, entry_bar
        pos, entry_px, entry_bar = d, o[i] + d * slip, i

    def close_pos(i: int, price: float, reason: str) -> None:
        nonlocal pos, held, locked, losers_today
        pnl = pos * (price - entry_px) * cfg.qty * cfg.point_value - 2 * cfg.commission_per_side * cfg.qty
        trades.append(NoiseTrade(pos, cfg.qty, entry_bar, idx[entry_bar], entry_px, i, idx[i], price, reason, pnl))
        if pnl < 0 and reason != "Session ended":
            losers_today += 1
        pos, held, locked = 0, math.nan, False

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
            if cfg.max_loss_per_trade > 0:
                # from the fill price; on the fill bar itself from the expected fill (signal close + slippage), as a
                # bracket order placed with the entry would be
                base = entry_px if entry_bar != i else est_px
                cap = base - pos * cfg.max_loss_per_trade / cfg.qty / cfg.point_value
                if (pos > 0 and cap > line) or (pos < 0 and cap < line):
                    line, reason = cap, "Max loss"
            if cfg.vwap_stop and not math.isnan(vwap_used):  # the paper's trailing stop
                if (pos > 0 and vwap_used > line) or (pos < 0 and vwap_used < line):
                    line, reason = vwap_used, "VWAP"
            if locked:  # a small win locked in: the stop at the entry plus lock_plus
                lk = entry_px + pos * cfg.lock_plus
                if (pos > 0 and lk > line) or (pos < 0 and lk < line):
                    line, reason = lk, "Lock"
            if cfg.tighten_only:  # the broker's stop is placed with the entry and only ever tightened
                if entry_bar != i and ((pos > 0 and held > line) or (pos < 0 and held < line)):
                    line, reason = held, held_why
                held, held_why = line, reason
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
            elif cfg.take_profit > 0 and (entry_bar != i or cfg.target_on_fill_bar):  # the take-profit limit
                tp = (entry_px if entry_bar != i else est_px) * (1 + pos * cfg.take_profit * sigma)
                if (pos > 0 and h[i] >= tp + cfg.tick) or (pos < 0 and l[i] <= tp - cfg.tick):
                    close_pos(i, tp, "Target")
                    events.append((i, "TARGET"))

        if use_stop and pos and not locked and cfg.lock_at > 0 and cfg.max_loss_per_trade > 0:
            # the lock arms when the bar reaches the trigger (high for a long, low for a short), from the next bar
            trigger = cfg.lock_at * cfg.max_loss_per_trade / cfg.qty / cfg.point_value
            locked = pos * ((h[i] if pos > 0 else l[i]) - entry_px) >= trigger

        if pos and (not in_rth or t_min == RTH_OPEN):  # a session ended early (half day, data gap)
            close_pos(i, c[i] - pos * slip, "Session ended")
            events.append((i, "EXIT"))

        if t_min == RTH_OPEN:
            pv_sum = v_sum = 0.0
            vwap_now = vwap_used = math.nan
            prev_close = last_rth_close
            day_open = o[i]
            losers_today = 0
            upper = lower = sigma = math.nan
            today = [math.nan] * N_CHECKS
            skip_today = t.strftime("%Y-%m-%d") in cfg.skip_dates  # substring test, like Pine's str.contains
            fed_today = cfg.fed_no_shorts and t.strftime("%Y-%m-%d") in cfg.fed_dates
        if in_rth:
            last_rth_close = c[i]
            if cfg.vwap_stop:
                w = vol[i] if vol[i] > 0 else 1.0
                pv_sum += w * (h[i] + l[i] + c[i]) / 3
                v_sum += w
                vwap_now = pv_sum / v_sum
                if cfg.vwap_stop == "bars":
                    vwap_used = vwap_now

        if in_rth and not math.isnan(day_open) and FIRST_CHECK <= end <= LAST_CHECK and (end - FIRST_CHECK) % STEP == 0:
            k = (end - FIRST_CHECK) // STEP
            today[k] = abs(c[i] / day_open - 1)
            if cfg.vwap_stop == "checks":
                vwap_used = vwap_now
            if filled >= lb_n and not math.isnan(prev_close):
                s = 0.0
                for d in range(lb_n):  # same summation order as the Pine loop
                    s += ring[d * N_CHECKS + k]
                sigma = s / lb_n
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                bands.append((i, upper, lower))
                short_ok = not (fed_today and end < FED_CUTOFF)
                fresh_ok = cfg.max_losers <= 0 or losers_today < cfg.max_losers  # the daily limit: new entries
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
                elif pos == 0 and c[i] > upper and fresh_ok:
                    pending = ("entry", 1)
                    events.append((i, "BUY"))
                elif pos == 0 and c[i] < lower and short_ok and fresh_ok:
                    pending = ("entry", -1)
                    events.append((i, "SELL"))
                if pending is not None and pending[0] == "entry":
                    d = pending[1]
                    est_px = c[i] + d * slip  # the expected fill, for the max loss on the fill bar
                    stop = tp = math.nan
                    if use_stop:  # the bracket: the closer of the line stop and the max loss, and the take-profit
                        stop = upper * (1 - cfg.stop_buffer * sigma) if d > 0 else lower * (1 + cfg.stop_buffer * sigma)
                        if cfg.max_loss_per_trade > 0:
                            cap = est_px - d * cfg.max_loss_per_trade / cfg.qty / cfg.point_value
                            stop = max(stop, cap) if d > 0 else min(stop, cap)
                        if cfg.take_profit > 0:
                            tp = est_px * (1 + d * cfg.take_profit * sigma)
                    orders.append((i, d, est_px, stop, tp))

        # heads-up: five minutes before a check, flat, and the close already past that check's line (round fifty)
        nxt = end + 5
        if (in_rth and 5 % minutes == 0 and not math.isnan(day_open) and FIRST_CHECK <= nxt <= LAST_CHECK
                and (nxt - FIRST_CHECK) % STEP == 0 and filled >= lb_n and not math.isnan(prev_close) and pos == 0
                and not skip_today and (cfg.max_losers <= 0 or losers_today < cfg.max_losers)):
            k = (nxt - FIRST_CHECK) // STEP
            s = 0.0
            for d in range(lb_n):  # same summation order as the check
                s += ring[d * N_CHECKS + k]
            sg = s / lb_n
            if c[i] > max(day_open, prev_close) * (1 + sg):
                headsups.append((i, 1))
            elif c[i] < min(day_open, prev_close) * (1 - sg) and not (fed_today and nxt < FED_CUTOFF):
                headsups.append((i, -1))

        if in_rth and end == RTH_CLOSE:
            if pos:
                close_pos(i, c[i] - pos * slip, "16:00 close")
                events.append((i, "FLAT"))
            if not math.isnan(day_open) and not any(math.isnan(x) for x in today):
                ring[slot * N_CHECKS : (slot + 1) * N_CHECKS] = today
                slot = (slot + 1) % lb_n
                filled += 1
            day_open = math.nan

    return NoiseResult(trades, events, bands, orders, headsups)
