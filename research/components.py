"""Round one hundred and thirty-seven (the audit's stage 6): does the breakout deserve its place?

    python research/components.py nsx1m_scaled.pkl nq1m_scaled.pkl

Each configuration is the whole strategy re-run (the bot's trades, then the breakout's in its gaps by the same
priority rules, research/combo_more.combine), never rows removed from a trade list. Fixed before running:
  combined            the strategy now: bot (evaluation: 3 losers, lock 1.0 / +2.5) + breakout at $400 (funded $200)
  momentum only       the bot alone
  breakout only       the breakout alone ($400 / $200)
  no breakout shorts  combined, a breakout day whose first touch is short has no breakout trade (the strategy's
                      breakout takes the first touch only)
  equal risk          combined with the breakout at the bot's $200 a trade in the evaluation too
Measured per period on the evaluation's settings (as the user's NinjaTrader run): net $, trades, $ a trade, winners
%, average win / loss, max drawdown on closed trades and on minute equity (open P/L included), net / max intraday
drawdown, worst day, longest losing streak, share of net from the 5 largest winners, % of months positive, net with
two more ticks of slippage a round trip ($1 a contract); and, on the account (research/slot_size: 52 weeks from
every start, payout stop on), net $ a week at $100 an evaluation.
Periods: 2011-18 (development), 2019 - mid 2025, Jul 2025 - Aug 2026 and NQ futures 2015-24. All four have been used
by earlier rounds, so none is untouched: the only data no round has seen is what comes after 16 October 2026.
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
import combo_live as C  # noqa: E402
import combo_more as M  # noqa: E402
import slot_eval as SE  # noqa: E402
import slot_size as S  # noqa: E402
import trap_reversal as T  # noqa: E402

CONFIGS = {"combined": (True, "all", 400.0, 200.0), "momentum only": (True, None, None, None),
           "breakout only": (False, "all", 400.0, 200.0), "no breakout shorts": (True, "long", 400.0, 200.0),
           "equal risk": (True, "all", 200.0, 200.0)}


def cands_for(bars, which, risk):
    if which is None:
        return []
    old, C.RISK = C.RISK, risk
    try:
        cands = M.w_candidates(bars, False)
    finally:
        C.RISK = old
    return [legs for legs in cands if which == "all" or legs[0]["d"] > 0]


def build(bars, bot, which, risk):
    """Legs (for the minute equity) and trades (day, $, contracts) of one configuration."""
    cands = cands_for(bars, which, risk)
    old, C.RISK = C.RISK, risk or 200.0
    try:
        legs, _ = M.combine(bars, bot, cands, False)
    finally:
        C.RISK = old
    q_at = {w["a"]: w["q"] for day in cands for w in day}
    trades = [(leg[0], leg[5], M.BOTQ if k < len(bot) else q_at[leg[1]]) for k, leg in enumerate(legs)]
    return legs, trades


def stats(legs, trades, first, last):
    t0, t1 = pd.Timestamp(first), pd.Timestamp(last)
    tr = [(d, p, q) for d, p, q in trades if t0 <= d <= t1]
    if not tr:
        return {}
    pnl = np.array([p for _, p, _ in tr])
    worse = pnl - np.array([q for _, _, q in tr]) * 1.0
    cum = np.cumsum(pnl)
    closed_dd = float(np.max(np.maximum.accumulate(np.concatenate([[0], cum]))[1:] - cum))
    # minute equity: per day, the legs' combined running best and worst (research/trap_reversal.leg_paths)
    peak = bal = intra_dd = 0.0
    for _day, dp, hi_run, lo_path in sorted(T.leg_paths(None, [g for g in legs if t0 <= g[0] <= t1]),
                                           key=lambda x: x[0]):
        run_peak = np.maximum(peak, bal + hi_run)
        intra_dd = max(intra_dd, float(np.max(run_peak - (bal + lo_path))))
        peak = max(peak, float(run_peak[-1]), bal + dp)
        bal += dp
    s = pd.Series(pnl, index=pd.DatetimeIndex([d for d, _, _ in tr]))
    daily = s.groupby(level=0).sum()
    monthly = s.groupby(s.index.to_period("M")).sum()
    losing = run = 0
    for p in pnl:
        run = run + 1 if p < 0 else 0
        losing = max(losing, run)
    net = float(pnl.sum())
    return {"net $": net, "trades": len(pnl), "$ a trade": net / len(pnl), "winners %": 100 * float((pnl > 0).mean()),
            "avg win": float(pnl[pnl > 0].mean()), "avg loss": float(pnl[pnl < 0].mean()),
            "closed DD": closed_dd, "intraday DD": intra_dd,
            "net / intraday DD": net / intra_dd if intra_dd else np.nan,
            "worst day": float(daily.min()), "losing streak": losing,
            "top-5 share %": 100 * float(np.sort(pnl)[-5:].sum()) / net if net > 0 else np.nan,
            "months up %": 100 * float((monthly > 0).mean()), "net, +2 ticks": float(worse.sum())}


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    ev_bot, pa_bot = T.bot_trades(bars, 3, 1.0, 2.5), T.bot_trades(bars, 2, 0.5, 6.25)
    rows = []
    for name, (use_bot, which, ev_risk, pa_risk) in CONFIGS.items():
        ev_legs, ev_trades = build(bars, ev_bot if use_bot else [], which, ev_risk)
        pa_legs, _ = build(bars, pa_bot if use_bot else [], which, pa_risk)
        ev_all, pa_all = T.leg_paths(bars, ev_legs), T.leg_paths(bars, pa_legs)
        for label, first, last_start, last in periods:
            row = {"period": label, "config": name, **stats(ev_legs, ev_trades, first, last)}
            ss = [d for d in sess if d >= pd.Timestamp(first)]
            starts = [s for s, d in enumerate(ss) if d <= pd.Timestamp(last_start) and s + S.HORIZON <= len(ss)]
            out = SE.slots(P.by_day(ev_all, ss), P.by_day(pa_all, ss), starts, None)
            row["account net $/wk at $100"] = (out[:, 0].mean() - 100 * out[:, 1].mean() -
                                               S.ACTIVATION * out[:, 2].mean()) / S.WEEKS
            rows.append(row)
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31", "2018-12-31"),
                   ("2019-2025", "2019-01-01", "2025-06-30", "2025-06-30"),
                   ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14", "2026-09-30"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 300)
    pd.set_option("display.max_columns", 30)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))


if __name__ == "__main__":
    main()
