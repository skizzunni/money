"""The pre-FOMC drift (ninjatrader/Strategies/MnqFomcDrift.cs) on 1-minute bars, with the NinjaTrader stand-in's fills.

On day D, if the next weekday is an FOMC announcement date: a market buy is sent at the close of the 13:59 bar and
fills at the 14:00 bar's open plus the slippage; its catastrophe stop is round(that 13:59 close x stop_pct / 100 /
tick) ticks under the fill. On the announcement day a market sell is sent at the close of the 13:54 bar and fills at
the 13:55 bar's open less the slippage. Per bar, in the stand-in's order: a pending exit fills at the open, then a
pending entry, then the stop (at the stop less the slippage, or at the open less the slippage if the bar opens under
it), then the decision at the bar's close.
"""
from __future__ import annotations

import math

import pandas as pd

TICK, PV = 0.25, 2.0


def next_weekday(day: pd.Timestamp) -> pd.Timestamp:
    return day + pd.Timedelta(days={4: 3, 5: 2}.get(day.weekday(), 1))


def trades(bars: pd.DataFrame, fed_dates: set[str], qty: int = 2, slip_ticks: int = 2, commission: float = 0.95,
           stop_pct: float = 4.0) -> list[dict]:
    """Every completed trade: entry / exit bar, prices, reason, P/L. bars: open, high, low, close; NY start times."""
    idx = bars.index.tz_convert("America/New_York") if bars.index.tz is not None else bars.index
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    slip = slip_ticks * TICK
    out, pos, pend_entry, pend_exit = [], None, None, False
    for i, t in enumerate(idx):
        if pend_exit and pos is not None:
            out.append(_close(pos, i, o[i] - slip, "FOMC exit", qty, commission))
            pos = None
        pend_exit = False
        if pend_entry is not None:
            fill = o[i] + slip
            pos = {"eb": i, "en": fill, "stop": fill - pend_entry * TICK if pend_entry else -math.inf}
            pend_entry = None
        if pos is not None and l[i] <= pos["stop"]:
            out.append(_close(pos, i, min(o[i], pos["stop"]) - slip, "Stop loss", qty, commission))
            pos = None
        tmin = t.hour * 60 + t.minute
        day = pd.Timestamp(t.date())
        if pos is not None and tmin == 834 and day.strftime("%Y-%m-%d") in fed_dates:
            pend_exit = True
        elif pos is None and tmin == 839 and next_weekday(day).strftime("%Y-%m-%d") in fed_dates:
            pend_entry = max(1, round(c[i] * stop_pct / 100.0 / TICK)) if stop_pct > 0 else 0
    return out


def _close(pos: dict, i: int, px: float, why: str, qty: int, commission: float) -> dict:
    return {"d": 1, "eb": pos["eb"], "en": pos["en"], "xb": i, "ex": px, "why": why, "q": qty,
            "pnl": qty * ((px - pos["en"]) * PV - 2 * commission)}
