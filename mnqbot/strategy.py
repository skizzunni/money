"""Setup models: liquidity sweep -> displacement -> fair value gap, and an
opening range breakout with a retest entry.

The idea in plain words:
  1. Mark obvious liquidity: previous day's RTH high/low, the overnight
     high/low, and the latest swing high/low. Stops pile up just beyond them.
  2. During the entry window, wait for price to run one of those levels
     (trade through it) and then close back on the other side: the sweep.
  3. Require a strong candle the other way that leaves a fair value gap
     (a three-bar imbalance): the displacement.
  4. Place a limit order back inside the gap, stop beyond the sweep extreme,
     target at a fixed reward:risk.

The opening range breakout: the range is the RTH bars from 09:30 for
``or_minutes``. The first bar in the entry window that closes outside it
gives a limit order back at the broken edge (the retest), stop part of the
range behind it, same reward:risk. One breakout per day.

Everything here only uses bars that have already closed, so the backtest
cannot peek at the future. ``SignalEngine.step(i)`` is called once per bar,
in order, and returns a ``Setup`` when one is confirmed at the close of bar i.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from .config import Instrument, StrategyConfig
from .data import atr

HIGH_LEVELS = ("PDH", "ONH", "SWH")  # buy-side liquidity, swept -> short setups
LOW_LEVELS = ("PDL", "ONL", "SWL")  # sell-side liquidity, swept -> long setups


@dataclass
class Setup:
    bar: int  # setup confirmed at the close of this bar; order is live from bar + 1
    direction: int  # +1 long, -1 short
    entry: float
    stop: float
    target: float
    level_name: str
    level_price: float
    sweep_bar: int
    fvg_low: float
    fvg_high: float

    @property
    def risk_points(self) -> float:
        return abs(self.entry - self.stop)


@dataclass
class _Level:
    price: float
    taken: bool = False


@dataclass
class _Armed:
    direction: int
    level_name: str
    level_price: float
    sweep_bar: int
    extreme: float
    expires: int


def _hhmm(s: str) -> int:
    return int(s.replace(":", ""))


def _plus_minutes(hhmm: int, minutes: int) -> int:
    total = (hhmm // 100) * 60 + hhmm % 100 + minutes
    return (total // 60) * 100 + total % 60


def round_to_tick(price: float, tick: float) -> float:
    """Nearest tick; exact half ticks round up. Same formula as the Pine scripts: floor(x / tick + 0.5)."""
    return round(math.floor(price / tick + 0.5) * tick, 10)


class SignalEngine:
    def __init__(self, bars: pd.DataFrame, cfg: StrategyConfig, inst: Instrument):
        self.cfg = cfg
        self.tick = inst.tick_size
        self.o = bars["open"].to_numpy(float)
        self.h = bars["high"].to_numpy(float)
        self.l = bars["low"].to_numpy(float)
        self.c = bars["close"].to_numpy(float)
        self.hhmm = bars["hhmm"].to_numpy(int)
        self.is_rth = bars["is_rth"].to_numpy(bool)
        self.is_on = bars["is_overnight"].to_numpy(bool)
        self.day = bars["trade_date"].to_numpy()
        self.atr = atr(self.h, self.l, self.c, cfg.atr_len)
        self.win_start = _hhmm(cfg.window_start)
        self.win_end = _hhmm(cfg.window_end)
        self.or_end = _plus_minutes(930, cfg.or_minutes)

        self.levels: dict[str, _Level] = {}
        self.armed: _Armed | None = None
        self._cur_day = None
        self._day_start = 0
        self._rth_hi = math.nan
        self._rth_lo = math.nan
        self._pdh = math.nan
        self._pdl = math.nan
        self._on_hi = math.nan
        self._on_lo = math.nan
        self._on_final = False
        self._or_hi = math.nan
        self._or_lo = math.nan
        self._orb_used = False
        # funnel: how far each idea gets (see engine.BacktestResult.funnel)
        self.n_sweeps = 0
        self.n_breakouts = 0
        self.setup_risks: list[float] = []  # stop size of every setup found, valid or not

    # ------------------------------------------------------------------ helpers
    def in_window(self, i: int) -> bool:
        return self.win_start <= self.hhmm[i] < self.win_end

    def _new_day(self, i: int) -> None:
        if not math.isnan(self._rth_hi):
            self._pdh, self._pdl = self._rth_hi, self._rth_lo
        self._rth_hi = self._rth_lo = math.nan
        self._on_hi = self._on_lo = math.nan
        self._on_final = False
        self._or_hi = self._or_lo = math.nan
        self._orb_used = False
        self.armed = None
        self.levels = {}
        if self.cfg.use_prev_day and not math.isnan(self._pdh):
            self.levels["PDH"] = _Level(self._pdh)
            self.levels["PDL"] = _Level(self._pdl)
        self._cur_day = self.day[i]
        self._day_start = i

    # --------------------------------------------------------------------- step
    def step(self, i: int) -> Setup | None:
        if self.day[i] != self._cur_day:
            self._new_day(i)

        # Overnight range is final once RTH opens.
        if self.is_rth[i] and not self._on_final:
            self._on_final = True
            if self.cfg.use_overnight and not math.isnan(self._on_hi):
                self.levels["ONH"] = _Level(self._on_hi)
                self.levels["ONL"] = _Level(self._on_lo)

        found = len(self.setup_risks)
        setup = self._check_armed(i)
        orb = self._check_orb(i, sweep_found=len(self.setup_risks) > found)
        self._check_sweeps(i)
        self._update_ranges(i)
        self._update_swings(i)
        if self.is_rth[i] and self.hhmm[i] < self.or_end:
            self._or_hi = self.h[i] if math.isnan(self._or_hi) else max(self._or_hi, self.h[i])
            self._or_lo = self.l[i] if math.isnan(self._or_lo) else min(self._or_lo, self.l[i])
        return setup or orb

    def _check_orb(self, i: int, sweep_found: bool) -> Setup | None:
        """First close outside the opening range -> limit back at the broken edge."""
        cfg = self.cfg
        if not cfg.use_orb or self._orb_used or math.isnan(self._or_hi):
            return None
        if self.hhmm[i] < self.or_end or not self.in_window(i):
            return None
        c = self.c[i]
        if not (c > self._or_hi or c < self._or_lo):
            return None
        self._orb_used = True
        self.n_breakouts += 1
        if sweep_found:  # a sweep setup on the same bar takes priority
            return None
        d = 1 if c > self._or_hi else -1
        entry = self._or_hi if d > 0 else self._or_lo
        stop = round_to_tick(entry - d * cfg.or_stop_frac * (self._or_hi - self._or_lo), self.tick)
        risk = abs(entry - stop)
        self.setup_risks.append(risk)
        if not (cfg.min_stop_points <= risk <= cfg.max_stop_points):
            return None
        return Setup(
            bar=i,
            direction=d,
            entry=entry,
            stop=stop,
            target=round_to_tick(entry + d * cfg.reward_risk * risk, self.tick),
            level_name="ORH" if d > 0 else "ORL",
            level_price=entry,
            sweep_bar=i,
            fvg_low=self._or_lo,
            fvg_high=self._or_hi,
        )

    def _check_armed(self, i: int) -> Setup | None:
        a = self.armed
        if a is None or i <= a.sweep_bar:
            return None
        if i > a.expires:
            self.armed = None
            return None
        cfg, tick = self.cfg, self.tick
        h, l, c, o = self.h, self.l, self.c, self.o

        if a.direction < 0:
            a.extreme = max(a.extreme, h[i])
            if c[i] > a.level_price:  # closed back above: breakout, not a sweep
                self.armed = None
                return None
        else:
            a.extreme = min(a.extreme, l[i])
            if c[i] < a.level_price:
                self.armed = None
                return None

        if not self.in_window(i) or i < 2 or i - 1 < a.sweep_bar:
            return None
        disp_atr = self.atr[i - 1]
        if math.isnan(disp_atr):
            return None
        min_gap = cfg.min_fvg_ticks * tick
        body = c[i - 1] - o[i - 1]

        if a.direction < 0:
            gap_hi, gap_lo = l[i - 2], h[i]
            ok = (
                gap_hi - gap_lo >= min_gap
                and -body >= cfg.displacement_atr * disp_atr
                and c[i] < a.level_price
            )
            if not ok:
                return None
            entry = round_to_tick(gap_lo + cfg.entry_level * (gap_hi - gap_lo), tick)
            stop = round_to_tick(a.extreme + cfg.stop_buffer_ticks * tick, tick)
            risk = stop - entry
            target = round_to_tick(entry - cfg.reward_risk * risk, tick)
        else:
            gap_lo, gap_hi = h[i - 2], l[i]
            ok = (
                gap_hi - gap_lo >= min_gap
                and body >= cfg.displacement_atr * disp_atr
                and c[i] > a.level_price
            )
            if not ok:
                return None
            entry = round_to_tick(gap_hi - cfg.entry_level * (gap_hi - gap_lo), tick)
            stop = round_to_tick(a.extreme - cfg.stop_buffer_ticks * tick, tick)
            risk = entry - stop
            target = round_to_tick(entry + cfg.reward_risk * risk, tick)

        self.armed = None
        self.setup_risks.append(risk)
        if not (cfg.min_stop_points <= risk <= cfg.max_stop_points):
            return None
        return Setup(
            bar=i,
            direction=a.direction,
            entry=entry,
            stop=stop,
            target=target,
            level_name=a.level_name,
            level_price=a.level_price,
            sweep_bar=a.sweep_bar,
            fvg_low=gap_lo,
            fvg_high=gap_hi,
        )

    def _check_sweeps(self, i: int) -> None:
        through = self.cfg.sweep_min_ticks * self.tick
        h, l, c = self.h[i], self.l[i], self.c[i]
        bear: tuple[str, float] | None = None  # highest buy-side level swept and closed back below
        bull: tuple[str, float] | None = None  # lowest sell-side level swept and closed back above

        for name in HIGH_LEVELS + LOW_LEVELS:  # fixed order, same as the Pine scripts
            lvl = self.levels.get(name)
            if lvl is None or lvl.taken:
                continue
            if name in HIGH_LEVELS and h >= lvl.price + through:
                lvl.taken = True
                if c < lvl.price and (bear is None or lvl.price > bear[1]):
                    bear = (name, lvl.price)
            elif name in LOW_LEVELS and l <= lvl.price - through:
                lvl.taken = True
                if c > lvl.price and (bull is None or lvl.price < bull[1]):
                    bull = (name, lvl.price)

        if not self.cfg.use_sweep or not self.in_window(i) or (bear and bull):
            return
        expires = i + self.cfg.max_bars_after_sweep
        if bear or bull:
            self.n_sweeps += 1
        if bear:
            self.armed = _Armed(-1, bear[0], bear[1], i, h, expires)
        elif bull:
            self.armed = _Armed(1, bull[0], bull[1], i, l, expires)

    def _update_ranges(self, i: int) -> None:
        if self.is_rth[i]:
            self._rth_hi = self.h[i] if math.isnan(self._rth_hi) else max(self._rth_hi, self.h[i])
            self._rth_lo = self.l[i] if math.isnan(self._rth_lo) else min(self._rth_lo, self.l[i])
        elif self.is_on[i] and not self._on_final:
            self._on_hi = self.h[i] if math.isnan(self._on_hi) else max(self._on_hi, self.h[i])
            self._on_lo = self.l[i] if math.isnan(self._on_lo) else min(self._on_lo, self.l[i])

    def _update_swings(self, i: int) -> None:
        """Confirm a swing at bar j = i - n once n bars on each side are known."""
        if not self.cfg.use_swings:
            return
        n = self.cfg.swing_len
        j = i - n
        if j - n < self._day_start:
            return
        left_h, right_h = self.h[j - n : j], self.h[j + 1 : i + 1]
        if self.h[j] > left_h.max() and self.h[j] >= right_h.max():
            self.levels["SWH"] = _Level(float(self.h[j]))
        left_l, right_l = self.l[j - n : j], self.l[j + 1 : i + 1]
        if self.l[j] < left_l.min() and self.l[j] <= right_l.min():
            self.levels["SWL"] = _Level(float(self.l[j]))


def scan(bars: pd.DataFrame, cfg: StrategyConfig, inst: Instrument) -> list[Setup]:
    """All setups in the data, ignoring position and risk limits (for research)."""
    eng = SignalEngine(bars, cfg, inst)
    return [s for i in range(len(bars)) if (s := eng.step(i)) is not None]


__all__ = ["Setup", "SignalEngine", "scan", "round_to_tick"]
