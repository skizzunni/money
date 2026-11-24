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
GAP = dict(k=0.5, exit_m=590, r=0.0, cap=30.0, min_body=0.03)


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


class Guard:
    """The cushion guard as MnqCleanBand.cs applies it at a ready day's start: the floor trails the highest day-start
    balance by `dd` (stopping at the start balance); under `below` $ of cushion, 1 contract and a day stop of `share` x
    the cushion ($100 at least, at most the day stop)."""

    def __init__(self, below: float = 1500.0, share: float = 0.25, dd: float = 2000.0, highest: float = 0.0, base: float = 50000.0,
                 strong_below: float = 1000.0):
        self.below, self.share, self.dd, self.base, self.strong_below = below, share, dd, base, strong_below
        self.hwm = max(base, highest)
        self.strong = False  # the day's "strong breaks only" (under strong_below $ above the floor)

    def day(self, profit: float, cap: int, day_stop: float) -> tuple[int, float]:
        bal = self.base + profit
        self.hwm = max(self.hwm, bal)
        cushion = bal - min(self.hwm - self.dd, self.base)
        self.strong = bool(self.below) and bool(self.strong_below) and cushion < self.strong_below
        if self.below and cushion < self.below:
            return 1, max(100.0, min(day_stop or float("inf"), self.share * cushion))
        return cap, day_stop


def py_trades(days: list, idx: list, day_stop: float = 0.0, steps=None, gap_from: float | None = 0.0,
              start: float = 0.0, gap: dict | None = None, max_q: int | None = None, add_at: float = 1.5,
              guard: Guard | None = None, **p) -> list:
    """The reference trades as (direction, entry bar, entry, exit, contracts), with the account rules the C# applies:
    contracts by the profit at the day's start, the gap leg (first in the day) once the profit reaches gap_from, the day
    stop across both."""
    pos_of = {v: i for i, v in enumerate(idx)}
    cfg = {**DEFAULTS, **p}
    out, cum = [], start
    guard = guard or Guard()
    for i in range(len(days)):
        q = 1
        if steps:
            for lim, qq in steps:
                if cum >= lim:
                    q = qq
        day = 0.0
        legs = []
        cap = max_q if max_q is not None else (3 if steps else 1)  # MaxContracts as the C# run sets it
        ds = day_stop
        guard.strong = False
        if i >= max(21, cfg["trend"] + 1):  # the cushion guard on ready days
            cap, ds = guard.day(cum, cap, day_stop)
            q = min(q, cap)
        if gap_from is not None and (gap_from <= 0 or cum >= gap_from) and i >= max(21, cfg["trend"] + 1):
            legs += S.gap_go(days, i, 0.25, **(gap or GAP))
        ng = len(legs)
        legs += S.noise(days, i, 0.25, stop_slip=1, nt=True, **{**cfg, "min_stretch": 1.5 if guard.strong else 0.0})
        for n_, (side, eb, epx, xpx, _why, *_) in enumerate(legs):
            if ds and day <= -ds:
                break
            qq = q  # a band entry StretchAddAt sigmas past the band: one more contract, at most MaxContracts
            if n_ >= ng and add_at and S.band_stretch(days, i, side, eb, cfg["k"]) >= add_at:
                qq = min(q + 1, cap)
            pnl = ((xpx - epx) * side * 2.0 - 2 * 0.62) * qq  # $0.62 a side, as the stand-in books it
            day += pnl
            out.append((side, pos_of[(i, eb)], round(epx, 6), round(xpx, 6), qq))
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
    """The shipped defaults: the $600 day stop and 1 / 2 / 3 contracts from +$2,000 / +$3,500 (StartProfit puts the
    account part way up so the steps act inside the test window)."""
    days = fixture_days()
    path = tmp_path / "bars.csv"
    idx = write_bars(days, path)
    nt = run_nt(sim, path, StartProfit=1500)
    ref = py_trades(days, idx, day_stop=600.0, steps=((0, 1), (2000, 2), (3500, 3)), start=1500.0)
    got = [(int(t[0]), int(t[1]), round(float(t[2]), 6), round(float(t[4]), 6)) for t in nt]
    qty = [int(x) for x in _qty(sim, path, StartProfit=1500)]
    assert got == [(s, b, e, x) for s, b, e, x, _q in ref]
    assert qty == [q for *_, q in ref]
    assert _qty(sim, path, StartProfit=3500)[0] == "3"  # +$3,500 and up: 3 MNQ (and back down after losses)
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
    assert sum(idx[int(t[1])][1] == 1 for t in nt) >= 5  # gap entries at 09:35
    free = run_nt(sim, path, MaxContracts=1, DayStop=0, CushionGuard=0)  # the target, without the guard's choices
    assert [(int(t[0]), int(t[1]), round(float(t[2]), 6), round(float(t[4]), 6)) for t in free] == \
        [(s, b, e, x) for s, b, e, x, _q in py_trades(days, idx, guard=Guard(below=0))]
    assert "Profit target" in {x[5] for x in free}
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
    plain = _run_all(sim, path, MaxContracts=1, DayStop=0, SimStopUpdates=True, StartProfit=100000, CushionGuard=0, **extra)
    worst = _run_all(sim, path, MaxContracts=1, DayStop=0, SimStopUpdates=True, StartProfit=100000, SimOcoCancelFirst=True,
                     CushionGuard=0, **extra)
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
    q = _qty(sim, path, FixedContracts=3, DayStop=0, CushionGuard=0)
    assert q and set(q) == {"3"}
    guarded = _qty(sim, path, FixedContracts=3, DayStop=0)  # the cushion guard overrides it near the floor
    assert set(guarded) == {"1", "3"}
    one = [x.split(",")[1:6] for x in _run_all(sim, path, MaxContracts=1, DayStop=0, CushionGuard=0) if x.startswith("T,")]
    three = [x.split(",")[1:6] for x in _run_all(sim, path, FixedContracts=3, DayStop=0, CushionGuard=0) if x.startswith("T,")]
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
    ref, cum, guard = [], 2500.0, Guard()
    for i in range(len(days)):
        q = 2 if cum >= 2000 else 1
        q = 3 if cum >= 3500 else q
        day = 0.0
        guard.strong = False
        cap, ds = guard.day(cum, 3, 0.0) if i >= 21 else (3, 0.0)
        q = min(q, cap)
        if 2 <= spikes[i] < 3:
            continue
        if spikes[i] >= 6:
            q = min(q + 1, cap)
        legs = (S.gap_go(days, i, 0.25, **GAP) if i >= 21 else []) + S.noise(days, i, 0.25, stop_slip=1, nt=True, **{**DEFAULTS, "min_stretch": 1.5 if guard.strong else 0.0})
        ng = len(legs) - len([x for x in legs if x[1] > 1])  # the gap leg enters on bar 1, band entries later
        for n_, (side, eb, epx, xpx, _w, *_) in enumerate(legs):
            if ds and day <= -ds:
                break
            qq = min(q + 1, cap) if n_ >= ng and S.band_stretch(days, i, side, eb) >= 1.5 else q
            day += ((xpx - epx) * side * 2.0 - 2 * 0.62) * qq
            ref.append((side, pos_of[(i, eb)], round(epx, 6), round(xpx, 6), qq))
        cum += day
    got = [(int(t[0]), int(t[1]), round(float(t[2]), 6), round(float(t[4]), 6), int(n[1])) for t, n in zip(tt, tn, strict=True)]
    assert len(ref) > 20 and rth
    assert got == ref
    assert any(q == 3 for *_, q in got)
    d = [x for x in out if x.startswith("D,")]
    assert d and "news 8.0x (+1 contract)" in d[0] or "news 1.0x" in d[0] or "news 2.5x: no trades today" in d[0]
    off = _run_all(sim, path, DayStop=0, StartProfit=2500, NewsDays=False)
    assert len([x for x in off if x.startswith("T,")]) > len(tt)


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("props,guard", [
    ({"StartProfit": -1200}, Guard()),                              # $48,800: $800 above a $48,000 floor
    ({"StartProfit": 0, "HighestBalance": 51000}, Guard(highest=51000)),  # the floor at $49,000: $1,000 above it
])
def test_clean_band_cushion_guard(sim, tmp_path, props, guard):  # noqa: F811
    """Near the trailing floor: 1 contract (no strong-break or news contract) and a day stop of a quarter of the
    cushion, trade for trade against the reference; the dashboard says so; off again once the cushion is back."""
    days = fixture_days()
    path = tmp_path / "bars.csv"
    idx = write_bars(days, path)
    out = _run_all(sim, path, DayStop=600, **props)
    tt = [x.split(",")[1:] for x in out if x.startswith("T,")]
    tn = [x.split(",")[1:] for x in out if x.startswith("TN,")]
    got = [(int(t[0]), int(t[1]), round(float(t[2]), 6), round(float(t[4]), 6), int(n[1])) for t, n in zip(tt, tn, strict=True)]
    ref = py_trades(days, idx, day_stop=600.0, steps=((0, 1), (2000, 2), (3500, 3)), start=float(props["StartProfit"]), guard=guard)
    assert len(ref) > 20 and got == ref
    assert got[0][4] == 1  # guarded from the first trade
    off = py_trades(days, idx, day_stop=600.0, steps=((0, 1), (2000, 2), (3500, 3)), start=float(props["StartProfit"]),
                    guard=Guard(below=0))
    assert off != ref  # the guard changed the trades
    d = [x for x in out if x.startswith("D,")]
    assert d



@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_clean_band_guard_live_floor_from_the_account(sim, tmp_path):  # noqa: F811
    """The replay of the history (here +$100,000 of simulated profit) must not set the live floor: at the switch to real
    time the high-water mark starts again from HighestBalance (0: the start balance), so live at $49,600 the floor is
    $48,000 and the cushion $1,600 (no guard); at $48,800 the cushion is $800 (guarded, strong breaks only)."""
    days = synthetic_days()
    path = tmp_path / "bars.csv"
    write_bars(days, path)
    start = len(days) * 78 - 30
    for liq, guarded in ((49600, False), (48800, True)):
        out = _run_all(sim, path, DayStop=0, StartProfit=100000, SimRealtimeFrom=start, SimNetLiq=liq)
        dash = [x for x in out if x.startswith("D,")]
        assert dash and ("CUSHION GUARD" in dash[-1]) == guarded, (liq, dash[-1])
        if guarded:
            assert "$800 above the floor" in dash[-1] and "strong breaks only" in dash[-1]


def half_days(days: list, idx: list, full: list, cut: int = 45, n: int = 4) -> list:
    """Up to n days (from the 25th) with a trade open at the 13:15 cut that closed later the same day."""
    return sorted({idx[int(t[1])][0] for t in full
                   if idx[int(t[1])][1] < cut <= idx[int(t[3])][1] and idx[int(t[3])][0] == idx[int(t[1])][0]
                   and idx[int(t[1])][0] >= 25})[:n]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("mode", ["template", "calendar", "rth", "eth"])
def test_clean_band_half_day_never_holds_overnight(sim, tmp_path, mode):  # noqa: F811
    """Half days (the session ends at 13:15) with a trade still open at 13:10:
      * template: the early close in the trading-hours template (NinjaTrader's lists them): out at the 13:10 open;
      * calendar: not in the template, but the Friday after Thanksgiving (2026-11-27): out at the 13:10 open all the same;
      * rth / eth, neither (an unlisted early close), the backstop: out on the next bar (an ETH chart: the open after the
        first bar past the cut; a regular-hours chart: the 09:35 open, the first fill after the next session's first bar).
    The session-close exit (IsExitOnSessionCloseStrategy) is not modelled by the stand-in: these are the strategy's own
    rules."""
    days = synthetic_days()
    path = tmp_path / "bars.csv"
    idx = write_bars(days, path)
    full = [x.split(",")[1:] for x in _run_all(sim, path, MaxContracts=1, DayStop=0) if x.startswith("T,")]
    cut = 45  # 13:15
    halves = half_days(days, idx, full, cut)
    assert len(halves) >= 2
    if mode == "calendar":  # the same sessions, dated so the first half day is 2026-11-27
        halves = halves[:1]
        start = pd.Timestamp("2026-11-27") - pd.offsets.BDay(halves[0])
        for d, when in zip(days, pd.bdate_range(start, periods=len(days)), strict=True):
            d["d"] = when.date()
        assert days[halves[0]]["d"] == pd.Timestamp("2026-11-27").date()
    for i in halves:
        for k in ("o", "h", "l", "c", "v", "mm"):
            days[i][k] = days[i][k][:cut]
    if mode == "eth":  # the overnight bars after the cut (18:00 - 18:25 the evening of the half day)
        rows, idx = [], []
        for di, d in enumerate(days):
            for k in range(len(d["o"])):
                t = pd.Timestamp(d["d"]) + pd.Timedelta(minutes=int(d["mm"][k]))
                rows.append(f"{t:%Y-%m-%d %H:%M}," + ",".join(repr(float(d[x][k])) for x in ("o", "h", "l", "c", "v")))
                idx.append((di, k))
            if di in halves:
                px = float(d["c"][-1])
                for j in range(6):
                    t = pd.Timestamp(d["d"]) + pd.Timedelta(hours=18, minutes=5 * j)
                    rows.append(f"{t:%Y-%m-%d %H:%M},{px!r},{px!r},{px!r},{px!r},10.0")
                    idx.append((di, 100 + j))
        path.write_text("\n".join(rows) + "\n")
    else:
        idx = write_bars(days, path)
    early = {"SimEarlyClose": ",".join(f"{days[i]['d']:%Y-%m-%d} 13:15" for i in halves)} if mode == "template" else {}
    out = _run_all(sim, path, MaxContracts=1, DayStop=0, **early)
    tt = [x.split(",")[1:] for x in out if x.startswith("T,")]
    assert not [x for x in out if "Exception" in x or "LOG:" in x]
    if mode in ("template", "calendar"):
        for i in halves:
            last = [t for t in tt if idx[int(t[1])][0] == i and not (idx[int(t[3])][0] == i and idx[int(t[3])][1] < cut - 1)]
            assert [(idx[int(t[3])], t[5]) for t in last] == [((i, cut - 1), "Session end")], (i, last)  # the 13:10 open
        assert all(idx[int(t[1])][0] == idx[int(t[3])][0] for t in tt)
        return
    for i in halves:
        held = [t for t in tt if idx[int(t[1])][0] == i and not (idx[int(t[3])][0] == i and idx[int(t[3])][1] < cut)]
        assert len(held) == 1, f"day {i}: {held}"  # the trade open at the cut (any earlier ones closed before it)
        d1, k1 = idx[int(held[0][3])]
        why = held[0][5]
        if mode == "eth":  # out at the next open after the first overnight bar: the half day's evening, not the next session
            assert (d1, k1, why) == (i, 101, "Session end"), (i, d1, k1, why)
        else:  # seen at the next session's first bar's close: out at the 09:35 open (or the stop, gapped through at 09:30)
            assert (d1, k1, why) in ((i + 1, 1, "Session end"), (i + 1, 0, "Stop loss")), (i, d1, k1, why)
    for t in tt:  # no trade anywhere runs past its session's first bar of the next day
        (d0, _k0), (d1, k1) = idx[int(t[1])], idx[int(t[3])]
        assert d1 == d0 or (d1 == d0 + 1 and k1 <= 1 and d0 in halves), (d0, d1, k1)
