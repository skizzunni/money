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
             cap_on_fill_bar: bool = False, entry_delay: int = 0,
             no_entry_checks: frozenset = frozenset(), minutes: int = 5,
             ratchet: bool = False, lock: tuple[float, float] | None = None, day_losers: int | None = None,
             side_once: bool = False, min_cap_units: float = 0.0, lock_touch: bool = False,
             lock2: tuple[float, float] | None = None, done_after_target: bool = False,
             ghost: bool = False, trail_pts: tuple[float, float] | None = None,
             skip_spike: float | None = None, lock_path: bool = False,
             limit_first: tuple[float, int] | None = None, second_chance: bool = False,
             skip_days: frozenset = frozenset(), checks_by_year: dict | None = None,
             time_lock: tuple[int, float] | None = None, time_exit: int | None = None,
             skip_checks_on: dict | None = None, lock_unconfirmed: float | None = None,
             confirmed: tuple[set, set, set] | None = None, relock: bool = False,
             lock_sigma: tuple[float, float, float] | None = None) -> pd.DataFrame:
    """target: take profit this many noise units from the first fill (limit); cap_pts: max loss in points;
    target_on_fill_bar False: the limit works from the bar after the fill, as the Pine script places it;
    cap_on_fill_bar True: the max loss works on the fill bar too, measured from the expected fill (the signal
    close plus a tick), as a bracket order placed with the entry would (1 contract only);
    entry_delay: entries fill this many bars late (a slow trader), at that bar's open plus a tick;
    no_entry_checks: check times (minutes after midnight, e.g. 930 for 15:30) that open no new trades;
    minutes: the bar length (1 or 5);
    ratchet: the stop never moves away from price during a trade (a broker stop placed with the entry that is only ever
    tightened), 1 contract;
    lock (arm, offset), in points: once a bar closes at least arm points in profit, the stop moves to the entry plus
    offset points (never back); lock_touch: the bar's high (long) or low (short) reaching it arms the lock, as a
    broker's auto-breakeven would, still from the next bar; lock2 (arm, offset): a second, higher step, armed the
    same way;
    done_after_target: no new entries today after a take-profit fills;
    ghost: with entry_delay, the entry is skipped if a trade filled at the first bar's open after the signal would
    have hit its stop (the closer of the line stop and the max loss) during the wait;
    trail_pts (activate, offset), in points: once the high (long) or low (short) has reached activate points in profit,
    a stop trails offset points behind the best high (low) so far, updated each bar for the next;
    lock_path: the lock arms and can fill inside the bar that reaches the trigger, along TradingView's bar path (open,
    then the nearer of high and low, then the other, then close): a stop trailing (trigger - offset) behind the best
    price, only in that bar; from the next bar the fixed lock;
    limit_first (k, n): at a signal, a limit k points better than the signal close works for n bars, filling when price
    trades a tick through it; if it hasn't filled, a market order at the next bar's open (the runners still get in);
    second_chance: after a max-loss stop, a stop order to re-enter at the stopped trade's fill price, same side, until
    the next half-hour check (once per signal);
    skip_days: dates (datetime.date, New York) with no new entries;
    checks_by_year: {year: check times (as no_entry_checks) with no new entries that year};
    time_lock (n, profit): n bars after the fill, if the bar closes at least profit points up, the lock (entry +
    lock offset) goes on from the next bar, as if the trigger had been reached;
    lock_unconfirmed, confirmed (three sets of check-bar times: a second market closed beyond its own upper line;
    below its lower line; it has a bar): a trade whose signal that market did not confirm locks at this trigger
    instead of lock[0] (times the second market has no bar for count as confirmed);
    lock_sigma (k, lo, hi): the lock trigger is k x the check's noise (sigma x price), kept between lo and hi points;
    relock: after a lock exit, a stop order re-enters on the same side at the trade's lock trigger price (its fill plus
    the trigger), until the next half-hour check (once per signal);
    skip_checks_on: {date: check times with no new entries that day} (e.g. 10:00 on release days);
    time_exit n: a trade that hasn't reached the lock n bars after the fill closes at that bar's close (market);
    skip_spike: no entry when the 5-minute bar ending at the check closed at or beyond this fraction of its range
    toward the signal's side (1 = at its high for a buy, at its low for a sell);
    day_losers: no new entries today after this many losing trades today;
    side_once: after a losing trade today, no new entries on that side today;
    min_cap_units: no entry when the max loss is less than this many noise units (sigma x price) from the signal
    close, i.e. when the stop is tiny next to today's noise."""
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
    held = math.nan  # with ratchet: the tightest stop so far in this trade
    peak = math.nan  # trail_pts: the best high (long) or low (short) since the fill, once activated
    est = math.nan  # the expected fill of a pending entry: the signal close plus a tick
    wait = 0  # bars still to wait before a pending entry fills (entry_delay)
    ghost_px = ghost_stop = math.nan  # the ghost trade's fill and stop while waiting
    lim_px, lim_left, lim_market, lim_bar = math.nan, 0, False, -1  # limit_first: the resting limit
    chance_side, chance_px, chance_done = 0, math.nan, False  # second_chance: the re-entry stop order
    trade_trigger = sig_trigger = lock[0] if lock is not None else math.nan  # this trade's lock trigger
    locked = locked2 = False  # lock: the stop has moved to the entry plus the offset (lock2: the second step)
    target_today = False
    losers, lost_sides = 0, set()  # losing trades today, and the sides they were on
    out = []

    def close(i, px, why):
        nonlocal pos, fills, armed, held, locked, locked2, losers, target_today, peak, chance_side, chance_px
        pnl = sum(pos * (px - e) * PV - FEE for e in fills)
        out.append((idx[first_bar], idx[i], pos, len(fills), pnl, why))
        if pnl < 0:
            losers += 1
            lost_sides.add(pos)
        if why == "target":
            target_today = True
        if second_chance and why == "cap" and not chance_done:
            chance_side, chance_px = pos, fills[0]
        if relock and why == "lock" and not chance_done:
            chance_side, chance_px = pos, fills[0] + pos * trade_trigger
        pos, fills, armed = 0, [], False
        held, locked, locked2 = math.nan, False, False
        peak = math.nan

    for i in range(len(bars)):
        t_min = mins[i]
        end = t_min + minutes
        in_rth = t_min >= OPEN and end <= CLOSE
        if pending and lim_left > 0:  # limit_first: the limit works for a few bars
            d = pending
            if (d > 0 and l[i] <= lim_px - TICK) or (d < 0 and h[i] >= lim_px + TICK):
                if pos == 0:
                    pos, fills, first_bar = d, [lim_px], i
                    best, armed, est, lim_bar = math.nan, False, lim_px, i
                pending, lim_left = 0, 0
            else:
                lim_left -= 1
                lim_market = lim_left == 0  # not filled: a market order at the next bar's open
        elif pending and lim_market:
            lim_market = False
            if pos == 0:
                pos, fills, first_bar = pending, [o[i] + pending * TICK], i
                best, armed, est = math.nan, False, o[i] + pending * TICK
            pending = 0
        elif pending and wait > 0:
            wait -= 1
            if ghost:
                if math.isnan(ghost_px):
                    ghost_px = o[i] + pending * TICK
                    line = upper * (1 - BUF * sigma) if pending > 0 else lower * (1 + BUF * sigma)
                    cap = ghost_px - pending * cap_pts
                    ghost_stop = max(line, cap) if pending > 0 else min(line, cap)
                if (pending > 0 and l[i] <= ghost_stop) or (pending < 0 and h[i] >= ghost_stop):
                    pending, wait = 0, 0  # the ghost was stopped: no trade
                    ghost_px = math.nan
        elif pending:
            ghost_px = math.nan
            if pos == 0:
                pos, fills, first_bar = pending, [o[i] + pending * TICK], i
                best, armed = math.nan, False
                if entry_delay:
                    est = o[i] + pending * TICK  # a late trader places the bracket from the real fill
            pending = 0
        if pos and first_bar == i:
            trade_trigger = sig_trigger
        if chance_side and pos == 0 and not pending:  # second_chance: the re-entry stop order
            d = chance_side
            if (d > 0 and h[i] >= chance_px) or (d < 0 and l[i] <= chance_px):
                px0 = (max(o[i], chance_px) if d > 0 else min(o[i], chance_px)) + d * TICK
                pos, fills, first_bar = d, [px0], i
                best, armed, est = math.nan, False, px0
                chance_side, chance_done = 0, True
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
            if not math.isnan(peak):
                tr = peak - pos * trail_pts[1]
                if (pos > 0 and tr > stop) or (pos < 0 and tr < stop):
                    stop, why = tr, "trail"
            for on, step in ((locked, lock), (locked2, lock2)):
                if on:
                    lk = fills[0] + pos * step[1]
                    if (pos > 0 and lk > stop) or (pos < 0 and lk < stop):
                        stop, why = lk, "lock"
            if ratchet:
                if first_bar == i or math.isnan(held):
                    held = stop
                stop = held = max(held, stop) if pos > 0 else min(held, stop)
            if first_bar == i:
                hit = l[i] <= stop if pos > 0 else h[i] >= stop
                px = (min(o[i], stop) if pos > 0 else max(o[i], stop)) - pos * TICK
            elif (pos > 0 and o[i] <= stop) or (pos < 0 and o[i] >= stop):
                hit, px = True, o[i] - pos * TICK
            else:
                hit, px = (l[i] <= stop if pos > 0 else h[i] >= stop), stop - pos * TICK
            if not hit and lock_path and lock is not None and not locked and first_bar != i:
                # TradingView's path through the bar: open, nearer extreme, farther extreme, close
                up_first = (h[i] - o[i]) <= (o[i] - l[i])
                fav, adv = (h[i], l[i]) if pos > 0 else (l[i], h[i])
                fav_first = up_first if pos > 0 else not up_first
                trig = fills[0] + pos * lock[0]
                if pos * (fav - trig) >= 0:
                    tr = fav - pos * (lock[0] - lock[1])  # the trailing stop once the bar's best price is reached
                    after = adv if fav_first else c[i]  # where the path goes after the best price
                    if pos * (after - tr) <= 0:
                        locked = True
                        hit, px, why = True, tr - pos * TICK, "lock"
            if hit:
                close(i, px, why)
            elif target is not None and (target_on_fill_bar or first_bar != i):  # after the stop (worst case first)
                tp = fills[0] * (1 + pos * target * sigma)
                if (pos > 0 and h[i] >= tp + TICK) or (pos < 0 and l[i] <= tp - TICK):
                    close(i, tp, "target")
        if pos and (not in_rth or t_min == OPEN):
            close(i, c[i] - pos * TICK, "session")
        if t_min == OPEN:
            losers, target_today = 0, False
            lost_sides.clear()
            prev_close, day_open = last_close, o[i]
            upper = lower = sigma = math.nan
            today[:] = np.nan
        if in_rth:
            last_close = c[i]
        if pos and time_exit is not None and not locked and i - first_bar >= time_exit:
            close(i, c[i] - pos * TICK, "time")
        if (pos and time_lock is not None and lock is not None and not locked and i - first_bar >= time_lock[0]
                and pos * (c[i] - fills[0]) >= time_lock[1]):
            locked = True
        if pos and lock is not None and not locked and lim_bar != i:
            seen = (h[i] if pos > 0 else l[i]) if lock_touch else c[i]
            locked = pos * (seen - fills[0]) >= trade_trigger  # from the next bar
        if pos and trail_pts is not None:
            ext = h[i] if pos > 0 else l[i]
            if not math.isnan(peak):
                peak = max(peak, ext) if pos > 0 else min(peak, ext)
            elif pos * (ext - fills[0]) >= trail_pts[0]:
                peak = ext
        if pos and lock2 is not None and not locked2:
            seen = (h[i] if pos > 0 else l[i]) if lock_touch else c[i]
            locked2 = pos * (seen - fills[0]) >= lock2[0]
        if pos and trail is not None and not math.isnan(sigma):  # best close and the arming test, at bar close
            best = c[i] if math.isnan(best) else (max(best, c[i]) if pos > 0 else min(best, c[i]))
            if not armed and pos * (c[i] - fills[0]) >= sigma * fills[0]:
                armed = True
        if in_rth and not math.isnan(day_open) and end in kof:
            chance_side, chance_done = 0, False
            j = kof[end]
            today[j] = abs(c[i] / day_open - 1)
            if filled >= LOOKBACK and not math.isnan(prev_close):
                sigma = ring[:, j].mean()
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                spike = 0.5
                if skip_spike is not None:
                    span = slice(max(0, i - 5 // minutes + 1), i + 1)
                    hi5, lo5 = h[span].max(), l[span].min()
                    if hi5 > lo5:
                        spike = (c[i] - lo5) / (hi5 - lo5) if c[i] > upper else (hi5 - c[i]) / (hi5 - lo5)
                day = idx[i].date()
                year_block = checks_by_year.get(day.year, frozenset()) if checks_by_year else frozenset()
                day_block = skip_checks_on.get(day, frozenset()) if skip_checks_on else frozenset()
                blocked = ((skip_spike is not None and spike >= skip_spike) or day in skip_days or end in year_block
                           or end in day_block
                           or end in no_entry_checks or (day_losers is not None and losers >= day_losers)
                           or (done_after_target and target_today)
                           or cap_pts < min_cap_units * sigma * c[i])
                if pos == 0 and c[i] > upper and not blocked and not (side_once and 1 in lost_sides):
                    pending, est, wait = 1, c[i] + TICK, entry_delay
                    if lock_sigma is not None:
                        sig_trigger = min(lock_sigma[2], max(lock_sigma[1], lock_sigma[0] * sigma * c[i]))
                    if lock_unconfirmed is not None and lock is not None:
                        ok = idx[i] not in confirmed[2] or idx[i] in confirmed[0]
                        sig_trigger = lock[0] if ok else lock_unconfirmed
                    if limit_first is not None:
                        lim_px, lim_left = c[i] - limit_first[0], limit_first[1]
                elif pos == 0 and c[i] < lower and not blocked and not (side_once and -1 in lost_sides):
                    pending, est, wait = -1, c[i] - TICK, entry_delay
                    if lock_sigma is not None:
                        sig_trigger = min(lock_sigma[2], max(lock_sigma[1], lock_sigma[0] * sigma * c[i]))
                    if lock_unconfirmed is not None and lock is not None:
                        ok = idx[i] not in confirmed[2] or idx[i] in confirmed[1]
                        sig_trigger = lock[0] if ok else lock_unconfirmed
                    if limit_first is not None:
                        lim_px, lim_left = c[i] + limit_first[0], limit_first[1]
                elif (pos and len(fills) < units and i != first_bar
                      and ((pos > 0 and c[i] > upper) or (pos < 0 and c[i] < lower))
                      and pos * (c[i] - fills[0]) >= k * sigma * fills[0]):
                    add_pending = True
        if in_rth and end == CLOSE:
            chance_side = 0
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
