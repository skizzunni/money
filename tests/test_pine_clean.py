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
    ({"Most contracts": 1, "Day stop: no new entry once the day is down $ (0 = off)": 0, "Gap trade only from this profit $ (0 = always)": 0,
      "Profit already made at the start $": 100000}, {"start": 100000.0}),
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


@pytest.mark.slow
def test_pine_clean_band_news_days():
    """The news rule in Pine (extended hours): as tests/test_ninjatrader_clean.py's news test, trade for trade."""
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine
    from test_ninjatrader_clean import DEFAULTS, synthetic_days
    days = synthetic_days()
    spikes = [(1.0, 2.5, 8.0)[i % 3] for i in range(len(days))]
    rows, idx = [], []
    for di, d in enumerate(days):
        o0 = float(d["o"][0])
        for m in range(500, 570, 5):
            rows.append((pd.Timestamp(d["d"]) + pd.Timedelta(minutes=m), o0, o0, o0, o0, 1000.0 * (spikes[di] if m == 510 else 1.0)))
            idx.append(None)
        for k in range(len(d["o"])):
            rows.append((pd.Timestamp(d["d"]) + pd.Timedelta(minutes=int(d["mm"][k])), d["o"][k], d["h"][k], d["l"][k], d["c"][k], d["v"][k]))
            idx.append((di, k))
    bars = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "volume"]).set_index("t")
    bars.index = bars.index.tz_localize("America/New_York")
    pos_of = {v: i for i, v in enumerate(idx)}
    rt = PineRuntime(load_pine(PINE), bars, {"Day stop: no new entry once the day is down $ (0 = off)": 0,
                                             "Profit already made at the start $": 2500}, timeframe_seconds=300)
    rt.run(lambda i, g: None)
    got = [(t["dir"], t["entry_bar"], round(t["entry"], 6), round(t["exit"], 6), t["qty"]) for t in rt.strategy.closed]
    ref, cum = [], 2500.0
    for i in range(len(days)):
        q = 3 if cum >= 4500 else 2 if cum >= 2000 else 1
        if 2 <= spikes[i] < 3:
            continue
        if spikes[i] >= 6:
            q = min(q + 1, 3)
        legs = (S.gap_go(days, i, 0.25, **GAP) if i >= 21 else []) + S.noise(days, i, 0.25, stop_slip=1, nt=True, tp_fill_bar=False, **DEFAULTS)
        day = 0.0
        ng = len(legs) - len([x for x in legs if x[1] > 1])  # the gap leg enters on bar 1, band entries later
        for n_, (side, eb, epx, xpx, _w, *_) in enumerate(legs):
            qq = min(q + 1, 3) if n_ >= ng and S.band_stretch(days, i, side, eb) >= 1.5 else q
            day += ((xpx - epx) * side * 2.0 - 2 * 0.62) * qq
            ref.append((side, pos_of[(i, eb)], round(epx, 6), round(xpx, 6), qq))
        cum += day
    assert len(ref) > 20
    assert got == ref


@pytest.mark.slow
def test_pine_clean_band_trades_through_holidays():
    """Holidays are not a hole (the history guard counts weekdays without a session): as the NinjaTrader test, trade
    for trade with the guard-free reference; and six sessions missing still block until they leave the window."""
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine
    from test_ninjatrader_clean import holiday_days, synthetic_days
    days = holiday_days()
    bars, idx = bars_of(days)
    one = {"Most contracts": 1, "Day stop: no new entry once the day is down $ (0 = off)": 0}
    rt = PineRuntime(load_pine(PINE), bars, one, timeframe_seconds=300)
    rt.run(lambda i, g: None)
    got = [(t["dir"], t["entry_bar"], round(t["entry"], 6), round(t["exit"], 6), t["qty"]) for t in rt.strategy.closed]
    assert got == py_trades(days, idx, tp_fill_bar=False)
    full = synthetic_days()
    holed = full[:60] + full[66:]
    bars, idx = bars_of(holed)
    rt = PineRuntime(load_pine(PINE), bars, one, timeframe_seconds=300)
    rt.run(lambda i, g: None)
    entries = {idx[t["entry_bar"]][0] for t in rt.strategy.closed}
    assert not any(60 <= d < 72 for d in entries) and any(d >= 75 for d in entries)
