# ruff: noqa: E501
"""pine/mnq_clean_band.pine against the same Python reference as MnqCleanBand.cs (research/zoo/strats.py, noise with
nt=True, the gap leg, the account rules), trade for trade, on the Pine interpreter (tests/pine_interpreter.py).
The one difference by design: Pine sets the take-profit from the fill price after the fill bar, so it works from the
next bar (NinjaTrader's bracket works from the fill bar)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from test_ninjatrader_clean import GAP, Guard, S, fixture_days, py_trades

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
    ({"Most contracts": 1, "Day stop: no new entry once the day is down $ (0 = off)": 0,
      "Second stop step once up this many hard stops (0 = off)": 0,
      "Gap: no trade when the 09:30 bar's range is over this x its 14-session average (0 = off)": 0},
     {"lad_r": 0.0, "gap": {**GAP, "max_bar": 0.0}}),
    ({}, {"day_stop": 600.0, "steps": ((0, 1), (2000, 2), (3500, 3))}),
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
def test_pine_clean_band_missing_check_bar():
    """Docs 162: a day without the bar ending 10:00; Pine matches the reference with "Sigma needs at least" 10 and 14
    (the shipped 10 keeps the 10:00 check on over the next 14 sessions), and the two differ."""
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine
    from test_ninjatrader_clean import drop_bar, synthetic_days
    days = drop_bar(synthetic_days(), 60, 595)
    bars, idx = bars_of(days)
    res = {}
    for n, sm in ((10, 10), (14, 0)):
        inputs = {"Most contracts": 1, "Day stop: no new entry once the day is down $ (0 = off)": 0,
                  "Sigma needs at least this many of the 14 sessions (14 = all, as before)": n}
        rt = PineRuntime(load_pine(PINE), bars, inputs, timeframe_seconds=300)
        rt.run(lambda i, g: None)
        got = [(t["dir"], t["entry_bar"], round(t["entry"], 6), round(t["exit"], 6), t["qty"]) for t in rt.strategy.closed]
        assert got == py_trades(days, idx, tp_fill_bar=False, sig_min=sm), n
        res[n] = got
    assert res[10] != res[14]


@pytest.mark.slow
def test_pine_clean_band_missing_open_bar():
    """Docs 164: a day without its 09:30 bar trades nothing and stays out of the history; Pine matches the reference
    run on the days with that day removed."""
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine
    from test_ninjatrader_clean import drop_bar, synthetic_days, without_day
    full = drop_bar(synthetic_days(), 60, 570)
    bars, idx = bars_of(full)
    inputs = {"Most contracts": 1, "Day stop: no new entry once the day is down $ (0 = off)": 0}
    rt = PineRuntime(load_pine(PINE), bars, inputs, timeframe_seconds=300)
    rt.run(lambda i, g: None)
    got = [(t["dir"], t["entry_bar"], round(t["entry"], 6), round(t["exit"], 6), t["qty"]) for t in rt.strategy.closed]
    want = py_trades(full[:60] + full[61:], without_day(idx, 60), tp_fill_bar=False)
    assert len(want) > 20
    assert got == want


@pytest.mark.slow
def test_pine_clean_band_dashboard():
    """Docs 172: the chart's status table, as MnqCleanBand.cs's dashboard: OK, and the news rule "n/a - turn on extended
    hours" on a regular-hours chart; "NO TRADING TODAY: no 09:30 bar" when the last day lacks its 09:30 bar."""
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine
    from test_ninjatrader_clean import drop_bar, synthetic_days
    for days, want in ((synthetic_days(), "Setup: OK"), (drop_bar(synthetic_days(), 159, 570), "NO TRADING TODAY: no 09:30 bar")):
        bars, _idx = bars_of(days)
        rt = PineRuntime(load_pine(PINE), bars, {}, timeframe_seconds=300)
        rt.run(lambda i, g: None)
        text = rt.tables[0].cells[(0, 0)]
        assert want in text and "turn on extended hours" in text


@pytest.mark.slow
def test_pine_clean_band_band_lines():
    """Docs 174: the plotted bands are level lines: nothing before the session's first check (10:00), each check's band
    (the formula on the check bar) held until the next check, never carried into the next session (display only)."""
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    import math

    from pine_interpreter import PineRuntime, load_pine
    days = fixture_days()
    bars, idx = bars_of(days)
    rt = PineRuntime(load_pine(PINE), bars, {}, timeframe_seconds=300)
    seen, held = [], 0

    def on_bar(i, g):
        seen.append((g["upBand"], g["loBand"], g["isCheck"]))
    rt.run(on_bar)
    for i, (up, lo, chk) in enumerate(seen):
        di, k = idx[i]
        mm = days[di]["mm"][k]
        if mm + 5 < 600:   # before the first check: no line (so the line breaks between sessions)
            assert up is None or math.isnan(up), (days[di]["d"], mm)
            continue
        if not chk and i > 0 and idx[i - 1][0] == di:
            assert (up, lo) == seen[i - 1][:2] or (math.isnan(up) and math.isnan(seen[i - 1][0]))
            held += up == up
        if up == up:
            assert up > lo
    assert held > 1000
    assert sum(1 for up, _lo, chk in seen if chk and up == up) > 100


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
    guard = Guard()
    for i in range(len(days)):
        q = 3 if cum >= 3500 else 2 if cum >= 2000 else 1
        guard.strong = False
        cap, ds = guard.day(cum, 3, 0.0) if i >= 21 else (3, 0.0)
        q = min(q, cap)
        if 2 <= spikes[i] < 3:
            continue
        if spikes[i] >= 6:
            q = min(q + 1, cap)
        legs = (S.gap_go(days, i, 0.25, **GAP) if i >= 21 else []) + S.noise(days, i, 0.25, stop_slip=1, nt=True, tp_fill_bar=False, **{**DEFAULTS, "min_stretch": 1.5 if guard.strong else 0.0})
        day = 0.0
        ng = len(legs) - len([x for x in legs if x[1] > 1])  # the gap leg enters on bar 1, band entries later
        for n_, (side, eb, epx, xpx, _w, *_) in enumerate(legs):
            if ds and day <= -ds:
                break
            qq = min(q + 1, cap) if n_ >= ng and S.band_stretch(days, i, side, eb, 1.0, DEFAULTS["sig_min"]) >= 1.5 else q
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


@pytest.mark.slow
def test_pine_clean_band_cushion_guard():
    """$800 above the floor ($48,800): the cushion guard as MnqCleanBand.cs applies it, trade for trade."""
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine
    days = fixture_days()
    bars, idx = bars_of(days)
    rt = PineRuntime(load_pine(PINE), bars, {"Profit already made at the start $": -1200}, timeframe_seconds=300)
    rt.run(lambda i, g: None)
    got = [(t["dir"], t["entry_bar"], round(t["entry"], 6), round(t["exit"], 6), t["qty"]) for t in rt.strategy.closed]
    want = py_trades(days, idx, tp_fill_bar=False, day_stop=600.0, steps=((0, 1), (2000, 2), (3500, 3)), start=-1200.0)
    assert len(want) > 20 and got == want and got[0][4] == 1
    assert GAP and S


@pytest.mark.slow
@pytest.mark.parametrize("eth,calendar", [(False, True), (False, False), (True, False)])
def test_pine_clean_band_half_day_never_holds_overnight(eth, calendar):
    """As the NinjaTrader test: the Friday after Thanksgiving (calendar): out at the 13:10 open; sessions cut at 13:15 on
    other dates with a trade open go out on the next bar (an ETH chart: the open after the first bar past the cut; a
    regular-hours chart: the 09:35 open), never into the next session's trading."""
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine
    from test_ninjatrader_clean import synthetic_days
    one = {"Most contracts": 1, "Day stop: no new entry once the day is down $ (0 = off)": 0}
    days = synthetic_days()
    bars, idx = bars_of(days)
    rt = PineRuntime(load_pine(PINE), bars, one, timeframe_seconds=300)
    rt.run(lambda i, g: None)
    cut = 45
    halves = sorted({idx[t["entry_bar"]][0] for t in rt.strategy.closed if idx[t["entry_bar"]][1] < cut <= idx[t["exit_bar"]][1]
                     and idx[t["exit_bar"]][0] == idx[t["entry_bar"]][0] and idx[t["entry_bar"]][0] >= 25})[:4]
    assert len(halves) >= 2
    if calendar:  # the same sessions, dated so the first half day is 2026-11-27
        halves = halves[:1]
        start = pd.Timestamp("2026-11-27") - pd.offsets.BDay(halves[0])
        for d, when in zip(days, pd.bdate_range(start, periods=len(days)), strict=True):
            d["d"] = when.date()
    for i in halves:
        for k in ("o", "h", "l", "c", "v", "mm"):
            days[i][k] = days[i][k][:cut]
    bars, idx = bars_of(days)
    if eth:  # the half day's evening bars (18:00 - 18:25), flat at its last close
        extra = []
        for i in halves:
            px = float(days[i]["c"][-1])
            for j in range(6):
                t = pd.Timestamp(days[i]["d"]) + pd.Timedelta(hours=18, minutes=5 * j)
                extra.append((t.tz_localize("America/New_York"), px, px, px, px, 10.0, (i, 100 + j)))
        add = pd.DataFrame([e[:6] for e in extra], columns=["t", "open", "high", "low", "close", "volume"]).set_index("t")
        both = pd.concat([bars.assign(k=range(len(bars))), add.assign(k=range(len(bars), len(bars) + len(add)))]).sort_index()
        idx = [(idx + [e[6] for e in extra])[k] for k in both["k"]]
        bars = both.drop(columns="k")
    rt = PineRuntime(load_pine(PINE), bars, one, timeframe_seconds=300)
    rt.run(lambda i, g: None)
    if calendar:
        i = halves[0]
        last = [t for t in rt.strategy.closed if idx[t["entry_bar"]][0] == i
                and not (idx[t["exit_bar"]][0] == i and idx[t["exit_bar"]][1] < cut - 1)]
        assert [(idx[t["exit_bar"]], t["reason"]) for t in last] == [((i, cut - 1), "Session end")], last
        assert all(idx[t["entry_bar"]][0] == idx[t["exit_bar"]][0] for t in rt.strategy.closed)
        return
    for i in halves:
        held = [t for t in rt.strategy.closed if idx[t["entry_bar"]][0] == i
                and not (idx[t["exit_bar"]][0] == i and idx[t["exit_bar"]][1] < cut)]
        assert len(held) == 1, (i, held)
        d1, k1 = idx[held[0]["exit_bar"]]
        if eth:
            assert (d1, k1) == (i, 101), (i, d1, k1)
        else:
            assert (d1, k1) in ((i + 1, 1), (i + 1, 0)), (i, d1, k1)  # out at 09:35 (or the stop, gapped through at 09:30)
    for t in rt.strategy.closed:
        (d0, _), (d1, k1) = idx[t["entry_bar"]], idx[t["exit_bar"]]
        assert d1 == d0 or (d1 == d0 + 1 and k1 <= 1 and d0 in halves), (d0, d1, k1)


@pytest.mark.slow
def test_pine_clean_band_fomc_days():
    """Docs 180: no trades on an FOMC statement day, as MnqCleanBand.cs and the reference; the default list is
    research/fomc_dates.csv; three traded days of the fixture as the FOMC days."""
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    import csv

    from pine_interpreter import PineRuntime, load_pine
    days = fixture_days()
    bars, idx = bars_of(days)
    base = {"Most contracts": 1, "Day stop: no new entry once the day is down $ (0 = off)": 0}

    def run(extra):
        rt = PineRuntime(load_pine(PINE), bars, {**base, **extra}, timeframe_seconds=300)
        rt.run(lambda i, g: None)
        return [(t["dir"], t["entry_bar"], round(t["entry"], 6), round(t["exit"], 6), t["qty"]) for t in rt.strategy.closed]
    off = run({"FOMC days (the 14:00 Fed statement): no trades": False})
    assert off == py_trades(days, idx, tp_fill_bar=False, fomc=False)
    traded = sorted({idx[t[1]][0] for t in off})
    pick = {days[i]["d"] for i in traded[25:28]}
    got = run({"FOMC statement days (yyyy-MM-dd, comma-separated)": ",".join(sorted(str(x) for x in pick))})
    assert got == py_trades(days, idx, tp_fill_bar=False, fomc_days=pick) and len(got) < len(off)
    with open(ROOT / "research" / "fomc_dates.csv") as f:
        want = ",".join(r["date"] for r in csv.DictReader(f))
    assert f'fomcDates = input.string("{want}",' in PINE.read_text()
