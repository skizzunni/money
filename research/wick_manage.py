"""Round seventy-seven: manage the rejection-wick trades and the others differently, on one 50K Apex account.

    python research/wick_manage.py nsx1m_scaled.pkl nq1m_scaled.pkl

Rounds seventy-five and seventy-six: when the 5-minute signal bar's wick against the trade is more than half its range
('wick trades', about 40% of the bot's trades), the trade earns $31-53 at 4 MNQ against $7-15 for the others; sizing
the wick trades up didn't help on a 50K account (a rougher path). Here every trade keeps 4 MNQ and the 25-point ($200)
max loss; the cue only changes how each kind of trade is managed. Variants, fixed before running:
  E0  the bot now (take-profit 1.5 noise units, lock at +1 max loss to entry + 2.5 points, market entry).
  E1  wick trades: take-profit 2.5 noise units (others 1.5).
  E2  other trades: take-profit 0.75 noise units (wick trades 1.5).
  E3  E1 and E2.
  E4  other trades lock earlier: at +0.5 max loss (12.5 points) the stop moves to entry + 2.5 (wick trades at +1).
  E5  other trades enter with a limit at the signal bar's midpoint instead of a market order, valid until the next
      check (no fill, no trade); wick trades as now. A limit fills only when price trades a tick through it, at the
      limit, with fees and no slippage; the bracket is measured from the limit price; on the fill bar the stop counts
      (at the stop minus a tick) but neither the take-profit nor the lock (the bar's extreme may come before the fill).
      A pending limit is cancelled at the next check, at 16:00 and at 09:30.
The wick flag is computed exactly as research/wick_size.py does: the 1-minute bars of the 5 minutes ending at the check.
Engine: a copy of mnqbot.noise.run (stop mode) with per-trade take-profit, lock and limit entries; on 1-minute bars,
take-profit working from the fill (target_on_fill_bar), $1.24 a contract round trip and a tick of slippage on market
and stop fills, the stop first when a bar reaches both. E0 must reproduce mnqbot.noise.run trade for trade (checked).
Minute equity for the Apex simulation as research/apex25k.py builds it (for a limit entry the fill minute's high/low
count in full: pessimistic for the intraday trail).
Measures (2011-18, 2019-25, NQ futures 2015-24, as research/wick_size.py): winners %, $ a week, worst losing stretch,
the 50K intraday-trail evaluation pass / bust % within 30 days (3 losers a day), payouts per evaluation and the chance
of all six payouts (research/apex_payouts.py, base caps; the funded account at 2 losers a day).
Adoption bar, fixed before running: more paid per evaluation than E0 in all three periods and an evaluation pass rate
no lower than E0's in any; among those, the highest paid per evaluation on 2019-25. Otherwise none.
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

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402

from mnqbot.noise import (  # noqa: E402
    FED_CUTOFF,
    FIRST_CHECK,
    LAST_CHECK,
    N_CHECKS,
    RTH_CLOSE,
    RTH_OPEN,
    STEP,
    NoiseConfig,
    run,
)

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
CAP, QTY = 25.0, 4
VARIANTS = {  # (wick tp, other tp, wick lock_at, other lock_at, other trades by limit)
    "E0": (1.5, 1.5, 1.0, 1.0, False), "E1": (2.5, 1.5, 1.0, 1.0, False), "E2": (1.5, 0.75, 1.0, 1.0, False),
    "E3": (2.5, 0.75, 1.0, 1.0, False), "E4": (1.5, 1.5, 1.0, 0.5, False), "E5": (1.5, 1.5, 1.0, 1.0, True)}


def engine(bars: pd.DataFrame, cfg: NoiseConfig, var=(1.5, 1.5, 1.0, 1.0, False)):
    """mnqbot.noise.run (stop mode, 1-minute bars, no tighten-only) with per-trade take-profit and lock by the wick
    flag, and limit entries for the other trades.

    Returns [(dir, entry_bar, entry, exit_bar, exit, reason, pnl, wick)]."""
    tp_w, tp_o, lk_w, lk_o, limit_o = var
    minutes = 1
    idx = bars.index.tz_convert(A.NY)
    tmin = (idx.hour * 60 + idx.minute).to_numpy()
    dates = idx.date
    o, c = bars["open"].to_numpy(float), bars["close"].to_numpy(float)
    h, lo = bars["high"].to_numpy(float), bars["low"].to_numpy(float)
    slip = cfg.slippage_ticks * cfg.tick
    lb_n = cfg.lookback
    ring = np.full(lb_n * N_CHECKS, np.nan)
    today = [math.nan] * N_CHECKS
    filled = slot = 0
    day_open = prev_close = last_rth_close = math.nan
    upper = lower = sigma = math.nan
    skip_today = fed_today = False
    pos = 0
    entry_px, entry_bar = 0.0, 0
    est_px = math.nan
    losers_today = 0
    locked = False
    tp_u, lock_at, wick = cfg.take_profit, cfg.lock_at, False  # the open trade's
    limit_fill = False  # the open trade was filled by a limit (fill bar: the stop fills at the stop)
    pending = None  # (direction, wick) market entry at the next open
    plimit = None  # (direction, price) pending limit for an 'other' trade
    trades = []

    def close_pos(i, price, reason):
        nonlocal pos, locked, losers_today
        fee = 2 * cfg.commission_per_side * cfg.qty
        pnl = pos * (price - entry_px) * cfg.qty * cfg.point_value - fee
        trades.append((pos, entry_bar, entry_px, i, price, reason, pnl, wick))
        if pnl < 0 and reason != "Session ended":
            losers_today += 1
        pos, locked = 0, False

    def set_trade(w):
        nonlocal tp_u, lock_at, wick
        wick = w
        tp_u, lock_at = (tp_w, lk_w) if w else (tp_o, lk_o)

    for i in range(len(bars)):
        t_min = tmin[i]
        end = t_min + minutes
        in_rth = t_min >= RTH_OPEN and end <= RTH_CLOSE

        if pending is not None:
            d, w = pending
            pending = None
            if pos == 0:
                pos, entry_px, entry_bar = d, o[i] + d * slip, i
                limit_fill = False
                set_trade(w)
        if plimit is not None and pos == 0 and in_rth and t_min != RTH_OPEN:
            d, lp = plimit
            if (d > 0 and lo[i] <= lp - cfg.tick) or (d < 0 and h[i] >= lp + cfg.tick):
                plimit = None
                pos, entry_px, entry_bar, est_px = d, lp, i, lp
                limit_fill = True
                set_trade(False)

        if pos and not math.isnan(upper):
            line = upper * (1 - cfg.stop_buffer * sigma) if pos > 0 else lower * (1 + cfg.stop_buffer * sigma)
            reason = "Back inside"
            base = entry_px if entry_bar != i else est_px
            cap = base - pos * cfg.max_loss_per_trade / cfg.qty / cfg.point_value
            if (pos > 0 and cap > line) or (pos < 0 and cap < line):
                line, reason = cap, "Max loss"
            if locked:
                lk = entry_px + pos * cfg.lock_plus
                if (pos > 0 and lk > line) or (pos < 0 and lk < line):
                    line, reason = lk, "Lock"
            if entry_bar == i and limit_fill:  # filled inside the bar: the stop can only fill at the stop
                hit = lo[i] <= line if pos > 0 else h[i] >= line
                price = line - pos * slip
            elif entry_bar == i:
                hit = lo[i] <= line if pos > 0 else h[i] >= line
                price = (min(o[i], line) if pos > 0 else max(o[i], line)) - pos * slip
            elif (pos > 0 and o[i] <= line) or (pos < 0 and o[i] >= line):
                hit, price = True, o[i] - pos * slip
            else:
                hit = lo[i] <= line if pos > 0 else h[i] >= line
                price = line - pos * slip
            if hit:
                close_pos(i, price, reason)
            elif tp_u > 0 and not (entry_bar == i and limit_fill):  # a limit fill's bar: its high may predate the fill
                tp = (entry_px if entry_bar != i else est_px) * (1 + pos * tp_u * sigma)
                if (pos > 0 and h[i] >= tp + cfg.tick) or (pos < 0 and lo[i] <= tp - cfg.tick):
                    close_pos(i, tp, "Target")

        if pos and not locked and lock_at > 0 and not (entry_bar == i and limit_fill):
            trigger = lock_at * cfg.max_loss_per_trade / cfg.qty / cfg.point_value
            locked = pos * ((h[i] if pos > 0 else lo[i]) - entry_px) >= trigger

        if pos and (not in_rth or t_min == RTH_OPEN):
            close_pos(i, c[i] - pos * slip, "Session ended")
        if not in_rth or t_min == RTH_OPEN:
            plimit = None

        if t_min == RTH_OPEN:
            prev_close = last_rth_close
            day_open = o[i]
            losers_today = 0
            upper = lower = sigma = math.nan
            today = [math.nan] * N_CHECKS
            ds = str(dates[i])
            skip_today = ds in cfg.skip_dates
            fed_today = cfg.fed_no_shorts and ds in cfg.fed_dates
        if in_rth:
            last_rth_close = c[i]

        if in_rth and not math.isnan(day_open) and FIRST_CHECK <= end <= LAST_CHECK and (end - FIRST_CHECK) % STEP == 0:
            plimit = None  # a limit is valid until the next check
            k = (end - FIRST_CHECK) // STEP
            today[k] = abs(c[i] / day_open - 1)
            if filled >= lb_n and not math.isnan(prev_close):
                s = 0.0
                for dd in range(lb_n):
                    s += ring[dd * N_CHECKS + k]
                sigma = s / lb_n
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                short_ok = not (fed_today and end < FED_CUTOFF)
                fresh_ok = cfg.max_losers <= 0 or losers_today < cfg.max_losers
                d = 0
                if skip_today or pos:
                    pass
                elif c[i] > upper and fresh_ok:
                    d = 1
                elif c[i] < lower and short_ok and fresh_ok:
                    d = -1
                if d:
                    # the 5-minute signal bar (as research/wick_size.py)
                    j = i
                    while j > 0 and tmin[j - 1] >= end - 5 and dates[j - 1] == dates[i]:
                        j -= 1
                    hh, ll, cc = h[j:i + 1].max(), lo[j:i + 1].min(), c[i]
                    rng = hh - ll
                    w = bool(rng > 0 and ((hh - cc) / rng if d > 0 else (cc - ll) / rng) > 0.5)
                    if limit_o and not w:
                        plimit = (d, round(((hh + ll) / 2) / cfg.tick) * cfg.tick)
                    else:
                        pending = (d, w)
                        est_px = c[i] + d * slip

        if in_rth and end == RTH_CLOSE:
            plimit = None
            if pos:
                close_pos(i, c[i] - pos * slip, "16:00 close")
            if not math.isnan(day_open) and not any(math.isnan(x) for x in today):
                ring[slot * N_CHECKS:(slot + 1) * N_CHECKS] = today
                slot = (slot + 1) % lb_n
                filled += 1
            day_open = math.nan
    return trades


def config(losers: int) -> NoiseConfig:
    return NoiseConfig(qty=1, max_loss_per_trade=CAP * A.PV, max_losers=losers, fed_dates=A.FED, skip_dates="",
                       target_on_fill_bar=True)


def paths(bars, trades):
    """Per-contract minute equity as research/apex25k.trades_for builds it: (session, pnl, max hi, lo, won)."""
    idx = bars.index.tz_convert(A.NY)
    h, lo = bars.high.to_numpy(float), bars.low.to_numpy(float)
    out = []
    for d, a, entry, b, _, _, pnl, _ in trades:
        if d > 0:
            hi_path, lo_path = h[a:b] - entry, lo[a:b] - entry
        else:
            hi_path, lo_path = entry - lo[a:b], entry - h[a:b]
        hi_path = np.append(hi_path * A.PV - A.FEE, pnl)
        lo_path = np.append(lo_path * A.PV - A.FEE, pnl)
        out.append((idx[a].normalize().tz_localize(None), pnl, np.maximum.accumulate(hi_path), lo_path))
    return out


def check_e0(path: str, first: str, last: str) -> str:
    """E0 against mnqbot.noise.run on a slice, trade for trade."""
    bars = A.rth(path)
    m = bars.index.tz_convert(A.NY)
    bars = bars[(m >= pd.Timestamp(first, tz=A.NY)) & (m < pd.Timestamp(last, tz=A.NY))]
    cfg = config(3)
    ref = run(bars, cfg, minutes=1).trades
    mine = engine(bars, cfg, VARIANTS["E0"])
    assert len(ref) == len(mine), (len(ref), len(mine))
    for r, x in zip(ref, mine, strict=True):
        assert (r.direction, r.entry_bar, r.exit_bar, r.reason) == (x[0], x[1], x[3], x[5]), (r, x)
        assert abs(r.entry - x[2]) < 1e-9 and abs(r.exit - x[4]) < 1e-9 and abs(r.pnl - x[6]) < 1e-9, (r, x)
    return f"E0 reproduces mnqbot.noise.run: {len(ref)} trades, {first} to {last}"


def evaluate(args):
    path, first, last_start, label, name = args
    var = VARIANTS[name]
    bars = A.rth(path)
    ev_raw, pa_raw = engine(bars, config(3), var), engine(bars, config(2), var)
    ev_tr = [(d, QTY * p, QTY * hi, QTY * lo_) for d, p, hi, lo_ in paths(bars, ev_raw)]
    pa_tr = [(d, QTY * p, QTY * hi, QTY * lo_) for d, p, hi, lo_ in paths(bars, pa_raw)]
    m = bars.index.tz_convert(A.NY)
    sess = [x for x in sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
            if x >= pd.Timestamp(first)]
    last = pd.Timestamp(last_start)
    ev_days, pa_days = P.by_day(ev_tr, sess), P.by_day(pa_tr, sess)
    starts = passes = busts = six = 0
    paid, memo = [], {}
    for s, day in enumerate(sess):
        if day > last:
            break
        starts += 1
        res, used = A.attempt(ev_days[s:], 1, "intraday", 30)
        busts += res == "failed"
        if res != "passed":
            paid.append(0.0)
            continue
        passes += 1
        f0 = s + used
        if f0 not in memo:
            pp, end_, _ = P.pa_run(pa_days[f0:], 1, P.CAPS["base"])
            memo[f0] = (sum(a for _, a in pp), end_ == "closed")
        paid.append(memo[f0][0])
        six += memo[f0][1]
    in_p = [x for x in ev_tr if pd.Timestamp(first) <= x[0] <= last]
    daily = pd.Series(0.0, index=pd.DatetimeIndex([d for d in sess if d <= last]))
    for day, pnl, _, _ in in_p:
        if day in daily.index:
            daily[day] += pnl
    eq = daily.cumsum()
    week = daily.groupby(daily.index.to_period("W")).sum()
    return {"period": label, "variant": name, "trades/week": len(in_p) / len(week),
            "win %": 100 * np.mean([x[1] > 0 for x in in_p]), "$/week": week.mean(),
            "worst stretch": float((eq.cummax() - eq).max()), "eval pass %": 100 * passes / starts,
            "eval bust %": 100 * busts / starts, "$ paid per eval": float(np.mean(paid)),
            "all 6 paid %": 100 * six / starts}


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 250)
    print(check_e0(nsx, "2017-01-01", "2019-01-01"))
    print(check_e0(nq, "2021-01-01", "2022-01-01"))
    periods = [(nsx, "2011-01-01", "2018-12-31", "2011-2018"), (nsx, "2019-01-01", "2025-06-30", "2019-2025"),
               (nq, "2015-03-01", "2024-12-31", "NQ 2015-2024")]
    jobs = [(p, f, ls, lab, n) for p, f, ls, lab in periods for n in VARIANTS]
    with ProcessPoolExecutor(max_workers=3) as pool:
        df = pd.DataFrame(list(pool.map(evaluate, jobs)))
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    base = df[df.variant == "E0"].set_index("period")
    ok = []
    for name in VARIANTS:
        if name == "E0":
            continue
        d = df[df.variant == name].set_index("period")
        good = all(d.loc[p, "$ paid per eval"] > base.loc[p, "$ paid per eval"] and
                   d.loc[p, "eval pass %"] >= base.loc[p, "eval pass %"] for p in base.index)
        print(f"{name}: {'beats' if good else 'does not beat'} E0 in all three periods")
        if good:
            ok.append((d.loc["2019-2025", "$ paid per eval"], name))
    print(f"\nadopted: {max(ok)[1] if ok else 'none (E0 stays)'}")


if __name__ == "__main__":
    main()
