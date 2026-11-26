# ruff: noqa: E501
"""MgcOvernightCarry.cs (gold's overnight move carried on, docs/STRATEGY_SEARCH.md 37) against its Python reference,
research/zoo/mk_search.py carry, on the NinjaTrader stand-in: the same trades, entry for entry, at the same prices and
sizes. Seeded synthetic gold sessions (18:00-17:00 New York, 5-minute bars); with ZOO_DATA holding gold5.pkl, also
2009 - Mar 2025 spot gold on MGC's tick grid."""
from __future__ import annotations

import os
import pickle
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from test_ninjatrader import DOTNET, ENV, sim  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "zoo"))
import mk_search as K  # noqa: E402

TICK, PV = 0.1, 10.0


def synthetic_gold(n: int = 120, seed: int = 5) -> list:
    """Seeded gold-like trading days (18:00 the evening before to 17:00, 276 five-minute bars), some with big
    overnight moves that carry on into the morning."""
    rng = np.random.default_rng(seed)
    days, px = [], 4000.0
    for d in pd.bdate_range("2026-03-02", periods=n):
        drift = rng.normal(0, 0.0015) if rng.random() < 0.4 else 0.0
        o, h, lo, c = [], [], [], []
        for k in range(276):
            op = px
            cl = op * (1 + rng.normal(0, 0.0008) + (drift / 120 if k < 230 else 0))
            o.append(op), c.append(cl), h.append(max(op, cl) * (1 + abs(rng.normal(0, 0.0003))))
            lo.append(min(op, cl) * (1 - abs(rng.normal(0, 0.0003))))
            px = cl
        r = {k: np.round(np.array(x), 1) for k, x in zip(("o", "h", "l", "c"), (o, h, lo, c), strict=True)}
        r["h"] = np.maximum(r["h"], np.maximum(r["o"], r["c"]))
        r["l"] = np.minimum(r["l"], np.minimum(r["o"], r["c"]))
        days.append({"d": d.date(), "mm": np.arange(0, 1380, 5), **r})
    return days


def write_gold(days: list, path: Path) -> list:
    """Bars as "yyyy-MM-dd HH:mm,o,h,l,c,v" (the bar's start, New York); minute m of trading day d is 18:00 of the
    day before + m. Returns (day, bar) by row."""
    rows, idx = [], []
    for di, d in enumerate(days):
        base = pd.Timestamp(d["d"]) - pd.Timedelta(hours=6)
        for k in range(len(d["o"])):
            t = base + pd.Timedelta(minutes=int(d["mm"][k]))
            rows.append(f"{t:%Y-%m-%d %H:%M}," + ",".join(repr(round(float(d[x][k]), 1)) for x in ("o", "h", "l", "c")) + ",1.0")
            idx.append((di, k))
    path.write_text("\n".join(rows) + "\n")
    return idx


def run(sim, path: Path, **props) -> list:  # noqa: F811
    args = [DOTNET, str(sim), str(path), "5", "Strategy=Gold", *[f"{k}={v}" for k, v in props.items()]]
    r = subprocess.run(args, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    return r.stdout.splitlines()


def py_trades(days: list, idx: list, steps=None, start: float = 0.0, max_q: int = 1, guard: float = 1500.0,
              highest: float = 0.0) -> list:
    """The reference: carry with the shipped settings, contracts by the profit at the day's start, no trade while the
    balance is under `guard` $ above the floor (the highest day-start balance less $2,000, at most $50,000)."""
    pos_of = {v: i for i, v in enumerate(idx)}
    out, cum, hwm = [], start, max(50000.0, highest)
    for i in range(len(days)):
        bal = 50000.0 + cum
        hwm = max(hwm, bal)
        if guard and bal - min(hwm - 2000.0, 50000.0) < guard:
            continue
        q = 1
        for lim, qq in steps or ():
            if cum >= lim:
                q = qq
        q = min(q, max_q)
        for side, kb, e, x, _why, _xb in K.carry(days, i, TICK):
            cum += ((x - e) * side * PV - 2 * 0.62) * q
            out.append((side, pos_of[(i, kb)], round(e, 6), round(x, 6), q))
    return out


def got_trades(lines: list) -> list:
    tt = [x.split(",")[1:] for x in lines if x.startswith("T,")]
    tn = [x.split(",")[1:] for x in lines if x.startswith("TN,")]
    return [(int(t[0]), int(t[1]), round(float(t[2]), 6), round(float(t[4]), 6), int(n[1])) for t, n in zip(tt, tn, strict=True)]


def gold_days() -> list:
    data = os.environ.get("ZOO_DATA")
    if data and (Path(data) / "gold5.pkl").exists():
        days = pickle.load(open(Path(data) / "gold5.pkl", "rb"))
        for d in days:  # MGC's tick grid, as the bars file prints them (one decimal)
            for k in ("o", "h", "l", "c"):
                d[k] = np.round(np.asarray(d[k]), 1)
            d["h"] = np.maximum(d["h"], np.maximum(d["o"], d["c"]))
            d["l"] = np.minimum(d["l"], np.minimum(d["o"], d["c"]))
        return [d for d in days if len(d["o"]) >= 180]
    return synthetic_gold()


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("props,py", [
    ({"MaxContracts": 1}, {}),
    ({"StartProfit": 1500}, {"steps": ((0, 1), (2000, 2), (3500, 3)), "start": 1500.0, "max_q": 3}),
])
def test_gold_carry_matches_python(sim, tmp_path, props, py):  # noqa: F811
    days = gold_days()
    path = tmp_path / "gold.csv"
    idx = write_gold(days, path)
    lines = run(sim, path, **props)
    got, ref = got_trades(lines), py_trades(days, idx, **py)
    assert len(ref) >= 5
    assert got == ref
    assert not [x for x in lines if "LOG:" in x or "Exception" in x]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_gold_carry_safety(sim, tmp_path):  # noqa: F811
    """Every entry has its stop set first, a tick past 60% of the way from the 08:20 open to the signal close, on the
    right side; every trade is out the same
    trading day by 14:15; one trade a day at most; at most MaxContracts."""
    days = gold_days()
    path = tmp_path / "gold.csv"
    idx = write_gold(days, path)
    lines = run(sim, path, StartProfit=10**5)
    orders = [x.split(",")[1:] for x in lines if x.startswith("O,")]
    stops = {(o[0], o[2]): float(o[3]) for o in orders if o[1] == "SetStopLoss"}
    enters = [o for o in orders if o[1] == "Enter"]
    assert enters
    for o in enters:
        di, k = idx[int(o[0])]
        side = 1 if o[2] == "CarryLong" else -1
        k820 = int(np.searchsorted(days[di]["mm"], 860))
        assert (o[0], o[2]) in stops
        want = np.round((days[di]["o"][k820] + 0.6 * (days[di]["c"][k] - days[di]["o"][k820]) - side * TICK) / TICK) * TICK
        assert abs(stops[(o[0], o[2])] - want) < 1e-6  # 60% of the way from the 08:20 open to the signal close
        assert side * (days[di]["c"][k] + side * TICK - stops[(o[0], o[2])]) > 0
    tt = [x.split(",")[1:] for x in lines if x.startswith("T,")]
    for t in tt:  # out the same trading day by 14:15, or (a gap in the bars / an early close) the first bar after
        (d0, k0), (d1, k1) = idx[int(t[1])], idx[int(t[3])]
        if d1 == d0:
            gap_bars = [m for m in days[d0]["mm"][k0:k1 + 1] if m >= 1210]
            assert days[d1]["mm"][k1] <= 1215 or len(gap_bars) <= 2
        else:
            assert d1 == d0 + 1 and k1 <= 1 and not any(m >= 1210 for m in days[d0]["mm"][k0:])
    assert len({idx[int(t[1])][0] for t in tt}) == len(tt)
    assert max(int(x.split(",")[2]) for x in lines if x.startswith("TN,")) <= 3


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_gold_carry_not_ready_without_history(sim, tmp_path):  # noqa: F811
    days = synthetic_gold(n=12)
    path = tmp_path / "gold.csv"
    write_gold(days, path)
    lines = run(sim, path)
    assert not [x for x in lines if x.startswith("T,")]
    assert any("NOT READY" in x for x in lines if x.startswith("D,"))


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_gold_carry_cushion_guard(sim, tmp_path):  # noqa: F811
    """$800 above the floor ($48,800): no gold trade until the cushion is back to $1,500; trade for trade with the
    reference; with the guard off it trades from the start."""
    days = gold_days()
    path = tmp_path / "gold.csv"
    idx = write_gold(days, path)
    lines = run(sim, path, MaxContracts=1, StartProfit=-1200)
    got, ref = got_trades(lines), py_trades(days, idx, start=-1200.0)
    assert got == ref
    free = got_trades(run(sim, path, MaxContracts=1, StartProfit=-1200, CushionGuard=0))
    assert free == py_trades(days, idx, start=-1200.0, guard=0)
    assert len(free) > len(got)
    assert any("CUSHION GUARD" in x for x in lines if x.startswith("D,")) or not got


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("mode", ["template", "calendar"])
def test_gold_carry_out_before_an_early_close(sim, tmp_path, mode):  # noqa: F811
    """A holiday's early close with a trade open, not held to the next session; the other days' trades unchanged:
      * template: COMEX's 13:45 close in the trading-hours template: out at the 13:40 open, 5 minutes before it;
      * calendar: not in the template, but the Friday after Thanksgiving (2026-11-27): out at the 13:10 open."""
    days = synthetic_gold(n=400)
    path = tmp_path / "gold.csv"
    idx = write_gold(days, path)
    full = [x.split(",")[1:] for x in run(sim, path, MaxContracts=1) if x.startswith("T,")]
    out_at = 1180 if mode == "template" else 1150  # 13:40 / 13:10 New York, minutes from 18:00 the evening before
    halves = [idx[int(t[1])][0] for t in full if days[idx[int(t[3])][0]]["mm"][idx[int(t[3])][1]] >= out_at][:3]
    assert len(halves) >= 2
    if mode == "calendar":  # the same sessions, dated so the first half day is 2026-11-27 (and no other is a half day)
        halves = halves[:1]
        start = pd.Timestamp("2026-11-27") - pd.offsets.BDay(halves[0])
        for d, when in zip(days, pd.bdate_range(start, periods=len(days)), strict=True):
            d["d"] = when.date()
        assert days[halves[0]]["d"] == pd.Timestamp("2026-11-27").date()
        days = days[:halves[0] + 15]  # before Christmas Eve
    rest = [(t[0], idx[int(t[1])], t[2], t[4]) for t in full if idx[int(t[1])][0] not in halves and idx[int(t[1])][0] < len(days)]
    cut = 1185  # 13:45 New York
    for i in halves:
        keep = days[i]["mm"] < cut
        for k in ("o", "h", "l", "c", "mm"):
            days[i][k] = days[i][k][keep]
    idx = write_gold(days, path)
    early = {"SimEarlyClose": ",".join(f"{days[i]['d']:%Y-%m-%d} 13:45" for i in halves)} if mode == "template" else {}
    lines = run(sim, path, MaxContracts=1, **early)
    tt = [x.split(",")[1:] for x in lines if x.startswith("T,")]
    assert not [x for x in lines if "LOG:" in x or "Exception" in x]
    for i in halves:
        mine = [t for t in tt if idx[int(t[1])][0] == i]
        assert len(mine) == 1
        d1, k1 = idx[int(mine[0][3])]
        assert (d1, days[i]["mm"][k1], mine[0][5]) == (i, out_at, "Time exit"), (i, d1, days[d1]["mm"][k1], mine[0][5])
    assert all(idx[int(t[1])][0] == idx[int(t[3])][0] for t in tt)
    assert [(t[0], idx[int(t[1])], t[2], t[4]) for t in tt if idx[int(t[1])][0] not in halves] == rest


def _gtrades(out: list) -> list:
    return [x.split(",")[1:] for x in out if x.startswith("T,")]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_gold_rejected_exit_retries(sim, tmp_path):  # noqa: F811
    """Docs 169-170: a refused 14:15 time exit is sent again on the next bar (it used to be held overnight and closed the
    next day by its stop)."""
    days = synthetic_gold()
    path = tmp_path / "g.csv"
    write_gold(days, path)
    props = dict(MaxContracts=3, StartProfit=5000)
    base = _gtrades(run(sim, path, **props))
    te = next(t for t in base if "Time" in t[5])
    out = run(sim, path, **props, RejectExitsAt=int(te[3]) - 1)
    hit = next(t for t in _gtrades(out) if t[1] == te[1])
    assert hit[5] == "Exit retry" and int(hit[3]) == int(te[3]) + 1
    assert any("was refused" in x for x in out) and any("sending it again" in x for x in out)


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_gold_partial_entry_rest_cancelled(sim, tmp_path):  # noqa: F811
    """Docs 169-170: an entry filling 1 of 3 and never the rest: the rest is cancelled and gold keeps trading (it used to
    trade no more)."""
    days = synthetic_gold()
    path = tmp_path / "g.csv"
    write_gold(days, path)
    props = dict(MaxContracts=3, StartProfit=5000, CushionGuard=0)
    base = _gtrades(run(sim, path, **props))
    pe = int(base[2][1])
    out = run(sim, path, **props, SimPartialEntryAt=pe - 1, SimPartialFirstQty=1, SimPartialDelayBars=-1)
    got = _gtrades(out)
    assert any("cancelling the entry's unfilled rest" in x for x in out)
    x = next(t for t in got if int(t[1]) == pe)
    later_base = [t[:6] for t in base if int(t[1]) > int(x[3])]
    later_got = [t[:6] for t in got if int(t[1]) > int(x[3])]
    assert len(later_got) >= 5 and later_got == later_base


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("minutes,props,want", [
    (5, {"SimInstrument": "MNQ 12-26"}, "WRONG INSTRUMENT: MgcOvernightCarry trades MGC only (this chart is MNQ 12-26)"),
    (5, {"SimInstrument": "GC 02-27"}, "WRONG INSTRUMENT"),
    (1, {}, "WRONG CHART: use a 5-minute MGC chart (this one is 1 Minute)"),
])
def test_gold_wrong_chart_trades_nothing(sim, tmp_path, minutes, props, want):  # noqa: F811
    """Docs 178 (the user's setup had MgcOvernightCarry on MNQ DEC26, 1-minute bars): the gold strategy on anything but
    a 5-minute MGC chart trades nothing, says so once in the Output window and on the chart; the right chart trades."""
    days = synthetic_gold()
    path = tmp_path / "g.csv"
    write_gold(days, path)
    args = [DOTNET, str(sim), str(path), str(minutes), "Strategy=Gold", *[f"{k}={v}" for k, v in props.items()]]
    r = subprocess.run(args, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    out = r.stdout.splitlines()
    assert not [x for x in out if x.startswith("T,")]
    assert sum(want in x for x in out if x.startswith("P,")) == 1
    assert any(want in x for x in out if x.startswith("D,"))
    assert _gtrades(run(sim, path, MaxContracts=3, StartProfit=5000))
