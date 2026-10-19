"""The candidate (ninjatrader/Strategies/MnqMomentumRunner.cs, docs/RUNNER.md) on the NinjaTrader stand-in.

Its entries, stops, lock and ratchet are B's (the same trades as B when every new limit is off); the sizing, the trail,
the flat time, the daily limits, the target, the account reserve, rejected orders and restarts work as the rules say.
Skipped when no dotnet is installed.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from test_ninjatrader import DOTNET, rth_minutes, run_sim, sim  # noqa: F401  (sim: the stand-in fixture)

from mnqbot.data import NY

pytestmark = pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
TICK, PV, FEE = 0.25, 2.0, 0.95
OFF = dict(EvalTarget=0, EvalTrail=100000, AccountReserve=0, DailyLossBackstop=100000, MaxLosingPositions=20)


def runner(sim, bars, tmp, **props):  # noqa: F811
    props.setdefault("SimCommissionPerSide", FEE)
    trades, orders, dash, printed = run_sim(sim, bars, tmp, minutes=1, breakout=None, Strategy="Runner", **props)
    return trades, orders, dash, printed


def entries(orders):
    """Each entry: (signal bar, name, qty, stop ticks sent with it)."""
    out = []
    for k, o in enumerate(orders):
        if o[1] == "Enter":
            stop = next(p for p in reversed(orders[:k]) if p[1] == "SetStopLoss" and p[2] == o[2] and p[0] == o[0])
            assert stop[4] == "Ticks", stop
            out.append((int(o[0]), o[2], int(o[3]), float(stop[3])))
    return out


def rpc(ticks):
    """Planned risk per contract: 2 x stop points + 2 commissions + 4 ticks ($3.90 in all at $0.95 a side)."""
    return ticks * TICK * PV + 2 * FEE + 4 * TICK * PV


def minutes_of(bars):
    m = bars.index.tz_convert(NY)
    return m, (m.hour * 60 + m.minute).to_numpy()


def test_the_rule_of_thumb():
    assert math.isclose(rpc(100), 53.90) and math.floor(200 / rpc(100)) == 3
    assert math.isclose(4 * rpc(100), 215.60) and math.isclose(3 * rpc(100), 161.70)


@pytest.mark.parametrize("seed", [3, 5])
def test_with_every_new_limit_off_it_trades_exactly_like_b(sim, tmp_path, seed):  # noqa: F811
    bars = rth_minutes(40, seed)
    b, _, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=False, SimCommissionPerSide=FEE)
    r, _, _, _ = runner(sim, bars, tmp_path, RunnerExit=False, MaxRisk=10000, SizingCommission=0, ReserveTicks=0,
                        FlatMinute=960, **OFF)
    assert len(b) > 20 and r == b


@pytest.mark.parametrize("seed", [3, 5, 9])
def test_size_from_the_stop_and_costs(sim, tmp_path, seed):  # noqa: F811
    """Fresh account, no daily or reserve limit binding: contracts = min(4, floor($200 / risk per contract)); the stop
    is B's, at most 25 points (100 ticks), and never more than $200 is planned."""
    bars = rth_minutes(40, seed)
    _, orders, _, _ = runner(sim, bars, tmp_path, RunnerExit=False, **OFF)
    ent = entries(orders)
    assert ent
    for _, _, q, ticks in ent:
        assert 1 <= ticks <= 100
        assert q == min(4, math.floor(200 / rpc(ticks) + 1e-9)), (q, ticks)
        assert q * rpc(ticks) <= 200 + 1e-9


def test_no_trade_when_one_contract_does_not_fit(sim, tmp_path):  # noqa: F811
    bars = rth_minutes(40, 5)
    _, ref, _, _ = runner(sim, bars, tmp_path, RunnerExit=False, **OFF)
    _, orders, _, printed = runner(sim, bars, tmp_path, RunnerExit=False, MaxRisk=20, **OFF)
    ent = entries(orders)
    assert len(ent) < len(entries(ref))
    for _, _, q, ticks in ent:
        assert rpc(ticks) <= 20 and q == math.floor(20 / rpc(ticks) + 1e-9)
    assert any("not taken: risk budget" in p for p in printed)


def atr5(bars, n=14):
    """ATR(n), Wilder, of completed 5-minute bars of 09:30-16:00, as known at the close of each 1-minute bar."""
    _, t = minutes_of(bars)
    out = np.full(len(bars), np.nan)
    atr, key, prev_c, count, total = np.nan, -1, np.nan, 0, 0.0
    h5 = l5 = c5 = np.nan
    for i, (hi, lo, c, tm) in enumerate(zip(bars.high, bars.low, bars.close, t, strict=True)):
        if 570 <= tm < 960:
            if tm // 5 != key:
                key, h5, l5 = tm // 5, hi, lo
            else:
                h5, l5 = max(h5, hi), min(l5, lo)
            c5 = c
            if (tm + 1) % 5 == 0:
                tr = h5 - l5 if np.isnan(prev_c) else max(h5, prev_c) - min(l5, prev_c)
                prev_c, key, count = c5, -1, count + 1
                if count <= n:
                    total += tr
                    atr = total / n if count == n else atr
                else:
                    atr = (atr * (n - 1) + tr) / n
        out[i] = atr
    return out


def stops_by_bar(orders, name):
    return {int(o[0]): float(o[3]) for o in orders if o[1] == "SetStopLoss" and o[2] == name and o[4] == "Price"}


@pytest.mark.parametrize("seed", [3, 5, 9])
def test_runner_trail(sim, tmp_path, seed):  # noqa: F811
    """The runner against itself without the trail (no take-profit in either): the stops are the same until the best
    price since the entry is 2R past the fill (R = the fill to the initial stop); from then each stop is the tighter of
    the untrailed stop and the best of best price - 3 x ATR(14, 5 min) so far, rounded to a tick. No stop loosens."""
    bars = rth_minutes(60, seed)
    hi, lo = bars.high.to_numpy(), bars.low.to_numpy()
    atr = atr5(bars)
    trail, o1, _, _ = runner(sim, bars, tmp_path, RunnerExit=True, **OFF)
    plain, o0, _, _ = runner(sim, bars, tmp_path, RunnerExit=False, TakeProfit=0, **OFF)
    ent1, ent0 = entries(o1), entries(o0)
    checked = 0
    for k, (t1, t0) in enumerate(zip(trail, plain, strict=False)):
        d, eb, en = int(t1[0]), int(t1[1]), float(t1[2])
        assert (t1[:3], ent1[k]) == (t0[:3], ent0[k])  # same entry while the trades so far are the same
        ticks = ent1[k][3]
        r_pts = ticks * TICK
        s1, s0 = stops_by_bar(o1, ent1[k][1]), stops_by_bar(o0, ent0[k][1])
        s1 = {b: v for b, v in s1.items() if eb <= b < int(t1[3])}
        s0 = {b: v for b, v in s0.items() if eb <= b < int(t0[3])}
        seq = [s1[b] for b in sorted(s1)]
        assert all(d * (y - x) >= -1e-9 for x, y in zip([en - d * r_pts, *seq], seq, strict=False))  # never loosens
        best, best_trail, on = en, np.nan, False
        for b in range(eb, int(t1[3])):
            best = max(best, hi[b]) if d > 0 else min(best, lo[b])
            on = on or d * (best - en) >= 2 * r_pts - 1e-9
            if on and not np.isnan(atr[b]):
                x = best - d * 3 * atr[b]
                x = (math.ceil(x / TICK - 1e-7) if d > 0 else math.floor(x / TICK + 1e-7)) * TICK
                best_trail = x if np.isnan(best_trail) else (max(best_trail, x) if d > 0 else min(best_trail, x))
            if b not in s1 or b not in s0:
                continue
            if not on:
                assert s1[b] == s0[b], (seed, k, b)
            else:
                want = s0[b] if np.isnan(best_trail) else (max(s0[b], best_trail) if d > 0 else min(s0[b], best_trail))
                assert math.isclose(s1[b], want, abs_tol=1e-9), (seed, k, b, s1[b], want)
                checked += s1[b] != s0[b]
        if t1 != t0:
            break  # the account differs from here on
    assert checked, "the trail moved some stop"


def test_flat_by_1555_and_before_an_early_close(sim, tmp_path):  # noqa: F811
    bars = rth_minutes(60, 3)
    m, t = minutes_of(bars)
    _, normal, _, _ = runner(sim, bars, tmp_path)
    late = sorted({m[b].date() for b, _, _, _ in entries(normal) if t[b] >= 13 * 60})  # days with a later entry
    assert late
    early = {d: 13 * 60 for d in late[:3]}
    flag = ",".join(f"{d:%Y-%m-%d} 13:00" for d in early)
    trades, orders, _, printed = runner(sim, bars, tmp_path, SimEarlyClose=flag)
    assert trades
    for row in trades:
        e, x = int(row[1]), int(row[3])
        limit = early.get(m[e].date(), 960) - 5
        assert m[x].date() == m[e].date() and t[x] <= limit, (row, m[e], m[x])
    for b, _, _, _ in entries(orders):
        assert t[b] + 1 < early.get(m[b].date(), 960) - 5
    assert any("not taken: after the flat time" in p for p in printed)


@pytest.mark.parametrize("split", [False, True])
def test_no_entry_after_two_losing_positions(sim, tmp_path, split):  # noqa: F811
    """After the day's second losing position, no entry that day; a position filled in two parts is one position."""
    stopped = 0
    for seed in (3, 5, 9):
        bars = rth_minutes(40, seed)
        m, _ = minutes_of(bars)
        trades, orders, _, printed = runner(sim, bars, tmp_path, SimSplitFills=split,
                                            **{**OFF, "MaxLosingPositions": 2})
        if split:
            assert trades == runner(sim, bars, tmp_path, **{**OFF, "MaxLosingPositions": 2})[0]
        for day in sorted(set(m.date)):
            losers = sorted(int(r[3]) for r in trades if m[int(r[3])].date() == day and float(r[6]) < 0)
            if len(losers) >= 2:
                assert not [b for b, _, _, _ in entries(orders) if m[b].date() == day and b >= losers[1]]
        stopped += sum("not taken: losing positions today" in p for p in printed)
    assert stopped


def test_daily_backstop_includes_the_next_trades_planned_risk(sim, tmp_path):  # noqa: F811
    """Each entry's planned risk fits in what is left of the day's $250 backstop after the day's closed result."""
    hit = 0
    for seed in (3, 5, 9):
        bars = rth_minutes(40, seed)
        m, _ = minutes_of(bars)
        trades, orders, _, printed = runner(sim, bars, tmp_path, **{**OFF, "DailyLossBackstop": 250})
        for b, _, q, ticks in entries(orders):
            day_net = sum(float(r[6]) for r in trades if m[int(r[3])].date() == m[b].date() and int(r[3]) <= b)
            assert q * rpc(ticks) <= min(200, 250 + day_net) + 1e-9, (seed, b, q, ticks, day_net)
        hit += sum("not taken: daily backstop" in p for p in printed)
    assert hit


def test_stops_for_good_at_the_target(sim, tmp_path):  # noqa: F811
    bars = rth_minutes(60, 5)
    trades, orders, dash, _ = runner(sim, bars, tmp_path, **{**OFF, "EvalTarget": 600})
    cum = np.cumsum([float(r[6]) for r in trades])
    assert cum[-1] >= 600 and (cum[:-1] < 600).all()  # the last trade reached it; nothing after
    assert not [b for b, _, _, _ in entries(orders) if b >= int(trades[-1][3])]
    assert "TARGET REACHED" in dash


@pytest.mark.parametrize("seed", [3, 5, 9])
def test_account_reserve(sim, tmp_path, seed):  # noqa: F811
    """A tight account ($700 trail, $300 reserve): positions are closed at the reserve line, entries stop when the
    room is gone, and the closed equity never ends below its own peak less the trail."""
    bars = rth_minutes(60, seed)
    trades, _, _, printed = runner(sim, bars, tmp_path, **{**OFF, "EvalTrail": 700, "AccountReserve": 300})
    eq = np.cumsum([float(r[6]) for r in trades])
    assert (eq >= np.maximum.accumulate(np.maximum(eq, 0)) - 700).all()
    assert any("not taken: account reserve room" in p for p in printed)


def test_open_position_closed_or_tightened_when_it_threatens_the_reserve(sim, tmp_path):  # noqa: F811
    """Live, the account's balance falls $1,650 (outside the strategy) while a position is open: the room above the
    reserve line is gone, so the position's stop moves up to the reserve line's price (or it is closed at market if
    the price is already past it); it ends sooner, never later, than without the drop."""
    bars = rth_minutes(40, 3)
    m, _ = minutes_of(bars)
    live = int(np.flatnonzero(m.date == sorted(set(m.date))[20])[0])
    common = dict(SimRealtimeFrom=live, EvalTarget=100000, DailyLossBackstop=100000, MaxLosingPositions=20)
    ref, ref_orders, _, _ = runner(sim, bars, tmp_path, **common)
    row = next(r for r in ref if int(r[1]) > live and int(r[3]) - int(r[1]) >= 8)
    eb, xb, d = int(row[1]), int(row[3]), int(row[0])
    p = eb + 2
    cum = np.zeros(len(bars))
    for r in ref:
        cum[int(r[3]):] += float(r[6])
    liq = 50000 + cum - np.where(np.arange(len(bars)) >= p, 1650, 0)
    path = tmp_path / "liq.txt"
    path.write_text("\n".join(repr(float(x)) for x in liq) + "\n")
    got, orders, _, _ = runner(sim, bars, tmp_path, SimLiqFile=str(path), **common)
    same = next(r for r in got if int(r[1]) == eb)
    assert int(same[3]) < xb and same[5] in ("Account reserve", "Stop loss"), (row, same)
    name = "Long" if d > 0 else "Short"
    before, after = stops_by_bar(ref_orders, name).get(p), stops_by_bar(orders, name).get(p)
    assert same[5] == "Account reserve" or d * (after - before) > 0, (before, after)


def test_rejected_stop_closes_and_a_rejected_close_is_sent_again(sim, tmp_path):  # noqa: F811
    bars = rth_minutes(40, 3)
    trades, orders, _, _ = runner(sim, bars, tmp_path, **OFF)
    for row in trades:
        s = stops_by_bar(orders, "Long" if int(row[0]) > 0 else "Short")
        cand = [b for b in s if int(row[1]) <= b < int(row[3]) - 3]
        if cand:
            b = cand[0]
            break
    got, _, _, _ = runner(sim, bars, tmp_path, RejectStopsAt=str(b), **OFF)
    assert {int(r[3]): r[5] for r in got}.get(b + 1) == "Close: rejected"
    got, _, _, printed = runner(sim, bars, tmp_path, RejectStopsAt=str(b), RejectExitsAt=str(b), **OFF)
    assert {int(r[3]): r[5] for r in got}.get(b + 2) == "Close: retry"
    assert any("closed again at market after a rejected order" in p for p in printed)


def test_rejected_entry_leaves_no_position(sim, tmp_path):  # noqa: F811
    bars = rth_minutes(40, 3)
    trades, orders, _, _ = runner(sim, bars, tmp_path, **OFF)
    b = entries(orders)[0][0]
    got, _, _, printed = runner(sim, bars, tmp_path, SimRejectEntriesAt=str(b), **OFF)
    assert int(trades[0][1]) == b + 1 and all(int(r[1]) != b + 1 for r in got)
    assert any("ORDER REJECTED" in p for p in printed) and len(got) >= len(trades) - 2


def write_state(folder, **kv):
    path = folder / "MnqNoiseMomentum" / "runner-account-Sim101.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{k}={v}\n" for k, v in kv.items()))
    return path


def test_account_state_survives_a_restart(sim, tmp_path):  # noqa: F811
    """Going live (a restart) reads the remembered highest equity and pass: a remembered pass makes no entry; a
    remembered high peak leaves no room for an entry; without the file the same start trades. Live it also writes
    the file back."""
    bars = rth_minutes(40, 3)
    live = int(np.flatnonzero(minutes_of(bars)[0].date == sorted(set(minutes_of(bars)[0].date))[20])[0])
    common = dict(SimRealtimeFrom=live, EvalTarget=100000, EvalTrail=2000, AccountReserve=300,
                  DailyLossBackstop=100000, MaxLosingPositions=20)

    def live_entries(folder):
        _, orders, _, printed = runner(sim, bars, tmp_path, SimUserDataDir=folder, **common)
        return [e for e in entries(orders) if e[0] >= live], printed

    fresh, _ = live_entries(tmp_path / "none")
    assert fresh
    passed = tmp_path / "passed"
    write_state(passed, peak=0, passed=1)
    got, printed = live_entries(passed)
    assert not got and any("target reached" in p and "account state from" in p for p in printed)
    high = tmp_path / "high"
    write_state(high, peak=1e6, passed=0)
    got, printed = live_entries(high)
    assert not got and any("not taken: account reserve room" in p for p in printed)
    saved = (tmp_path / "none" / "MnqNoiseMomentum" / "runner-account-Sim101.txt").read_text()
    assert "peak=" in saved and "passed=0" in saved


def test_liquidation_threshold_input_raises_the_peak(sim, tmp_path):  # noqa: F811
    """Live, the threshold Apex shows sets the least highest equity: a threshold at the balance leaves no room."""
    bars = rth_minutes(40, 3)
    _, orders, _, _ = runner(sim, bars, tmp_path, SimRealtimeFrom=8000, LiquidationThreshold=60000,
                             EvalTarget=100000, DailyLossBackstop=100000, MaxLosingPositions=20)
    assert not [e for e in entries(orders) if e[0] >= 8000]


def test_entries_are_bs_signals_only(sim, tmp_path):  # noqa: F811
    """Every candidate entry is one of B's entries (same bar, same side): B's model makes the signals; the limits only
    skip or resize them, and a signal is skipped while the candidate still holds a position."""
    bars = rth_minutes(40, 9)
    _, b_orders, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=False, SimCommissionPerSide=FEE)
    _, r_orders, _, _ = runner(sim, bars, tmp_path)
    b_set = {(int(o[0]), o[2]) for o in b_orders if o[1] == "Enter"}
    r_set = {(b, n) for b, n, _, _ in entries(r_orders)}
    assert r_set and r_set <= b_set


def test_minute_chart_required(sim, tmp_path):  # noqa: F811
    bars = rth_minutes(20, 3)
    trades, _, dash, _ = run_sim(sim, bars.iloc[::5], tmp_path, minutes=5, breakout=None, Strategy="Runner")
    assert not trades and "use a 1-minute chart" in dash


def test_eval_start_ignores_trades_before_it(sim, tmp_path):  # noqa: F811
    """EvaluationStart: nothing is traded before it, and the evaluation's equity starts at 0 there."""
    bars = rth_minutes(40, 5)
    m, _ = minutes_of(bars)
    start = sorted(set(m.date))[25]
    trades, _, _, _ = runner(sim, bars, tmp_path, EvaluationStart=f"{start:%Y-%m-%d}", **OFF)
    assert trades and all(m[int(r[1])].date() >= start for r in trades)
    assert pd.Timestamp(start) > pd.Timestamp(m[0].date())
