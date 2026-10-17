"""Round seventy-eight: trade live only when the bot's own recent results are good (an equity-curve filter).

    python research/regime_filter.py nsx1m_scaled.pkl nq1m_scaled.pkl

Momentum strategies run in streaks: trend-friendly weeks and choppy weeks. The bot keeps running virtually every day
(the NinjaTrader engine already does: it tracks its own trades whether or not orders are placed), and the account
trades live only when the bot's own virtual results over the last completed sessions are good. Only completed past
sessions are used: the decision for a session is made before its 09:30 bar. Not tested before in this repo: the
regimes of rounds six and seven were market measures (volatility, last month, overnight range), and the daily loser
limit acts inside a day.

Variants, fixed before running. The virtual bot is the bot as it trades now, at 4 MNQ, $200 (25 points), take-profit
from the fill, 1-minute bars (research/apex25k.trades_for), 3 losers a day in the evaluation and 2 in the funded
account; each phase's filter reads that phase's own virtual bot. A session's virtual P/L is the sum of its trades
($0 on a day without trades); "the last n sessions" are the n completed sessions before the one being decided; with
fewer than n behind it (the start of the data), the session trades live.
  R0  the bot now: live every session at 4 MNQ.
  R1  live (4 MNQ) only if the virtual P/L of the last 10 sessions is > 0; otherwise no orders.
  R2  the same over the last 20 sessions.
  R3  the same over the last 5 sessions.
  R4  4 MNQ when the last 10 sessions' virtual P/L is > 0, otherwise 2 MNQ.
  R5  after 3 losing virtual days in a row, sit out until a virtual winning day, then live again from the next
      session. Days with no virtual P/L ($0) neither break nor extend a streak.
Measures, 2011-18, 2019-25 and NQ futures 2015-24 (the machinery of research/wick_size.py: apex25k.attempt and
apex_payouts.pa_run on per-trade scaled paths with q = 1, base caps): evaluation pass / bust %, paid per evaluation,
all six payouts %, $ a week and worst losing stretch of the live trades, share of sessions traded live.
Adoption bar, fixed before running: paid per evaluation higher than R0's in all three periods AND an evaluation pass
rate no lower than R0's in any; among those, the highest paid per evaluation on 2019-25.
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
CAP, Q = 25.0, 4
VARIANTS = ("R0", "R1", "R2", "R3", "R4", "R5")


def multipliers(virtual: np.ndarray, variant: str) -> np.ndarray:
    """Contracts for each session from the virtual daily P/L of the sessions before it (never the session itself)."""
    n = len(virtual)
    m = np.full(n, Q, dtype=float)
    if variant == "R0":
        return m
    if variant in ("R1", "R2", "R3", "R4"):
        look = {"R1": 10, "R2": 20, "R3": 5, "R4": 10}[variant]
        csum = np.r_[0.0, np.cumsum(virtual)]
        for s in range(look, n):
            good = csum[s] - csum[s - look] > 0  # sessions s-look .. s-1
            if not good:
                m[s] = 2.0 if variant == "R4" else 0.0
        return m
    # R5: a streak of 3 losing virtual days sends the account out until a virtual winning day
    out, streak = False, 0
    for s in range(n):
        m[s] = 0.0 if out else Q  # decided from the days before s
        v = virtual[s]
        if v > 0:
            streak, out = 0, False
        elif v < 0:
            streak += 1
            if streak >= 3:
                out = True
    return m


def check_rules() -> None:
    v = np.array([1, -1, -1, -1, 0, -1, 5, -1, 2, 0], float)
    r5 = multipliers(v, "R5")
    # out after the 3rd loser (day 3) from day 4; $0 day 4 keeps it out; day 6 wins -> live from day 7
    assert list(r5) == [4, 4, 4, 4, 0, 0, 0, 4, 4, 4], r5
    v = np.array([-5.0] * 10 + [10.0] + [1.0] * 9 + [0.0])
    r1 = multipliers(v, "R1")
    assert r1[:10].tolist() == [4.0] * 10  # fewer than 10 sessions behind: live
    assert r1[10] == 0.0  # sessions 0-9 sum to -50; session 10's own +10 is not used
    assert r1[11] == 0.0  # sessions 1-10: -45 + 10 = -35
    assert r1[20] == 4.0 if (v[10:20].sum() > 0) else r1[20] == 0.0
    assert multipliers(v, "R4")[10] == 2.0
    r3 = multipliers(np.array([1, 1, 1, 1, 1, -10, 1, 1, 1, 1, 1, 1], float), "R3")
    assert r3[5] == 4.0 and r3[6] == 0.0 and r3[10] == 0.0 and r3[11] == 4.0, r3


def daily_virtual(trades, sess_index: dict, n: int) -> np.ndarray:
    v = np.zeros(n)
    for day, pnl, _, _ in trades:
        k = sess_index.get(day)
        if k is not None:
            v[k] += Q * pnl
    return v


def sized(trades, sess_index, mult):
    out = []
    for day, pnl, hi_run, lo_path in trades:
        k = sess_index.get(day)
        q = mult[k] if k is not None else 0.0
        if q:
            out.append((day, q * pnl, q * hi_run, q * lo_path))
    return out


def evaluate(args):
    path, first, last_start, label = args
    ev_tr = A.trades_for((path, CAP, 3))[1]
    pa_tr = A.trades_for((path, CAP, 2))[1]
    bars = A.rth(path)
    m = bars.index.tz_convert(A.NY)
    all_sess = sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
    sess_index = {d: k for k, d in enumerate(all_sess)}
    v_ev = daily_virtual(ev_tr, sess_index, len(all_sess))
    v_pa = daily_virtual(pa_tr, sess_index, len(all_sess))
    sess = [x for x in all_sess if x >= pd.Timestamp(first)]
    last = pd.Timestamp(last_start)
    in_period = np.array([pd.Timestamp(first) <= d <= last for d in all_sess])
    rows = []
    for name in VARIANTS:
        m_ev, m_pa = multipliers(v_ev, name), multipliers(v_pa, name)
        ev_sized, pa_sized = sized(ev_tr, sess_index, m_ev), sized(pa_tr, sess_index, m_pa)
        ev_days, pa_days = P.by_day(ev_sized, sess), P.by_day(pa_sized, sess)
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
            first_pa = s + used
            if first_pa not in memo:
                pp, end, _ = P.pa_run(pa_days[first_pa:], 1, P.CAPS["base"])
                memo[first_pa] = (sum(a for _, a in pp), end == "closed")
            paid.append(memo[first_pa][0])
            six += memo[first_pa][1]
        daily = pd.Series(0.0, index=pd.DatetimeIndex([d for d in sess if d <= last]))
        for day, pnl, _, _ in ev_sized:
            if day in daily.index:
                daily[day] += pnl
        eq = daily.cumsum()
        week = daily.groupby(daily.index.to_period("W")).sum()
        rows.append({"period": label, "variant": name, "eval pass %": 100 * passes / starts,
                     "eval bust %": 100 * busts / starts, "$ paid per eval": float(np.mean(paid)),
                     "all 6 paid %": 100 * six / starts, "$/week": week.mean(),
                     "worst stretch": float((eq.cummax() - eq).max()),
                     "sessions live %": 100 * float(np.mean(m_ev[in_period] > 0))})
    return rows


def main() -> None:
    check_rules()
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 250)
    jobs = [(nsx, "2011-01-01", "2018-12-31", "2011-2018"), (nsx, "2019-01-01", "2025-06-30", "2019-2025"),
            (nq, "2015-03-01", "2024-12-31", "NQ 2015-2024")]
    with ProcessPoolExecutor(max_workers=3) as pool:
        df = pd.DataFrame([r for rows in pool.map(evaluate, jobs) for r in rows])
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    base = df[df.variant == "R0"].set_index("period")
    ok = []
    for name in VARIANTS[1:]:
        d = df[df.variant == name].set_index("period")
        good = all(d.loc[p, "$ paid per eval"] > base.loc[p, "$ paid per eval"] and
                   d.loc[p, "eval pass %"] >= base.loc[p, "eval pass %"] for p in base.index)
        print(f"{name}: {'beats' if good else 'does not beat'} R0 in all three periods")
        if good:
            ok.append((d.loc["2019-2025", "$ paid per eval"], name))
    print(f"\nadopted: {max(ok)[1] if ok else 'none (R0 stays)'}")


if __name__ == "__main__":
    main()
