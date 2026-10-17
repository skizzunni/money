"""Round sixty-six: getting all six payouts from a 50K Apex funded account.

    python research/payout_policy.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user, Apex only, one account at a time, wants the six payouts a 50K Performance Account (PA) allows. Round
sixty-one (research/apex_payouts.py) found most PAs bust after one or two payouts, and its payout log suggests why:
the bot earns on a few big days, and Apex pays only when, since the last payout, at least 5 days made $200 or more
and no day made more than 50% of the profit. A PA can hold the money and still not be allowed to ask for it, then
give it back. Two levers aimed at that, plus size, all inside Apex's rules (no hedging, flat by 16:00, at most
20 MNQ in the PA):

  daily profit stop: once the day's equity (closed + open, from the day's start) reaches +$X, close at that level
    (filled at +$X less a tick of slippage per contract) and stop for the day. A big day can then be at most $X,
    which keeps it under 50% of the profit and turns trend days into several qualifying days. X: none, $400, $600,
    $900 in the PA. In the evaluation (no consistency rule) only none or $1,000, tested alone with the current PA.
  protect mode in the PA: while the balance is at or above the payout balance ($52,600, i.e. +$2,600 since the PA
    started, the same test apex_payouts.py uses) and no payout has been taken yet in this cycle, trade 2 MNQ (same
    25-point cap, $100 a trade) until the payout is requested; then back to the normal size. Off or on.
  size in the PA: 3, 4 or 6 MNQ at a 25-point cap ($150, $200, $300 a trade), 2 losers a day (round sixty-one's
    funded setting; 3 losers is left out to keep the grid at 24).

Everything else is apex_payouts.py's model, unchanged: the bot (v1.6 rules, take-profit from the fill) on 1-minute
bars, $1.24 fees and a tick of slippage, open profit and loss minute by minute, the worse order inside a minute; the
evaluation is the 50K intraday trail ($3,000 target, $2,000 drawdown trailing open profit, 30 calendar days) at the
current setting, 4 MNQ, $200, 3 losers; the PA rules (drawdown trailing open profit until it locks at +$100, tiered
daily loss limit, payout rules, caps base / low / high, six payouts then closed). When the profit stop and a loss
event (the drawdown or the daily loss limit) fall in the same minute, the loss counts.

Measures, per period (starts every session as in apex_payouts.py: 2011-2018 discovery, 2019 - mid 2025, NQ futures
2015 - 2024): evaluation pass %; per evaluation bought: expected payouts ($), P(6 payouts), P(at least one payout);
per PA: payouts, weeks from the PA's start to its first and to its sixth payout (for those that get there), and
payouts per week alive.
Pass bar, fixed before running: the policy with the highest P(6 payouts per evaluation) on 2011-2018 (base caps)
must beat the current setup (PA 4 MNQ, $200, 2 losers, no profit stop, no protect mode) by at least 25% relative in
P(6 payouts per evaluation), with expected payouts per evaluation no lower, on 2019-2025 and on NQ futures (base
caps). The evaluation profit stop is reported on its own (pass rate and payouts per evaluation).
"""
from __future__ import annotations

import itertools
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402

A.TARGET, A.DD, A.DLL, A.DAYS = 3000.0, 2000.0, 1000.0, 30  # the 50K evaluation, set before the workers fork
CAP, EVAL_Q, EVAL_LOSERS, PA_LOSERS = 25.0, 4, 3, 2
SLIP = 0.25 * A.PV  # a tick of slippage per contract, $
PA_Q, PA_X, PROTECT = (3, 4, 6), (None, 400.0, 600.0, 900.0), (False, True)
POLICIES = [dict(q=q, x=x, protect=p, eval_x=None) for q, x, p in itertools.product(PA_Q, PA_X, PROTECT)]
EVAL_STOP = dict(q=4, x=None, protect=False, eval_x=1000.0)  # the evaluation profit stop with the current PA
CURRENT = dict(q=4, x=None, protect=False, eval_x=None)
PROTECT_Q = 2
DATA = {}  # filled in the parent before the job pool forks: label -> (eval days, pa days, sessions, last start)


def eval_run(days, q, horizon_days, stop_x=None):
    """The 50K intraday-trail evaluation from days[0], with an optional daily profit stop: like A.attempt."""
    bal = peak = 0.0
    start = days[0][0]
    for n, (day, trades) in enumerate(days):
        if (day - start).days >= horizon_days:
            return "timeout", n
        day_start = bal
        for pnl, hi_run, lo_path in trades:
            run_peak = np.maximum(peak, bal + q * hi_run)  # the highest equity, open profit included
            bust = np.flatnonzero(bal + q * lo_path <= run_peak - A.DD)
            win = np.flatnonzero(bal + q * hi_run - day_start >= stop_x) if stop_x else np.array([], int)
            i_b = bust[0] if bust.size else math.inf
            if win.size and win[0] < i_b:  # the profit stop, strictly before any loss event
                peak = max(peak, run_peak[win[0]])
                bal = day_start + stop_x - q * SLIP
                peak = max(peak, bal)
                if bal >= A.TARGET:
                    return "passed", n + 1
                break
            if bust.size:
                return "failed", n + 1
            peak = max(peak, run_peak[-1])
            bal += q * pnl
            peak = max(peak, bal)
            if bal >= A.TARGET:
                return "passed", n + 1
    return "timeout", len(days)


def pa_run(days, q, caps, stop_x=None, protect=False):
    """One PA from days[0], as apex_payouts.pa_run, with an optional daily profit stop and protect mode."""
    bal = peak = 0.0
    paid, cycle = [], []
    for n, (_, trades) in enumerate(days):
        day_start, dll = bal, P.dll_for(bal)
        for pnl, hi_run, lo_path in trades:
            qq = PROTECT_Q if protect and bal >= P.MIN_BAL else q  # size set before each trade
            run_peak = np.maximum(peak, bal + qq * hi_run)
            thr = np.minimum(run_peak - P.PA_DD, P.PA_LOCK)
            eq = bal + qq * lo_path
            bust, stop = np.flatnonzero(eq <= thr), np.flatnonzero(eq - day_start <= -dll)
            win = np.flatnonzero(bal + qq * hi_run - day_start >= stop_x) if stop_x else np.array([], int)
            first_loss = min(bust[0] if bust.size else math.inf, stop[0] if stop.size else math.inf)
            if win.size and win[0] < first_loss:  # the profit stop: closed at +X, done for the day
                peak = max(peak, run_peak[win[0]])
                bal = day_start + stop_x - qq * SLIP
                peak = max(peak, bal)
                break
            if bust.size and (not stop.size or bust[0] < stop[0] or
                              (bust[0] == stop[0] and thr[bust[0]] >= day_start - dll)):
                return paid, "failed", n + 1
            if stop.size:
                peak = max(peak, run_peak[stop[0]])
                bal = day_start - dll
                if bal <= min(peak - P.PA_DD, P.PA_LOCK):
                    return paid, "failed", n + 1
                break
            peak = max(peak, run_peak[-1])
            bal += qq * pnl
            peak = max(peak, bal)
        cycle.append(bal - day_start)
        prof = sum(cycle)
        if (sum(x >= P.QUAL for x in cycle) >= 5 and bal >= P.MIN_BAL and prof > 0 and max(cycle) <= 0.5 * prof):
            amt = min(caps[len(paid)], bal - P.SAFETY)
            if amt >= P.MIN_PAY:
                paid.append((n, amt))
                bal -= amt
                cycle = []
                if len(paid) == 6:
                    return paid, "closed", n + 1
    return paid, "alive", len(days)


def _job(args):
    label, pol = args
    ev_days, pa_days, sessions, last_start = DATA[label]
    memo, rows = {}, {k: [] for k in P.CAPS}
    passes = n = 0
    for s, day in enumerate(sessions):
        if day > last_start:
            break
        n += 1
        res, used = eval_run(ev_days[s:], EVAL_Q, A.DAYS, pol["eval_x"])
        if res != "passed":
            for k in P.CAPS:
                rows[k].append(None)
            continue
        passes += 1
        first = s + used
        if first not in memo:
            memo[first] = {}
            for k, caps in P.CAPS.items():
                paid, end, used_pa = pa_run(pa_days[first:], pol["q"], caps, pol["x"], pol["protect"])
                weeks = (sessions[first + used_pa - 1] - sessions[first - 1]).days / 7 if used_pa else 0.0
                wk = [(sessions[first + i] - sessions[first - 1]).days / 7 for i, _ in paid]
                memo[first][k] = (sum(a for _, a in paid), len(paid), end, weeks, wk)
        for k in P.CAPS:
            rows[k].append(memo[first][k])
    out = {"period": label, "PA MNQ": pol["q"], "PA $ a trade": round(pol["q"] * CAP * A.PV),
           "profit stop": "-" if pol["x"] is None else f"${pol['x']:.0f}", "protect": "on" if pol["protect"] else "-",
           "eval stop": "-" if pol["eval_x"] is None else f"${pol['eval_x']:.0f}", "pass %": 100 * passes / n}
    for k, rs in rows.items():
        pa = [r for r in rs if r is not None]
        out[f"{k} $/eval"] = sum(r[0] for r in pa) / n
        out[f"{k} P6 %"] = 100 * sum(r[1] == 6 for r in pa) / n
        out[f"{k} P1 %"] = 100 * sum(r[1] >= 1 for r in pa) / n
        out[f"{k} payouts/PA"] = np.mean([r[1] for r in pa]) if pa else 0.0
        w1 = [r[4][0] for r in pa if r[1] >= 1]
        w6 = [r[4][5] for r in pa if r[1] == 6]
        out[f"{k} wk to 1st"] = np.mean(w1) if w1 else float("nan")
        out[f"{k} wk to 6th"] = np.mean(w6) if w6 else float("nan")
        weeks = sum(r[3] for r in pa)
        out[f"{k} $/wk funded"] = sum(r[0] for r in pa) / weeks if weeks else 0.0
        out[f"{k} alive %"] = 100 * np.mean([r[2] == "alive" for r in pa]) if pa else 0.0
    return out


def load(path, periods, pool):
    runs = dict(pool.map(A.trades_for, [(path, CAP, EVAL_LOSERS), (path, CAP, PA_LOSERS)]))
    bars = A.rth(path)
    m = bars.index.tz_convert(A.NY)
    sess = list(pd.DatetimeIndex(sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))))
    for label, first, last_start in periods:
        ss = [x for x in sess if x >= pd.Timestamp(first)]
        ev = P.by_day([x for x in runs[(CAP, EVAL_LOSERS)] if x[0] >= ss[0]], ss)
        pa = P.by_day([x for x in runs[(CAP, PA_LOSERS)] if x[0] >= ss[0]], ss)
        DATA[label] = (ev, pa, ss, pd.Timestamp(last_start))


def same(a, b):
    return all(a[k] == b[k] for k in ("q", "x", "protect", "eval_x"))


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 250)
    with ProcessPoolExecutor(max_workers=3) as pool:
        load(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30")), pool)
        load(nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),), pool)
    labels = ("2011-2018", "2019-2025", "NQ 2015-2024")
    pols = POLICIES + [EVAL_STOP]
    with ProcessPoolExecutor(max_workers=3) as pool:  # forks after DATA is filled
        allr = pd.DataFrame(list(pool.map(_job, [(lb, p) for lb in labels for p in pols])))
    allr["pol"] = [i % len(pols) for i in range(len(allr))]
    cols = ["PA MNQ", "PA $ a trade", "profit stop", "protect", "eval stop", "pass %", "base $/eval", "base P6 %",
            "base P1 %", "base payouts/PA", "base wk to 1st", "base wk to 6th", "base $/wk funded", "base alive %",
            "low $/eval", "low P6 %", "high $/eval", "high P6 %"]
    for lb in labels:
        d = allr[allr.period == lb]
        print(f"\n{lb}, sorted by P(6 payouts) per evaluation (base caps)")
        print(d.sort_values("base P6 %", ascending=False)[cols].round(1).to_string(index=False))
    cur = POLICIES.index(next(p for p in POLICIES if same(p, CURRENT)))
    disc = allr[(allr.period == "2011-2018") & (allr.pol < len(POLICIES))]
    best = int(disc.sort_values(["base P6 %", "base $/eval"], ascending=False).iloc[0].pol)
    b = POLICIES[best]
    print(f"\nbest on 2011-2018: PA {b['q']} MNQ, profit stop {b['x']}, protect {b['protect']}")
    ok = best != cur
    for lb in ("2019-2025", "NQ 2015-2024"):
        d = allr[allr.period == lb]
        rb, rc = d[d.pol == best].iloc[0], d[d.pol == cur].iloc[0]
        good = rb["base P6 %"] >= 1.25 * rc["base P6 %"] and rb["base $/eval"] >= rc["base $/eval"]
        ok &= good
        print(f"  {lb}: P6 {rb['base P6 %']:.2f}% against {rc['base P6 %']:.2f}%, ${rb['base $/eval']:.0f} per "
              f"evaluation against ${rc['base $/eval']:.0f}: {'PASS' if good else 'FAIL'}")
    print(f"  {'PASS' if ok else 'FAIL'}")
    e = len(POLICIES)
    for lb in labels:
        d = allr[allr.period == lb]
        re_, rc = d[d.pol == e].iloc[0], d[d.pol == cur].iloc[0]
        print(f"evaluation profit stop $1,000, {lb}: pass {re_['pass %']:.1f}% against {rc['pass %']:.1f}%, "
              f"${re_['base $/eval']:.0f} per evaluation against ${rc['base $/eval']:.0f}, "
              f"P6 {re_['base P6 %']:.2f}% against {rc['base P6 %']:.2f}%")


if __name__ == "__main__":
    main()
