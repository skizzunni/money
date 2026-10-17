"""The NinjaTrader version (ninjatrader/) trades exactly like mnqbot/noise.py.

The C# engine is compiled with the .NET SDK (C# 5, like NinjaTrader 8's compiler) and run on the same bars as the
Python bot; every trade, alert, bracket and heads-up must match. The strategy is compiled against
ninjatrader/tests/Sim/NinjaTraderStubs.cs, a stand-in for the parts of NinjaTrader's API it uses with a simple fill
model, and the trades it places on the stand-in's account must be the bot's trades. Skipped when no dotnet is installed.
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from conftest import synth_bars
from test_noise import above_all_day, above_then_below, above_then_inside, below_all_day, scenario, with_high, with_low

from mnqbot.data import NY
from mnqbot.noise import NoiseConfig, run

ROOT = Path(__file__).resolve().parents[1]
NT = ROOT / "ninjatrader"
DOTNET = shutil.which("dotnet") or ("/opt/dotnet/dotnet" if Path("/opt/dotnet/dotnet").exists() else None)
pytestmark = pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
ENV = {**os.environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"}
# Python setting -> C# NoiseSettings field
FIELDS = {"qty": "Qty", "max_loss_per_trade": "MaxLoss", "take_profit": "TakeProfit", "lock_at": "LockAt",
          "lock_plus": "LockPlus", "max_losers": "MaxLosers", "stop_buffer": "StopBuffer", "lookback": "Lookback",
          "skip_dates": "SkipDates", "fed_dates": "FedDates", "fed_no_shorts": "FedNoShorts"}


def build(project: Path, out: Path) -> None:
    r = subprocess.run([DOTNET, "build", str(project), "-c", "Release", "-o", str(out), "--nologo"],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    out = tmp_path_factory.mktemp("ntharness")
    build(NT / "tests" / "Harness" / "Harness.csproj", out)
    return out / "Harness.dll"


def write_bars(bars: pd.DataFrame, tmp: Path) -> Path:
    idx = bars.index.tz_convert(NY)
    path = tmp / "bars.csv"
    with path.open("w") as f:
        for t, o, h, lo, c in zip(idx, bars.open, bars.high, bars.low, bars.close, strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{float(o)!r},{float(h)!r},{float(lo)!r},{float(c)!r}\n")
    return path


def run_cs(harness, bars: pd.DataFrame, cfg: NoiseConfig, minutes: int = 5, tmp: Path | None = None):
    path = write_bars(bars, tmp)
    args = [f"{FIELDS[k]}={getattr(cfg, k)}" for k in FIELDS]
    r = subprocess.run([DOTNET, str(harness), str(path), str(minutes), *args], capture_output=True, text=True,
                       env=ENV)
    assert r.returncode == 0, r.stderr
    rows = [line.split(",") for line in r.stdout.splitlines()]
    return {k: [row[1:] for row in rows if row[0] == k] for k in "TEOH"}


def same(a: str, b: float) -> bool:
    return (a == "nan" and math.isnan(b)) or math.isclose(float(a), b, rel_tol=1e-12, abs_tol=1e-9)


def assert_same(harness, bars, cfg, tmp_path, minutes=5):
    res = run(bars, cfg, minutes=minutes)
    cs = run_cs(harness, bars, cfg, minutes, tmp_path)
    assert len(cs["T"]) == len(res.trades), (len(cs["T"]), len(res.trades))
    for row, t in zip(cs["T"], res.trades, strict=True):
        d, eb, en, xb, ex, why, pnl = row
        assert (int(d), int(eb), int(xb), why) == (t.direction, t.entry_bar, t.exit_bar, t.reason), (row, t)
        assert same(en, t.entry) and same(ex, t.exit) and same(pnl, t.pnl), (row, t)
    assert [(int(b), a) for b, a in cs["E"]] == res.events
    assert len(cs["O"]) == len(res.orders)
    for row, o in zip(cs["O"], res.orders, strict=True):
        assert (int(row[0]), int(row[1])) == o[:2] and all(same(x, y) for x, y in zip(row[2:], o[2:], strict=True))
    assert [(int(b), int(d)) for b, d in cs["H"]] == res.headsups
    return res


HAND = {"above all day": above_all_day, "above then inside": above_then_inside,
        "above then below": above_then_below, "below all day": below_all_day}


@pytest.mark.parametrize("name", HAND)
def test_hand_built_sessions(harness, tmp_path, name):
    bars, _ = scenario(HAND[name])
    assert assert_same(harness, bars, NoiseConfig(), tmp_path).trades


def test_stop_touch_and_take_profit(harness, tmp_path):
    bars, p = scenario(above_all_day)
    first = 14 * 78
    bars = with_low(bars, first + 8, p * 0.999)  # a dip to the line stop
    bars = with_high(bars, first + 20, p * 1.02)  # through the take-profit
    assert assert_same(harness, bars, NoiseConfig(), tmp_path).trades


SETTINGS = {
    "evaluation 3 MNQ": NoiseConfig(qty=3),
    "funded 10 MNQ": NoiseConfig(qty=10),
    "no max loss": NoiseConfig(qty=10, max_loss_per_trade=0.0),
    "tight max loss": NoiseConfig(qty=1, max_loss_per_trade=100.0),
    "no lock, no limit": NoiseConfig(qty=10, lock_at=0.0, max_losers=0),
    "early lock": NoiseConfig(qty=10, lock_at=0.85),
    "no take-profit": NoiseConfig(qty=3, take_profit=0.0),
    "stop on the line": NoiseConfig(qty=3, stop_buffer=0.0),
    "daily limit 1": NoiseConfig(qty=10, max_losers=1),
}


@pytest.mark.parametrize("name", SETTINGS)
@pytest.mark.parametrize("seed", [3, 5, 9])
def test_random_sessions(harness, tmp_path, name, seed):
    res = assert_same(harness, synth_bars(sessions=90, seed=seed), SETTINGS[name], tmp_path)
    assert len(res.trades) > 10


def test_every_exit_kind_is_covered(harness, tmp_path):
    reasons = set()
    for seed in (3, 5, 9):
        reasons |= {t.reason for t in assert_same(harness, synth_bars(sessions=120, seed=seed), NoiseConfig(qty=10),
                                                  tmp_path).trades}
    assert {"Back inside", "Max loss", "Lock", "Target", "16:00 close"} <= reasons, reasons


def test_fed_and_skip_dates(harness, tmp_path):
    bars = synth_bars(sessions=90, seed=5)
    days = sorted({str(t.date()) for t in bars.index.tz_convert(NY)})[20:]
    cfg = NoiseConfig(qty=3, fed_dates=",".join(days[::3]), skip_dates=",".join(days[1::5]))
    assert assert_same(harness, bars, cfg, tmp_path).trades


def test_one_minute_bars(harness, tmp_path):
    five = synth_bars(sessions=40, seed=7)
    one = five.loc[five.index.repeat(5)].copy()  # flat 1-minute bars inside each 5-minute bar
    one.index = pd.DatetimeIndex([t + pd.Timedelta(minutes=k) for t in five.index for k in range(5)])
    one["open"] = one["close"] = one["high"] = one["low"] = five["close"].repeat(5).to_numpy()
    assert_same(harness, one, NoiseConfig(qty=3), tmp_path, minutes=1)


def gappy(bars: pd.DataFrame, seed: int, share: float = 0.15) -> pd.DataFrame:
    """Opens away from the previous close on a share of the bars (news, the 09:30 open), so the fill differs from
    the expected fill and stops fill at the open."""
    rng = np.random.default_rng(seed)
    out = bars.copy()
    pick = rng.random(len(out)) < share
    gap = np.round(rng.normal(0, 6, len(out)) * 4) / 4
    out.loc[pick, "open"] = out.open[pick] + gap[pick]
    out["high"] = out[["high", "open"]].max(axis=1)
    out["low"] = out[["low", "open"]].min(axis=1)
    return out


@pytest.mark.parametrize("seed", [3, 5])
def test_gaps(harness, tmp_path, seed):
    res = assert_same(harness, gappy(synth_bars(sessions=90, seed=seed), seed), NoiseConfig(qty=10), tmp_path)
    off = [abs(t.entry - o[2]) > 0.3 for t, o in zip(res.trades, res.orders, strict=False)]
    assert any(off), "some fills are away from the expected fill"


def test_take_profit_needs_a_tick_through(harness, tmp_path):
    bars, _ = scenario(above_all_day)
    t = run(bars, NoiseConfig()).trades[0]
    tp = t.entry * (1 + 1.5 * 0.001)  # the quiet history's noise is 0.1%
    bars = with_high(bars, t.entry_bar + 1, tp)  # touches it: no fill
    assert run(bars, NoiseConfig()).trades[0].reason != "Target"
    bars = with_high(bars, t.entry_bar + 2, tp + 0.25)  # a tick through: fills
    assert assert_same(harness, bars, NoiseConfig(), tmp_path).trades[0].reason == "Target"


# ── The strategy (Strategies/MnqNoiseMomentum.cs) placing orders, on the stand-in's fills
@pytest.fixture(scope="module")
def sim(tmp_path_factory):
    out = tmp_path_factory.mktemp("ntsim")
    build(NT / "tests" / "Sim" / "Sim.csproj", out)  # also proves it compiles as C# 5 with no warnings
    return out / "Sim.dll"


def run_sim(sim, bars: pd.DataFrame, tmp: Path, minutes: int = 5, **props):
    path = write_bars(bars, tmp)
    args = [f"{k}={v}" for k, v in props.items()]
    r = subprocess.run([DOTNET, str(sim), str(path), str(minutes), *args], capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-3000:]
    lines = r.stdout.splitlines()
    trades = [row.split(",")[1:] for row in lines if row.startswith("T,")]
    orders = [row.split(",")[1:] for row in lines if row.startswith("O,")]
    dash = next((row[2:] for row in lines if row.startswith("D,")), "")
    printed = [row[2:] for row in lines if row.startswith("P,")]
    return trades, orders, dash, printed


TIME_EXITS = ("16:00 close", "Session ended")
# the strategy's switch: a 50K evaluation trades 4 MNQ, $200 max loss, 3 losers a day; funded 10 MNQ, $350, 4 losers
ACCOUNTS = {False: dict(qty=4, max_loss_per_trade=200.0, max_losers=3), True: dict(qty=10, max_loss_per_trade=350.0,
                                                                                  max_losers=4)}


def account(funded: bool, **kw) -> NoiseConfig:
    return NoiseConfig(**ACCOUNTS[funded], target_on_fill_bar=True, **kw)


def assert_flat_by_16(trades, bars):
    """Every account trade is closed by the 16:00 bar (filled at its open at the latest), on the day it opened."""
    idx = bars.index.tz_convert(NY)
    for row in trades:
        t0, t1 = idx[int(row[1])], idx[int(row[3])]
        assert t1.date() == t0.date() and t1.hour * 60 + t1.minute <= 960, (row, t0, t1)


def assert_strategy_matches(trades, res):
    """The strategy's account trades are the bot's trades. A market exit at 16:00 fills at the next bar's open,
    which in these bars is the 15:55 close the bot uses."""
    assert len(trades) == len(res.trades)
    for row, t in zip(trades, res.trades, strict=True):
        d, eb, en, xb, ex, _, pnl = row
        assert (int(d), int(eb)) == (t.direction, t.entry_bar), (row, t)
        assert int(xb) == t.exit_bar + (t.reason in TIME_EXITS), (row, t)
        assert same(en, t.entry) and same(ex, t.exit) and same(pnl, t.pnl), (row, t)


@pytest.mark.parametrize("funded", [False, True])
@pytest.mark.parametrize("seed", [3, 5, 9])
def test_strategy_places_the_bots_trades(sim, tmp_path, seed, funded):
    bars = synth_bars(sessions=90, seed=seed)
    trades, orders, _, _ = run_sim(sim, bars, tmp_path, Funded=funded, RoundPrices=False)
    res = run(bars, account(funded))
    assert_strategy_matches(trades, res)
    entries = [o for o in orders if o[1] == "Enter"]
    assert len(entries) == len(res.trades) and {o[3] for o in entries} == {str(ACCOUNTS[funded]["qty"])}
    for e in entries:  # the stop goes in before every entry, on the same bar
        before = [o for o in orders if o[0] == e[0] and o[1] == "SetStopLoss" and o[2] == e[2]]
        assert before and orders.index(before[0]) < orders.index(e)


def test_strategy_moves_the_stop_and_locks(sim, tmp_path):
    bars = synth_bars(sessions=120, seed=3)
    trades, orders, _, _ = run_sim(sim, bars, tmp_path, Funded=True, RoundPrices=False)
    res = run(bars, NoiseConfig(qty=10, target_on_fill_bar=True))
    assert_strategy_matches(trades, res)
    reasons = {t.reason for t in res.trades}
    assert {"Back inside", "Max loss", "Lock", "Target", "16:00 close"} <= reasons, reasons


@pytest.mark.parametrize("funded", [False, True])
def test_strategy_on_the_tick_grid(sim, tmp_path, funded):
    bars = synth_bars(sessions=120, seed=5)
    qty = ACCOUNTS[funded]["qty"]
    trades, orders, _, _ = run_sim(sim, bars, tmp_path, Funded=funded)
    res = run(bars, account(funded))
    cap = ACCOUNTS[funded]["max_loss_per_trade"]
    prices = [float(o[3]) for o in orders if o[1] in ("SetStopLoss", "SetProfitTarget") and o[4] == "Price"]
    ticks = [float(o[3]) for o in orders if o[1] in ("SetStopLoss", "SetProfitTarget") and o[4] == "Ticks"]
    assert prices and all(abs(p * 4 - round(p * 4)) < 1e-9 for p in prices), "every order on the 0.25 tick"
    assert ticks and all(t == int(t) and t >= 1 for t in ticks), "brackets in whole ticks"
    stops = [float(o[3]) for o in orders if o[1] == "SetStopLoss" and o[4] == "Ticks"]
    assert max(stops) * 0.25 * qty * 2 <= cap + 1e-9, "the first stop never risks more than the max loss"
    by_bar = {o[0]: o for o in res.orders}
    for o in orders:  # the first take-profit is never closer than the tested one
        if o[1] == "SetProfitTarget" and o[4] == "Ticks" and int(o[0]) in by_bar:
            _, d, est, _, tp = by_bar[int(o[0])]
            assert float(o[3]) * 0.25 >= d * (tp - est) - 1e-9, o
    assert [(int(r[0]), int(r[1])) for r in trades][:20] == [(t.direction, t.entry_bar) for t in res.trades][:20]
    worst = cap + 2 * 0.62 * qty + 0.25 * 2 * qty  # the max loss, fees and a tick of slippage on the stop
    assert min(float(r[6]) for r in trades) >= -worst - 1e-6, "a stop rounded toward the price: never past $350"
    assert_flat_by_16(trades, bars)
    total, bot = sum(float(r[6]) for r in trades), sum(t.pnl for t in res.trades)
    assert abs(total - bot) < 0.02 * sum(abs(t.pnl) for t in res.trades)


@pytest.mark.parametrize("seed", [3, 9])
def test_strategy_on_gaps(sim, tmp_path, seed):
    """Fills away from the expected price: the bracket is set in ticks from the fill, so it is always on the right
    side of it, and no trade loses more than the max loss beyond what the gap itself costs (the stand-in also fails on
    a stop set at or past the price, which a broker would reject)."""
    bars = gappy(synth_bars(sessions=90, seed=seed), seed, share=0.3)
    trades, orders, _, _ = run_sim(sim, bars, tmp_path, Funded=True)
    assert len(trades) > 10
    assert_flat_by_16(trades, bars)
    for d, eb, en, xb, ex, why, pnl in trades:
        if eb == xb and why == "Profit target":
            assert int(d) * (float(ex) - float(en)) > 0, "a take-profit on the fill bar is always a profit"
        if why == "Stop loss" and eb == xb:
            assert float(pnl) >= -(350 + 12.4 + 5) - 1e-6, "the fill-bar stop is measured from the real fill"


def test_strategy_on_one_minute_bars(sim, tmp_path):
    five = synth_bars(sessions=40, seed=7)
    one = five.loc[five.index.repeat(5)].copy()
    one.index = pd.DatetimeIndex([t + pd.Timedelta(minutes=k) for t in five.index for k in range(5)])
    closes = five["close"].repeat(5).to_numpy()
    one["close"] = closes
    one["open"] = np.concatenate([[closes[0]], closes[:-1]])  # each bar opens at the last close
    one["high"] = one[["open", "close"]].max(axis=1)
    one["low"] = one[["open", "close"]].min(axis=1)
    trades, _, _, _ = run_sim(sim, one, tmp_path, minutes=1, RoundPrices=False)
    assert_strategy_matches(trades, run(one, account(False), minutes=1))


def test_alerts_only_places_no_orders(sim, tmp_path):
    bars = synth_bars(sessions=60, seed=3)
    trades, orders, dash, printed = run_sim(sim, bars, tmp_path, PlaceOrders=False)
    assert not trades and not [o for o in orders if o[1] in ("Enter", "Exit")]
    n = len(run(bars, NoiseConfig(**ACCOUNTS[False])).orders)
    assert n and sum("BUY 4 MNQ" in p or "SELL 4 MNQ" in p for p in printed) == n
    assert "Orders: OFF" in dash


def test_dashboard_and_switch(sim, tmp_path):
    bars = synth_bars(sessions=30, seed=3)
    _, _, dash, printed = run_sim(sim, bars, tmp_path)
    assert "Evaluation, 4 MNQ, $200 max loss, 3 losers a day" in dash and "Orders: ON" in dash
    assert any("BUY 4 MNQ (Evaluation)" in p or "SELL 4 MNQ (Evaluation)" in p for p in printed)
    _, _, dash, printed = run_sim(sim, bars, tmp_path, Funded=True)
    assert "Funded, 10 MNQ, $350 max loss, 4 losers a day" in dash
    assert any("BUY 10 MNQ (Funded)" in p or "SELL 10 MNQ (Funded)" in p for p in printed)
    _, orders, dash, _ = run_sim(sim, synth_bars(sessions=8, seed=3), tmp_path)
    assert "History: 8/14" in dash and not orders  # not enough sessions loaded: it says so, and trades nothing
    _, _, _, printed = run_sim(sim, synth_bars(sessions=20, seed=3), tmp_path)
    daily = [p for p in printed if "MNQ Noise Momentum (Evaluation, 4 MNQ, orders ON)" in p]
    assert len(daily) == 20  # the Output window says every morning whether it can trade
    assert "loading history, 7/14 full sessions" in daily[7] and "ready, trading today" in daily[15]


def test_a_rejected_stop_closes_the_position(sim, tmp_path):
    """The broker rejects a stop change: the position is closed at market at once (here the next bar's open), and
    again in a later trade (the guard against closing twice resets when flat)."""
    bars = synth_bars(sessions=60, seed=3)
    trades, _, _, _ = run_sim(sim, bars, tmp_path, RoundPrices=False)
    long_ones = [t for t in trades if int(t[3]) - int(t[1]) >= 4]
    bars_at = [int(long_ones[0][1]) + 2, int(long_ones[3][1]) + 2]
    got, _, _, printed = run_sim(sim, bars, tmp_path, RoundPrices=False, RejectStopsAt=",".join(map(str, bars_at)))
    closed = {int(t[3]): t[5] for t in got}
    for b in bars_at:
        assert closed.get(b + 1) == "Close: rejected", (b, closed)
    assert sum("ORDER REJECTED" in p for p in printed) == 4
    assert sum("closed at market so it is never left without a stop" in p for p in printed) == 2
