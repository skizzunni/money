# ruff: noqa: E501
"""pine/mnq_clean_band.pine against the same Python reference as MnqCleanBand.cs (research/zoo/strats.py, noise with
nt=True, the gap leg, the account rules), trade for trade, on the Pine interpreter (tests/pine_interpreter.py).
The one difference by design: Pine sets the take-profit from the fill price after the fill bar, so it works from the
next bar (NinjaTrader's bracket works from the fill bar)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from test_ninjatrader_clean import GAP, S, fixture_days, py_trades

ROOT = Path(__file__).resolve().parents[1]
PINE = ROOT / "pine" / "mnq_clean_band.pine"


def bars_of(days: list) -> tuple[pd.DataFrame, list]:
    rows, idx = [], []
    for di, d in enumerate(days):
        for k in range(len(d["o"])):
            t = pd.Timestamp(d["d"]) + pd.Timedelta(minutes=int(d["mm"][k]))
            rows.append((t, d["o"][k], d["h"][k], d["l"][k], d["c"][k], d["v"][k]))
            idx.append((di, k))
    b = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "volume"]).set_index("t")
    b.index = b.index.tz_localize("America/New_York")
    return b, idx


@pytest.mark.slow
@pytest.mark.parametrize("inputs,kw", [
    ({"Most contracts": 1, "Day stop: no new entry once the day is down $ (0 = off)": 0}, {}),
    ({}, {"day_stop": 600.0, "steps": ((0, 1), (2000, 2), (4500, 3))}),
    ({"Most contracts": 1, "Day stop: no new entry once the day is down $ (0 = off)": 0, "Gap trade only from this profit $": 0,
      "Profit already made at the start $": 100000}, {"gap_from": 0.0, "start": 100000.0}),
])
def test_pine_clean_band_matches_python(inputs, kw):
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine
    days = fixture_days()
    bars, idx = bars_of(days)
    rt = PineRuntime(load_pine(PINE), bars, inputs, timeframe_seconds=300)
    rt.run(lambda i, g: None)
    got = [(t["dir"], t["entry_bar"], round(t["entry"], 6), round(t["exit"], 6), t["qty"]) for t in rt.strategy.closed]
    want = py_trades(days, idx, tp_fill_bar=False, **kw)
    assert len(want) > 20
    assert got == want
    assert GAP and S
