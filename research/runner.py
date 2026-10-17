"""Round sixty-three: let the trend days run (a runner past the take-profit), on one 50K Apex account.

    python research/runner.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user wants more money a week from one 50K Apex account (intraday trail: $3,000 target, $2,000 drawdown trailing
open profit). The bot's money comes from a few trend days; today it takes all 4 contracts off at the take-profit,
1.5 noise units from the fill. Idea: at the take-profit take off half (2 of 4 MNQ) and keep a runner for the rest of
the trend day.

Already tested, so not repeated here (docs/RESULTS.md): take-profits of 1.0-3.0 noise units for the whole position
(rounds seventeen and twenty-six, and walk-forward at 10 MNQ / $350 with the lock in round fifty-two: 1.5 stays);
half off at +0.5 or +1.0 with the rest to breakeven or as before (round twenty-five, before the take-profit and the
lock existed); trailing 1 or 2 noise units behind the best close from +1 noise unit (round sixteen, same). New here:
the runner starts AT the 1.5 take-profit, with the v1.6 lock and $200 cap at 4 MNQ, judged on the Apex evaluation and
payouts; and a farther target, 3.5 noise units, for the whole position (only 1.0-3.0 were tested).

Rules, fixed before running. The bot as mnqbot.noise v1.6 trades it at 4 MNQ, $200 max loss (25 points), lock at +25
points to entry + 2.5, line stop 0.24 noise units past the line, 3 losers a day, take-profit from the fill (on the
fill bar from the expected fill, as the NinjaTrader bracket), flat at 16:00, Fed rule, 1-minute bars 09:30-16:00.
Variants (a noise unit in points = sigma x the entry price):
  bot          all 4 off at the take-profit, 1.5 noise units (the strategy now);
  trail 0.5    2 off at the take-profit, the other 2 trail a stop 0.5 noise units behind the best price since the
               take-profit (starting at the take-profit - 0.5), never looser than the bot's own stop; to 16:00;
  trail 1.0    the same, 1.0 noise unit behind;
  fixed 0.25   2 off at the take-profit, the runner's stop fixed at the take-profit - 0.25 noise units; to 16:00;
  bot stop     2 off at the take-profit, the runner keeps the bot's own stop (line / max loss / lock); to 16:00;
  target 3.5   all 4 off at 3.5 noise units.
The runner's stop works from the bar after the take-profit; if that bar already closed past it, the runner is closed
at that close. Stop fills: at the stop, or at the open when the open is past it, minus a tick; the stop counts first
when a bar reaches both. $1.24 a contract round trip. A trade (entry to last exit) is a loser for the daily limit when
its total is below zero.
Equity inside a trade, minute by minute, for the evaluation and payouts: the realized part plus the open contracts at
the minute's best and worst price; on a minute with a partial fill the best is counted with all contracts still open
and the worst with whichever count is worse (both conservative for a trailing drawdown).
Measures per period: $ a week at 4 MNQ, win %, worst losing stretch (closed trades), the 50K intraday-trail evaluation
pass / bust % within 30 days (research/apex25k.attempt, $3,000 target, $2,000 drawdown including open profit), and
expected payouts per evaluation bought (research/apex_payouts.pa_run, base caps), evaluation and funded account both
at the variant. Starts: every session up to 2018-12-31 (2011-18), 2025-06-30 (2019-26), 2024-12-31 (NQ 2015-25).
Pass bar, fixed before running: the best 2011-18 variant by payouts per evaluation must beat the bot by at least 10%
in payouts per evaluation, with a 30-day pass rate no lower, on 2019-2026 AND on NQ futures 2015-2025.
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

from mnqbot.data import NY  # noqa: E402
from mnqbot.noise import FED_CUTOFF, FIRST_CHECK, LAST_CHECK, N_CHECKS, RTH_CLOSE, RTH_OPEN, STEP  # noqa: E402

A.TARGET, A.DD, A.DLL, A.DAYS = 3000.0, 2000.0, 1000.0, 30  # the 50K evaluation, set before the workers fork
QTY, HALF, PV, FEE, TICK = 4, 2, 2.0, 1.24, 0.25
MAX_LOSS, LOCK_PLUS, BUF, LOSERS, LOOKBACK = 200.0, 2.5, 0.24, 3, 14
VARIANTS = {
    "bot": dict(tp=1.5, runner=None),
    "trail 0.5": dict(tp=1.5, runner="trail", k=0.5),
    "trail 1.0": dict(tp=1.5, runner="trail", k=1.0),
    "fixed 0.25": dict(tp=1.5, runner="fixed", k=0.25),
    "bot stop": dict(tp=1.5, runner="botstop", k=0.0),
    "target 3.5": dict(tp=3.5, runner=None),
}
PERIODS = {"idx": (("2011-2018", "2011-01-01", "2018-12-31", 2011, 2018),
                   ("2019-2026", "2019-01-01", "2025-06-30", 2019, 2026)),
           "nq": (("NQ 2015-2025", "2015-03-01", "2024-12-31", 2015, 2025),)}


def simulate(bars: pd.DataFrame, tp_units: float, runner: str | None, k: float = 0.0):
    """mnqbot.noise.run (stop mode, v1.6) at 4 MNQ with an optional runner. Returns one row per trade:
    (session day, total P/L $, minute-by-minute best equity (running max) $, worst equity $), fees included."""
    idx = bars.index.tz_convert(NY)
    o, c = bars["open"].to_numpy(float), bars["close"].to_numpy(float)
    h, lo_ = bars["high"].to_numpy(float), bars["low"].to_numpy(float)
    minutes = 1
    slip = TICK
    cap_pts = MAX_LOSS / QTY / PV
    trigger = 1.0 * MAX_LOSS / QTY / PV  # lock at +1 max loss
    fed = A.FED
    ring = np.full(LOOKBACK * N_CHECKS, np.nan)
    today = [math.nan] * N_CHECKS
    filled = slot = 0
    day_open = prev_close = last_rth_close = math.nan
    upper = lower = sigma = math.nan
    fed_today = False
    pos = n_open = 0
    entry_px = est_px = 0.0
    entry_bar = 0
    realized = 0.0  # $ banked by a partial exit, before fees
    phase = 1
    run_stop = best = math.nan
    losers_today = 0
    locked = False
    pending = 0
    path_hi: list[float] = []
    path_lo: list[float] = []
    out = []

    def finish(i, price, why):
        nonlocal pos, n_open, realized, phase, locked, losers_today
        total = realized + pos * (price - entry_px) * n_open * PV - FEE * QTY
        hi = np.maximum.accumulate(np.append(np.array(path_hi), total))
        lo_path = np.append(np.array(path_lo), total)
        out.append((idx[entry_bar].normalize().tz_localize(None), total, hi, lo_path, why))
        if total < 0 and why != "Session ended":
            losers_today += 1
        pos, n_open, realized, phase, locked = 0, 0, 0.0, 1, False
        path_hi.clear()
        path_lo.clear()

    for i in range(len(bars)):
        t = idx[i]
        t_min = t.hour * 60 + t.minute
        end = t_min + minutes
        in_rth = t_min >= RTH_OPEN and end <= RTH_CLOSE

        if pending:
            d, pending = pending, 0
            if pos == 0:
                pos, n_open, entry_px, entry_bar = d, QTY, o[i] + d * slip, i
                realized, phase = 0.0, 1

        exited = False
        if pos and not math.isnan(upper):
            d = pos
            line = upper * (1 - BUF * sigma) if d > 0 else lower * (1 + BUF * sigma)
            why = "Back inside"
            base = entry_px if entry_bar != i else est_px
            cap = base - d * cap_pts
            if (d > 0 and cap > line) or (d < 0 and cap < line):
                line, why = cap, "Max loss"
            if locked:
                lk = entry_px + d * LOCK_PLUS
                if (d > 0 and lk > line) or (d < 0 and lk < line):
                    line, why = lk, "Lock"
            tighter = (d > 0 and run_stop > line) or (d < 0 and run_stop < line)
            if phase == 2 and runner in ("trail", "fixed") and tighter:
                line, why = run_stop, "Runner stop"
            if entry_bar == i:
                hit = lo_[i] <= line if d > 0 else h[i] >= line
                price = (min(o[i], line) if d > 0 else max(o[i], line)) - d * slip
            elif (d > 0 and o[i] <= line) or (d < 0 and o[i] >= line):
                hit, price = True, o[i] - d * slip
            else:
                hit = lo_[i] <= line if d > 0 else h[i] >= line
                price = line - d * slip
            n_before, r_before = n_open, realized
            if hit:
                finish(i, price, why)
                exited = True
            elif phase == 1 and tp_units > 0:
                tp = base * (1 + d * tp_units * sigma)
                if (d > 0 and h[i] >= tp + TICK) or (d < 0 and lo_[i] <= tp - TICK):
                    if runner is None:
                        finish(i, tp, "Target")
                        exited = True
                    else:
                        realized += d * (tp - entry_px) * HALF * PV
                        n_open, phase = QTY - HALF, 2
                        unit = sigma * entry_px
                        best = tp
                        run_stop = tp - d * k * unit if runner in ("trail", "fixed") else math.nan
                        past = (d > 0 and c[i] <= run_stop) or (d < 0 and c[i] >= run_stop)
                        if runner in ("trail", "fixed") and past:
                            # the bar already closed past the runner's stop: out at the close
                            fav, adv = (h[i], lo_[i]) if d > 0 else (lo_[i], h[i])
                            path_hi.append(r_before + n_before * d * (fav - entry_px) * PV - FEE * QTY)
                            path_lo.append(min(r_before + n_before * d * (adv - entry_px) * PV,
                                               realized + n_open * d * (adv - entry_px) * PV) - FEE * QTY)
                            finish(i, c[i] - d * slip, "Runner stop")
                            exited = True
            if pos and not exited:
                fav, adv = (h[i], lo_[i]) if d > 0 else (lo_[i], h[i])
                path_hi.append(r_before + n_before * d * (fav - entry_px) * PV - FEE * QTY)
                path_lo.append(min(r_before + n_before * d * (adv - entry_px) * PV,
                                   realized + n_open * d * (adv - entry_px) * PV) - FEE * QTY)
                if phase == 2 and runner == "trail":
                    best = max(best, h[i]) if d > 0 else min(best, lo_[i])
                    unit = sigma * entry_px
                    run_stop = max(run_stop, best - k * unit) if d > 0 else min(run_stop, best + k * unit)

        if pos and not locked:
            locked = pos * ((h[i] if pos > 0 else lo_[i]) - entry_px) >= trigger

        if pos and (not in_rth or t_min == RTH_OPEN):
            finish(i, c[i] - pos * slip, "Session ended")

        if t_min == RTH_OPEN:
            prev_close, day_open = last_rth_close, o[i]
            losers_today = 0
            upper = lower = sigma = math.nan
            today = [math.nan] * N_CHECKS
            fed_today = t.strftime("%Y-%m-%d") in fed
        if in_rth:
            last_rth_close = c[i]

        if in_rth and not math.isnan(day_open) and FIRST_CHECK <= end <= LAST_CHECK and (end - FIRST_CHECK) % STEP == 0:
            kk = (end - FIRST_CHECK) // STEP
            today[kk] = abs(c[i] / day_open - 1)
            if filled >= LOOKBACK and not math.isnan(prev_close):
                s = 0.0
                for dd in range(LOOKBACK):
                    s += ring[dd * N_CHECKS + kk]
                sigma = s / LOOKBACK
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                short_ok = not (fed_today and end < FED_CUTOFF)
                fresh_ok = losers_today < LOSERS
                if pos == 0 and c[i] > upper and fresh_ok:
                    pending = 1
                elif pos == 0 and c[i] < lower and short_ok and fresh_ok:
                    pending = -1
                if pending:
                    est_px = c[i] + pending * slip

        if in_rth and end == RTH_CLOSE:
            if pos:
                finish(i, c[i] - pos * slip, "16:00 close")
            if not math.isnan(day_open) and not any(math.isnan(x) for x in today):
                ring[slot * N_CHECKS:(slot + 1) * N_CHECKS] = today
                slot = (slot + 1) % LOOKBACK
                filled += 1
            day_open = math.nan
    return out


def _sim(args):
    path, name = args
    v = VARIANTS[name]
    return name, simulate(A.rth(path), v["tp"], v["runner"], v.get("k", 0.0))


def worst_stretch(pnls):
    eq = np.cumsum(pnls)
    return float(np.max(np.maximum.accumulate(np.maximum(eq, 0)) - eq)) if len(eq) else 0.0


def _eval(args):
    name, trades, sessions, first, last_start, y0, y1, label = args
    ss = [x for x in sessions if x >= pd.Timestamp(first)]
    days = P.by_day([(d, p, hi, lo) for d, p, hi, lo, _ in trades if d >= ss[0]], ss)
    starts = [s for s, x in enumerate(ss) if x <= pd.Timestamp(last_start)]
    passes = busts = 0
    payouts = []
    memo = {}
    for s in starts:
        res, used = A.attempt(days[s:], 1, "intraday", 30)
        if res == "failed":
            busts += 1
        if res != "passed":
            payouts.append(0.0)
            continue
        passes += 1
        f = s + used
        if f not in memo:
            paid, _, _ = P.pa_run(days[f:], 1, P.CAPS["base"])
            memo[f] = sum(a for _, a in paid)
        payouts.append(memo[f])
    yr = [x for x in trades if y0 <= x[0].year <= y1]
    pnl = [x[1] for x in yr]
    n_sess = sum(1 for x in sessions if y0 <= x.year <= y1)
    return {"period": label, "variant": name, "trades/week": 5 * len(pnl) / n_sess,
            "win %": 100 * np.mean([p > 0 for p in pnl]), "$/week": 5 * sum(pnl) / n_sess,
            "worst stretch $": worst_stretch(pnl), "eval pass %": 100 * passes / len(starts),
            "eval bust %": 100 * busts / len(starts), "$ payouts/eval": float(np.mean(payouts))}


def sessions_of(path):
    m = A.rth(path).index.tz_convert(NY)
    return list(pd.DatetimeIndex(sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))))


def main() -> None:
    files = {"idx": sys.argv[1], "nq": sys.argv[2]}
    pd.set_option("display.width", 220)
    rows = []
    with ProcessPoolExecutor(max_workers=3) as pool:
        for key, path in files.items():
            sims = dict(pool.map(_sim, [(path, n) for n in VARIANTS]))
            sess = sessions_of(path)
            jobs = [(n, sims[n], sess, first, last, y0, y1, label)
                    for label, first, last, y0, y1 in PERIODS[key] for n in VARIANTS]
            rows += list(pool.map(_eval, jobs))
    df = pd.DataFrame(rows)
    for label in ("2011-2018", "2019-2026", "NQ 2015-2025"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    disc = df[(df.period == "2011-2018") & (df.variant != "bot")]
    best = disc.sort_values("$ payouts/eval", ascending=False).iloc[0].variant
    print(f"\nbest on 2011-2018 by payouts per evaluation: {best}")
    ok = True
    for label in ("2019-2026", "NQ 2015-2025"):
        d = df[df.period == label].set_index("variant")
        b, c = d.loc[best], d.loc["bot"]
        good = b["$ payouts/eval"] >= 1.1 * c["$ payouts/eval"] and b["eval pass %"] >= c["eval pass %"]
        ok &= good
        print(f"  {label}: ${b['$ payouts/eval']:.0f} per evaluation, {b['eval pass %']:.1f}% pass, against the bot's "
              f"${c['$ payouts/eval']:.0f}, {c['eval pass %']:.1f}%: {'PASS' if good else 'FAIL'}")
    print(f"  {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
