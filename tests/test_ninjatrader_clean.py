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

DEFAULTS = dict(vwap=True, trend=20, hard=200.0, vwap_stop=True, k=1.0, be_r=0.4, max_trades=9, last=840)


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


def py_trades(days: list, idx: list, day_stop: float = 0.0, steps=None, **p) -> list:
    """The reference trades as (direction, entry bar, entry, exit, contracts), with the account rules the C# applies."""
    pos_of = {v: i for i, v in enumerate(idx)}
    out, cum = [], 0.0
    for i in range(len(days)):
        q = 1
        if steps:
            for lim, qq in steps:
                if cum >= lim:
                    q = qq
        day = 0.0
        for side, eb, epx, xpx, _why, _xb in S.noise(days, i, 0.25, stop_slip=1, nt=True, **{**DEFAULTS, **p}):
            if day_stop and day <= -day_stop:
                break
            pnl = (xpx - epx) * side * 2.0 * q  # the stand-in books no commission
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
    ref = py_trades(days, idx, day_stop=600.0, steps=((0, 1), (2000 - 1500, 2), (4500 - 1500, 3)))
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


def _run_all(sim, path, **props):  # noqa: F811
    args = [DOTNET, str(sim), str(path), "5", "Strategy=Clean", *[f"{k}={v}" for k, v in props.items()]]
    r = subprocess.run(args, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    return r.stdout.splitlines()


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("how", ["SimCancelStopsAt", "RejectStopsAt"])
def test_clean_band_never_without_a_stop(sim, tmp_path, how):  # noqa: F811
    """A stop the broker cancels or rejects while the position is open: out at market at the next bar's open."""
    days = synthetic_days()
    path = tmp_path / "bars.csv"
    write_bars(days, path)
    out = _run_all(sim, path, MaxContracts=1, DayStop=0)
    trades = [x.split(",")[1:] for x in out if x.startswith("T,")]
    moves = [int(x.split(",")[1]) for x in out if x.startswith("O,") and ",SetStopLoss," in x]
    pick = None
    for t in trades:
        eb, xb = int(t[1]), int(t[3])
        inside = [b for b in moves if eb <= b < xb - 1]
        if inside:
            pick = (eb, inside[0])
            break
    assert pick, "no stop move inside a trade"
    out2 = _run_all(sim, path, MaxContracts=1, DayStop=0, SimStopUpdates=True, **{how: pick[1]})
    t2 = [x.split(",")[1:] for x in out2 if x.startswith("T,")]
    hit = [t for t in t2 if int(t[1]) == pick[0]]
    assert hit and hit[0][5] == "No stop" and int(hit[0][3]) == pick[1] + 1
    assert any("closing it at market" in x for x in out2)


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
