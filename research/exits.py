"""Round one hundred and thirty-eight (the audit's stages 7-8): the lock's giveback, and two other exits.

    python research/exits.py nsx1m_scaled.pkl nq1m_scaled.pkl

In the user's NinjaTrader run, 16 bot trades made +$180 between them after $6,296 of best open profit: the lock. Once
a trade is 1R up (R, the initial risk: $200 / 4 MNQ / $2 = 25 points in the evaluation; the funded lock arms at 0.5R)
the stop moves to entry + 2.5 points and stays there unless the line or the take-profit (1.5 noise units) ends the
trade first. That is the rule as designed, not a delayed update. Two alternatives, defined before running
(mnqbot/noise.py, research-only options, the rest of the strategy unchanged and re-run in full):
  trail 1R      once the lock arms, the stop also sits 25 points behind the best high (long) / low (short) since the
                entry, as of the last bar's close (works from the next bar, never loosens; an open past it exits at
                the open less a tick). The line, the $200 cap, the lock and the take-profit stay.
  half at 1R    half the contracts close at a limit 25 points from the fill (a tick through it; the stop first in a bar
                that reaches both); the other half keeps every rule. R is not redefined. A trade closed in two parts is
                one trade (its loser count, its statistics).
Measured as round 137 (research/components.stats; the evaluation's settings) and on the account (52 weeks, payout
stop on, net $100 an evaluation). Bar, fixed before running: an alternative is worth carrying forward only if it nets
more on the account in all four periods AND its intraday drawdown is no larger in three of the four.
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
import components as K  # noqa: E402
import slot_eval as SE  # noqa: E402
import slot_size as S  # noqa: E402
import trap_reversal as T  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

EXITS = {"lock (now)": {}, "trail 1R": {"trail_points": 25.0}, "half at 1R": {"partial_at": 1.0}}


def bot(bars, losers, lock_at, lock_plus, extra):
    cfg = NoiseConfig(qty=1, max_loss_per_trade=T.CAP * A.PV, max_losers=losers, fed_dates=A.FED, skip_dates="",
                      target_on_fill_bar=True, lock_at=lock_at, lock_plus=lock_plus, **extra)
    return run(bars, cfg, minutes=1).trades


def bot_legs(bars, trades, q):
    """trap_reversal.bot_legs, with each record's share of the position (a partial exit closes part of it)."""
    h, lo = bars.high.to_numpy(float), bars.low.to_numpy(float)
    idx = bars.index.tz_convert(A.NY).normalize().tz_localize(None)
    legs = []
    for t in trades:
        a, b = t.entry_bar, t.exit_bar
        hp, lp = (h[a:b] - t.entry, lo[a:b] - t.entry) if t.direction > 0 else (t.entry - lo[a:b], t.entry - h[a:b])
        f = t.frac
        legs.append((idx[a], a, b, np.append(f * (hp * A.PV - A.FEE), t.pnl) * q,
                     np.append(f * (lp * A.PV - A.FEE), t.pnl) * q, q * t.pnl))
    return legs


def build(bars, trades, risk):
    old, C.RISK = C.RISK, risk
    try:
        cands = M.w_candidates(bars, False)
        legs, _ = M.combine(bars, trades, cands, False)
    finally:
        C.RISK = old
    legs[:len(trades)] = bot_legs(bars, trades, M.BOTQ)
    # one trade per position: the bot's records merged by entry bar; the breakout's one each
    merged = {}
    for t, leg in zip(trades, legs[:len(trades)], strict=True):
        d, p, q = merged.get(t.entry_bar, (leg[0], 0.0, M.BOTQ))
        merged[t.entry_bar] = (d, p + leg[5], q)
    q_at = {w["a"]: w["q"] for day in cands for w in day}
    out = list(merged.items()) + [(leg[1], (leg[0], leg[5], q_at[leg[1]])) for leg in legs[len(trades):]]
    return legs, [v for _, v in sorted(out, key=lambda x: x[0])]  # in time order (entry bar)


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    rows = []
    for name, extra in EXITS.items():
        ev_legs, ev_trades = build(bars, bot(bars, 3, 1.0, 2.5, extra), 400.0)
        pa_legs, _ = build(bars, bot(bars, 2, 0.5, 6.25, extra), 200.0)
        ev_all, pa_all = T.leg_paths(bars, ev_legs), T.leg_paths(bars, pa_legs)
        for label, first, last_start, last in periods:
            row = {"period": label, "exit": name, **K.stats(ev_legs, ev_trades, first, last)}
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
    key = df.set_index(["exit", "period"])
    periods = list(df.period.unique())
    for name in list(EXITS)[1:]:
        col = "account net $/wk at $100"
        more = all(key.loc[(name, p)][col] > key.loc[("lock (now)", p)][col] for p in periods)
        dd = sum(key.loc[(name, p)]["intraday DD"] <= key.loc[("lock (now)", p)]["intraday DD"] for p in periods)
        print(f"{name}: account more in all four: {more}; intraday DD no larger in {dd} of 4 -> "
              f"{'CARRY FORWARD' if more and dd >= 3 else 'NOT ADOPTED'}")


if __name__ == "__main__":
    main()
