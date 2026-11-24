# ruff: noqa: E501
"""pine/mgc_overnight_carry.pine against the same Python reference as MgcOvernightCarry.cs (research/zoo/mk_search.py
carry), trade for trade, on the Pine interpreter (tests/pine_interpreter.py): seeded synthetic gold sessions, and with
ZOO_DATA holding gold5.pkl the last 500 sessions of spot gold (to Mar 2025)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from test_ninjatrader_gold import gold_days, py_trades, synthetic_gold

ROOT = Path(__file__).resolve().parents[1]
PINE = ROOT / "pine" / "mgc_overnight_carry.pine"


def bars_of(days: list) -> tuple[pd.DataFrame, list]:
    rows, idx = [], []
    for di, d in enumerate(days):
        base = pd.Timestamp(d["d"]) - pd.Timedelta(hours=6)
        for k in range(len(d["o"])):
            rows.append((base + pd.Timedelta(minutes=int(d["mm"][k])), d["o"][k], d["h"][k], d["l"][k], d["c"][k], 1.0))
            idx.append((di, k))
    b = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "volume"]).set_index("t")
    b.index = b.index.tz_localize("America/New_York", ambiguous="infer")
    return b, idx


def run(days, inputs):
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine
    bars, idx = bars_of(days)
    rt = PineRuntime(load_pine(PINE), bars, inputs, mintick=0.1, pointvalue=10.0, timeframe_seconds=300)  # MGC
    rt.run(lambda i, g: None)
    return [(t["dir"], t["entry_bar"], round(t["entry"], 6), round(t["exit"], 6), t["qty"]) for t in rt.strategy.closed], idx


@pytest.mark.slow
@pytest.mark.parametrize("inputs,kw", [
    ({"Most contracts": 1}, {}),
    ({"Profit already made at the start $": 1500}, {"steps": ((0, 1), (2000, 2), (3500, 3)), "start": 1500.0, "max_q": 3}),
])
def test_pine_gold_carry_matches_python(inputs, kw):
    days = synthetic_gold()
    got, idx = run(days, inputs)
    want = py_trades(days, idx, **kw)
    assert len(want) >= 5
    assert got == want


@pytest.mark.slow
def test_pine_gold_carry_on_real_gold():
    days = gold_days()
    if len(days) < 1000:
        pytest.skip("needs ZOO_DATA with gold5.pkl")
    days = days[-500:]
    got, idx = run(days, {"Most contracts": 1})
    want = py_trades(days, idx)
    assert len(want) >= 10
    assert got == want


@pytest.mark.slow
def test_pine_gold_carry_cushion_guard():
    days = synthetic_gold()
    got, idx = run(days, {"Most contracts": 1, "Profit already made at the start $": -1200})
    assert got == py_trades(days, idx, start=-1200.0)
    free, _ = run(days, {"Most contracts": 1, "Profit already made at the start $": -1200,
                         "Cushion guard: no trade below this $ above the floor (0 = off)": 0})
    assert free == py_trades(days, idx, start=-1200.0, guard=0) and len(free) > len(got)


@pytest.mark.slow
def test_pine_gold_carry_out_by_13_10_on_a_half_day():
    """As the NinjaTrader test's calendar case: a trade open at 13:10 the Friday after Thanksgiving (2026-11-27) goes
    out at the 13:10 open; the session cut at 13:45 (COMEX's early close)."""
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine
    days = synthetic_gold(n=400)
    bars, idx = bars_of(days)
    one = {"Most contracts": 1}
    rt = PineRuntime(load_pine(PINE), bars, one, mintick=0.1, pointvalue=10.0, timeframe_seconds=300)
    rt.run(lambda i, g: None)
    late = [idx[t["entry_bar"]][0] for t in rt.strategy.closed if days[idx[t["exit_bar"]][0]]["mm"][idx[t["exit_bar"]][1]] >= 1150]
    assert late
    i = late[0]
    start = pd.Timestamp("2026-11-27") - pd.offsets.BDay(i)
    for d, when in zip(days, pd.bdate_range(start, periods=len(days)), strict=True):
        d["d"] = when.date()
    days = days[:i + 15]  # before Christmas Eve
    keep = days[i]["mm"] < 1185  # 13:45
    for k in ("o", "h", "l", "c", "mm"):
        days[i][k] = days[i][k][keep]
    bars, idx = bars_of(days)
    rt = PineRuntime(load_pine(PINE), bars, one, mintick=0.1, pointvalue=10.0, timeframe_seconds=300)
    rt.run(lambda i_, g: None)
    mine = [t for t in rt.strategy.closed if idx[t["entry_bar"]][0] == i]
    assert len(mine) == 1
    d1, k1 = idx[mine[0]["exit_bar"]]
    assert (d1, days[d1]["mm"][k1], mine[0]["reason"]) == (i, 1150, "Time exit")
    assert all(idx[t["entry_bar"]][0] == idx[t["exit_bar"]][0] for t in rt.strategy.closed)
