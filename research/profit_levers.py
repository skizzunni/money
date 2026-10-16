"""Round sixteen: more profit from the trades the bot already takes, without more trades.

    python research/profit_levers.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Reasoning, written before running. About two thirds of trades lose; the profit comes from a few trend
days that keep going after the breakout. Two levers act on that, from opposite ends:
  A. Add to winners. At a later half-hour check, if the trade is up at least k noise units and the close
     is still outside the line, add one more unit at the next open, up to N units. Size goes where the
     edge is, on the days that keep trending. The whole position keeps one max loss: $116.67 per base
     contract measured from the average entry, so a trade can never lose more than the cap however many
     units it has (plus fees, slippage and gaps).
     Variants: (N=2, k=1.0), (N=3, k=1.0), (N=2, k=0.5).
  B. Protect winners. Once a trade is up 1 noise unit (sigma x price) at a bar close, a trailing stop sits
     m noise units behind the best close since entry, or at the entry ("breakeven"). The stop in force is
     the closest of it, the line stop and the max loss. Variants: m = 1.0, m = 2.0, breakeven.
Everything else is the bot as it trades: 5-minute bars, half-hour checks, line stop 0.24 noise units past
the line, $116.67 max loss per base contract, flat at 16:00. 1 base contract, $1.24 fees + 1 tick per
contract on every fill, prices at today's level month by month (timeframes.py).

Pass bar, fixed before running, against the bot as it is:
  Discovery 2011-2018: $ per day at least 10% higher; daily t-stat no more than 0.3 lower; $ per day per
  dollar of worst losing stretch no lower (so it isn't just more risk). The passing variant with the most
  $ per day goes on.
  Confirmation 2019-2022: $ per day higher, and the same two other tests.
  Final test 2023 - Sep 2026, run once: the same as confirmation. Only a pass changes the bot.
"""
from __future__ import annotations

import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import more_trades as MT  # noqa: E402

from mnqbot.data import NY  # noqa: E402

LOOKBACK, BUF, CAP_PTS = 14, 0.24, (350.0 / 3) / 2.0
TICK, PV, FEE = 0.25, 2.0, 1.24
OPEN, CLOSE, FIRST, LAST = 570, 960, 600, 930
VARIANTS = {"bot": {}, "add to 2 at +1": {"units": 2, "k": 1.0}, "add to 3 at +1": {"units": 3, "k": 1.0},
            "add to 2 at +0.5": {"units": 2, "k": 0.5}, "trail 1.0": {"trail": 1.0}, "trail 2.0": {"trail": 2.0},
            "breakeven": {"trail": 0.0}}
PERIODS = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022), ("2023-2026", 2023, 2026))


def simulate(bars: pd.DataFrame, units: int = 1, k: float = 1.0, trail: float | None = None,
             target: float | None = None, cap_pts: float = CAP_PTS, target_on_fill_bar: bool = True,
             cap_on_fill_bar: bool = False, entry_delay: int = 0) -> pd.DataFrame:
    """target: take profit this many noise units from the first fill (limit); cap_pts: max loss in points;
    target_on_fill_bar False: the limit works from the bar after the fill, as the Pine script places it;
    cap_on_fill_bar True: the max loss works on the fill bar too, measured from the expected fill (the signal
    close plus a tick), as a bracket order placed with the entry would (1 contract only);
    entry_delay: entries fill this many bars late (a slow trader), at that bar's open plus a tick."""
    checks = list(range(FIRST, LAST + 1, 30))
    kof = {m: j for j, m in enumerate(checks)}
    idx = bars.index.tz_convert(NY)
    mins = (idx.hour * 60 + idx.minute).to_numpy()
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ring = np.full((LOOKBACK, len(checks)), np.nan)
    today = np.full(len(checks), np.nan)
    filled = slot = 0
    day_open = prev_close = last_close = math.nan
    upper = lower = sigma = math.nan
    pos, fills, first_bar, pending, add_pending = 0, [], 0, 0, False
    best, armed = math.nan, False
    est = math.nan  # the expected fill of a pending entry: the signal close plus a tick
    wait = 0  # bars still to wait before a pending entry fills (entry_delay)
    out = []

    def close(i, px, why):
        nonlocal pos, fills, armed
        pnl = sum(pos * (px - e) * PV - FEE for e in fills)
        out.append((idx[first_bar], idx[i], pos, len(fills), pnl, why))
        pos, fills, armed = 0, [], False

    for i in range(len(bars)):
        t_min = mins[i]
        end = t_min + 5
        in_rth = t_min >= OPEN and end <= CLOSE
        if pending and wait > 0:
            wait -= 1
        elif pending:
            if pos == 0:
                pos, fills, first_bar = pending, [o[i] + pending * TICK], i
                best, armed = math.nan, False
                if entry_delay:
                    est = o[i] + pending * TICK  # a late trader places the bracket from the real fill
            pending = 0
        if add_pending:
            if pos:
                fills.append(o[i] + pos * TICK)
            add_pending = False
        if pos and not math.isnan(upper):
            stop = upper * (1 - BUF * sigma) if pos > 0 else lower * (1 + BUF * sigma)
            why = "line"
            if first_bar != i:
                avg = sum(fills) / len(fills)
                cap = avg - pos * cap_pts / len(fills)
                if (pos > 0 and cap > stop) or (pos < 0 and cap < stop):
                    stop, why = cap, "cap"
                if armed:
                    tr = fills[0] if trail == 0.0 else best - pos * trail * sigma * best
                    if (pos > 0 and tr > stop) or (pos < 0 and tr < stop):
                        stop, why = tr, "trail"
            elif cap_on_fill_bar:
                cap = est - pos * cap_pts
                if (pos > 0 and cap > stop) or (pos < 0 and cap < stop):
                    stop, why = cap, "cap"
            if first_bar == i:
                hit = l[i] <= stop if pos > 0 else h[i] >= stop
                px = (min(o[i], stop) if pos > 0 else max(o[i], stop)) - pos * TICK
            elif (pos > 0 and o[i] <= stop) or (pos < 0 and o[i] >= stop):
                hit, px = True, o[i] - pos * TICK
            else:
                hit, px = (l[i] <= stop if pos > 0 else h[i] >= stop), stop - pos * TICK
            if hit:
                close(i, px, why)
            elif target is not None and (target_on_fill_bar or first_bar != i):  # after the stop (worst case first)
                tp = fills[0] * (1 + pos * target * sigma)
                if (pos > 0 and h[i] >= tp + TICK) or (pos < 0 and l[i] <= tp - TICK):
                    close(i, tp, "target")
        if pos and (not in_rth or t_min == OPEN):
            close(i, c[i] - pos * TICK, "session")
        if t_min == OPEN:
            prev_close, day_open = last_close, o[i]
            upper = lower = sigma = math.nan
            today[:] = np.nan
        if in_rth:
            last_close = c[i]
        if pos and trail is not None and not math.isnan(sigma):  # best close and the arming test, at bar close
            best = c[i] if math.isnan(best) else (max(best, c[i]) if pos > 0 else min(best, c[i]))
            if not armed and pos * (c[i] - fills[0]) >= sigma * fills[0]:
                armed = True
        if in_rth and not math.isnan(day_open) and end in kof:
            j = kof[end]
            today[j] = abs(c[i] / day_open - 1)
            if filled >= LOOKBACK and not math.isnan(prev_close):
                sigma = ring[:, j].mean()
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                if pos == 0 and c[i] > upper:
                    pending, est, wait = 1, c[i] + TICK, entry_delay
                elif pos == 0 and c[i] < lower:
                    pending, est, wait = -1, c[i] - TICK, entry_delay
                elif (pos and len(fills) < units and i != first_bar
                      and ((pos > 0 and c[i] > upper) or (pos < 0 and c[i] < lower))
                      and pos * (c[i] - fills[0]) >= k * sigma * fills[0]):
                    add_pending = True
        if in_rth and end == CLOSE:
            if pos:
                close(i, c[i] - pos * TICK, "16:00")
            add_pending = False
            if not math.isnan(day_open) and not np.isnan(today).any():
                ring[slot] = today
                slot = (slot + 1) % LOOKBACK
                filled += 1
            day_open = math.nan
    return pd.DataFrame(out, columns=["entry_time", "exit_time", "dir", "units", "pnl", "why"])


def _job(args):
    path, name = args
    return name, simulate(pd.read_pickle(path), **VARIANTS[name])


def main() -> None:
    bars = MT._bars(sys.argv[1])
    cache = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("bars5_scaled.pkl")
    if not cache.exists():
        bars.to_pickle(cache)
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == OPEN].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2011-01-01") & ~sessions.isin(list(first_sessions))]
    with ProcessPoolExecutor(max_workers=4) as ex:
        runs = {n: MT.clean(tf, first_sessions) for n, tf in ex.map(_job, [(str(cache), n) for n in VARIANTS])}
    table, rows = {}, []
    for name, tf in runs.items():
        for label, y0, y1 in PERIODS:
            ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
            yr = tf.entry_time.dt.year
            t = tf[(yr >= y0) & (yr <= y1)]
            s = MT.stats(t, ss)
            s["$/day per $1k stretch"] = 1000 * s["$/day"] / s["worst stretch"]
            s["max units %"] = 100 * (t.units > 1).mean()
            table[(name, label)] = s
            rows.append((name, label, s["$/day"], s["t"], s["worst stretch"], s["$/day per $1k stretch"],
                         s["win %"], s["months up %"], s["max units %"]))
    df = pd.DataFrame(rows, columns=["variant", "period", "$/day", "t", "worst stretch", "$/day per $1k stretch",
                                     "win %", "months up %", "trades with adds %"])
    print(df.round(2).to_string(index=False))

    def passes(name, label, lift):
        a, b = table[(name, label)], table[("bot", label)]
        return (a["$/day"] >= lift * b["$/day"] and a["t"] >= b["t"] - 0.3
                and a["$/day per $1k stretch"] >= b["$/day per $1k stretch"])

    cands = [n for n in VARIANTS if n != "bot" and passes(n, "2011-2018", 1.10)]
    print(f"\nDiscovery 2011-2018: {cands or 'none pass'}")
    if not cands:
        return
    best = max(cands, key=lambda n: table[(n, "2011-2018")]["$/day"])
    ok = passes(best, "2019-2022", 1.0 + 1e-9)
    print(f"Best: {best}. Confirmation 2019-2022: {'PASS' if ok else 'FAIL'}")
    if ok:
        print(f"Final test 2023 - Sep 2026: {'PASS' if passes(best, '2023-2026', 1.0 + 1e-9) else 'FAIL'}")


if __name__ == "__main__":
    main()
