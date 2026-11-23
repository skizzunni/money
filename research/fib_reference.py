# ruff: noqa: E501
"""The Fibonacci pullback strategy as NinjaTrader would trade it (one working limit, the nearer leg; rejected 2026-11-23,
docs/NINJATRADER_V38.md "Fibonacci pullback"). Not built.

On 1-minute bars (New York time, the bar's start; regular hours 09:30-16:00), one trade a day:
  * the legs, from the day's regular-hours bars so far: long, the day's high H and the lowest low before it L; short,
    the day's low and the highest high before it. A leg counts when it is at least `min_leg` x the last close;
  * at each bar close from 09:59 to 14:28 (so an order can fill from 10:00 to 14:29), when flat and no trade yet today,
    a limit order works at the `entry` retracement of the nearer valid leg (long: H - entry x (H - L); short: L + entry
    x (H - L)), moved at every close as the legs change, cancelled at the 14:29 close;
  * filled as NinjaTrader's simulator fills a limit: at the open when the bar opens at or through it, otherwise at the
    limit once the bar trades a tick through it;
  * a stop at the `stop` retracement less a tick (from the fill bar on: at the stop, or the open when it gaps through,
    a tick of slippage) and a target at L + target x (H - L) (long; a tick through it, not on the fill bar), the stop
    first when a bar reaches both;
  * flat at the open after the 15:59 bar (a tick of slippage) if still open;
  * contracts: qty + one per `profit_step` of closed profit since `trail_from` (the first bar when blank), at most
    `max_qty`; $0.62 a side.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

NY = "America/New_York"


@dataclass
class FibConfig:
    qty: int = 1
    entry: float = 0.618
    stop: float = 0.786
    target: float = 1.0
    min_leg: float = 0.003
    first_order: int = 599  # the earliest bar close (minute of its start) that places an order (fills from 10:00)
    last_order: int = 868  # the last bar close that may place or move one (fills up to 14:29)
    flat: int = 959  # the bar whose close sends the exit
    profit_step: float = 1500.0
    max_qty: int = 10
    trail_from: str = ""
    tick: float = 0.25
    point_value: float = 2.0
    commission_per_side: float = 0.62
    slippage_ticks: int = 1


@dataclass
class FibTrade:
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


def _rt(x: float, tick: float) -> float:
    return round(round(x / tick) * tick, 10)


def run(bars: pd.DataFrame, cfg: FibConfig) -> list[FibTrade]:
    t = bars.index.tz_convert(NY)
    mins = (t.hour * 60 + t.minute).to_numpy()
    o, h, lo, c = (bars[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    tick, slip, pv = cfg.tick, cfg.slippage_ticks * cfg.tick, cfg.point_value
    start = pd.Timestamp(cfg.trail_from, tz=NY) if cfg.trail_from else t[0]
    trades: list[FibTrade] = []
    day = None
    hi_v = lo_v = math.nan
    rth_h: list[float] = []
    rth_l: list[float] = []
    hi_i = lo_i = -1
    traded = False
    order = None  # (side, limit, stop, target, qty) working for the next bar
    pos = None  # dict: side, qty, entry, bar, stop, target
    exit_next = False
    closed = 0.0

    def close_pos(i: int, px: float, why: str) -> None:
        nonlocal pos, closed
        p = pos
        pnl = p["side"] * (px - p["entry"]) * p["qty"] * pv - 2 * cfg.commission_per_side * p["qty"]
        if t[p["bar"]] >= start:
            closed += pnl
        trades.append(FibTrade(p["side"], p["qty"], p["bar"], t[p["bar"]], p["entry"], i, t[i], px, why, pnl))
        pos = None

    for i in range(len(o)):
        m = mins[i]
        # the bar's fills: a market exit sent at the last close, the working limit, the bracket
        if pos is not None and exit_next:
            close_pos(i, o[i] - pos["side"] * slip, "16:00")
        exit_next = False
        if pos is None and order is not None:
            side, lim, st, tg, q = order
            if side * (lim - o[i]) >= 0:
                px = o[i]
            elif (side > 0 and lo[i] <= lim - tick) or (side < 0 and h[i] >= lim + tick):
                px = lim
            else:
                px = math.nan
            if not math.isnan(px):
                pos = {"side": side, "qty": q, "entry": px, "bar": i, "stop": st, "target": tg}
                order = None
                traded = True
        if pos is not None:
            s, st = pos["side"], pos["stop"]
            if pos["bar"] == i:
                hit = lo[i] <= st if s > 0 else h[i] >= st
                px = (min(o[i], st) if s > 0 else max(o[i], st)) - s * slip
            elif (s > 0 and o[i] <= st) or (s < 0 and o[i] >= st):
                hit, px = True, o[i] - s * slip
            else:
                hit, px = (lo[i] <= st if s > 0 else h[i] >= st), st - s * slip
            if hit:
                close_pos(i, px, "Stop")
            elif pos["bar"] != i and ((s > 0 and h[i] >= pos["target"] + tick) or
                                      (s < 0 and lo[i] <= pos["target"] - tick)):
                close_pos(i, pos["target"], "Target")
        # the bar's close
        rth = 570 <= m < 960
        if rth and t[i].date() != day:
            day, rth_h, rth_l, hi_i, lo_i, traded, order = t[i].date(), [], [], -1, -1, False, None
            hi_v = lo_v = math.nan
        if not rth:
            order = None
            continue
        rth_h.append(h[i])
        rth_l.append(lo[i])
        k = len(rth_h) - 1
        if math.isnan(hi_v) or h[i] > hi_v:
            hi_v, hi_i = h[i], k
        if math.isnan(lo_v) or lo[i] < lo_v:
            lo_v, lo_i = lo[i], k
        if pos is not None and m >= cfg.flat:
            exit_next = True
        order = None
        if pos is not None or traded or not (cfg.first_order <= m <= cfg.last_order):
            continue
        best = None
        for side in (1, -1):
            if side > 0:
                if hi_i <= 0:
                    continue
                top, bot = hi_v, min(rth_l[:hi_i + 1])
            else:
                if lo_i <= 0:
                    continue
                top, bot = max(rth_h[:lo_i + 1]), lo_v
            size = top - bot
            if size < cfg.min_leg * c[i] or size <= 0:
                continue
            if side > 0:
                lim = _rt(top - cfg.entry * size, tick)
                st = _rt(top - cfg.stop * size, tick) - tick
                tg = _rt(bot + cfg.target * size, tick)
            else:
                lim = _rt(bot + cfg.entry * size, tick)
                st = _rt(bot + cfg.stop * size, tick) + tick
                tg = _rt(top - cfg.target * size, tick)
            # the setup is dead once price has traded through its stop since the swing
            if (side > 0 and min(rth_l[hi_i:]) <= st) or (side < 0 and max(rth_h[lo_i:]) >= st):
                continue
            dist = abs(c[i] - lim)
            if best is None or dist < best[0]:
                best = (dist, side, lim, st, tg)
        if best is not None:
            q = cfg.qty
            if cfg.profit_step > 0 and t[i] >= start:
                q += int(max(0.0, closed) // cfg.profit_step)
            q = min(q, cfg.max_qty) if cfg.max_qty > 0 else q
            order = (best[1], best[2], best[3], best[4], q)
    return trades


def trades_frame(trades: list[FibTrade]) -> pd.DataFrame:
    return pd.DataFrame([vars(x) for x in trades])
