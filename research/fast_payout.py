"""Round eighty-seven: the first payout within two weeks of being funded, on a 50K Apex intraday-trail account.

    python research/fast_payout.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user: the first payout should come within two weeks; play it a little riskier, but more likely to win than to
lose. Apex's first payout needs 5 days of $200 or more, a balance of $52,600 (+$2,600), and no day above half the
profit since the start; the drawdown is $2,000, trailing open profit until it locks at +$100; the daily loss limit is
$1,000 (research/apex_payouts.py). The fastest route: more size, a DAILY PROFIT STOP (once the day is up $X, close
and stop for the day: profit spread over qualifying days, each under half the total) and a DAILY LOSS STOP (once the
day is down $Y, close and stop), with the bot's own entries.

Simulation: a funded account starts on every session (it doesn't depend on when an evaluation passed); it runs up to
10 sessions (two weeks) and stops at the first payout or a bust. The bot on 1-minute bars, 25-point max loss a trade
(so $50 a contract), take-profit 1.5 from the fill, per-trade minute equity (research/lock_apex.trades_for, scaled by
the contracts); the profit and loss stops act on the day's minute equity (closed + open), filled at the level less a
tick of slippage a contract; in a minute that reaches both, the loss counts first.
Policies, fixed before running: contracts 4, 6, 8, 10 x profit stop $400, $600, $800, $1,000, none x loss stop $500,
$800, none x losers a day 1, 2, 3 x lock (0.5, +6.25) or (1.0, +2.5): 360.
Measures: P(first payout within 10 sessions), P(bust within 10 sessions), the first payout's average size, and
P(first payout within 20 sessions).
Pick and bar, fixed before running: the policy with the highest P(payout within 10 sessions) on 2011-18 is the pick;
it is reported on 2019-25 and NQ futures 2015-24 against the strategy's funded setting now (4 MNQ, no stops,
2 losers, lock 0.5 / +6.25). It is adopted if it is higher than the current setting on both, and its chance of a
payout within 10 sessions is above its chance of a bust within 10 sessions on both.
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
import lock_apex as L  # noqa: E402

SLIP = 0.25 * A.PV  # a tick a contract on a stop's fill
QS, XS, YS, LOSERS = (4, 6, 8, 10), (400.0, 600.0, 800.0, 1000.0, None), (500.0, 800.0, None), (1, 2, 3)
LOCKS = ((0.5, 6.25), (1.0, 2.5))
POLICIES = list(itertools.product(QS, XS, YS, LOSERS, LOCKS))
CURRENT = (4, None, None, 2, (0.5, 6.25))
H = 10


def first_payout(days, q, x, y, horizon):
    """A funded account from days[0], up to `horizon` sessions: ('paid', sessions, $) | ('bust', sessions, 0) |
    ('none', horizon, 0)."""
    bal = peak = 0.0
    cycle = []
    for n, (_, trades) in enumerate(days[:horizon]):
        day_start, dll = bal, P.dll_for(bal)
        for pnl, hi_run, lo_path in trades:
            run_peak = np.maximum(peak, bal + q * hi_run)
            thr = np.minimum(run_peak - P.PA_DD, P.PA_LOCK)
            eq = bal + q * lo_path
            day_eq_hi, day_eq_lo = bal + q * hi_run - day_start, eq - day_start
            bust = np.flatnonzero(eq <= thr)
            dl = np.flatnonzero(day_eq_lo <= -dll)
            ls = np.flatnonzero(day_eq_lo <= -y) if y else np.array([], int)
            win = np.flatnonzero(day_eq_hi >= x) if x else np.array([], int)
            first = {k: v[0] for k, v in (("bust", bust), ("dll", dl), ("loss", ls), ("win", win)) if v.size}
            if not first:
                peak = max(peak, run_peak[-1])
                bal += q * pnl
                peak = max(peak, bal)
                continue
            m = min(first.values())
            losers_now = [k for k in ("bust", "dll", "loss") if first.get(k) == m]
            if not losers_now:  # the profit stop came first (a loss level in the same minute counts first)
                peak = max(peak, run_peak[first["win"]])
                bal = day_start + x - q * SLIP
                peak = max(peak, bal)
                break
            # a loss-side level first; in the same minute price falls through the highest of them first
            levels = {"bust": thr[m] if "bust" in losers_now else -math.inf,
                      "dll": day_start - dll if "dll" in losers_now else -math.inf,
                      "loss": day_start - y - q * SLIP if "loss" in losers_now else -math.inf}
            which = max(levels, key=levels.get)
            peak = max(peak, run_peak[m])
            if which == "bust":
                return "bust", n + 1, 0.0
            bal = levels[which]
            if bal <= min(peak - P.PA_DD, P.PA_LOCK):
                return "bust", n + 1, 0.0
            break
        cycle.append(bal - day_start)
        prof = sum(cycle)
        if sum(c >= P.QUAL for c in cycle) >= 5 and bal >= P.MIN_BAL and prof > 0 and max(cycle) <= 0.5 * prof:
            amt = min(P.CAPS["base"][0], bal - P.SAFETY)
            if amt >= P.MIN_PAY:
                return "paid", n + 1, amt
    return "none", min(horizon, len(days)), 0.0


def job(args):
    path, periods, losers, lock = args
    bars = A.rth(path)
    tr = L.trades_for(bars, losers, *lock)
    m = bars.index.tz_convert(A.NY)
    all_sess = sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
    rows = []
    for label, first, last_start in periods:
        sess = [d for d in all_sess if d >= pd.Timestamp(first)]
        days = P.by_day(tr, sess)
        starts = [s for s, d in enumerate(sess) if d <= pd.Timestamp(last_start)]
        for q, x, y in itertools.product(QS, XS, YS):
            r10 = [first_payout(days[s:], q, x, y, H) for s in starts]
            r20 = [first_payout(days[s:], q, x, y, 2 * H) for s in starts]
            paid = [r for r in r10 if r[0] == "paid"]
            rows.append({"period": label, "MNQ": q, "profit stop": x or 0, "loss stop": y or 0, "losers": losers,
                         "lock": f"{lock[0]}/+{lock[1]}",
                         "paid in 10 %": 100 * len(paid) / len(r10),
                         "bust in 10 %": 100 * sum(r[0] == "bust" for r in r10) / len(r10),
                         "paid in 20 %": 100 * sum(r[0] == "paid" for r in r20) / len(r20),
                         "1st payout $": float(np.mean([r[2] for r in paid])) if paid else 0.0,
                         "sessions to pay": float(np.median([r[1] for r in paid])) if paid else np.nan})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    idx_p = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))
    nq_p = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)
    jobs = [(path, per, lz, lk) for path, per in ((nsx, idx_p), (nq, nq_p)) for lz in LOSERS for lk in LOCKS]
    with ProcessPoolExecutor(max_workers=4) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    key = ["MNQ", "profit stop", "loss stop", "losers", "lock"]
    cur = dict(zip(key, (4, 0, 0, 2, "0.5/+6.25"), strict=True))
    pd.set_option("display.width", 250)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        d = df[df.period == label].sort_values("paid in 10 %", ascending=False)
        print(f"\n{label}: top 15 by P(first payout within 10 sessions), and the current setting")
        c = d[np.logical_and.reduce([d[k] == v for k, v in cur.items()])]
        print(pd.concat([d.head(15), c]).drop(columns="period").round(1).to_string(index=False))
    disc = df[df.period == "2011-2018"].sort_values("paid in 10 %", ascending=False).iloc[0]
    pick = {k: disc[k] for k in key}
    print(f"\npick on 2011-18: {pick} ({disc['paid in 10 %']:.1f}% paid within 10 sessions)")
    ok = True
    for label in ("2019-2025", "NQ 2015-2024"):
        d = df[df.period == label]
        b = d[np.logical_and.reduce([d[k] == v for k, v in pick.items()])].iloc[0]
        c = d[np.logical_and.reduce([d[k] == v for k, v in cur.items()])].iloc[0]
        good = b["paid in 10 %"] > c["paid in 10 %"] and b["paid in 10 %"] > b["bust in 10 %"]
        ok &= good
        print(f"  {label}: paid in 10 {b['paid in 10 %']:.1f}% (bust {b['bust in 10 %']:.1f}%) vs current "
              f"{c['paid in 10 %']:.1f}% (bust {c['bust in 10 %']:.1f}%): {'PASS' if good else 'FAIL'}")
    print(f"  {'ADOPT' if ok else 'NOT ADOPTED'}")


if __name__ == "__main__":
    main()
