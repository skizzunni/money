"""Bar-by-bar backtester with prop-firm risk rails.

Fill rules are deliberately pessimistic, because an optimistic backtest is
how people talk themselves into blowing an account:
  * Limit entries/targets fill only if price trades *through* them
    (``limit_fill_through_ticks``), and always at the limit price.
  * Stops fill with slippage, and at the open if the bar gaps past them.
  * If a bar touches both stop and target, the stop wins.
  * On the bar an entry fills, only the stop is checked (no same-bar target),
    and breakeven moves wait for the next bar.

It also runs back-to-back prop evaluations: each "attempt" starts with a
fresh account, trails an end-of-day drawdown line, and ends in a pass
(target + min days + consistency) or a fail (equity touches the line).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .config import BotConfig
from .data import annotate
from .strategy import Setup, SignalEngine, _hhmm


@dataclass
class Trade:
    trade_date: date
    direction: int
    qty: int
    level: str
    setup_time: pd.Timestamp
    entry_time: pd.Timestamp
    entry: float
    stop: float
    target: float
    exit_time: pd.Timestamp
    exit: float
    reason: str
    gross: float
    costs: float
    pnl: float
    risk_dollars: float
    attempt: int

    @property
    def r(self) -> float:
        return self.pnl / self.risk_dollars if self.risk_dollars else 0.0

    @property
    def side(self) -> str:
        return "long" if self.direction > 0 else "short"


@dataclass
class Attempt:
    number: int
    start_date: date
    end_date: date | None = None
    outcome: str = "open"  # passed / failed / open
    note: str = ""  # why it failed: "breached" the drawdown line or "stalled" too close to it to trade
    sessions: int = 0
    trading_days: int = 0
    profit: float = 0.0
    best_day: float = 0.0


@dataclass
class BacktestResult:
    trades: list[Trade]
    daily: pd.DataFrame
    attempts: list[Attempt]
    equity: pd.Series
    skipped: dict[str, int]
    bars: pd.DataFrame
    config: BotConfig
    orders: list[tuple[Setup, int]] = field(default_factory=list)  # every limit order placed, filled or not
    funnel: dict = field(default_factory=dict)  # sweeps -> setups -> dropped -> signals -> filled

    def trades_frame(self) -> pd.DataFrame:
        rows = []
        for t in self.trades:
            row = {k: getattr(t, k) for k in t.__dataclass_fields__}
            row["side"], row["r"] = t.side, t.r
            rows.append(row)
        return pd.DataFrame(rows)


@dataclass
class _Pending:
    setup: Setup
    qty: int


@dataclass
class _Position:
    setup: Setup
    qty: int
    entry_bar: int
    stop: float
    be_done: bool = False


@dataclass
class _AttemptState:
    number: int
    start_cum: float
    start_date: date
    peak_eod: float = 0.0
    sessions: int = 0
    trading_days: int = 0
    day_pnls: list[float] = field(default_factory=list)
    failed: bool = False
    buffer_skips: int = 0  # setups in a row too big for the remaining drawdown buffer


def per_contract_risk(cfg: BotConfig, risk_points: float) -> float:
    """Worst-case $ loss for one contract stopped out, including fees and slippage."""
    inst, costs = cfg.instrument, cfg.costs
    return (
        risk_points * inst.point_value
        + 2 * costs.commission_per_side
        + costs.slippage_ticks * inst.tick_size * inst.point_value
    )


def min_tradable_buffer(cfg: BotConfig) -> float:
    """Distance to the drawdown line below which even the tightest allowed trade can't be sized.

    An account that sits there can't trade and can't fail; a real trader would
    pay for a reset, so the simulations count it as a failed attempt.
    """
    one = per_contract_risk(cfg, cfg.strategy.min_stop_points)
    frac = cfg.risk.drawdown_buffer_frac
    return one / frac if frac > 0 else one


class Backtester:
    def __init__(self, bars: pd.DataFrame, cfg: BotConfig | None = None):
        self.cfg = cfg or BotConfig()
        self.bars = bars if "trade_date" in bars.columns else annotate(bars)
        if len(self.bars) == 0:
            raise ValueError("no bars to backtest")

    # ---------------------------------------------------------------- sizing
    def per_contract_risk(self, risk_points: float) -> float:
        return per_contract_risk(self.cfg, risk_points)

    def size(self, risk_points: float, day_pnl: float, buffer: float) -> int:
        risk = self.cfg.risk
        budget = min(
            risk.risk_per_trade,
            risk.daily_max_loss + day_pnl,
            risk.drawdown_buffer_frac * buffer,
        )
        per = self.per_contract_risk(risk_points)
        if budget <= 0 or per <= 0:
            return 0
        qty = math.floor(budget / per + 1e-9)
        return max(0, min(qty, risk.max_contracts, self.cfg.prop.max_contracts))

    # ------------------------------------------------------------------- run
    def run(self) -> BacktestResult:
        cfg, b = self.cfg, self.bars
        inst, costs, risk, prop = cfg.instrument, cfg.costs, cfg.risk, cfg.prop
        tick, pv = inst.tick_size, inst.point_value
        slip = costs.slippage_ticks * tick
        thru = costs.limit_fill_through_ticks * tick
        flatten = _hhmm(cfg.strategy.flatten_at)
        lock_rel = prop.lock_level - prop.start_balance
        stall_buffer = min_tradable_buffer(cfg)
        stall_skips = 3
        skip_days = set(risk.no_trade_dates)
        blackouts = [tuple(_hhmm(x) for x in w.split("-")) for w in risk.blackout_windows]

        o = b["open"].to_numpy(float)
        h = b["high"].to_numpy(float)
        l = b["low"].to_numpy(float)
        c = b["close"].to_numpy(float)
        hhmm = b["hhmm"].to_numpy(int)
        days = b["trade_date"].to_numpy()
        times = b.index

        sig = SignalEngine(b, cfg.strategy, inst)
        trades: list[Trade] = []
        daily_rows: list[dict] = []
        attempts: list[Attempt] = []
        skipped: dict[str, int] = {}
        orders: list[tuple[Setup, int]] = []
        n_filled = n_unfilled = 0
        equity = [0.0] * len(b)

        cum = 0.0  # realized net P/L since the start of the backtest
        pending: _Pending | None = None
        pos: _Position | None = None
        att = _AttemptState(1, 0.0, days[0])
        cur_day = None
        day_start_cum = day_worst = 0.0
        day_trades = 0
        day_blocked = False  # account failed today

        def threshold() -> float:
            return min(att.peak_eod - prop.max_drawdown, lock_rel)

        def close_pos(i: int, price: float, reason: str) -> None:
            nonlocal pos, cum
            p = pos
            d = p.setup.direction
            gross = d * (price - p.setup.entry) * p.qty * pv
            fee = 2 * costs.commission_per_side * p.qty
            cum += gross - fee
            trades.append(
                Trade(
                    trade_date=days[i],
                    direction=d,
                    qty=p.qty,
                    level=p.setup.level_name,
                    setup_time=times[p.setup.bar],
                    entry_time=times[p.entry_bar],
                    entry=p.setup.entry,
                    stop=p.setup.stop,
                    target=p.setup.target,
                    exit_time=times[i],
                    exit=price,
                    reason=reason,
                    gross=gross,
                    costs=fee,
                    pnl=gross - fee,
                    risk_dollars=p.qty * self.per_contract_risk(p.setup.risk_points),
                    attempt=att.number,
                )
            )
            pos = None

        def finish_attempt(outcome: str, end: date | None, note: str = "") -> None:
            attempts.append(
                Attempt(
                    number=att.number,
                    start_date=att.start_date,
                    end_date=end if outcome != "open" else None,
                    outcome=outcome,
                    note=note,
                    sessions=att.sessions,
                    trading_days=att.trading_days,
                    profit=cum - att.start_cum,
                    best_day=max(att.day_pnls, default=0.0),
                )
            )

        def consistent(total: float, day_pnls: list[float]) -> bool:
            frac = prop.consistency_max_day_frac
            return frac <= 0 or max(day_pnls, default=0.0) < frac * total

        def end_day(last_i: int) -> None:
            nonlocal att
            day_pnl = cum - day_start_cum
            daily_rows.append(
                {
                    "trade_date": cur_day,
                    "pnl": day_pnl,
                    "trades": day_trades,
                    "worst": day_worst,
                    "hit_loss_limit": day_pnl <= -risk.daily_max_loss,
                    "hit_profit_lock": day_pnl >= risk.daily_profit_lock,
                    "attempt": att.number,
                }
            )
            att.sessions += 1
            if day_trades:
                att.trading_days += 1
                att.day_pnls.append(day_pnl)
            outcome, note = None, ""
            if att.failed:
                outcome, note = "failed", "breached"
            else:
                rel = cum - att.start_cum
                att.peak_eod = max(att.peak_eod, rel)
                if (
                    rel >= prop.profit_target
                    and att.trading_days >= prop.min_trading_days
                    and consistent(rel, att.day_pnls)
                ):
                    outcome = "passed"
                elif rel - threshold() < stall_buffer or att.buffer_skips >= stall_skips:
                    outcome, note = "failed", "stalled"
            if outcome:
                finish_attempt(outcome, cur_day, note)
                att = _AttemptState(att.number + 1, cum, days[min(last_i + 1, len(days) - 1)])

        def blocked(i: int) -> str | None:
            day_pnl = cum - day_start_cum
            if pos is not None or pending is not None:
                return "busy"
            if day_blocked:
                return "account_failed"
            if str(cur_day) in skip_days:
                return "no_trade_day"
            if any(a <= hhmm[i] < z for a, z in blackouts):
                return "news_blackout"
            if hhmm[i] >= flatten:
                return "late"
            if day_trades >= risk.max_trades_per_day:
                return "max_trades"
            if day_pnl <= -risk.daily_max_loss:
                return "daily_loss"
            if day_pnl >= risk.daily_profit_lock:
                return "profit_lock"
            rel = cum - att.start_cum
            if rel >= prop.profit_target:
                days_if_done = att.trading_days + (1 if day_trades else 0)
                pnls = att.day_pnls + ([day_pnl] if day_trades else [])
                if days_if_done >= prop.min_trading_days and consistent(rel, pnls):
                    return "target_reached"
            return None

        for i in range(len(b)):
            # ---- new trading day
            if days[i] != cur_day:
                if cur_day is not None:
                    if pos is not None:
                        close_pos(i - 1, c[i - 1], "day_end")
                    pending = None
                    end_day(i - 1)
                cur_day = days[i]
                day_start_cum = cum
                day_worst = 0.0
                day_trades = 0
                day_blocked = False

            # ---- working entry order
            if pending is not None:
                s = pending.setup
                if hhmm[i] >= flatten or day_blocked:
                    pending = None
                    n_unfilled += 1
                else:
                    d = s.direction
                    filled = h[i] >= s.entry + thru if d < 0 else l[i] <= s.entry - thru
                    if filled:
                        pos = _Position(s, pending.qty, i, s.stop)
                        pending = None
                        day_trades += 1
                        n_filled += 1
                        stopped = h[i] >= pos.stop if d < 0 else l[i] <= pos.stop
                        if stopped:
                            close_pos(i, pos.stop + slip if d < 0 else pos.stop - slip, "stop")
                    else:
                        missed = l[i] <= s.target if d < 0 else h[i] >= s.target
                        if missed or i - s.bar >= cfg.strategy.order_expiry_bars:
                            pending = None
                            n_unfilled += 1

            # ---- open position (entered on an earlier bar)
            if pos is not None and pos.entry_bar < i:
                s, d = pos.setup, pos.setup.direction
                stop_reason = "breakeven" if pos.be_done else "stop"
                if d < 0:
                    if o[i] >= pos.stop:
                        close_pos(i, o[i] + slip, stop_reason)
                    elif h[i] >= pos.stop:
                        close_pos(i, pos.stop + slip, stop_reason)
                    elif l[i] <= s.target - thru:
                        close_pos(i, s.target, "target")
                else:
                    if o[i] <= pos.stop:
                        close_pos(i, o[i] - slip, stop_reason)
                    elif l[i] <= pos.stop:
                        close_pos(i, pos.stop - slip, stop_reason)
                    elif h[i] >= s.target + thru:
                        close_pos(i, s.target, "target")
                be_r = cfg.strategy.breakeven_at_r
                if pos is not None and be_r > 0 and not pos.be_done:
                    trigger = s.entry + d * be_r * s.risk_points
                    if (d < 0 and l[i] <= trigger) or (d > 0 and h[i] >= trigger):
                        pos.stop = s.entry
                        pos.be_done = True

            # ---- prop drawdown line (checked against the bar's worst price)
            unreal_worst = 0.0
            if pos is not None:
                s, d = pos.setup, pos.setup.direction
                adverse = h[i] if d < 0 else l[i]
                unreal_worst = d * (adverse - s.entry) * pos.qty * pv
            rel_worst = cum - att.start_cum + unreal_worst
            day_worst = min(day_worst, cum - day_start_cum + unreal_worst)
            if not att.failed and rel_worst <= threshold():
                att.failed = True
                day_blocked = True
                if pending is not None:
                    n_unfilled += 1
                pending = None
                if pos is not None:
                    s, d = pos.setup, pos.setup.direction
                    room = (cum - att.start_cum) - threshold()
                    px = s.entry - d * room / (pos.qty * pv)
                    close_pos(i, min(max(px, l[i]), h[i]), "liquidated")

            # ---- end-of-session flatten
            if pos is not None and hhmm[i] >= flatten:
                d = pos.setup.direction
                close_pos(i, c[i] - slip if d > 0 else c[i] + slip, "flatten")

            # ---- signals (state advances every bar, orders only when allowed)
            setup = sig.step(i)
            if setup is not None:
                why = blocked(i)
                if why is None:
                    buffer = (cum - att.start_cum) - threshold()
                    qty = self.size(setup.risk_points, cum - day_start_cum, buffer)
                    if qty >= 1:
                        pending = _Pending(setup, qty)
                        orders.append((setup, qty))
                        att.buffer_skips = 0
                    else:
                        why = "size_zero"
                        if risk.drawdown_buffer_frac * buffer < self.per_contract_risk(setup.risk_points):
                            att.buffer_skips += 1
                if why:
                    skipped[why] = skipped.get(why, 0) + 1

            unreal_close = 0.0
            if pos is not None:
                s = pos.setup
                unreal_close = s.direction * (c[i] - s.entry) * pos.qty * pv
            equity[i] = cum + unreal_close

        last = len(b) - 1
        if pos is not None:
            close_pos(last, c[last], "end_of_data")
            equity[last] = cum
        end_day(last)
        if att.sessions:
            finish_attempt("open", None)

        daily = pd.DataFrame(daily_rows).set_index("trade_date")
        risks = sig.setup_risks
        lo, hi = cfg.strategy.min_stop_points, cfg.strategy.max_stop_points
        funnel = {
            "days": int(b.groupby("trade_date")["is_rth"].any().sum()),
            "sweeps": sig.n_sweeps,
            "setups": len(risks),
            "stop_too_tight": sum(r < lo for r in risks),
            "stop_too_wide": sum(r > hi for r in risks),
            "blocked": sum(v for k, v in skipped.items() if k != "size_zero"),
            "too_big_to_size": skipped.get("size_zero", 0),
            "signals": len(orders),
            "filled": n_filled,
            "never_filled": n_unfilled,
            "stop_points_avg": sum(risks) / len(risks) if risks else None,
            "stop_points_min": min(risks, default=None),
            "stop_points_max": max(risks, default=None),
        }
        return BacktestResult(
            trades=trades,
            daily=daily,
            attempts=attempts,
            equity=pd.Series(equity, index=b.index, name="equity"),
            skipped=skipped,
            bars=b,
            config=cfg,
            orders=orders,
            funnel=funnel,
        )


def backtest(bars: pd.DataFrame, cfg: BotConfig | None = None) -> BacktestResult:
    return Backtester(bars, cfg).run()
