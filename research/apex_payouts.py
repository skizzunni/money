"""Round sixty-one: what a 50K Apex account pays out, from evaluation to its last payout, and how many it takes to make
$3,000 a week.

    python research/apex_payouts.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user wants $3,000 a week. One account can't carry the size that takes (round sixty), so the income has to come
from several funded accounts (Performance Accounts, PA) traded the same way through a copier. What one PA pays is set
by Apex's payout rules, so they are simulated with the bot itself on 1-minute bars (research/apex25k.py's trades:
v1.6 rules, take-profit from the fill, $1.24 fees and a tick of slippage, open profit and loss minute by minute).

Apex 4.0 (March 2026), as 2026 reviews quote it; Apex's site refuses this machine and the sources disagree on the
payout caps and contract scaling, so those are varied:
  evaluation: 50K intraday trail (the user's), $3,000 target, $2,000 drawdown trailing the highest equity including
    open profit, 30 calendar days; traded at the bot's evaluation setting, 4 MNQ, $200 max loss, 3 losers a day;
  PA (funded): starts the session after the pass. $2,000 drawdown trailing the highest equity including open profit,
    until the threshold reaches the start + $100 ($50,100), then fixed. Daily loss limit $1,000 until the balance is
    $3,000 up, $2,000 until $6,000 up, then $3,000: hitting it closes the trade and ends the day (not a fail).
    A payout can be requested at the end of a day when, since the last payout: at least 5 days made $200 or more,
    the balance is at least $2,600 up ($52,600), and no day made more than 50% of the profit. It pays the cap or
    the balance above $52,100, whichever is less, if that is at least $500 (100% to the trader). Caps, payouts 1-6:
    base $1,500, $1,500, $2,000, $2,500, $2,500, $3,000; low $1,500 each; high $2,000, $2,500, $3,000 x 4. After
    the sixth payout the account closes. Contracts: up to 20 MNQ (the most conservative scaling source).

Candidates for the PA, fixed before running (contracts, max loss a trade; each with 2, 3 or 4 losers a day): the
funded setting now, 10 MNQ at $350; the 17.5-point cap at 4, 6, 8, 12, 15 and 20 MNQ; a 25-point cap at 4, 6, 8
and 10 MNQ; 3 and 4 MNQ at $350.
Measure, per evaluation bought: the chance it passes and the PA then pays at least once, and the expected payouts;
per PA: expected payouts and months from the pass to the account's end (closed after 6 payouts, or busted).
Pass bar, fixed before running: the PA setting with the highest expected payouts per evaluation on 2011-2018 (base
caps) must also beat the current funded setting (10 MNQ, $350, 4 losers) by at least 10% on 2019 - mid 2025 and on
NQ futures 2015 - 2024, and under the low and the high caps. If it fails, the funded setting stays.
Starts: every session; an evaluation needs room to finish (starts up to 2025-06-30 on the index data, 2024-12-31 on
NQ futures); a PA still alive when the data ends is counted with what it paid so far (reported as a share).
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402

A.TARGET, A.DD, A.DLL, A.DAYS = 3000.0, 2000.0, 1000.0, 30  # the 50K evaluation, set before the workers fork
EVAL = (4, 25.0, 3)  # 4 MNQ, $200 (25 points), 3 losers
PA_DD, PA_LOCK, SAFETY, MIN_BAL, MIN_PAY, QUAL = 2000.0, 100.0, 2100.0, 2600.0, 500.0, 200.0
CAPS = {"base": (1500, 1500, 2000, 2500, 2500, 3000), "low": (1500,) * 6, "high": (2000, 2500, 3000, 3000, 3000, 3000)}
COMBOS = [(10, 17.5), (4, 17.5), (6, 17.5), (8, 17.5), (12, 17.5), (15, 17.5), (20, 17.5), (4, 25.0), (6, 25.0),
          (8, 25.0), (10, 25.0), (3, 175 / 3), (4, 43.75)]
LOSERS = (2, 3, 4)
CURRENT = (10, 350, 4)


def dll_for(bal: float) -> float:
    return 1000.0 if bal < 3000 else 2000.0 if bal < 6000 else 3000.0


def pa_run(days, q, caps):
    """One PA from days[0]: (payouts as [(session index, $)], 'closed' | 'failed' | 'alive', sessions used)."""
    bal = peak = 0.0
    paid, cycle = [], []
    for n, (_, trades) in enumerate(days):
        day_start, dll = bal, dll_for(bal)
        for pnl, hi_run, lo_path in trades:
            run_peak = np.maximum(peak, bal + q * hi_run)  # the highest equity so far, open profit included
            thr = np.minimum(run_peak - PA_DD, PA_LOCK)  # trails until it reaches the start + $100
            eq = bal + q * lo_path
            bust, stop = np.flatnonzero(eq <= thr), np.flatnonzero(eq - day_start <= -dll)
            # in the minute both are crossed, price falls through the higher one first
            if bust.size and (not stop.size or bust[0] < stop[0] or
                              (bust[0] == stop[0] and thr[bust[0]] >= day_start - dll)):
                return paid, "failed", n + 1
            if stop.size:  # the daily loss limit: closed at the limit, done for the day
                peak = max(peak, run_peak[stop[0]])
                bal = day_start - dll
                if bal <= min(peak - PA_DD, PA_LOCK):
                    return paid, "failed", n + 1
                break
            peak = max(peak, run_peak[-1])
            bal += q * pnl
            peak = max(peak, bal)
        cycle.append(bal - day_start)
        prof = sum(cycle)
        if (sum(x >= QUAL for x in cycle) >= 5 and bal >= MIN_BAL and prof > 0 and max(cycle) <= 0.5 * prof):
            amt = min(caps[len(paid)], bal - SAFETY)
            if amt >= MIN_PAY:
                paid.append((n, amt))
                bal -= amt
                cycle = []
                if len(paid) == 6:
                    return paid, "closed", n + 1
    return paid, "alive", len(days)


def _job(args):
    """Every start in the period: the evaluation at EVAL, then the PA at (q, cap, losers)."""
    eval_trades, pa_trades, sessions, last_start, q, cap, losers, label = args
    ev_days = by_day(eval_trades, sessions)
    pa_days = by_day(pa_trades, sessions)
    out = {k: [] for k in CAPS}
    memo = {}  # PA start -> results: evaluations started on different days can pass on the same day
    passes = n_starts = 0
    for s, day in enumerate(sessions):
        if day > last_start:
            break
        n_starts += 1
        res, used = A.attempt(ev_days[s:], EVAL[0], "intraday", 30)
        if res != "passed":
            for k in CAPS:
                out[k].append((0.0, 0, "no pass", 0.0))
            continue
        passes += 1
        first = s + used  # the PA's first session: the one after the pass
        if first not in memo:
            memo[first] = {}
            for k, caps in CAPS.items():
                paid, end, n = pa_run(pa_days[first:], q, caps)
                months = (sessions[first + n - 1] - sessions[first - 1]).days / 30.4 if n else 0.0
                memo[first][k] = (sum(a for _, a in paid), len(paid), end, months)
        for k in CAPS:
            out[k].append(memo[first][k])
    row = {"period": label, "PA MNQ": q, "PA max loss $": round(q * cap * A.PV), "PA losers": losers,
           "eval pass %": 100 * passes / n_starts}
    for k, rs in out.items():
        pa = [r for r in rs if r[2] != "no pass"]
        row[f"{k} $/eval"] = np.mean([r[0] for r in rs])
        row[f"{k} paid once %"] = 100 * np.mean([r[1] > 0 for r in rs])
        row[f"{k} $/PA"] = np.mean([r[0] for r in pa]) if pa else 0.0
        row[f"{k} payouts/PA"] = np.mean([r[1] for r in pa]) if pa else 0.0
        row[f"{k} busted %"] = 100 * np.mean([r[2] == "failed" for r in pa]) if pa else 0.0
        row[f"{k} 6 paid %"] = 100 * np.mean([r[2] == "closed" for r in pa]) if pa else 0.0
        row[f"{k} alive %"] = 100 * np.mean([r[2] == "alive" for r in pa]) if pa else 0.0
        row[f"{k} PA months"] = np.mean([r[3] for r in pa]) if pa else 0.0
    return row


def by_day(trades, sessions):
    d = {}
    for day, pnl, hi_run, lo_path in trades:
        d.setdefault(day, []).append((pnl, hi_run, lo_path))
    return [(x, d.get(x, [])) for x in sessions]


def table(path, periods, pool):
    keys = sorted({(EVAL[1], EVAL[2])} | {(cap, lz) for _, cap in COMBOS for lz in LOSERS})
    runs = dict(pool.map(A.trades_for, [(path, cap, lz) for cap, lz in keys]))
    bars = A.rth(path)
    m = bars.index.tz_convert(A.NY)
    sess = list(pd.DatetimeIndex(sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))))
    jobs = []
    for label, first, last_start in periods:
        ss = [x for x in sess if x >= pd.Timestamp(first)]
        ev = [x for x in runs[(EVAL[1], EVAL[2])] if x[0] >= ss[0]]
        for q, cap in COMBOS:
            for lz in LOSERS:
                pa = [x for x in runs[(cap, lz)] if x[0] >= ss[0]]
                jobs.append((ev, pa, ss, pd.Timestamp(last_start), q, cap, lz, label))
    return pd.DataFrame(list(pool.map(_job, jobs)))


def is_current(df):
    return (df["PA MNQ"] == CURRENT[0]) & (df["PA max loss $"] == CURRENT[1]) & (df["PA losers"] == CURRENT[2])


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 250)
    with ProcessPoolExecutor(max_workers=4) as pool:
        idx = table(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30")), pool)
        fut = table(nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),), pool)
    allr = pd.concat([idx, fut])
    cols = ["PA MNQ", "PA max loss $", "PA losers", "eval pass %", "base $/eval", "base paid once %", "base $/PA",
            "base payouts/PA", "base busted %", "base 6 paid %", "base alive %", "base PA months", "low $/eval",
            "high $/eval"]
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        d = allr[allr.period == label]
        print(f"\n{label}, sorted by expected payouts per evaluation bought (base caps)")
        print(d.sort_values("base $/eval", ascending=False)[cols].round(1).to_string(index=False))
    disc = allr[allr.period == "2011-2018"]
    best = disc.sort_values("base $/eval", ascending=False).iloc[0]
    key = (best["PA MNQ"], best["PA max loss $"], best["PA losers"])
    print(f"\nbest on 2011-2018: {key[0]} MNQ, ${key[1]}, {key[2]} losers (${best['base $/eval']:.0f} per evaluation)")
    ok = True
    for label in ("2019-2025", "NQ 2015-2024"):
        d = allr[allr.period == label]
        b = d[(d["PA MNQ"] == key[0]) & (d["PA max loss $"] == key[1]) & (d["PA losers"] == key[2])].iloc[0]
        c = d[is_current(d)].iloc[0]
        for k in CAPS:
            good = b[f"{k} $/eval"] >= 1.1 * c[f"{k} $/eval"]
            ok &= good
            print(f"  {label}, {k} caps: ${b[f'{k} $/eval']:.0f} per evaluation against the current "
                  f"${c[f'{k} $/eval']:.0f}: {'PASS' if good else 'FAIL'}")
    print(f"  {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
