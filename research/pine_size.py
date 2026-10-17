"""Round sixty-seven (description, not a test): the user's TradingView size on Apex.

    python research/pine_size.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user's TradingView run traded 10 MNQ with a $1,170 max loss ($117 a contract, 58.5 points) and made $6,000+ in a
day in October 2026 (round fifty-three's check on real MNQ data: +$21,285 from 21 September to 15 October). The
settings in the NinjaTrader strategy are 4 MNQ at $200. The user asks why one makes in a day what the other doesn't
make in a month, and wants payouts fast. This shows, with the same simulation as rounds sixty-one and sixty-six
(research/apex_payouts.py, base caps, the evaluation at the same size as the funded account), what the big size does
on the 50K intraday-trail evaluation and funded account: how often and how fast it passes and pays, and how often it
busts. Also the bot alone over 16 years at each size: the average week, the share of weeks at $1,500 or more, days at
+$6,000 or more and at -$2,000 or less (a 50K account's whole drawdown). Nothing is selected here; every row is shown.
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

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
SIZES = [(4, 25.0, 3, 2, "NinjaTrader now: 4 MNQ, $200"), (10, 58.5, 4, 4, "TradingView: 10 MNQ, $1,170, 4 losers"),
         (10, 58.5, 2, 2, "10 MNQ, $1,170, 2 losers"), (10, 58.5, 1, 1, "10 MNQ, $1,170, 1 loser"),
         (10, 17.5, 4, 4, "10 MNQ, $350, 4 losers")]


def run_size(args):
    path, first, last_start, (q, cap, ev_losers, pa_losers, name), label = args
    ev_tr = A.trades_for((path, cap, ev_losers))[1]
    pa_tr = ev_tr if pa_losers == ev_losers else A.trades_for((path, cap, pa_losers))[1]
    bars = A.rth(path)
    m = bars.index.tz_convert(A.NY)
    sess = [x for x in sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
            if x >= pd.Timestamp(first)]
    ev_days, pa_days = P.by_day(ev_tr, sess), P.by_day(pa_tr, sess)
    starts = passes = 0
    used_pass, paid_eval, first_weeks, six = [], [], [], 0
    for s, day in enumerate(sess):
        if day > pd.Timestamp(last_start):
            break
        starts += 1
        res, used = A.attempt(ev_days[s:], q, "intraday", 30)
        if res != "passed":
            paid_eval.append(0.0)
            continue
        passes += 1
        used_pass.append(used)
        paid, end, _ = P.pa_run(pa_days[s + used:], q, P.CAPS["base"])
        paid_eval.append(sum(a for _, a in paid))
        six += end == "closed"
        if paid:
            first_weeks.append((sess[s + used + paid[0][0]] - sess[s + used - 1]).days / 7)
    # the bot alone, every session in the period
    daily = pd.Series(0.0, index=pd.DatetimeIndex([d for d in sess if d <= pd.Timestamp(last_start)]))
    for day, pnl, _, _ in ev_tr:
        if day in daily.index:
            daily[day] += q * pnl
    week = daily.groupby(daily.index.to_period("W")).sum()
    return {"period": label, "setting": name, "eval pass %": 100 * passes / starts,
            "sessions to pass (median)": float(np.median(used_pass)) if used_pass else np.nan,
            "$ paid per eval": float(np.mean(paid_eval)), "all 6 paid %": 100 * six / starts,
            "paid >= once %": 100 * np.mean([x > 0 for x in paid_eval]),
            "weeks to 1st payout (median)": float(np.median(first_weeks)) if first_weeks else np.nan,
            "$/week avg": week.mean(), "weeks >= $1.5k %": 100 * (week >= 1500).mean(),
            "losing weeks %": 100 * (week < 0).mean(), "days >= +$6k %": 100 * (daily >= 6000).mean(),
            "days <= -$2k %": 100 * (daily <= -2000).mean(), "worst week": week.min()}


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 250)
    jobs = [(nsx, "2011-01-01", "2018-12-31", s, "2011-2018") for s in SIZES]
    jobs += [(nsx, "2019-01-01", "2025-06-30", s, "2019-2025") for s in SIZES]
    jobs += [(nq, "2015-03-01", "2024-12-31", s, "NQ 2015-2024") for s in SIZES]
    with ProcessPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(run_size, jobs))
    df = pd.DataFrame(rows)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))


if __name__ == "__main__":
    main()
