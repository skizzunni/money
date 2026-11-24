# ruff: noqa: E501
"""MnqCleanBand.cs (the Clean Noise-Band with the 50K fixes) against its Python reference, research/zoo/strats.py's
noise(nt=True), on the NinjaTrader stand-in: the same trades, entry for entry, at the same prices.

Bars: the repo's MNQ fixture months if the scratch data is absent is not enough history, so the test builds its bars
from tests/fixtures (5-minute regular-hours bars) when present, else skips."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from test_ninjatrader import DOTNET, ENV, sim  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "zoo"))
sys.path.insert(0, str(ROOT / "research"))
import harness as H  # noqa: E402
import strats as S  # noqa: E402

DEFAULTS = dict(vwap=False, trend=20, hard=200.0, vwap_stop=True, k=1.0, be_r=0.4, max_trades=9, last=840, tp_r=2.5,
                range_pos=0.65, max_move=1.1, be_plus=2.0, move_free="first_check")
GAP = dict(k=0.3, exit_m=590, r=0.0, cap=40.0, min_body=0.03)


def fixture_days() -> list:
    data = os.environ.get("ZOO_DATA")
    if data and (Path(data) / "zoo_days.pkl").exists():
        return H.load_sets(data)["live"][0]
    return synthetic_days()


def synthetic_days(n: int = 160, seed: int = 7) -> list:
    """Seeded MNQ-like sessions (78 five-minute bars, a random drift a day so some days trend), on the tick grid."""
    rng = np.random.default_rng(seed)
    days, px = [], 21000.0
    for d in pd.bdate_range("2026-01-05", periods=n):
        drift = rng.normal(0, 0.0012)
        px *= 1 + rng.normal(0, 0.004)
        o, h, lo, c, v = [], [], [], [], []
        last = px
        for _ in range(78):
            op = last
            cl = op * (1 + drift / 78 * 6 * (rng.random() < 0.5) + rng.normal(0, 0.0012))
            hi = max(op, cl) * (1 + abs(rng.normal(0, 0.0005)))
            lw = min(op, cl) * (1 - abs(rng.normal(0, 0.0005)))
            o.append(op), h.append(hi), lo.append(lw), c.append(cl), v.append(float(rng.integers(50, 5000)))
            last = cl
        r = {k: np.round(np.array(x) / 0.25) * 0.25 for k, x in zip(("o", "h", "l", "c"), (o, h, lo, c), strict=True)}
        r["h"] = np.maximum(r["h"], np.maximum(r["o"], r["c"]))
        r["l"] = np.minimum(r["l"], np.minimum(r["o"], r["c"]))
        days.append({"d": d.date(), "mm": np.arange(570, 960, 5), "v": np.array(v), "s": 1.0, **r})
        px = last
    return days


def write_bars(days: list, path: Path) -> list:
    rows, idx = [], []
    for di, d in enumerate(days):
        for k in range(len(d["o"])):
            m = int(d["mm"][k])
            t = pd.Timestamp(d["d"]) + pd.Timedelta(minutes=m)
            rows.append(f"{t:%Y-%m-%d %H:%M}," + ",".join(repr(float(d[x][k])) for x in ("o", "h", "l", "c", "v")))
            idx.append((di, k))
    path.write_text("\n".join(rows) + "\n")
    return idx


def run_nt(sim, path: Path, **props) -> list:  # noqa: F811
    args = [DOTNET, str(sim), str(path), "5", "Strategy=Clean", *[f"{k}={v}" for k, v in props.items()]]
    r = subprocess.run(args, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    return [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]


def py_trades(days: list, idx: list, day_stop: float = 0.0, steps=None, gap_from: float | None = 0.0,
              start: float = 0.0, gap: dict | None = None, **p) -> list:
    """The reference trades as (direction, entry bar, entry, exit, contracts), with the account rules the C# applies:
    contracts by the profit at the day's start, the gap leg (first in the day) once the profit reaches gap_from, the day
    stop across both."""
    pos_of = {v: i for i, v in enumerate(idx)}
    cfg = {**DEFAULTS, **p}
    out, cum = [], start
    for i in range(len(days)):
        q = 1
        if steps:
            for lim, qq in steps:
                if cum >= lim:
                    q = qq
        day = 0.0
        legs = []
        if gap_from is not None and (gap_from <= 0 or cum >= gap_from) and i >= max(21, cfg["trend"] + 1):
            legs += S.gap_go(days, i, 0.25, **(gap or GAP))
        legs += S.noise(days, i, 0.25, stop_slip=1, nt=True, **cfg)
        for side, eb, epx, xpx, _why, *_ in legs:
            if day_stop and day <= -day_stop:
                break
            pnl = ((xpx - epx) * side * 2.0 - 2 * 0.62) * q  # $0.62 a side, as the stand-in books it
            day += pnl
            out.append((side, pos_of[(i, eb)], round(epx, 6), round(xpx, 6), q))
        cum += day
    return out


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("props,py", [
    ({"MaxContracts": 1, "DayStop": 0}, {}),
    ({"MaxContracts": 1, "DayStop": 0, "TrendDays": 0, "BreakEvenAt": 0, "LastEntry": 900}, {"trend": 0, "be_r": 0.0, "last": 900}),
    ({"MaxContracts": 1, "DayStop": 0, "VwapStop": False, "HardStop": 150}, {"vwap_stop": False, "hard": 150.0}),
])
def test_clean_band_matches_python(sim, tmp_path, props, py):  # noqa: F811
    days = fixture_days()
    path = tmp_path / "bars.csv"
    idx = write_bars(days, path)
    nt = run_nt(sim, path, **props)
    ref = py_trades(days, idx, **py)
    assert len(ref) > 20
    got = [(int(t[0]), int(t[1]), round(float(t[2]), 6), round(float(t[4]), 6)) for t in nt]
    want = [(s, b, e, x) for s, b, e, x, _q in ref]
    assert got == want


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_clean_band_defaults_with_account_rules(sim, tmp_path):  # noqa: F811
    """The shipped defaults: the $600 day stop and 1 / 2 / 3 contracts from +$2,000 / +$4,500 (StartProfit puts the
    account part way up so the steps act inside the test window)."""
    days = fixture_days()
    path = tmp_path / "bars.csv"
    idx = write_bars(days, path)
    nt = run_nt(sim, path, StartProfit=1500)
    ref = py_trades(days, idx, day_stop=600.0, steps=((0, 1), (2000, 2), (4500, 3)), start=1500.0)
    got = [(int(t[0]), int(t[1]), round(float(t[2]), 6), round(float(t[4]), 6)) for t in nt]
    qty = [int(x) for x in _qty(sim, path, StartProfit=1500)]
    assert got == [(s, b, e, x) for s, b, e, x, _q in ref]
    assert qty == [q for *_, q in ref]
    assert _qty(sim, path, StartProfit=4500)[0] == "3"  # +$4,500 and up: 3 MNQ (and back down after losses)
    assert _qty(sim, path, StartProfit=2000)[0] == "2"
    assert set(_qty(sim, path, StartProfit=10**5)) == {"3"}  # never more than MaxContracts
    assert _qty(sim, path, StartProfit=0)[0] == "1"  # a fresh account starts at 1
    assert set(_qty(sim, path, StartProfit=10**5, MaxContracts=1)) == {"1"}


def _qty(sim, path, **props):  # noqa: F811
    args = [DOTNET, str(sim), str(path), "5", "Strategy=Clean", *[f"{k}={v}" for k, v in props.items()]]
    r = subprocess.run(args, capture_output=True, text=True, env=ENV)
    return [x.split(",")[2] for x in r.stdout.splitlines() if x.startswith("TN,")]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_clean_band_gap_leg(sim, tmp_path):  # noqa: F811
    """The gap leg (on from the first day here) and the take-profit, trade for trade."""
    days = fixture_days()
    path = tmp_path / "bars.csv"
    idx = write_bars(days, path)
    nt = run_nt(sim, path, MaxContracts=1, DayStop=0)
    ref = py_trades(days, idx)
    got = [(int(t[0]), int(t[1]), round(float(t[2]), 6), round(float(t[4]), 6)) for t in nt]
    assert got == [(s, b, e, x) for s, b, e, x, _q in ref]
    names = {x[5] for x in nt}
    assert sum(idx[int(t[1])][1] == 1 for t in nt) >= 5  # gap entries at 09:35
    assert "Profit target" in names
    # without the 09:30 bar size rule (GapMinBody 0) the gap trades of the reference without it, and more of them
    nt0 = run_nt(sim, path, MaxContracts=1, DayStop=0, GapMinBody=0)
    ref0 = py_trades(days, idx, gap={**GAP, "min_body": 0.0})
    got0 = [(int(t[0]), int(t[1]), round(float(t[2]), 6), round(float(t[4]), 6)) for t in nt0]
    assert got0 == [(s, b, e, x) for s, b, e, x, _q in ref0]
    assert sum(idx[int(t[1])][1] == 1 for t in nt0) > sum(idx[int(t[1])][1] == 1 for t in nt)


def _run_all(sim, path, **props):  # noqa: F811
    args = [DOTNET, str(sim), str(path), "5", "Strategy=Clean", *[f"{k}={v}" for k, v in props.items()]]
    r = subprocess.run(args, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    return r.stdout.splitlines()


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("how", ["SimCancelStopsAt", "RejectStopsAt"])
@pytest.mark.parametrize("live", [False, True])
def test_clean_band_never_without_a_stop(sim, tmp_path, how, live):  # noqa: F811
    """A stop the broker cancels or rejects while the position is open: out at market at that bar's close (filled at
    the next open), in a backtest and live; with every stop update reported and nothing cancelled, never a "No stop"
    (a target's OCO cancel of the stop does not close anything twice)."""
    days = synthetic_days()
    path = tmp_path / "bars.csv"
    write_bars(days, path)
    extra = {"SimRealtimeFrom": 30 * 78} if live else {}
    out = _run_all(sim, path, MaxContracts=1, DayStop=0, SimStopUpdates=True, **extra)
    trades = [x.split(",")[1:] for x in out if x.startswith("T,")]
    assert not any(t[5] == "No stop" for t in trades)
    moves = [int(x.split(",")[1]) for x in out if x.startswith("O,") and ",SetStopLoss," in x]
    pick = None
    for t in trades:
        eb, xb = int(t[1]), int(t[3])
        inside = [b for b in moves if eb <= b < xb - 1 and (not live or b > 30 * 78)]
        if inside:
            pick = (eb, inside[0])
            break
    assert pick, "no stop move inside a trade"
    out2 = _run_all(sim, path, MaxContracts=1, DayStop=0, SimStopUpdates=True, **extra, **{how: pick[1]})
    t2 = [x.split(",")[1:] for x in out2 if x.startswith("T,")]
    hit = [t for t in t2 if int(t[1]) == pick[0]]
    assert hit and hit[0][5] == "No stop" and int(hit[0][3]) == pick[1] + 1
    assert any("closing it at market" in x for x in out2)
    assert [t for t in t2 if int(t[3]) < pick[0]] == [t for t in trades if int(t[3]) < pick[0]]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_clean_band_no_trading_on_a_history_hole(sim, tmp_path):  # noqa: F811
    """Six sessions missing from the chart's history: no entries until the hole is out of the 14-session window."""
    days = synthetic_days()
    holed = days[:60] + days[66:]
    path = tmp_path / "bars.csv"
    idx = write_bars(holed, path)
    out = _run_all(sim, path, MaxContracts=1, DayStop=0)
    entries = {idx[int(x.split(",")[2])][0] for x in out if x.startswith("T,")}
    assert not any(60 <= d < 60 + 12 for d in entries)  # the window that holds the hole
    assert any(d >= 75 for d in entries)  # trading again once it has passed
    assert any("NO TRADING" in x for x in out)
    out_off = _run_all(sim, path, MaxContracts=1, DayStop=0, BlockOnDataGap=False)
    assert any(60 <= idx[int(x.split(",")[2])][0] < 72 for x in out_off if x.startswith("T,"))


def holiday_days() -> list:
    """synthetic_days() with a holiday calendar's worst three weeks (Jan 2025 in 2015-2025 NQ): four weekdays without
    a complete session inside one 14-session window (two Thursdays and Fridays a week apart, as Christmas and New Year
    or Thanksgiving's closed Thursday and half Friday, which the history leaves out)."""
    days = synthetic_days()
    thu = next(i for i, d in enumerate(days) if i >= 50 and pd.Timestamp(d["d"]).dayofweek == 3)
    drop = {thu, thu + 1, thu + 5, thu + 6}
    out = [d for i, d in enumerate(days) if i not in drop]
    dates = [pd.Timestamp(d["d"]) for d in out]
    assert max((dates[i] - dates[i - 14]).days for i in range(14, len(dates))) > 23  # the old guard would have blocked
    return out


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_clean_band_trades_through_holidays(sim, tmp_path):  # noqa: F811
    """Holidays and half days are not a hole: with the guard on (the default) the trades are the guard-free reference's,
    trade for trade, and the log has no NO TRADING (the Mondays after Thanksgiving, Christmas and New Year trade)."""
    days = holiday_days()
    path = tmp_path / "bars.csv"
    idx = write_bars(days, path)
    out = _run_all(sim, path, MaxContracts=1, DayStop=0)
    got = [(int(t[0]), int(t[1]), round(float(t[2]), 6), round(float(t[4]), 6)) for t in
           (x.split(",")[1:] for x in out if x.startswith("T,"))]
    assert got == [(s, b, e, x) for s, b, e, x, _q in py_trades(days, idx)]
    assert not any("NO TRADING" in x for x in out)


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_clean_band_sizes_from_the_account_when_live(sim, tmp_path):  # noqa: F811
    """Enabled mid-session: from the switch to real time the size comes from the account (here $56,000: 3 MNQ), not
    from the replayed history's profit."""
    days = synthetic_days()
    path = tmp_path / "bars.csv"
    idx = write_bars(days, path)
    base = _run_all(sim, path, DayStop=0)
    first = [x.split(",")[1:] for x in base if x.startswith("T,")]
    start = int(first[len(first) // 2][1]) - 3  # a few bars before a mid-history entry
    out = _run_all(sim, path, DayStop=0, SimRealtimeFrom=start, SimNetLiq=56000)
    tn = [x.split(",")[1:] for x in out if x.startswith("TN,")]
    tt = [x.split(",")[1:] for x in out if x.startswith("T,")]
    after = [int(q[1]) for q, t in zip(tn, tt, strict=True) if int(t[1]) > start]
    assert after and set(after) == {3}
    assert any(x.startswith("P,") and "Clean band live: profit over the start balance $6000, 3 MNQ" in x for x in out)
    assert idx  # the bars were written


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("live", [False, True])
def test_clean_band_oco_cancel_does_not_exit_twice(sim, tmp_path, live):  # noqa: F811
    """Targets and market exits whose stop cancel arrives before the position shows flat: the same trades, no "No stop",
    no extra order."""
    days = synthetic_days()
    path = tmp_path / "bars.csv"
    write_bars(days, path)
    extra = {"SimRealtimeFrom": 30 * 78} if live else {}
    plain = _run_all(sim, path, MaxContracts=1, DayStop=0, SimStopUpdates=True, StartProfit=100000, **extra)
    worst = _run_all(sim, path, MaxContracts=1, DayStop=0, SimStopUpdates=True, StartProfit=100000, SimOcoCancelFirst=True, **extra)
    tp = [x for x in plain if x.startswith("T,")]
    tw = [x for x in worst if x.startswith("T,")]
    assert tw == tp
    assert any(",Profit target," in x for x in tw) and any(",Gap exit," in x or ",Session end," in x for x in tw)
    assert [x for x in worst if x.startswith("O,") and "Exit" in x] == [x for x in plain if x.startswith("O,") and "Exit" in x]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_clean_band_dashboard_says_if_it_is_ready(sim, tmp_path):  # noqa: F811
    days = synthetic_days()
    path = tmp_path / "bars.csv"
    write_bars(days, path)
    d = [x for x in _run_all(sim, path) if x.startswith("D,")]
    assert d and "Setup: OK" in d[0] and "MNQ a trade" in d[0]
    short = tmp_path / "short.csv"
    write_bars(days[:12], short)
    d2 = [x for x in _run_all(sim, short) if x.startswith("D,")]
    assert d2 and "NOT READY: 11 complete sessions loaded, needs 21" in d2[0]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_clean_band_fixed_contracts(sim, tmp_path):  # noqa: F811
    """FixedContracts: that many on every trade from the start, whatever the profit (the same trades)."""
    days = synthetic_days()
    path = tmp_path / "bars.csv"
    write_bars(days, path)
    q = _qty(sim, path, FixedContracts=3, DayStop=0)
    assert q and set(q) == {"3"}
    one = [x.split(",")[1:6] for x in _run_all(sim, path, MaxContracts=1, DayStop=0) if x.startswith("T,")]
    three = [x.split(",")[1:6] for x in _run_all(sim, path, FixedContracts=3, DayStop=0) if x.startswith("T,")]
    assert one == three


def write_bars_eth(days: list, path: Path, spikes: list) -> list:
    """The RTH bars plus 08:20-09:25 pre-open bars (flat at the day's open) whose 08:30 volume is `spikes[i]` x the
    08:20 / 08:25 bars' (1,000 each). Returns the RTH bars' (day, bar) by row, None for pre-open rows."""
    rows, idx = [], []
    for di, d in enumerate(days):
        o0 = float(d["o"][0])
        for m in range(500, 570, 5):
            t = pd.Timestamp(d["d"]) + pd.Timedelta(minutes=m)
            v = 1000.0 * spikes[di] if m == 510 else 1000.0
            rows.append(f"{t:%Y-%m-%d %H:%M},{o0!r},{o0!r},{o0!r},{o0!r},{v!r}")
            idx.append(None)
        for k in range(len(d["o"])):
            t = pd.Timestamp(d["d"]) + pd.Timedelta(minutes=int(d["mm"][k]))
            rows.append(f"{t:%Y-%m-%d %H:%M}," + ",".join(repr(float(d[x][k])) for x in ("o", "h", "l", "c", "v")))
            idx.append((di, k))
    path.write_text("\n".join(rows) + "\n")
    return idx


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_clean_band_news_days(sim, tmp_path):  # noqa: F811
    """News days (an ETH chart): a mild-news day (2-3x) has no trades, a big-news day (>= 6x) a contract more (never past
    MaxContracts), the rest as usual; trade for trade against the reference."""
    days = synthetic_days()
    spikes = [(1.0, 2.5, 8.0)[i % 3] for i in range(len(days))]
    path = tmp_path / "bars.csv"
    idx = write_bars_eth(days, path, spikes)
    rth = [x for x in idx if x is not None]
    pos_of = {v: i for i, v in enumerate(idx)}
    out = _run_all(sim, path, DayStop=0, StartProfit=2500)
    tt = [x.split(",")[1:] for x in out if x.startswith("T,")]
    tn = [x.split(",")[1:] for x in out if x.startswith("TN,")]
    ref, cum = [], 2500.0
    for i in range(len(days)):
        q = 2 if cum >= 2000 else 1
        q = 3 if cum >= 4500 else q
        day = 0.0
        if 2 <= spikes[i] < 3:
            continue
        if spikes[i] >= 6:
            q = min(q + 1, 3)
        legs = (S.gap_go(days, i, 0.25, **GAP) if i >= 21 else []) + S.noise(days, i, 0.25, stop_slip=1, nt=True, **DEFAULTS)
        for side, eb, epx, xpx, _w, *_ in legs:
            day += ((xpx - epx) * side * 2.0 - 2 * 0.62) * q
            ref.append((side, pos_of[(i, eb)], round(epx, 6), round(xpx, 6), q))
        cum += day
    got = [(int(t[0]), int(t[1]), round(float(t[2]), 6), round(float(t[4]), 6), int(n[1])) for t, n in zip(tt, tn, strict=True)]
    assert len(ref) > 20 and rth
    assert got == ref
    assert any(q == 3 for *_, q in got)
    d = [x for x in out if x.startswith("D,")]
    assert d and "news 8.0x (+1 contract)" in d[0] or "news 1.0x" in d[0] or "news 2.5x: no trades today" in d[0]
    off = _run_all(sim, path, DayStop=0, StartProfit=2500, NewsDays=False)
    assert len([x for x in off if x.startswith("T,")]) > len(tt)
