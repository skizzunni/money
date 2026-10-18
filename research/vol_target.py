"""Round one hundred and thirty-six: volatility-targeted size, judged as money a week on one account.

    python research/vol_target.py nsx1m_scaled.pkl nq1m_scaled.pkl

Every size so far was fixed, or followed the account or a signal. Volatility-managed portfolios (Moreira and Muir,
2017, Journal of Finance) scale exposure inversely to recent volatility: when the size of the market's swings is
predictable but the return per unit of swing is not, this raises the return for the risk. On the Apex account the
risk that binds is the size of a day's swing against the $2,000 drawdown, which is exactly what this evens out.
Rule, fixed before running, no look-ahead: each session's size multiple k = (the median, over all earlier sessions, of
the 14-session average 09:30-16:00 range) / (the average range of the 14 sessions before today), clipped; 1 for the
first 60 sessions. The whole day (bot + breakout, evaluation and funded) is scaled by k (fees too: a slight
approximation, and the contracts are not rounded). Variants:
  vol <= 1x      clipped to 0.5 - 1.0: only ever smaller than now (always within 10 MNQ)
  vol 0.75-1.25  clipped to 0.75 - 1.25 (the breakout's 10 MNQ trades would exceed 10: overstated)
  vol 0.5-1.5    clipped to 0.5 - 1.5 (the same, more)
The strategy as it trades now (breakout $400 in the evaluation, $200 funded, payout stop on), 52 weeks from every
start, net of $100 an evaluation and $79 an activation (research/slot_size). Also each variant's daily Sharpe on the
funded account's days. Pick and bar, fixed before running (as rounds 133-135): the highest net a week at $100 on
2011-18; adopted if it nets more than now on 2019-25 AND NQ 2015-24 and no less in the newest 13 months.
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
import slot_eval as SE  # noqa: E402
import slot_funded as SF  # noqa: E402
import slot_size as S  # noqa: E402
import trap_reversal as T  # noqa: E402

VARIANTS = {"now": None, "vol <= 1x": (0.5, 1.0), "vol 0.75-1.25": (0.75, 1.25), "vol 0.5-1.5": (0.5, 1.5)}


def multiples(bars, sessions, lo, hi):
    """k for each session, from the ranges of the sessions before it only."""
    m = bars.index.tz_convert(A.NY)
    day = pd.DatetimeIndex(m.normalize().tz_localize(None))
    rng = bars.high.groupby(day).max() - bars.low.groupby(day).min()
    avg14 = rng.rolling(14).mean().shift(1)  # the 14 sessions before today
    ref = avg14.expanding().median()  # over all earlier sessions (avg14 already excludes today)
    k = (ref / avg14).clip(lo, hi)
    k[np.arange(len(k)) < 60] = 1.0
    return {d: float(k.get(d, 1.0)) if np.isfinite(k.get(d, np.nan)) else 1.0 for d in sessions}


def scaled(days, k):
    return [(d, [(k[d] * p, k[d] * h, k[d] * lo) for p, h, lo in tr]) for d, tr in days]


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    ev = SF.legs(bars, T.bot_trades(bars, 3, 1.0, 2.5), 400.0)
    pa = SF.legs(bars, T.bot_trades(bars, 2, 0.5, 6.25), 200.0)
    ks = {name: multiples(bars, sess, *v) if v else None for name, v in VARIANTS.items()}
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        starts = [s for s, d in enumerate(ss) if d <= pd.Timestamp(last_start) and s + S.HORIZON <= len(ss)]
        ev_days, pa_days = P.by_day(ev, ss), P.by_day(pa, ss)
        for name, k in ks.items():
            e, p = (ev_days, pa_days) if k is None else (scaled(ev_days, k), scaled(pa_days, k))
            out = SE.slots(e, p, starts, None)
            day_pnl = np.array([sum(x for x, _, _ in tr) for _, tr in p])
            row = {"period": label, "setup": name, "starts": len(starts), "paid $/wk": out[:, 0].mean() / S.WEEKS,
                   "evals": out[:, 1].mean(), "funded accts": out[:, 2].mean(),
                   "funded day Sharpe": day_pnl.mean() / day_pnl.std(),
                   "mean k": float(np.mean([k[d] for d in ss])) if k else 1.0}
            for fee in S.FEES:
                row[f"net $/wk at ${fee:.0f}"] = (out[:, 0].mean() - fee * out[:, 1].mean() -
                                                  S.ACTIVATION * out[:, 2].mean()) / S.WEEKS
            rows.append(row)
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"),
                   ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 250)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(3).to_string(index=False))
    key = df.set_index(["setup", "period"])["net $/wk at $100"]
    pick = df[df.period == "2011-2018"].sort_values("net $/wk at $100", ascending=False).iloc[0].setup
    print(f"\npick on 2011-18: {pick}")
    if pick == "now":
        print("the pick is the current setting: nothing to change")
        return
    ok = all(key[(pick, p)] > key[("now", p)] for p in ("2019-2025", "NQ 2015-2024"))
    ok &= key[(pick, "Jul 2025-Aug 2026")] >= key[("now", "Jul 2025-Aug 2026")]
    print("ADOPT" if ok else "NOT ADOPTED")


if __name__ == "__main__":
    main()
