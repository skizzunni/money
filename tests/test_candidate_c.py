"""Candidate C (ninjatrader/Strategies/MnqMomentumC.cs, docs/CANDIDATE_C.md) on the NinjaTrader stand-in.

C qualifies each check from the market data alone, gates orders by the actual position, a pending entry and the risk
limits, and counts the evaluation as passed only on realized profit. With every new limit off it trades exactly like B.
Skipped when no dotnet is installed.
"""
from __future__ import annotations

import math
import re

import numpy as np
import pytest
from test_ninjatrader import DOTNET, rth_minutes, run_sim, sim  # noqa: F401  (sim: the stand-in fixture)
from test_runner import FEE, entries, minutes_of, rpc

pytestmark = pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
OFF = dict(MaxRisk=10000, SizingCommission=0, ReserveTicks=0, EvalTarget=0, EvalTrail=100000, AccountReserve=0,
           DailyLossBackstop=100000, MaxLosingPositions=3, FlatMinute=960)
NOACCOUNT = dict(EvalTarget=0, EvalTrail=100000, AccountReserve=0, DailyLossBackstop=100000, MaxLosingPositions=20)
LINE = re.compile(r"C check (\d{4}-\d\d-\d\d \d\d:\d\d) (long|short): (.*)")


def cand(sim, bars, tmp, **props):  # noqa: F811
    props.setdefault("SimCommissionPerSide", FEE)
    return run_sim(sim, bars, tmp, minutes=1, breakout=None, Strategy="C", **props)


def checks(printed):
    """The check lines: (time, side, 'taken' or the reason)."""
    out = []
    for p in printed:
        m = LINE.match(p)
        if m:
            what = m.group(3)
            out.append((m.group(1), m.group(2), "taken" if what.startswith("entry sent") else
                        what.split("not taken: ", 1)[1].split(" [")[0]))
    return out


@pytest.mark.parametrize("model", [False, True])
@pytest.mark.parametrize("seed", [3, 5, 9])
def test_with_every_new_limit_off_it_trades_exactly_like_b(sim, tmp_path, seed, model):  # noqa: F811
    bars = rth_minutes(40, seed)
    b, _, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=False, SimCommissionPerSide=FEE)
    c, _, _, _ = cand(sim, bars, tmp_path, SignalsFromModel=model, **OFF)
    assert len(b) > 20 and c == b


def test_every_qualifying_check_gets_one_line_and_the_audit_adds_up(sim, tmp_path):  # noqa: F811
    """With orders off, every qualifying check is listed; with orders on, each of those same checks is either taken or
    refused with a reason (nothing is silently suppressed), and the audit's counts add up."""
    bars = rth_minutes(40, 5)
    _, _, _, off = cand(sim, bars, tmp_path, PlaceOrders=False)
    _, orders, _, printed = cand(sim, bars, tmp_path, **NOACCOUNT)
    q_off = [(t, s) for t, s, _ in checks(off)]
    got = checks(printed)
    assert q_off and [(t, s) for t, s, _ in got] == q_off
    taken = sum(w == "taken" for _, _, w in got)
    assert taken == len(entries(orders))
    audit = " ".join(p for p in printed if p.startswith("C audit"))
    assert f"qualifying signals {len(q_off)}, entries sent {taken}" in audit
    listed = next(p for p in printed if p.startswith("C audit: not taken: ")).split("not taken: ", 1)[1]
    counts = {k: int(n) for k, n in (x.rsplit(" ", 1) for x in listed.split("; "))}
    assert counts == {w: sum(x == w for _, _, x in got) for w in {x for _, _, x in got if x != "taken"}}
    reasons = {w for _, _, w in got if w != "taken"}
    assert reasons <= {"open position", "losing positions today", "daily backstop", "after the flat time"}


def _find_refusal_recovery(sim, tmp_path):  # noqa: F811
    """A B entry whose model trade spans later qualifying checks: refusing it at the broker leaves the model 'in a
    trade'. Returns bars, the rejected signal bar, and both runs."""
    for seed in (3, 5, 9, 11, 13):
        bars = rth_minutes(40, seed)
        _, ref, _, _ = cand(sim, bars, tmp_path, **NOACCOUNT)
        for b, _, _, _ in entries(ref):
            m0 = cand(sim, bars, tmp_path, SimRejectEntriesAt=str(b), SignalsFromModel=True, **NOACCOUNT)
            if any(w == "the model's hypothetical position" for _, _, w in checks(m0[3])):
                m1 = cand(sim, bars, tmp_path, SimRejectEntriesAt=str(b), **NOACCOUNT)
                return bars, b, m0, m1
    raise AssertionError("no case found")


def test_a_refused_entry_leaves_no_hypothetical_position(sim, tmp_path):  # noqa: F811
    """The broker rejects an entry. Coupled to B's model (C0), the model's hypothetical position then blocks the next
    qualifying checks although the strategy is flat; kept apart (C1), the first such check is taken."""
    bars, b, m0, m1 = _find_refusal_recovery(sim, tmp_path)
    blocked = [t for t, _, w in checks(m0[3]) if w == "the model's hypothetical position"]
    after = {t: w for t, _, w in checks(m1[3])}
    assert after[blocked[0]] == "taken", (blocked[0], after[blocked[0]])
    assert any("ORDER REJECTED" in p for p in m1[3])
    assert all(int(t[1]) != b + 1 for t in m1[0])  # no position from the rejected entry


def test_a_pending_entry_blocks_another_entry(sim, tmp_path):  # noqa: F811
    """An entry that stays working (not filled) for 40 bars: a qualifying check meanwhile is refused 'pending entry
    order', never a second order."""
    hit = 0
    for seed in (3, 5, 9):
        bars = rth_minutes(40, seed)
        _, orders, _, printed = cand(sim, bars, tmp_path, SimHoldEntryBars=40, **NOACCOUNT)
        hit += sum(w == "pending entry order" for _, _, w in checks(printed))
        sent = [int(o[0]) for o in orders if o[1] == "Enter"]
        assert all(b2 - b1 > 0 for b1, b2 in zip(sent, sent[1:], strict=False))
    assert hit


def test_pass_only_on_realized_profit(sim, tmp_path):  # noqa: F811
    """Live, the account's cash says $10 short of the target while a position shows enough open profit to pass: the
    position is closed, but C does not count the pass and keeps trading on later signals; the earlier rule stopped."""
    bars = rth_minutes(40, 3)
    m, _ = minutes_of(bars)
    live = int(np.flatnonzero(m.date == sorted(set(m.date))[20])[0])
    common = dict(SimRealtimeFrom=live, EvaluationStart=f"{m[live]:%Y-%m-%d}", EvalTarget=1000,
                  DailyLossBackstop=100000, MaxLosingPositions=20, EvalTrail=100000, AccountReserve=0)
    ref, _, _, _ = cand(sim, bars, tmp_path, **{**common, "EvalTarget": 100000})
    close = bars.close.to_numpy()
    eb = p = None
    for r in ref:  # a position with a bar at least 20 points in profit, not its last
        if int(r[1]) > live:
            ks = [k for k in range(int(r[1]), int(r[3]) - 1) if int(r[0]) * (close[k] - float(r[2])) >= 20]
            if ks:
                eb, p = int(r[1]), ks[0]
                break
    assert p is not None
    liq = np.full(len(bars), 50000.0)
    liq[p:] = 50000 + 1000 - 10
    path = tmp_path / "liq.txt"
    path.write_text("\n".join(repr(float(x)) for x in liq) + "\n")
    new, o_new, _, pr_new = cand(sim, bars, tmp_path, SimLiqFile=str(path), **common)
    old, o_old, _, pr_old = cand(sim, bars, tmp_path, SimLiqFile=str(path), PassOnRealizedOnly=False, **common)
    closed_at = {int(r[1]): r for r in new}
    assert closed_at[eb][5] == "Evaluation target" and int(closed_at[eb][3]) == p + 1
    assert not any("evaluation target reached" in x for x in pr_new)
    assert [o for o in o_new if o[1] == "Enter" and int(o[0]) > p + 1]  # trades on
    assert not [o for o in o_old if o[1] == "Enter" and int(o[0]) > p + 1]  # the earlier rule stopped


def test_realized_pass_stops_for_good(sim, tmp_path):  # noqa: F811
    bars = rth_minutes(60, 5)
    trades, orders, dash, printed = cand(sim, bars, tmp_path, **{**NOACCOUNT, "EvalTarget": 600})
    cum = np.cumsum([float(r[6]) for r in trades])
    assert cum[-1] >= 600 and (cum[:-1] < 600).all()
    assert not [b for b, _, _, _ in entries(orders) if b >= int(trades[-1][3])]
    assert "TARGET REACHED (realized)" in dash
    assert any("evaluation target reached on realized net profit" in p for p in printed)


@pytest.mark.parametrize("seed", [3, 5, 9])
def test_size_from_the_stop_and_costs(sim, tmp_path, seed):  # noqa: F811
    bars = rth_minutes(40, seed)
    _, orders, _, _ = cand(sim, bars, tmp_path, **NOACCOUNT)
    ent = entries(orders)
    assert ent
    for _, _, q, ticks in ent:
        assert 1 <= ticks <= 100 and q == min(4, math.floor(200 / rpc(ticks) + 1e-9)) and q * rpc(ticks) <= 200 + 1e-9


@pytest.mark.parametrize("split", [False, True])
def test_two_losing_positions_end_the_day(sim, tmp_path, split):  # noqa: F811
    stopped = 0
    for seed in (3, 5, 9):
        bars = rth_minutes(40, seed)
        m, _ = minutes_of(bars)
        trades, orders, _, printed = cand(sim, bars, tmp_path, SimSplitFills=split,
                                          **{**NOACCOUNT, "MaxLosingPositions": 2})
        for day in sorted(set(m.date)):
            losers = sorted(int(r[3]) for r in trades if m[int(r[3])].date() == day and float(r[6]) < 0)
            if len(losers) >= 2:
                assert not [b for b, _, _, _ in entries(orders) if m[b].date() == day and b >= losers[1]]
        stopped += sum(w == "losing positions today" for _, _, w in checks(printed))
    assert stopped


def test_daily_backstop_includes_the_planned_risk(sim, tmp_path):  # noqa: F811
    hit = 0
    for seed in (3, 5, 9):
        bars = rth_minutes(40, seed)
        m, _ = minutes_of(bars)
        trades, orders, _, printed = cand(sim, bars, tmp_path, **{**NOACCOUNT, "DailyLossBackstop": 250})
        for b, _, q, ticks in entries(orders):
            day_net = sum(float(r[6]) for r in trades if m[int(r[3])].date() == m[b].date() and int(r[3]) <= b)
            assert q * rpc(ticks) <= min(200, 250 + day_net) + 1e-9
        hit += sum(w == "daily backstop" for _, _, w in checks(printed))
    assert hit


def test_flat_by_1555_and_early_close(sim, tmp_path):  # noqa: F811
    bars = rth_minutes(60, 3)
    m, t = minutes_of(bars)
    _, normal, _, _ = cand(sim, bars, tmp_path)
    late = sorted({m[b].date() for b, _, _, _ in entries(normal) if t[b] >= 13 * 60})
    early = {d: 13 * 60 for d in late[:3]}
    trades, orders, _, printed = cand(sim, bars, tmp_path, SimEarlyClose=",".join(f"{d:%Y-%m-%d} 13:00" for d in early))
    for row in trades:
        e, x = int(row[1]), int(row[3])
        assert m[x].date() == m[e].date() and t[x] <= early.get(m[e].date(), 960) - 5
    assert any(w == "after the flat time" for _, _, w in checks(printed))


def test_account_reserve_and_the_stop_report(sim, tmp_path):  # noqa: F811
    """A tight account: refusals for room are listed, and the audit says trading stopped when every qualifying check
    after the last entry was refused for room."""
    bars = rth_minutes(60, 3)
    trades, _, _, printed = cand(sim, bars, tmp_path, **{**NOACCOUNT, "EvalTrail": 700, "AccountReserve": 300})
    eq = np.cumsum([float(r[6]) for r in trades])
    assert (eq >= np.maximum.accumulate(np.maximum(eq, 0)) - 700).all()
    assert any(w == "account reserve room" for _, _, w in checks(printed))
    assert any(p.startswith("C audit: STOPPED:") for p in printed)


def test_rejected_stop_closes_and_a_rejected_close_is_sent_again(sim, tmp_path):  # noqa: F811
    bars = rth_minutes(40, 3)
    trades, orders, _, _ = cand(sim, bars, tmp_path, **NOACCOUNT)
    for row in trades:
        name = "Long" if int(row[0]) > 0 else "Short"
        cand_bars = [int(o[0]) for o in orders if o[1] == "SetStopLoss" and o[2] == name and o[4] == "Price"
                     and int(row[1]) <= int(o[0]) < int(row[3]) - 3]
        if cand_bars:
            b = cand_bars[0]
            break
    got, _, _, _ = cand(sim, bars, tmp_path, RejectStopsAt=str(b), **NOACCOUNT)
    assert {int(r[3]): r[5] for r in got}.get(b + 1) == "Close: rejected"
    got, _, _, _ = cand(sim, bars, tmp_path, RejectStopsAt=str(b), RejectExitsAt=str(b), **NOACCOUNT)
    assert {int(r[3]): r[5] for r in got}.get(b + 2) == "Close: retry"


def test_remembered_pass_survives_a_restart(sim, tmp_path):  # noqa: F811
    bars = rth_minutes(40, 3)
    m, _ = minutes_of(bars)
    live = int(np.flatnonzero(m.date == sorted(set(m.date))[20])[0])
    common = dict(SimRealtimeFrom=live, EvalTarget=100000, DailyLossBackstop=100000, MaxLosingPositions=20)
    _, fresh, _, _ = cand(sim, bars, tmp_path, SimUserDataDir=tmp_path / "none", **common)
    assert [e for e in entries(fresh) if e[0] >= live]
    folder = tmp_path / "passed"
    f = folder / "MnqNoiseMomentum" / "c-account-Sim101.txt"
    f.parent.mkdir(parents=True)
    f.write_text("peak=0\npassed=1\n")
    _, orders, _, printed = cand(sim, bars, tmp_path, SimUserDataDir=folder, **common)
    assert not [e for e in entries(orders) if e[0] >= live]
    assert any("account state from" in p and "target reached" in p for p in printed)


# ── C2: the entry budget uses the full room above the reserve (ReserveRoomShare 1); 0.5 is the earlier C1 rule
DETAIL = re.compile(r"not taken: account reserve room \[room (-?[\d.]+), usable (-?[\d.]+), one contract ([\d.]+)\]")


def test_room_share_changes_nothing_without_the_reserve(sim, tmp_path):  # noqa: F811
    """G1: with no evaluation trail or reserve, the share of the room is never binding: identical trades."""
    for seed in (3, 5):
        bars = rth_minutes(40, seed)
        a = cand(sim, bars, tmp_path, ReserveRoomShare=1.0, **NOACCOUNT)[0]
        b = cand(sim, bars, tmp_path, ReserveRoomShare=0.5, **NOACCOUNT)[0]
        assert a and a == b


@pytest.mark.parametrize("seed", [3, 5, 9])
def test_full_room_refuses_only_when_one_contract_does_not_fit(sim, tmp_path, seed):  # noqa: F811
    """G2 on a tight account ($700 trail, $300 reserve): every refusal for room has usable room below one contract's
    planned risk (with the full room, usable = room; with the earlier rule, half); the closed equity never ends below
    its peak less the trail. (Entries can be fewer with the full room: a larger position near the reserve uses the room
    sooner.)"""
    bars = rth_minutes(60, seed)
    tight = {**NOACCOUNT, "EvalTrail": 700, "AccountReserve": 300}
    full, _, _, p_full = cand(sim, bars, tmp_path, ReserveRoomShare=1.0, **tight)
    _, _, _, p_half = cand(sim, bars, tmp_path, ReserveRoomShare=0.5, **tight)
    for printed, share in ((p_full, 1.0), (p_half, 0.5)):
        details = [m for m in (DETAIL.search(p) for p in printed) if m]
        assert details
        for m in details:
            room, usable, one = (float(m.group(k)) for k in (1, 2, 3))
            assert usable < one and math.isclose(usable, room * share, abs_tol=0.011)
    eq = np.cumsum([float(r[6]) for r in full])
    assert (eq >= np.maximum.accumulate(np.maximum(eq, 0)) - 700).all()


def test_one_line_per_session_and_its_status(sim, tmp_path):  # noqa: F811
    bars = rth_minutes(40, 5)
    _, orders, _, printed = cand(sim, bars, tmp_path, **NOACCOUNT)
    sess = [p for p in printed if p.startswith("C session ")]
    m, t = minutes_of(bars)
    assert len(sess) == len(set(m.date))
    assert sum(int(re.search(r"entries (\d+)", s).group(1)) for s in sess) == len(entries(orders))
    for s in sess:
        n = int(re.search(r"entries (\d+)", s).group(1))
        q = int(re.search(r"qualifying (\d+)", s).group(1))
        status = s.split(": ", 1)[1].split(";")[0]
        assert (status == "active") == (n > 0)
        assert status != "no qualifying setup" or q == 0
    assert sum("warm-up" in s for s in sess) >= 14


# ── Execution correctness: a part-filled entry's remainder, positions counted by entry order, peaks inside a bar
def qty_of(row):
    d, en, ex, pnl = int(row[0]), float(row[2]), float(row[4]), float(row[6])
    per = d * (ex - en) * 2.0 - 2 * FEE
    return round(pnl / per) if abs(per) > 1e-9 else None


def _entry_with_qty(sim, tmp_path, at_least=2, min_bars=0, losing=None):  # noqa: F811
    for seed in (3, 5, 9, 11):
        bars = rth_minutes(40, seed)
        trades, orders, _, _ = cand(sim, bars, tmp_path, **NOACCOUNT)
        for b, _, q, _ in entries(orders):
            row = next((r for r in trades if int(r[1]) == b + 1), None)
            if row is None or q < at_least or int(row[3]) - int(row[1]) < min_bars:
                continue
            if losing is not None and (float(row[6]) < 0) != losing:
                continue
            return bars, b, q, row
    raise AssertionError("no such entry")


def test_partly_filled_entry_remainder_is_tracked_and_cancelled_if_the_position_closes_first(sim, tmp_path):  # noqa: F811
    """1 of the entry's contracts fills; the rest never does. The remainder stays tracked (no other entry is sent while
    it works), and when the 1-contract position closes the remainder is cancelled, so it can never open a late,
    unplanned position."""
    bars, b, q, _ = _entry_with_qty(sim, tmp_path)
    trades, orders, _, printed = cand(sim, bars, tmp_path, SimPartialEntryAt=b, SimPartialFirstQty=1,
                                      SimPartialDelayBars=-1, **NOACCOUNT)
    row = next(r for r in trades if int(r[1]) == b + 1)
    assert qty_of(row) == 1
    x = int(row[3])
    cancels = [int(o[0]) for o in orders if o[1] == "Cancel"]
    assert cancels and cancels[0] >= x, (cancels, x)
    assert not [o for o in orders if o[1] == "Enter" and b < int(o[0]) < cancels[0]]
    assert any("remainder is cancelled" in p for p in printed)
    sent = {int(o[0]) + 1 for o in orders if o[1] == "Enter"}
    assert all(int(r[1]) in sent for r in trades), "every position comes from an entry the strategy sent"


def test_remainder_that_fills_later_joins_the_position(sim, tmp_path):  # noqa: F811
    bars, b, q, _ = _entry_with_qty(sim, tmp_path, min_bars=5)
    trades, orders, _, _ = cand(sim, bars, tmp_path, SimPartialEntryAt=b, SimPartialFirstQty=1, SimPartialDelayBars=2,
                                **NOACCOUNT)
    row = next(r for r in trades if int(r[1]) == b + 1)
    assert qty_of(row) == q
    assert not [o for o in orders if o[1] == "Enter" and b < int(o[0]) <= b + 3]
    assert not [o for o in orders if o[1] == "Cancel"]


def test_a_losing_position_filled_in_two_parts_counts_once(sim, tmp_path):  # noqa: F811
    """A losing position whose contracts filled two bars apart has two trade records with different entry times; the
    day's losing-position count (from the entry order) counts it once."""
    bars, b, q, _ = _entry_with_qty(sim, tmp_path, min_bars=5, losing=True)
    trades, _, _, printed = cand(sim, bars, tmp_path, SimPartialEntryAt=b, SimPartialFirstQty=1, SimPartialDelayBars=2,
                                 **NOACCOUNT)
    m, _ = minutes_of(bars)
    day = m[b].date()
    losers = sum(1 for r in trades if m[int(r[3])].date() == day and float(r[6]) < 0)
    line = next(p for p in printed if p.startswith(f"C session {day:%Y-%m-%d}:"))
    assert int(re.search(r"losing positions (\d+)", line).group(1)) == losers


def test_unrealized_peak_inside_the_exit_bar_is_captured(sim, tmp_path):  # noqa: F811
    """The first position fills on a bar that then runs 200 points its way and closes at the take-profit inside that
    same bar. The earlier rule never saw it open at a bar's close, so its highest equity stopped at the realized
    profit; C counts the bar's best price as reached before the exit (the cautious assumption for the trail)."""
    bars = rth_minutes(40, 3)
    _, orders, _, _ = cand(sim, bars, tmp_path, **NOACCOUNT)
    b, name, q, _ = entries(orders)[0]
    d = 1 if name == "Long" else -1
    f = b + 1  # the fill bar
    bars = bars.copy()
    o = bars.open.iloc[f]
    if d > 0:
        bars.iloc[f, bars.columns.get_loc("high")] = o + 200
        bars.iloc[f, bars.columns.get_loc("low")] = o
    else:
        bars.iloc[f, bars.columns.get_loc("low")] = o - 200
        bars.iloc[f, bars.columns.get_loc("high")] = o
    bars = bars.iloc[:f + 5]  # nothing after it: the run's highest equity is this position's
    trades, _, _, printed = cand(sim, bars, tmp_path, **NOACCOUNT)
    first = trades[0]
    assert int(first[1]) == f and int(first[3]) == f and first[5] == "Profit target", first
    en = float(first[2])
    extreme = o + 200 if d > 0 else o - 200
    bound = d * (extreme - en) * q * 2.0 - 2 * FEE * q
    assert bound > float(first[6]) + 100  # far beyond the realized profit
    audit = next(p for p in printed if "highest equity" in p)
    peak = float(re.search(r"highest equity (-?[\d.]+)", audit).group(1))
    assert peak >= bound - 0.01, (peak, bound)
