"""Round sixty-three: a size ladder on one 50K Apex account, in the evaluation and in the funded account.

    python research/size_ladder.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user wants more money a week from one account. Round sixty-one sized the funded account flat (4 MNQ, $200, 2
losers) because larger flat sizes bust the $2,000 drawdown before they pay. A ladder sizes up only when the account
can carry it. Round twenty-one tested profit ladders in an evaluation (another firm's rules, at most 3 contracts):
none beat a fixed size. What is new here is the funded account: once the threshold locks at +$100, the cushion
(balance minus threshold) grows with the balance, so a larger size can be carried without risking the account more
than a flat 4 does at the start. In the evaluation (intraday trail) the cushion never exceeds $2,000, so the
evaluation ladders follow closed profit instead (toward the $3,000 target).

Everything as research/apex_payouts.py (round sixty-one): the bot (v1.6 rules) on 1-minute bars, take-profit from the
fill, $1.24 fees and a tick of slippage, open profit and loss minute by minute; Apex 50K intraday-trail evaluation
($3,000 target, $2,000 trailing the highest equity including open profit, 30 calendar days); the funded account
(threshold trails until +$100 then locks, tiered daily loss limit $1,000/$2,000/$3,000, payouts after 5 days of
$200+, a $52,600 balance and no day over 50% of the profit, base caps $1,500, $1,500, $2,000, $2,500, $2,500, $3,000,
six payouts, at most 20 MNQ). The max loss stays 25 points a trade at every size ($200 at 4 MNQ, $300 at 6, $400 at
8), so the trades are the same at every size and only the contracts change; the evaluation trades with 3 losers a
day, the funded account with 2, as the bot is set now. Contracts are set before each trade from the state then.

Ladders, fixed before running (evaluation part + funded part; "profit" = closed balance since the start, "cushion" =
balance minus the threshold):
  E0  evaluation flat 4 MNQ.
  E1  4; 6 once profit >= $1,000; back to 4 when profit < $500.
  E2  4; 6 once profit >= $1,000; 8 once >= $2,000; down a step when profit falls $500 below the step's level.
  F0  funded flat 4 MNQ.
  F1  4; 6 when cushion >= $3,000; 8 when >= $4,000.
  F2  4; 6 at >= $3,000; 8 at >= $4,000; 10 at >= $5,000; 12 at >= $6,000.
  F3  q = cushion // $350, between 4 and 20 (each trade's max loss about 14% of the cushion).
  Eight ladders: E0+F0 (the bot now, baseline), E0+F1, E0+F2, E0+F3, E1+F0, E2+F0, E1+F2, E2+F3.
Measures: evaluation pass / bust / timeout % in 30 days; expected payouts per evaluation bought (base caps); for funded
accounts, payouts per month alive (total paid / total months alive) and the same per week; bust %.
Pass bar, fixed before running: the ladder with the highest expected payouts per evaluation on 2011-2018 must beat
E0+F0 by at least 10% on expected payouts per evaluation, with an evaluation pass rate no lower, on 2019-2026 (starts
to 2025-06-30, so each evaluation and account has room to play out) AND on NQ futures 2015-2025 (starts to
2024-12-31). If the 2011-18 best is E0+F0 itself, the result is FAIL.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402

CAP_PTS, EVAL_LOSERS, PA_LOSERS, CAPS = 25.0, 3, 2, P.CAPS["base"]
LADDERS = [("E0", "F0"), ("E0", "F1"), ("E0", "F2"), ("E0", "F3"), ("E1", "F0"), ("E2", "F0"), ("E1", "F2"),
           ("E2", "F3")]


def eval_q(name: str, profit: float, q: int) -> int:
    """Contracts for the next evaluation trade, from closed profit and the size now (for the step-down buffers)."""
    if name == "E0":
        return 4
    if name == "E1":
        if profit >= 1000:
            return 6
        return 4 if profit < 500 else q
    up = 8 if profit >= 2000 else 6 if profit >= 1000 else 4  # E2
    if up >= q:
        return up
    down = 8 if profit >= 1500 else 6 if profit >= 500 else 4  # a step down only $500 below the step's level
    return min(q, down)


def pa_q(name: str, cushion: float) -> int:
    if name == "F0":
        return 4
    if name == "F1":
        return 8 if cushion >= 4000 else 6 if cushion >= 3000 else 4
    if name == "F2":
        for level, q in ((6000, 12), (5000, 10), (4000, 8), (3000, 6)):
            if cushion >= level:
                return q
        return 4
    return int(min(20, max(4, cushion // 350)))  # F3


def eval_attempt(days, name, horizon=30):
    """research/apex25k.attempt (intraday plan) with the contracts chosen before each trade."""
    bal = peak = 0.0
    q = 4
    start = days[0][0]
    for n, (day, trades) in enumerate(days):
        if (day - start).days >= horizon:
            return "timeout", n
        for pnl, hi_run, lo_path in trades:
            q = eval_q(name, bal, q)
            run_peak = np.maximum(peak - bal, q * hi_run)
            if (q * lo_path - run_peak <= -A.DD).any():
                return "failed", n + 1
            peak = max(peak, bal + q * hi_run[-1])
            bal += q * pnl
            peak = max(peak, bal)
            if bal >= A.TARGET:
                return "passed", n + 1
    return "timeout", len(days)


def pa_ladder(days, name):
    """research/apex_payouts.pa_run with the contracts chosen before each trade from the cushion."""
    bal = peak = 0.0
    paid, cycle = [], []
    for n, (_, trades) in enumerate(days):
        day_start, dll = bal, P.dll_for(bal)
        for pnl, hi_run, lo_path in trades:
            q = pa_q(name, bal - min(peak - P.PA_DD, P.PA_LOCK))
            run_peak = np.maximum(peak, bal + q * hi_run)
            thr = np.minimum(run_peak - P.PA_DD, P.PA_LOCK)
            eq = bal + q * lo_path
            bust, stop = np.flatnonzero(eq <= thr), np.flatnonzero(eq - day_start <= -dll)
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
            bal += q * pnl
            peak = max(peak, bal)
        cycle.append(bal - day_start)
        prof = sum(cycle)
        if sum(x >= P.QUAL for x in cycle) >= 5 and bal >= P.MIN_BAL and prof > 0 and max(cycle) <= 0.5 * prof:
            amt = min(CAPS[len(paid)], bal - P.SAFETY)
            if amt >= P.MIN_PAY:
                paid.append((n, amt))
                bal -= amt
                cycle = []
                if len(paid) == 6:
                    return paid, "closed", n + 1
    return paid, "alive", len(days)


def _job(args):
    ev_trades, pa_trades, sessions, last_start, ladder, label = args
    ev_days, pa_days = P.by_day(ev_trades, sessions), P.by_day(pa_trades, sessions)
    memo, res = {}, []
    for s, day in enumerate(sessions):
        if day > last_start:
            break
        outcome, used = eval_attempt(ev_days[s:], ladder[0])
        if outcome != "passed":
            res.append((outcome, 0.0, None, 0.0))
            continue
        first = s + used
        if first not in memo:
            paid, end, n = pa_ladder(pa_days[first:], ladder[1])
            months = (sessions[first + n - 1] - sessions[first - 1]).days / 30.4 if n else 0.0
            memo[first] = (sum(a for _, a in paid), end, months)
        total, end, months = memo[first]
        res.append(("passed", total, end, months))
    n = len(res)
    pas = [r for r in res if r[0] == "passed"]
    months = sum(r[3] for r in pas)
    per_month = sum(r[1] for r in pas) / months if months else 0.0
    return {"period": label, "ladder": "+".join(ladder),
            "eval pass %": 100 * len(pas) / n,
            "eval bust %": 100 * sum(r[0] == "failed" for r in res) / n,
            "eval timeout %": 100 * sum(r[0] == "timeout" for r in res) / n,
            "$/eval": sum(r[1] for r in res) / n,
            "$/funded acct": np.mean([r[1] for r in pas]) if pas else 0.0,
            "funded bust %": 100 * np.mean([r[2] == "failed" for r in pas]) if pas else 0.0,
            "funded months": np.mean([r[3] for r in pas]) if pas else 0.0,
            "paid $/month funded": per_month, "paid $/week funded": per_month * 7 / 30.4}


def table(path, periods, pool):
    runs = dict(pool.map(A.trades_for, [(path, CAP_PTS, EVAL_LOSERS), (path, CAP_PTS, PA_LOSERS)]))
    bars = A.rth(path)
    m = bars.index.tz_convert(A.NY)
    sess = list(pd.DatetimeIndex(sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))))
    jobs = []
    for label, first, last_start in periods:
        ss = [x for x in sess if x >= pd.Timestamp(first)]
        ev = [x for x in runs[(CAP_PTS, EVAL_LOSERS)] if x[0] >= ss[0]]
        pa = [x for x in runs[(CAP_PTS, PA_LOSERS)] if x[0] >= ss[0]]
        jobs += [(ev, pa, ss, pd.Timestamp(last_start), lad, label) for lad in LADDERS]
    return pd.DataFrame(list(pool.map(_job, jobs)))


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 250)
    with ProcessPoolExecutor(max_workers=3) as pool:
        idx = table(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2026", "2019-01-01", "2025-06-30")), pool)
        fut = table(nq, (("NQ 2015-2025", "2015-03-01", "2024-12-31"),), pool)
    allr = pd.concat([idx, fut])
    for label in ("2011-2018", "2019-2026", "NQ 2015-2025"):
        print(f"\n{label}, sorted by expected payouts per evaluation")
        print(allr[allr.period == label].sort_values("$/eval", ascending=False).drop(columns="period")
              .round(1).to_string(index=False))
    disc = allr[allr.period == "2011-2018"]
    best = disc.sort_values("$/eval", ascending=False).iloc[0]["ladder"]
    print(f"\nbest on 2011-2018: {best}")
    ok = best != "E0+F0"
    for label in ("2019-2026", "NQ 2015-2025"):
        d = allr[allr.period == label].set_index("ladder")
        b, c = d.loc[best], d.loc["E0+F0"]
        good = b["$/eval"] >= 1.1 * c["$/eval"] and b["eval pass %"] >= c["eval pass %"]
        ok &= good
        print(f"  {label}: ${b['$/eval']:.0f} per evaluation, {b['eval pass %']:.1f}% pass against E0+F0 "
              f"${c['$/eval']:.0f}, {c['eval pass %']:.1f}%: {'PASS' if good else 'FAIL'}")
    print(f"  {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
