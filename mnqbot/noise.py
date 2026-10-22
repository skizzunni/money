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
  * nt_execution and round_prices (off by default) switch to the NinjaTrader strategy's execution instead: the
    bracket measured from the actual fill, the 16:00 exit at the next bar's open, a passed stop as a market exit,
    prices on the tick grid. With both on it matches MnqNoiseMomentum.cs trade for trade (docs/PARITY.md).
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
    "2025-01-01,2025-01-09,2025-01-20,2025-02-17,2025-04-18,2025-05-26,2025-06-19,2025-07-03,2025-07-04,2025-09-01,"
    "2025-11-27,2025-11-28,2025-12-24,2025-12-25,"
    "2026-01-01,2026-01-19,2026-02-16,2026-04-03,2026-05-25,2026-06-19,2026-07-03,2026-09-07,"
    "2026-11-26,2026-11-27,2026-12-24,2026-12-25,2027-01-01,2027-01-18,2027-02-15,2027-03-26,"
    "2027-05-31,2027-06-18,2027-07-05,2027-09-06,2027-11-25,2027-11-26,2027-12-24"
)
# Scheduled FOMC announcement days (statement at 14:00 New York time), from federalreserve.gov. Same list as
# the Pine input; research/fomc_dates.csv has 2011-2026.
FED_DATES = (
    "2025-01-29,2025-03-19,2025-05-07,2025-06-18,2025-07-30,2025-09-17,2025-10-29,2025-12-10,"
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
    # research only (v2.1 study, docs/RESULTS.md), all off by default: fewer losers in a row without a daily stop.
    # streak_k / streak_skip: after streak_k losing trades in a row (across days; a winner resets the count), skip the
    # next streak_skip entry signals. side_cooldown: after a losing trade, skip the next this many signals on that side
    # today. side_margin: after a losing trade today, a new entry on that side needs the close past the line by this
    # many more noise units (until a winner on that side or the next session).
    # the trade after a losing trade (research only, off by default): after_loss_qty_div divides the contracts (the same
    # max loss, so a wider stop); after_loss_lock sets its lock trigger (in its own max losses); after_loss_hourly takes
    # it only at a check on the hour
    after_loss_qty_div: float = 1.0
    after_loss_ml_mult: float = 1.0  # its max loss x this (the same contracts, a wider stop)
    # a second tier for two or more losers in a row (0: the same as after one loser), and the rule on the losing
    # trade's side only (another side: the normal size)
    after_loss2_qty_div: float = 0.0
    after_loss2_ml_mult: float = 0.0
    after_loss_same_side: bool = False
    after_loss_tp: float = 0.0  # its take-profit, noise units (0: take_profit)
    # research only (v2.3 study), off by default. entry_k: a new entry needs the close past the noise area widened by
    # this factor (the stops keep the area itself). late_tp / late_tp_from: entries from checks closing at or after
    # late_tp_from (minute of day) take late_tp noise units as their take-profit
    entry_k: float = 1.0
    # after a big session (its 09:30-16:00 range over big_day_k x the average of the last big_day_n sessions' ranges,
    # as a share of the open; that session included), no entries or heads-ups today in that session's direction (its
    # close against its open). 0 = off; the Pine script's default since v2.3 is 1.5 x the last 10 sessions
    big_day_k: float = 0.0
    big_day_n: int = 20
    big_day_against_tp: float = -1.0  # research: the take-profit of a trade against the big session (-1: as others)
    # research (after v2.3): a trade against the big session takes cfg.qty / big_day_against_qty_div contracts (the
    # same max loss, a wider stop); big_day_both: no entries at all the day after a big session
    big_day_against_qty_div: float = 1.0
    big_day_both: bool = False
    # research (after v2.3): after side_run_k losing trades in a row on one side (across days; a winner on that side
    # resets it), skip the next side_run_skip signals on that side
    side_run_k: int = 0
    side_run_skip: int = 1
    # research (v2.4 study): once the lock arms, add add_at_lock contracts at the next bar's open; they share the
    # position's exits (stop, lock, take-profit, 16:00) and close with it
    add_at_lock: int = 0
    # research (v2.4 study): the trend, the last session's close against the average of the last trend_n sessions'
    # closes. A trade against it (on side trend_side only; 0: both) is skipped, or with trend_qty_div > 0 takes
    # cfg.qty / trend_qty_div contracts (the same max loss)
    trend_n: int = 0
    trend_side: int = 0
    trend_qty_div: float = 0.0
    trend_ml_mult: float = 1.0  # the against-trend trade's max loss x this
    trend_with_mult: float = 1.0  # a trade with the trend: contracts and max loss x this (the same stop in points)
    trend_with_ml: float = 1.0  # a trade with the trend: its max loss x this (the same contracts)
    # research (v2.4 study): no new entries at these checks (minutes of the day the check's bar closes, e.g. "840")
    skip_checks: str = ""
    after_target_done: bool = False  # research: no new entries today after a take-profit fills
    # research (v2.4 study): the equity curve. While the closed-trade P&L is below its average over the last eq_n
    # trades (positions), a new entry takes cfg.qty / eq_div contracts and the max loss x eq_ml
    eq_n: int = 0
    eq_div: float = 2.0
    eq_ml: float = 1.0
    # a calm stretch: the last calm_short sessions' average range under calm_k x the last calm_long's. Then no new
    # entries or heads-ups today; research: with calm_div > 0, cfg.qty / calm_div contracts instead (the same max loss).
    # 0 = off; the Pine script's default since v2.5 is 0.7, 10 against 40 sessions
    calm_k: float = 0.0
    calm_div: float = 0.0
    calm_short: int = 10  # the sessions in the two averages
    calm_long: int = 60
    # research (v2.4 study): a first lock step. Once the trade has been lock1_at max losses in profit, the stop moves to
    # the entry plus lock1_plus points (negative: below the entry for a long), from the next bar; the lock proper later
    lock1_at: float = 0.0
    lock1_plus: float = 0.0
    confirm: bool = False  # research (v2.5 study): an entry needs the last check today past that side's line too
    # research (v2.5 study): the max loss in noise units, cap_sigma x the check's noise x the price (contracts as usual;
    # the dollar max loss then follows it, and the lock trigger with it); 0 = the dollar max loss
    cap_sigma: float = 0.0
    # research (v2.5 study): the lock arms only at a half-hour check, if the trade has reached the trigger since the
    # fill (on a 30-minute chart every bar is a check, so 5- and 30-minute charts then behave alike)
    lock_at_checks: bool = False
    # research (v2.5 study): the lock as the broker would run it inside the bar (a trailing stop that activates at the
    # trigger, offset trigger - lock_plus, through TradingView's bar path: the extreme nearer the open first). After
    # that bar the stop stays at the trailing level it reached (at least the entry + lock_plus)
    lock_intrabar: bool = False
    grace: bool = False  # research (v2.5 study): until the first check after the fill, the max loss stop only
    late_tp: float = 0.0
    late_tp_from: int = 0
    # research only (v2.2 study), off by default: a runner after the take-profit. tp_keep: the share of the contracts
    # kept open when the take-profit fills (rounded to whole contracts); the rest keeps every stop rule, plus
    # runner_lock (the stop at the entry plus this share of the take-profit's distance) and tp2 (a second take-profit,
    # noise units from the entry; 0 = none)
    tp_keep: float = 0.0
    # no new entries from checks closing after this minute of the day (900: 15:00, the Pine script's default since v2.2;
    # 0 = every check)
    last_entry_end: int = 0
    runner_lock: float = 0.0
    tp2: float = 0.0
    after_loss_lock: float = 0.0
    after_loss_hourly: bool = False
    streak_k: int = 0
    streak_skip: int = 1
    side_cooldown: int = 0
    side_margin: float = 0.0
    # research only (round 116), not in the Pine script or NinjaTrader: the paper's VWAP trailing stop. "checks": the
    # stop is also never looser than the day's VWAP as of the last check (long: max(stop, VWAP)); "bars": as of the
    # last bar's close. Volume-weighted typical price from 09:30; time-weighted where the data has no volume.
    vwap_stop: str = ""
    # research only (round 138), not in the Pine script, both off by default (partial_at is the NinjaTrader
    # strategy's PartialAtR with partial_r "initial"). R: see partial_r. trail_points: once the lock has armed, the
    # stop also sits this many points behind the best high (long) / low (short) since the entry, decided at a bar's
    # close, working from the next bar, never loosening. partial_at: this many R from the entry fill, a limit closes
    # partial_frac of the position (a tick through it; the stop first in a bar that reaches both); the rest keeps
    # every rule above.
    trail_points: float = 0.0
    partial_at: float = 0.0
    partial_frac: float = 0.5
    partial_next_bar: bool = False  # the part's limit works from the bar after the fill (as NinjaTrader can send it)
    # R for partial_at. "cap": max_loss_per_trade / qty / point_value (round 138). "initial": the trade's initial risk,
    # the bracket's stop distance from the expected fill (the closer of the line stop and the cap), and the part's
    # take-profit measured from the real fill and working from the fill bar, as the NinjaTrader strategy sends it: the
    # half as its own entry with its own take-profit
    partial_r: str = "cap"
    # NinjaTrader's execution (the MnqNoiseMomentum strategy as it sends its orders; docs/PARITY.md), off by default
    # so the Pine script's rules stay the default. nt_execution: the bracket sent with the entry is measured at the
    # signal from the expected fill (stop: the closer of the line stop and the max loss; take-profit) and placed that
    # many points from the actual fill; a stop the last bar's close has already passed is a market exit at this bar's
    # open ("Stop passed"); the 16:00 exit is a market order filled at the next bar's open. round_prices: orders on
    # the tick grid, the bracket's stop distance rounded down and its take-profit distance up, a moving stop rounded
    # toward the price and a take-profit away from it (NinjaTrader's RoundPrices, on there by default).
    nt_execution: bool = False
    round_prices: bool = False


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
    frac: float = 1.0  # the share of the position this record closes (partial_at: the part and the rest)


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
    consec = skip_left = 0  # the v2.1 study's streak rule: losers in a row, signals still to skip
    loss_side = 0  # the side of the last losing trade
    day_hi = day_lo = math.nan  # today's 09:30-16:00 high and low (big_day_k)
    day_ranges: list[float] = []  # completed sessions' range / open, oldest first
    day_dirs: list[int] = []  # and their direction (close against open)
    block_dir = 0  # big_day_k: no entries on this side today
    day_closes: list[float] = []  # completed sessions' closes (trend_n)
    trend = 0  # trend_n: the trend's direction today
    calm = False  # calm_k: today follows a calm stretch
    in_grace = False  # grace: no check since the fill yet
    fav = math.nan  # the best high (long) / low (short) since the fill, for the lock
    lock_px = math.nan  # lock_intrabar: the stop the in-bar lock reached
    prev_side = 0  # confirm: the last check today closed above its upper line (1), below its lower (-1), or inside
    target_today = False  # after_target_done: a take-profit filled today
    eq_curve: list[float] = [0.0]  # eq_n: the closed P&L after each position
    side_cd = {1: 0, -1: 0}  # signals still to skip on a side today (side_cooldown)
    side_lost = {1: False, -1: False}  # a loser on that side today (side_margin)
    side_run = {1: 0, -1: 0}  # losers in a row on each side, across days (side_run_k)
    side_skip = {1: 0, -1: 0}  # signals still to skip on each side (side_run_k)
    add_px, add_bar, add_due = math.nan, 0, False  # add_at_lock: the added contracts' fill, its bar, an add to send
    locked = False  # the trade has reached the lock trigger (a broker's auto-breakeven)
    locked1 = False  # lock1_at: the first step reached
    held, held_why = math.nan, ""  # tighten_only: the tightest stop so far in this trade, and what set it
    rest, part_pnl = 1.0, 0.0  # partial_at: the share still open, and what the closed part made
    tp_dist = math.nan  # tp_keep: the first take-profit's distance from the entry once it filled (the runner is on)
    best = math.nan  # trail_points: the best high (long) / low (short) since the entry, to the last bar's close
    r_pts = cfg.max_loss_per_trade / cfg.qty / cfg.point_value if cfg.max_loss_per_trade > 0 else math.nan
    if cfg.partial_r not in ("cap", "initial"):
        raise ValueError(f"partial_r must be 'cap' or 'initial', not {cfg.partial_r!r}")
    r_next = r_trade = math.nan  # partial_r "initial": the pending entry's initial risk, and the open trade's
    # nt_execution: the pending entry's bracket (points from the fill: stop, take-profit; what the stop is), and the
    # open trade's
    br_next: tuple[float, float, str] = (math.nan, math.nan, "")
    br_trade: tuple[float, float, str] = (math.nan, math.nan, "")
    tick = cfg.tick

    def ticks_down(points: float) -> float:
        return max(tick, math.floor(points / tick + 1e-7) * tick) if cfg.round_prices else points

    def ticks_up(points: float) -> float:
        return max(tick, math.ceil(points / tick - 1e-7) * tick) if cfg.round_prices and points == points else points

    def on_grid(d: int, price: float) -> float:
        """A long's stop and take-profit both round up (the stop toward the price, the take-profit away from it), a
        short's both down: a loss never goes past the max loss, a target never takes less than tested."""
        if not cfg.round_prices or math.isnan(price):
            return price
        n = price / tick
        return (math.ceil(n - 1e-7) if d > 0 else math.floor(n + 1e-7)) * tick
    vol = bars["volume"].to_numpy(float) if "volume" in bars else np.zeros(len(bars))
    pv_sum = v_sum = 0.0  # today's volume-weighted (or time-weighted) typical price, from 09:30
    vwap_now = vwap_used = math.nan
    pending: tuple[str, int] | None = None  # ("entry", direction) or ("close", 0), filled at the next open
    trades: list[NoiseTrade] = []
    events: list[tuple[int, str]] = []
    bands: list[tuple[int, float, float]] = []
    orders: list[tuple[int, int, float, float, float]] = []
    headsups: list[tuple[int, int]] = []

    q_next = q_trade = cfg.qty  # contracts of the pending entry and of the open trade (after_loss_qty_div)
    lock_next = lock_trade = cfg.lock_at  # their lock triggers, in max losses (after_loss_lock)
    ml_next = ml_trade = cfg.max_loss_per_trade  # their max losses, $ (after_loss_ml_mult)
    tp_next = tp_trade = cfg.take_profit  # their take-profits, noise units (after_loss_tp)

    def open_pos(i: int, d: int) -> None:
        nonlocal pos, entry_px, entry_bar, r_trade, br_trade, q_trade, lock_trade, ml_trade, tp_trade
        nonlocal in_grace
        in_grace = True
        pos, entry_px, entry_bar, r_trade, br_trade = d, o[i] + d * slip, i, r_next, br_next
        q_trade, lock_trade, ml_trade, tp_trade = q_next, lock_next, ml_next, tp_next

    def close_pos(i: int, price: float, reason: str) -> None:
        nonlocal pos, held, locked, losers_today, rest, part_pnl, best, consec, skip_left, loss_side, tp_dist
        nonlocal add_px, add_due, target_today, locked1, fav, lock_px
        pnl = rest * (pos * (price - entry_px) * q_trade * cfg.point_value - 2 * cfg.commission_per_side * q_trade)
        trades.append(NoiseTrade(pos, q_trade, entry_bar, idx[entry_bar], entry_px, i, idx[i], price, reason, pnl,
                                 rest))
        if not math.isnan(add_px):  # the added contracts close with the position (one trade for the loser count)
            n = cfg.add_at_lock
            ap = pos * (price - add_px) * n * cfg.point_value - 2 * cfg.commission_per_side * n
            trades.append(NoiseTrade(pos, cfg.add_at_lock, add_bar, idx[add_bar], add_px, i, idx[i], price, "Added",
                                     ap, 1.0))
            pnl += ap
        add_px, add_due = math.nan, False
        if cfg.eq_n:
            eq_curve.append(eq_curve[-1] + pnl + part_pnl)
        if reason == "Target":
            target_today = True
        if pnl + part_pnl < 0 and reason != "Session ended":  # a trade closed in parts is one trade
            losers_today += 1
            consec += 1
            loss_side = pos
            if cfg.streak_k and consec >= cfg.streak_k:
                skip_left = cfg.streak_skip
            side_cd[pos] = cfg.side_cooldown
            side_lost[pos] = True
            side_run[pos] += 1
            if cfg.side_run_k and side_run[pos] >= cfg.side_run_k:
                side_skip[pos], side_run[pos] = cfg.side_run_skip, 0
        elif pnl + part_pnl >= 0:
            consec = 0
            side_lost[pos] = False
            side_run[pos] = 0
        pos, held, locked, rest, part_pnl, best, tp_dist = 0, math.nan, False, 1.0, 0.0, math.nan, math.nan
        locked1, fav, lock_px = False, math.nan, math.nan

    def study_ok(d: int, past_margin: bool) -> bool:
        """The v2.1 study's rules (all off by default): may a signal on side d be taken?"""
        nonlocal skip_left
        if cfg.after_loss_hourly and consec > 0 and end % 60:
            return False
        if cfg.last_entry_end and end > cfg.last_entry_end:
            return False
        if cfg.skip_checks and str(end) in cfg.skip_checks.split(","):
            return False
        if cfg.after_target_done and target_today:
            return False
        if block_dir and (d == block_dir or cfg.big_day_both):
            return False
        if side_skip[d] > 0:
            side_skip[d] -= 1
            return False
        if against_trend(d) and not cfg.trend_qty_div:
            return False
        if calm and not cfg.calm_div:
            return False
        if cfg.confirm and prev_side != d:
            return False
        if cfg.side_margin and side_lost[d] and not past_margin:
            return False
        if side_cd[d] > 0:
            side_cd[d] -= 1
            return False
        if skip_left > 0:
            skip_left -= 1
            return False
        return True

    def against_trend(d: int) -> bool:
        return bool(cfg.trend_n) and d == -trend and cfg.trend_side in (0, d)

    def close_part(i: int, price: float, f: float | None = None) -> None:
        nonlocal rest, part_pnl
        f = cfg.partial_frac if f is None else f
        part_pnl = f * (pos * (price - entry_px) * q_trade * cfg.point_value - 2 * cfg.commission_per_side * q_trade)
        trades.append(NoiseTrade(pos, q_trade, entry_bar, idx[entry_bar], entry_px, i, idx[i], price, "Partial",
                                 part_pnl, f))
        rest = 1.0 - f

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
            elif kind == "flat" and pos:  # nt_execution: the 16:00 market exit
                close_pos(i, o[i] - pos * slip, "16:00 close")
            elif kind == "entry":
                if pos == -d:
                    close_pos(i, o[i] - pos * slip, "reversed")
                if pos == 0:
                    open_pos(i, d)
        if add_due and pos:  # add_at_lock: a market order from the last bar
            add_px, add_bar, add_due = o[i] + pos * slip, i, False

        # the resting stop at the line (checked before the script-side logic, like the broker)
        if use_stop and pos and not math.isnan(upper):
            line = upper * (1 - cfg.stop_buffer * sigma) if pos > 0 else lower * (1 + cfg.stop_buffer * sigma)
            reason = "Back inside"
            if cfg.grace and in_grace:  # research: no line stop yet, the max loss only
                line = -math.inf if pos > 0 else math.inf
            if cfg.max_loss_per_trade > 0:
                # from the fill price; on the fill bar itself from the expected fill (signal close + slippage), as a
                # bracket order placed with the entry would be
                base = entry_px if entry_bar != i else est_px
                cap = base - pos * ml_trade / q_trade / cfg.point_value
                if (pos > 0 and cap > line) or (pos < 0 and cap < line):
                    line, reason = cap, "Max loss"
            if cfg.vwap_stop and not math.isnan(vwap_used):  # the paper's trailing stop
                if (pos > 0 and vwap_used > line) or (pos < 0 and vwap_used < line):
                    line, reason = vwap_used, "VWAP"
            if locked1 and not locked:  # research: the first lock step
                lk1 = entry_px + pos * cfg.lock1_plus
                if (pos > 0 and lk1 > line) or (pos < 0 and lk1 < line):
                    line, reason = lk1, "Lock 1"
            if locked:  # a small win locked in: the stop at the entry plus lock_plus
                lk = entry_px + pos * cfg.lock_plus if math.isnan(lock_px) else lock_px
                if (pos > 0 and lk > line) or (pos < 0 and lk < line):
                    line, reason = lk, "Lock"
                if not math.isnan(tp_dist) and cfg.runner_lock > 0:  # research: the runner keeps part of the target
                    rl = entry_px + pos * cfg.runner_lock * tp_dist
                    if (pos > 0 and rl > line) or (pos < 0 and rl < line):
                        line, reason = rl, "Runner lock"
                if cfg.trail_points > 0 and not math.isnan(best):  # research: trailing behind the best price
                    tr = best - pos * cfg.trail_points
                    if (pos > 0 and tr > line) or (pos < 0 and tr < line):
                        line, reason = tr, "Trail"
            if cfg.nt_execution:
                if entry_bar == i:  # the bracket sent with the entry, points from the actual fill
                    line, reason = entry_px - pos * br_trade[0], br_trade[2]
                else:
                    line = on_grid(pos, line)
            if cfg.tighten_only:  # the broker's stop is placed with the entry and only ever tightened
                if entry_bar != i and ((pos > 0 and held > line) or (pos < 0 and held < line)):
                    line, reason = held, held_why
                held, held_why = line, reason
            if cfg.nt_execution and entry_bar != i and pos * (c[i - 1] - line) <= 0:
                hit, price, reason = True, o[i] - pos * slip, "Stop passed"  # sent at the last close, filled now
            elif entry_bar == i:  # a stop attached to the entry can fill on the fill bar itself
                hit = l[i] <= line if pos > 0 else h[i] >= line
                price = (min(o[i], line) if pos > 0 else max(o[i], line)) - pos * slip
            elif (pos > 0 and o[i] <= line) or (pos < 0 and o[i] >= line):  # the line moved past the price, or a gap
                hit, price = True, o[i] - pos * slip
            else:
                hit = l[i] <= line if pos > 0 else h[i] >= line
                price = line - pos * slip
            if (cfg.lock_intrabar and not locked and not hit and entry_bar != i and lock_trade > 0
                    and cfg.max_loss_per_trade > 0):
                trig = lock_trade * ml_trade / q_trade / cfg.point_value
                ext, adv = (h[i], l[i]) if pos > 0 else (l[i], h[i])
                tp_px = entry_px * (1 + pos * tp_trade * sigma) if tp_trade > 0 else math.nan
                if pos * (ext - entry_px) >= trig and not (pos * (ext - tp_px) >= cfg.tick):  # no target this bar
                    tr = ext - pos * (trig - cfg.lock_plus)
                    fav_first = (abs(h[i] - o[i]) <= abs(l[i] - o[i])) == (pos > 0)
                    after = adv if fav_first else c[i]  # where the path goes after the extreme
                    if pos * (after - tr) <= 0:
                        hit, price, reason = True, tr - pos * slip, "Lock"
                    lock_px = tr
            if hit:
                close_pos(i, price, reason)
                events.append((i, "EXIT"))
            initial = cfg.partial_r == "initial"
            r_now = r_trade if initial else r_pts
            if (pos and rest == 1.0 and cfg.partial_at > 0 and not math.isnan(r_now)  # research: part at +partial_at R
                    and not (cfg.partial_next_bar and entry_bar == i)):
                pt = (entry_px if entry_bar != i or initial else est_px) + pos * cfg.partial_at * r_now
                if (pos > 0 and h[i] >= pt + cfg.tick) or (pos < 0 and l[i] <= pt - cfg.tick):
                    close_part(i, pt)
            if not pos or hit:
                pass
            elif not math.isnan(tp_dist):  # research: the runner after the take-profit, and its second target
                if cfg.tp2 > 0:
                    t2 = entry_px * (1 + pos * cfg.tp2 * sigma)
                    if (pos > 0 and h[i] >= t2 + cfg.tick) or (pos < 0 and l[i] <= t2 - cfg.tick):
                        close_pos(i, t2, "Target 2")
                        events.append((i, "TARGET"))
            elif tp_trade > 0 and (entry_bar != i or cfg.target_on_fill_bar):  # the take-profit limit
                tp = (entry_px if entry_bar != i else est_px) * (1 + pos * tp_trade * sigma)
                if cfg.nt_execution:
                    tp = entry_px + pos * br_trade[1] if entry_bar == i else on_grid(pos, tp)
                if (pos > 0 and h[i] >= tp + cfg.tick) or (pos < 0 and l[i] <= tp - cfg.tick):
                    keep = round(q_trade * cfg.tp_keep) if cfg.tp_keep > 0 and rest == 1.0 else 0
                    if 0 < keep < q_trade:
                        close_part(i, tp, 1.0 - keep / q_trade)
                        tp_dist = abs(tp - entry_px)
                    else:
                        close_pos(i, tp, "Target")
                    events.append((i, "TARGET"))

        if pos and cfg.trail_points > 0:  # the best price so far, as of this bar's close (used from the next bar)
            bp = h[i] if pos > 0 else l[i]
            best = bp if math.isnan(best) else (max(best, bp) if pos > 0 else min(best, bp))

        if use_stop and pos and not locked and lock_trade > 0 and cfg.max_loss_per_trade > 0:
            # the lock arms when the bar reaches the trigger (high for a long, low for a short), from the next bar
            trigger = lock_trade * ml_trade / q_trade / cfg.point_value
            fav = (h[i] if pos > 0 else l[i]) if math.isnan(fav) else (max(fav, h[i]) if pos > 0 else min(fav, l[i]))
            at_check = FIRST_CHECK <= end <= LAST_CHECK and (end - FIRST_CHECK) % STEP == 0
            if not cfg.lock_at_checks or at_check:
                locked = pos * (fav - entry_px) >= trigger
            add_due = locked and cfg.add_at_lock > 0
            if cfg.lock1_at > 0 and not locked1:
                t1 = cfg.lock1_at * ml_trade / q_trade / cfg.point_value
                locked1 = pos * ((h[i] if pos > 0 else l[i]) - entry_px) >= t1

        if pos and (not in_rth or t_min == RTH_OPEN):  # a session ended early (half day, data gap)
            close_pos(i, c[i] - pos * slip, "Session ended")
            events.append((i, "EXIT"))

        if t_min == RTH_OPEN:
            block_dir = 0
            target_today = False
            prev_side = 0
            if cfg.calm_k and len(day_ranges) >= cfg.calm_long:
                cs, cl = cfg.calm_short, cfg.calm_long
                calm = sum(day_ranges[-cs:]) / cs < cfg.calm_k * (sum(day_ranges[-cl:]) / cl)  # as the Pine script
            if cfg.trend_n and len(day_closes) >= cfg.trend_n:
                ma = sum(day_closes[-cfg.trend_n:]) / cfg.trend_n
                trend = 1 if day_closes[-1] > ma else -1 if day_closes[-1] < ma else 0
            if cfg.big_day_k > 0 and len(day_ranges) >= cfg.big_day_n:
                avg = sum(day_ranges[-cfg.big_day_n:]) / cfg.big_day_n
                if day_ranges[-1] > cfg.big_day_k * avg:
                    block_dir = day_dirs[-1]
            day_hi = day_lo = math.nan
            pv_sum = v_sum = 0.0
            vwap_now = vwap_used = math.nan
            prev_close = last_rth_close
            day_open = o[i]
            losers_today = 0
            side_cd[1] = side_cd[-1] = 0
            side_lost[1] = side_lost[-1] = False
            upper = lower = sigma = math.nan
            today = [math.nan] * N_CHECKS
            skip_today = t.strftime("%Y-%m-%d") in cfg.skip_dates  # substring test, like Pine's str.contains
            fed_today = cfg.fed_no_shorts and t.strftime("%Y-%m-%d") in cfg.fed_dates
        if in_rth:
            last_rth_close = c[i]
            day_hi = h[i] if math.isnan(day_hi) else max(day_hi, h[i])
            day_lo = l[i] if math.isnan(day_lo) else min(day_lo, l[i])
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
                up_e, lo_e = upper, lower  # the entry lines (entry_k: a wider area for entries only)
                if cfg.entry_k != 1.0:
                    up_e = max(day_open, prev_close) * (1 + cfg.entry_k * sigma)
                    lo_e = min(day_open, prev_close) * (1 - cfg.entry_k * sigma)
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
                elif pos == 0 and c[i] > up_e and fresh_ok:
                    if study_ok(1, c[i] > upper * (1 + cfg.side_margin * sigma)):
                        pending = ("entry", 1)
                        events.append((i, "BUY"))
                elif pos == 0 and c[i] < lo_e and short_ok and fresh_ok:
                    if study_ok(-1, c[i] < lower * (1 - cfg.side_margin * sigma)):
                        pending = ("entry", -1)
                        events.append((i, "SELL"))
                prev_side = 1 if c[i] > upper else -1 if c[i] < lower else 0  # confirm: for the next check
                in_grace = False
                if pending is not None and pending[0] == "entry":
                    d = pending[1]
                    after_loss = consec > 0 and (not cfg.after_loss_same_side or d == loss_side)
                    tier2 = after_loss and consec >= 2 and (cfg.after_loss2_qty_div or cfg.after_loss2_ml_mult)
                    qd = (cfg.after_loss2_qty_div or 1.0) if tier2 else cfg.after_loss_qty_div
                    mm = (cfg.after_loss2_ml_mult or 1.0) if tier2 else cfg.after_loss_ml_mult
                    q_next = max(1, round(cfg.qty / qd)) if after_loss else cfg.qty
                    ml_next = cfg.max_loss_per_trade * (mm if after_loss else 1.0)
                    if cfg.cap_sigma > 0:
                        ml_next = cfg.cap_sigma * sigma * c[i] * q_next * cfg.point_value * (mm if after_loss else 1.0)
                    if cfg.trend_qty_div and against_trend(d):
                        q_next = max(1, round(q_next / cfg.trend_qty_div))
                        ml_next *= cfg.trend_ml_mult
                    elif cfg.trend_n and d == trend:
                        q_next = max(1, round(q_next * cfg.trend_with_mult))
                        ml_next *= cfg.trend_with_mult * cfg.trend_with_ml
                    if calm and cfg.calm_div:
                        q_next = max(1, round(q_next / cfg.calm_div))
                    if cfg.eq_n and len(eq_curve) > cfg.eq_n:
                        if eq_curve[-1] < sum(eq_curve[-cfg.eq_n:]) / cfg.eq_n:
                            q_next = max(1, round(q_next / cfg.eq_div))
                            ml_next *= cfg.eq_ml
                    if cfg.big_day_against_qty_div != 1.0 and block_dir == -d:
                        q_next = max(1, round(q_next / cfg.big_day_against_qty_div))
                    lock_next = cfg.after_loss_lock if (after_loss and cfg.after_loss_lock > 0) else cfg.lock_at
                    tp_next = cfg.after_loss_tp if (after_loss and cfg.after_loss_tp > 0) else cfg.take_profit
                    if cfg.late_tp > 0 and end >= cfg.late_tp_from:
                        tp_next = cfg.late_tp
                    if cfg.big_day_against_tp >= 0 and block_dir == -d:
                        tp_next = cfg.big_day_against_tp
                    est_px = c[i] + d * slip  # the expected fill, for the max loss on the fill bar
                    stop = tp = math.nan
                    if use_stop:  # the bracket: the closer of the line stop and the max loss, and the take-profit
                        stop = upper * (1 - cfg.stop_buffer * sigma) if d > 0 else lower * (1 + cfg.stop_buffer * sigma)
                        at_line = stop
                        if cfg.max_loss_per_trade > 0:
                            cap = est_px - d * ml_next / q_next / cfg.point_value
                            stop = max(stop, cap) if d > 0 else min(stop, cap)
                        if tp_next > 0:
                            tp = est_px * (1 + d * tp_next * sigma)
                    r_next = abs(est_px - stop) if use_stop else math.nan
                    if use_stop:
                        why = "Max loss" if stop != at_line else "Back inside"
                        br_next = (ticks_down(d * (est_px - stop)), ticks_up(d * (tp - est_px)), why)
                    orders.append((i, d, est_px, stop, tp))

        # heads-up: five minutes before a check, flat, and the close already past that check's line (round fifty)
        nxt = end + 5
        if (in_rth and 5 % minutes == 0 and not math.isnan(day_open) and FIRST_CHECK <= nxt <= LAST_CHECK
                and (nxt - FIRST_CHECK) % STEP == 0 and filled >= lb_n and not math.isnan(prev_close) and pos == 0
                and not skip_today and (cfg.max_losers <= 0 or losers_today < cfg.max_losers)
                and not (cfg.last_entry_end and nxt > cfg.last_entry_end) and not (calm and not cfg.calm_div)):
            k = (nxt - FIRST_CHECK) // STEP
            s = 0.0
            for d in range(lb_n):  # same summation order as the check
                s += ring[d * N_CHECKS + k]
            sg = s / lb_n
            if c[i] > max(day_open, prev_close) * (1 + sg):
                if block_dir != 1:
                    headsups.append((i, 1))
            elif c[i] < min(day_open, prev_close) * (1 - sg) and not (fed_today and nxt < FED_CUTOFF):
                if block_dir != -1:
                    headsups.append((i, -1))

        if in_rth and end == RTH_CLOSE:
            if pos and cfg.nt_execution:
                pending = ("flat", 0)  # a market order, filled at the next bar's open
                events.append((i, "FLAT"))
            elif pos:
                close_pos(i, c[i] - pos * slip, "16:00 close")
                events.append((i, "FLAT"))
            if not math.isnan(day_open) and not math.isnan(day_hi):  # big_day_k's session record
                day_ranges.append((day_hi - day_lo) / day_open)
                day_dirs.append(1 if c[i] > day_open else -1 if c[i] < day_open else 0)
                day_closes.append(c[i])
            if not math.isnan(day_open) and not any(math.isnan(x) for x in today):
                ring[slot * N_CHECKS : (slot + 1) * N_CHECKS] = today
                slot = (slot + 1) % lb_n
                filled += 1
            day_open = math.nan

    return NoiseResult(trades, events, bands, orders, headsups)
