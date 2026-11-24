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
