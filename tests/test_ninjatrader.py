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
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from conftest import synth_bars
from test_noise import above_all_day, above_then_below, above_then_inside, below_all_day, scenario, with_high, with_low

from mnqbot.data import NY
from mnqbot.noise import NoiseConfig, run

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import combo_live  # noqa: E402
import combo_priority  # noqa: E402

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


def run_sim(sim, bars: pd.DataFrame, tmp: Path, minutes: int = 5, breakout: bool | None = False, **props):
    """The strategy on the stand-in. breakout: the breakout setup on or off (None: the strategy's default); off by
    default here, so the bot's own trades can be compared with the Python bot's."""
    if breakout is not None:
        props["UseBreakout"] = breakout
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
# the switch: a 50K evaluation trades 4 MNQ, $200, 3 losers a day; funded 4 MNQ, $200, 2 losers, the lock at 0.5 / +6.25
ACCOUNTS = {False: dict(qty=4, max_loss_per_trade=200.0, max_losers=3, tighten_only=True),
            True: dict(qty=4, max_loss_per_trade=200.0, max_losers=2, lock_at=0.5, lock_plus=6.25, tighten_only=True)}


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
    res = run(bars, account(True))
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
            a = ACCOUNTS[True]
            worst = a["max_loss_per_trade"] + (2 * 0.62 + 2 * 0.25) * a["qty"]  # fees and a tick of slippage
            assert float(pnl) >= -worst - 1e-6, "the fill-bar stop is measured from the real fill"


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
    assert "Funded, 4 MNQ, $200 max loss, 2 losers a day" in dash
    assert any("BUY 4 MNQ (Funded)" in p or "SELL 4 MNQ (Funded)" in p for p in printed)
    _, orders, dash, _ = run_sim(sim, synth_bars(sessions=8, seed=3), tmp_path, breakout=None)
    assert "History: 8/14" in dash and not orders  # not enough sessions loaded: it says so, and trades nothing
    assert "Breakout: " in dash  # on by default
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


# ── The breakout in the bot's gaps (docs/RESULTS.md round 101): the account's trades are research/combo_priority.py's
def rth_minutes(sessions: int, seed: int) -> pd.DataFrame:
    """Random-walk 1-minute bars, 09:30-15:59 only, each opening at the last close; a drift on some days, so both
    the bot and the breakout trade."""
    rng = np.random.default_rng(seed)
    price, frames = 20_000.0, []
    for day in pd.bdate_range("2026-03-02", periods=sessions):
        idx = pd.date_range(f"{day.date()} 09:30", f"{day.date()} 15:59", freq="1min", tz=NY)
        drift = rng.choice([0.0, 0.0, 0.25, -0.25, 0.5, -0.5])
        rows = []
        for _ in idx:
            path = price + np.cumsum(rng.standard_t(3, size=4) * 1.5 + drift / 4)
            c = float(np.round(path[-1] * 4) / 4)
            rows.append((price, float(np.ceil(max(price, path.max()) * 4) / 4),
                         float(np.floor(min(price, path.min()) * 4) / 4), c))
            price = c
        frames.append(pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx))
    df = pd.concat(frames)
    df["volume"] = 100.0
    return df


def combo_reference(bars: pd.DataFrame, funded: bool, target_r: float = 8.0):
    """The bot's trades and the breakout's in its gaps, as research/combo_priority.py trades them; the breakout from
    the bot's fifteenth session (the strategy waits for its 14 sessions of history) and not on the skip dates."""
    bot = [(t.entry_bar, t.exit_bar, t.direction, t.entry, t.exit, t.pnl, t.reason)
           for t in run(bars, account(funded), minutes=1).trades]
    idx = bars.index.tz_convert(NY)
    first = sorted(set(idx.normalize()))[14]
    old, combo_live.RISK = combo_live.RISK, 200.0 if funded else 400.0  # the strategy's breakout risk (round 134)
    try:
        w = [leg for leg in combo_live.williams_legs(bars, month_skip=False,
                                                     skip_dates=NoiseConfig().skip_dates.split(","), target_r=target_r)
             if idx[leg[0]] >= first]
    finally:
        combo_live.RISK = old
    legs = combo_priority.priority(bars, [b[:6] + (4,) for b in bot], w)
    why = {b[0]: b[6] for b in bot}
    return sorted((a, b, d, en, ex, pnl, why.get(a, "breakout")) for a, b, d, en, ex, pnl, _ in legs)


@pytest.mark.parametrize("target_r", [8.0, 1.0])
@pytest.mark.parametrize("funded", [False, True])
@pytest.mark.parametrize("seed", [3, 5, 9])
def test_breakout_in_the_bots_gaps(sim, tmp_path, seed, funded, target_r):
    bars = rth_minutes(60, seed)
    trades, orders, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, Funded=funded, RoundPrices=False,
                                   BreakoutTarget=target_r)
    last_day = bars.index.tz_convert(NY).normalize()[-1]
    ref = [r for r in combo_reference(bars, funded, target_r) if bars.index.tz_convert(NY)[r[0]].normalize() < last_day]
    trades = [t for t in trades if bars.index.tz_convert(NY)[int(t[1])].normalize() < last_day]
    assert len(trades) == len(ref), (len(trades), len(ref))
    kinds = set()
    for row, (a, b, d, en, ex, pnl, why) in zip(trades, ref, strict=True):
        rd, ra, ren, rb, rex, rwhy, rpnl = row
        assert (int(rd), int(ra)) == (d, a), (row, (a, b, d, en, ex, pnl, why))
        if why == "breakout":
            kinds.add("cut" if rwhy == "Breakout: bot first" else "reversed" if rwhy == "Close position" else rwhy)
            # a stop or a take-profit fills in its bar; a 16:00 exit and a cut fill at the next bar's open
            assert int(rb) == b + (rwhy not in ("Stop loss", "Profit target")), (row, b)
        else:
            assert int(rb) == b + (why in TIME_EXITS), (row, b, why)
        assert same(ren, en) and same(rex, ex), (row, en, ex)
        assert math.isclose(float(rpnl), pnl, abs_tol=1e-6), (row, pnl)
    assert {"Stop loss", "Flat 16:00"} <= kinds or target_r < 2, kinds
    if target_r < 2:
        assert "Profit target" in kinds, kinds
    assert "cut" in kinds or "reversed" in kinds, kinds
    sizes = {int(o[3]) for o in orders if o[1] == "Enter" and o[2].startswith("W")}
    assert sizes and all(1 <= q <= 10 for q in sizes)


# ── The evaluation's target (docs/RESULTS.md round 124): everything closed the moment the evaluation is up the target
@pytest.mark.parametrize("seed", [3, 5, 9])
@pytest.mark.parametrize("target", [300.0, 700.0, 1500.0])
def test_evaluation_target_closes_everything(sim, tmp_path, seed, target):
    bars = rth_minutes(60, seed)
    base, _, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, RoundPrices=False, EvalTarget=0)
    got, orders, dash, printed = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, RoundPrices=False,
                                         EvalTarget=target, EvalTargetInHistory=True)
    pnl = [float(t[6]) for t in got]
    assert len(got) < len(base), "the target is reached before the data ends"
    k = len(got) - 1
    assert got[:k] == base[:k], "every trade before the one reaching the target is the same"
    assert got[k][:3] == base[k][:3], "the trade reaching it is the same entry"
    assert sum(pnl[:k]) < target + 25 <= sum(pnl[:k]) + max(float(base[k][6]), max(pnl[k], 0)) + 1e3
    assert sum(pnl) >= target, (sum(pnl), target)  # the buffer covers the closing fees
    # the take-profit at the target's price (or the normal one, when closer) fills before any close-based exit
    assert got[k][5] == "Profit target", got[k]
    d, en, ex = int(got[k][0]), float(got[k][2]), float(got[k][4])
    q = round(pnl[k] / (d * (ex - en) * 2.0 - 1.24))
    at_target = en + d * (target + 25 - sum(pnl[:k])) / (q * 2.0)
    assert math.isclose(ex, at_target, abs_tol=1e-6) or d * (ex - at_target) < 0, (ex, at_target)
    last_exit = int(got[k][3])
    assert not [o for o in orders if o[1] == "Enter" and int(o[0]) >= last_exit], "no new trades after the target"
    assert any("EVALUATION TARGET REACHED" in p for p in printed) and "TARGET REACHED" in dash


def test_evaluation_target_only_in_the_evaluation_and_live(sim, tmp_path):
    bars = rth_minutes(60, 3)
    funded, _, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, Funded=True, RoundPrices=False)
    funded_t, _, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, Funded=True, RoundPrices=False,
                                EvalTarget=300, EvalTargetInHistory=True)
    assert funded == funded_t, "no target on the funded account"
    ev, _, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, RoundPrices=False, EvalTarget=0)
    hist, _, dash, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, RoundPrices=False, EvalTarget=300)
    assert ev == hist, "the history before going live is not counted"
    assert "target close works live" in dash


def best_equity(bars, trades):
    """For each trade (strategy rows): the account's closed P/L before it, and its best open P/L ($) from the bars."""
    h, lo = bars.high.to_numpy(float), bars.low.to_numpy(float)
    out, cum = [], 0.0
    for d, eb, en, xb, ex, why, pnl in trades:
        d, eb, xb, en, ex, pnl = int(d), int(eb), int(xb), float(en), float(ex), float(pnl)
        per = d * (ex - en) * 2.0 - 1.24
        q = round(pnl / per) if abs(per) > 1e-9 else 1
        # a stop or a take-profit fills inside its bar; a market exit at the exit bar's open, so that bar's range was
        # never open to the trade
        last = xb + 1 if why in ("Stop loss", "Profit target") else xb
        hi = max(h[eb:last].max(initial=-np.inf), ex)
        low = min(lo[eb:last].min(initial=np.inf), ex)
        fav = (hi - en) if d > 0 else (en - low)
        out.append((cum, q * (fav * 2.0 - 1.24)))
        cum += pnl
    return out


def test_evaluation_target_on_a_breakout_trade(sim, tmp_path):
    """A target only a breakout trade's run-up reaches (above every earlier trade's best): that trade exits at the
    target's price, the trades before it are unchanged and nothing follows."""
    hits = 0
    for seed in (3, 5, 9, 11, 13):
        bars = rth_minutes(60, seed)
        base, orders, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, RoundPrices=False, EvalTarget=0)
        w_entries = {o[0] for o in orders if o[1] == "Enter" and o[2].startswith("W")}
        best = best_equity(bars, base)
        peak = -1e9
        for k, (cum, fav) in enumerate(best):
            if str(int(base[k][1]) - 1) in w_entries and cum + fav > peak + 150 and cum + fav > 150:
                target = max(peak, cum) + (cum + fav - max(peak, cum)) / 2 - 25
                if target <= 0:
                    continue
                got, _, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, RoundPrices=False,
                                       EvalTarget=target, EvalTargetInHistory=True)
                assert got[:k] == base[:k] and len(got) == k + 1 and got[k][:3] == base[k][:3], (seed, k)
                assert got[k][5] == "Profit target" and sum(float(t[6]) for t in got) >= target, (seed, got[k])
                hits += 1
                break
            peak = max(peak, cum + fav, cum + float(base[k][6]))
    assert hits, "a breakout trade reached the target on some seed"


def test_bold_finish(sim, tmp_path):
    """From day 20 of the evaluation, 2.5x size (bot 10 MNQ, the breakout's contracts x2.5 within 10); before, the same
    trades; never on the funded account."""
    bars = rth_minutes(60, 5)
    day0 = bars.index.tz_convert(NY)[0].strftime("%Y-%m-%d")
    bold = dict(EvalStartDate=day0, BoldFromDay=20, BoldSize=2.5)
    base, b_orders, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, RoundPrices=False)
    got, orders, dash, printed = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, RoundPrices=False, **bold)
    idx = bars.index.tz_convert(NY)
    cut = pd.Timestamp(day0, tz=NY) + pd.Timedelta(days=20)
    first_bold = next(k for k, t in enumerate(base) if idx[int(t[1])] >= cut)
    assert got[:first_bold] == base[:first_bold], "the same trades before the bold days"
    base_q = {o[0]: int(o[3]) for o in b_orders if o[1] == "Enter"}
    n_bot = n_w = 0
    for o in orders:
        if o[1] != "Enter" or idx[int(o[0])] < cut:
            continue
        if o[2].startswith("W"):
            n_w += 1
            assert int(o[3]) == min(10, max(1, math.floor(base_q.get(o[0], int(o[3])) * 2.5))), o
        else:
            n_bot += 1
            assert int(o[3]) == 10, o
    assert n_bot and n_w, (n_bot, n_w)
    assert "Bold finish: from" in dash and any("BUY 10 MNQ" in p or "SELL 10 MNQ" in p for p in printed)
    funded, _, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, RoundPrices=False, Funded=True)
    funded_b, _, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, RoundPrices=False, Funded=True, **bold)
    assert funded == funded_b, "not on the funded account"


# ── Alerts only (orders off: the user clicks, as Apex's no-automation rule requires): a trader who does exactly what
# the alerts say ends up with the strategy's own trades
def follow_alerts(bars, printed, minutes=1):
    """A manual trader on the stand-in's fill model, doing only what the alert lines say: a market order the bar after
    an alert, the stop and take-profit it names attached from the fill, moved when told."""
    import re
    from zoneinfo import ZoneInfo

    london = ZoneInfo("Europe/London")
    ends = {}
    for i, t in enumerate(bars.index.tz_convert(NY)):
        ends[(t + pd.Timedelta(minutes=minutes)).tz_convert(london).strftime("%m/%d/%Y %H:%M:%S")] = i
    by_bar = {}
    for line in printed:
        stamp, _, msg = line.partition("  ")
        if stamp in ends:
            by_bar.setdefault(ends[stamp], []).append(msg)
    o, h, lo = bars.open.to_numpy(float), bars.high.to_numpy(float), bars.low.to_numpy(float)
    c = bars.close.to_numpy(float)
    tick = 0.25
    pos = None  # dict(d, q, entry, bar, stop, tp)
    pend_exit, pend_entry, trades = False, None, []

    def close(i, px):
        nonlocal pos
        trades.append((pos["d"], pos["bar"], pos["entry"], i, px,
                       round(pos["d"] * (px - pos["entry"]) * 2.0 * pos["q"] - 1.24 * pos["q"], 6)))
        pos = None

    num = r"(-?\d+(?:\.\d+)?)"
    for i in range(len(c)):
        if pend_exit and pos:
            close(i, o[i] - pos["d"] * tick)
        pend_exit = False
        if pend_entry:
            d, q, st, tp = pend_entry
            if pos:  # a reversal: the old position goes first
                close(i, o[i] - pos["d"] * tick)
            pos = dict(d=d, q=q, entry=o[i] + d * tick, bar=i, stop=st, tp=tp)
            pend_entry = None
        if pos:
            d, st, tp = pos["d"], pos["stop"], pos["tp"]
            if pos["bar"] == i:
                hit, px = (lo[i] <= st, min(o[i], st) - tick) if d > 0 else (h[i] >= st, max(o[i], st) + tick)
            elif (d > 0 and o[i] <= st) or (d < 0 and o[i] >= st):
                hit, px = True, o[i] - d * tick
            else:
                hit, px = (lo[i] <= st if d > 0 else h[i] >= st), st - d * tick
            if hit:
                close(i, px)
            elif tp is not None and ((d > 0 and h[i] >= tp + tick) or (d < 0 and lo[i] <= tp - tick)):
                close(i, tp)
        for msg in by_bar.get(i, []):
            m = re.search(r"(BUY|SELL) (\d+) MNQ .*?Stop " + num + r".*?(?:take-profit " + num + ")?[,.]", msg)
            if ("BUY" in msg or "SELL" in msg) and "at market" in msg and m and "HEADS-UP" not in msg:
                if msg.startswith("First CLOSE") and pos:
                    pend_exit = True
                d = 1 if m.group(1) == "BUY" else -1
                tp = re.search(r"take-profit " + num, msg)
                pend_entry = (d, int(m.group(2)), float(m.group(3)), float(tp.group(1)) if tp else None)
                if pos and pos["d"] == d and not msg.startswith("First CLOSE"):
                    pend_exit = True
            elif msg.startswith("MOVE STOP") and pos:
                pos["stop"] = float(re.search(r"stop to " + num, msg).group(1))
                if (pos["d"] > 0 and pos["stop"] >= c[i]) or (pos["d"] < 0 and pos["stop"] <= c[i]):
                    pend_exit = True  # a stop past the price can't rest: out at market
            elif msg.startswith("MOVE TAKE-PROFIT") and pos:
                pos["tp"] = float(re.search(r"take-profit to " + num, msg).group(1))
            elif msg.startswith("FLAT") and pos:
                pend_exit = True
    return trades


@pytest.mark.parametrize("target_r", [8.0, 1.0])
@pytest.mark.parametrize("seed", [3, 5, 9])
@pytest.mark.parametrize("funded", [False, True])
def test_alerts_only_trader_matches_the_strategy(sim, tmp_path, seed, funded, target_r):
    bars = rth_minutes(50, seed)
    auto, _, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, Funded=funded, EvalTarget=0,
                            BreakoutTarget=target_r)
    _, orders, dash, printed = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, Funded=funded, EvalTarget=0,
                                       PlaceOrders=False, BreakoutTarget=target_r)
    assert not [o for o in orders if o[1] == "Enter"], "alerts only: no orders"
    manual = follow_alerts(bars, printed)
    last = bars.index.tz_convert(NY).normalize()[-1]
    keep = [t for t in auto if bars.index.tz_convert(NY)[int(t[1])].normalize() < last]
    manual = [t for t in manual if bars.index.tz_convert(NY)[t[1]].normalize() < last]
    assert len(manual) == len(keep), (len(manual), len(keep))
    for m, a in zip(manual, keep, strict=True):
        assert (m[0], m[1], m[3]) == (int(a[0]), int(a[1]), int(a[3])), (m, a)
        assert math.isclose(m[2], float(a[2]), abs_tol=1e-6) and math.isclose(m[4], float(a[4]), abs_tol=1e-6), (m, a)
        assert math.isclose(m[5], float(a[6]), abs_tol=1e-4), (m, a)


def test_alerts_only_evaluation_target(sim, tmp_path):
    """Alerts only, live: once the account itself is $3,000 up, one alert to close everything, no trade alerts after."""
    bars = rth_minutes(40, 3)
    _, _, _, before = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, PlaceOrders=False,
                              EvalTargetInHistory=True, SimNetLiq=52990)
    assert not any("EVALUATION TARGET REACHED" in p for p in before)
    _, _, dash, printed = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, PlaceOrders=False,
                                  EvalTargetInHistory=True, SimNetLiq=53000)
    hit = [k for k, p in enumerate(printed) if "EVALUATION TARGET REACHED" in p]
    assert len(hit) == 1 and "CLOSE EVERYTHING NOW" in printed[hit[0]]
    later = printed[hit[0] + 1:]
    assert not [p for p in later if "at market. Price" in p], "no trade alerts after the target"
    assert "TARGET REACHED" in dash and "$3,000 of $3,000" not in dash and "$3000 of $3000" in dash


def test_alerts_only_take_profit_at_the_evaluation_target(sim, tmp_path):
    """Alerts only, live, the account $2,950 up: a position's take-profit is moved to the price that brings it to the
    target ($3,000 + $25: $75 to go, 4 MNQ = 9.375 points from the price), when that is nearer than its own."""
    bars = rth_minutes(40, 3)
    _, _, _, printed = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, PlaceOrders=False,
                               EvalTargetInHistory=True, SimNetLiq=52950)
    moves = [p for p in printed if "MOVE TAKE-PROFIT" in p]
    assert moves, "the take-profit is moved to the target's price"
    stamps = bars.index.tz_convert(NY).map(lambda t: (t + pd.Timedelta(minutes=1)).tz_convert("Europe/London")
                                            .strftime("%m/%d/%Y %H:%M:%S"))
    closes = dict(zip(stamps, bars.close, strict=True))
    first = moves[0]
    stamp, _, msg = first.partition("  ")
    px = float(msg.split("take-profit to ")[1].split(" ")[0].rstrip("."))
    assert abs(abs(px - closes[stamp]) - 9.375) <= 0.25, (first, closes[stamp])
    assert not any("EVALUATION TARGET REACHED" in p for p in printed)


def account_equity(bars, trades):
    """The stand-in's net liquidation at each bar's close: $50,000 + closed P/L + open P/L."""
    c = bars.close.to_numpy(float)
    eq = np.full(len(c), 50000.0)
    for d, eb, en, xb, ex, _, pnl in trades:
        d, eb, xb, en, ex, pnl = int(d), int(eb), int(xb), float(en), float(ex), float(pnl)
        per = d * (ex - en) * 2.0 - 1.24
        q = round(pnl / per) if abs(per) > 1e-9 else 1
        eq[xb:] += pnl
        eq[eb:xb] += d * (c[eb:xb] - en) * 2.0 * q
    return eq


@pytest.mark.parametrize("state", [(4, 2000.0, 400.0), (4, 1600.0, 1500.0), (2, 900.0, 300.0)])
def test_funded_payout_stop(sim, tmp_path, state):
    """Funded, the payout stop on, the cycle state given, the account $2,500 up: the first bar at which closing (with
    $10 to spare) makes the day payout-eligible (the cycle's $200 days, the account $2,600 up, no day over half the
    cycle), recomputed here from the trades, is the payout day: flat at once, no more entries that day."""
    qual0, prof0, best0 = state
    bars = rth_minutes(40, 5)
    props = dict(Funded=True, PayoutStop=True, PayoutStopInHistory=True, FundedQualDays=qual0, FundedCycleProfit=prof0,
                 FundedBestDay=best0, AccountStart=47500, RoundPrices=False)
    trades, orders, dash, printed = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, **props)
    idx = bars.index.tz_convert(NY)
    stamps = {(t + pd.Timedelta(minutes=1)).tz_convert("Europe/London").strftime("%m/%d/%Y %H:%M:%S"): i
              for i, t in enumerate(idx)}
    hits = [stamps[p.partition("  ")[0]] for p in printed if "PAYOUT-ELIGIBLE" in p]
    eq = account_equity(bars, trades)
    tmin = (idx.hour * 60 + idx.minute).to_numpy()
    # the replica: the cycle rolls at each 09:30 (the day before added), eligibility at each bar after
    qual, prof, best, start, expected = qual0, prof0, best0, None, None
    for k in range(len(idx)):
        if tmin[k] == 570:
            if start is not None:
                day = eq[k] - eq[start]
                qual += day >= 200
                prof += day
                best = max(best, day)
            start = k
        if start is None:
            continue
        today, bal = eq[k] - eq[start] - 10, eq[k] - 47500 - 10
        if (today >= 200 and qual + 1 >= 5 and bal >= 2600 and prof + today > 0 and
                max(best, today) <= 0.5 * (prof + today) and min(1500, bal - 2100) >= 500):
            expected = k
            break
    if expected is None:
        assert not hits, "no bar was eligible"
        return
    assert hits and hits[0] == expected, (hits[:1], expected)
    i = hits[0]
    day = idx[i].normalize()
    assert not [o for o in orders if o[1] == "Enter" and int(o[0]) >= i and idx[int(o[0])].normalize() == day]
    open_then = [t for t in trades if int(t[1]) <= i < int(t[3])]
    assert all(int(t[3]) == i + 1 and t[5] == "Payout-eligible" for t in open_then), open_then
    import re
    taken = re.search(r"payouts taken (\d+)", dash)
    assert taken and int(taken.group(1)) == len(hits), (dash, len(hits))


PAYOUT_CAPS = (1500, 1500, 2000, 2500, 2500, 3000)
PAYOUT_PROPS = dict(Funded=True, PayoutStop=True, AccountStart=47600, RoundPrices=False)


def scripted_account(bars, seed):
    """An account path for the payout cycle's tests: each day a set result, reached in a straight line from the day's
    start (so the day's best is at its close), whatever the strategy's own trades do."""
    rng = np.random.default_rng(seed)
    day = bars.index.tz_convert(NY).normalize()
    liq, base = np.empty(len(bars)), 50000.0
    for d in day.unique():
        k = np.flatnonzero(day == d)
        total = float(rng.choice([260.0, 240.0, -150.0, 310.0, 220.0, 120.0, -80.0, 420.0]))
        liq[k] = base + total * np.arange(1, len(k) + 1) / len(k)
        base += total
    return liq


def payout_replica(bars, liq, withdraw=None, state=(0, 0.0, 0.0, 0), start_bal=47600.0, naive=False):
    """The payout cycle as the strategy keeps it, bar by bar: the bars at which closing makes the day
    payout-eligible, and the cycle at the end (qual days, profit, best day, payouts taken). naive: as before the
    payout asked for was tracked (a payout leaving the account is a losing day)."""
    qual, prof, best, taken = state
    tday = (bars.index.tz_convert(NY) + pd.Timedelta(hours=6)).normalize()
    w_bar, w_amt = withdraw if withdraw else (len(liq), 0.0)
    cday, start, last, pending, today_paid, hits = None, None, None, 0.0, False, []
    for k in range(len(liq)):
        x = liq[k] - (w_amt if k >= w_bar else 0.0)
        if pending > 0 and last is not None and last - x >= 0.9 * pending:
            start -= pending
            pending = 0.0
        if tday[k] != cday:
            if cday is not None:
                res = x - start
                if today_paid:
                    qual, prof, best, taken = 0, 0.0, 0.0, taken + 1
                else:
                    qual, prof, best = qual + (res >= 200), prof + res, max(best, res)
            cday, start, today_paid = tday[k], x, False
        last = x
        if today_paid or taken >= 6:
            continue
        today, bal = x - start - 10, x - start_bal - pending - 10
        amount = min(PAYOUT_CAPS[taken], bal - 2100)
        if (today >= 200 and qual + 1 >= 5 and bal >= 2600 and prof + today > 0 and
                max(best, today) <= 0.5 * (prof + today) and amount >= 500):
            today_paid, pending = True, 0.0 if naive else amount
            hits.append((k, float(amount)))
    return hits, (qual, prof, best, taken)


def payout_run(sim, bars, liq, tmp, n=None, **props):
    """The strategy on the first n bars with the scripted account; the bars of its PAYOUT-ELIGIBLE alerts and its
    payout-cycle dashboard line."""
    n = len(bars) if n is None else n
    liq_file = tmp / "liq.txt"
    liq_file.write_text("\n".join(repr(float(x)) for x in liq[:n]) + "\n")
    trades, orders, dash, printed = run_sim(sim, bars.iloc[:n], tmp, minutes=1, breakout=True, SimLiqFile=liq_file,
                                            **{**PAYOUT_PROPS, **props})
    idx = bars.index.tz_convert(NY)
    stamps = {(t + pd.Timedelta(minutes=1)).tz_convert("Europe/London").strftime("%m/%d/%Y %H:%M:%S"): i
              for i, t in enumerate(idx)}
    hits = [stamps[p.partition("  ")[0]] for p in printed if "PAYOUT-ELIGIBLE" in p]
    cycle = next((s for s in dash.split(" | ") if s.startswith("Payout cycle")), "")
    return hits, cycle, printed


def cycle_numbers(cycle):
    import re
    m = re.match(r"Payout cycle: (\d+)/5 days of \$200, (-?)\$(\d+) since the last payout, best day (-?)\$(\d+), "
                 r"payouts taken (\d+)", cycle)
    assert m, cycle
    return int(m.group(1)), float(m.group(2) + m.group(3)), float(m.group(4) + m.group(5)), int(m.group(6))


@pytest.fixture(scope="module")
def payout_case():
    bars = rth_minutes(40, 5)
    liq = scripted_account(bars, 8)
    first, _ = payout_replica(bars, liq)
    assert len(first) >= 3, first
    w_bar = first[0][0] + 2 * 390 + 100  # two days after the first payout day, mid-morning
    withdraw = (int(w_bar), float(first[0][1]))
    hits, end = payout_replica(bars, liq, withdraw)
    return bars, liq, withdraw, hits, end


def test_payout_cycle_on_a_scripted_account(sim, tmp_path, payout_case):
    """Several payout cycles, a payout leaving the account two days after it was asked for: the strategy's payout
    days are the replica's, the payout that left is not a losing day, and the cycle at the end is the replica's."""
    bars, liq, withdraw, want, end = payout_case
    hits, cycle, _ = payout_run(sim, bars, liq, tmp_path, PayoutStopInHistory=True,
                                SimWithdraw=f"{withdraw[0]}:{withdraw[1]!r}")
    assert hits == [k for k, _ in want], (hits, want)
    qual, prof, best, taken = cycle_numbers(cycle)
    assert (qual, taken) == (end[0], end[3]) and abs(prof - end[1]) <= 0.5 and abs(best - end[2]) <= 0.5, (cycle, end)
    # with the payout never leaving, the same days: it was already out of the balance; the amount each alert says
    # to ask for is the replica's (with the payouts asked for kept out of the balance)
    same, _, printed = payout_run(sim, bars, liq, tmp_path, PayoutStopInHistory=True)
    assert same == hits
    said = [float(p.split("about $")[1].split(")")[0]) for p in printed if "PAYOUT-ELIGIBLE" in p]
    kept, _ = payout_replica(bars, liq)
    assert [round(a) for _, a in kept] == said, (kept, said)
    assert [round(a) for _, a in payout_replica(bars, liq, naive=True)[0]] != said
    # and had the strategy counted the payout leaving as a loss, a later payout day would move
    lost, _ = payout_replica(bars, liq, withdraw, naive=True)
    assert [k for k, _ in lost] != hits


def restart_points(want, withdraw):
    first = want[0][0]
    day0 = first - first % 390
    return {"before the payout, same day": day0 + 100, "after the payout, same day": first + 5,
            "the next day's first bar": day0 + 390, "before the payout leaves": withdraw[0] - 50,
            "after it left": withdraw[0] + 200, "a later cycle": want[1][0] + 30,
            # a full day of the last cycle behind it: its best day comes from the file
            "the last cycle, a day in": want[-1][0] - want[-1][0] % 390 + 2 * 390 + 50}


@pytest.mark.parametrize("where", ["before the payout, same day", "after the payout, same day",
                                   "the next day's first bar", "before the payout leaves", "after it left",
                                   "a later cycle", "the last cycle, a day in"])
def test_payout_cycle_survives_a_restart(sim, tmp_path, payout_case, where):
    """The strategy stopped at a bar and started again (the history replayed, live from that bar) goes on from its
    file: the same payout days after the restart, and the same cycle at the end, as without the restart."""
    bars, liq, withdraw, want, end = payout_case
    s = restart_points(want, withdraw)[where]
    w = f"{withdraw[0]}:{withdraw[1]!r}"
    data = tmp_path / "nt8"
    a_dir, b_dir = tmp_path / "a", tmp_path / "b"
    a_dir.mkdir()
    b_dir.mkdir()
    hits_a, cycle_a, _ = payout_run(sim, bars, liq, a_dir, PayoutStopInHistory=True, SimWithdraw=w,
                                    SimUserDataDir=tmp_path / "nt8-a")
    payout_run(sim, bars, liq, b_dir, n=s, PayoutStopInHistory=True, SimWithdraw=w, SimUserDataDir=data)
    assert list(data.glob("MnqNoiseMomentum/payout-cycle-Sim101.txt")), "the state is written"
    hits_b, cycle_b, printed = payout_run(sim, bars, liq, b_dir, SimRealtimeFrom=s, SimWithdraw=w,
                                          SimUserDataDir=data)
    assert any("continuing from" in p for p in printed)
    assert hits_b == [k for k in hits_a if k >= s], (hits_b, hits_a, s)
    assert cycle_b.replace(" (remembered)", "") == cycle_a, (cycle_b, cycle_a)
    assert "(remembered)" in cycle_b


def test_payout_cycle_restart_without_the_file(sim, tmp_path, payout_case):
    """New settings replace the remembered state; RememberPayoutCycle off: no file, a restart starts from the
    settings."""
    bars, liq, withdraw, want, _ = payout_case
    s = want[0][0] + 390
    data = tmp_path / "nt8"
    payout_run(sim, bars, liq, tmp_path, n=s, PayoutStopInHistory=True, SimUserDataDir=data)
    _, cycle, printed = payout_run(sim, bars, liq, tmp_path, SimRealtimeFrom=s, SimUserDataDir=data,
                                   FundedQualDays=1)
    assert any("the settings changed" in p for p in printed) and "(remembered)" not in cycle
    off = tmp_path / "nt8-off"
    payout_run(sim, bars, liq, tmp_path, n=s, PayoutStopInHistory=True, SimUserDataDir=off, RememberPayoutCycle=False)
    assert not off.exists() or not list(off.rglob("*.txt"))


def test_payout_cycle_days_the_strategy_was_off(sim, tmp_path, payout_case):
    """Stopped on one day and started again two weekdays later, during the day: a warning, the day it missed counted
    with the day before (fewer $200 days, never more), and the cycle's profit still the account's."""
    bars, liq, _, want, _ = payout_case
    first = want[0][0]
    day_k = (first - first % 390) - 3 * 390  # three days before the first payout day
    s_stop, s_start, n = day_k + 200, day_k + 2 * 390 + 120, day_k + 3 * 390
    data = tmp_path / "nt8"
    payout_run(sim, bars, liq, tmp_path, n=s_stop, PayoutStopInHistory=True, SimUserDataDir=data)
    _, cycle, printed = payout_run(sim, bars, liq, tmp_path, n=n, SimRealtimeFrom=s_start, SimUserDataDir=data)
    assert any("was off on 1 weekday(s)" in p for p in printed), printed[-5:]
    _, ref = payout_run(sim, bars, liq, tmp_path, n=n, PayoutStopInHistory=True, SimUserDataDir=tmp_path / "ref")[:2]
    q, p, _, t = cycle_numbers(cycle)
    q_ref, p_ref, _, t_ref = cycle_numbers(ref)
    assert t == t_ref and abs(p - p_ref) <= 0.5 and q <= q_ref, (cycle, ref)


def test_payout_stop_on_by_default_and_live_only(sim, tmp_path):
    """The payout stop is on by default (round 132) on the funded account; in a backtest it doesn't act (it reads the
    real account), so the trades are those with it off; the dashboard says it works live."""
    bars = rth_minutes(30, 3)
    on, _, dash, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, Funded=True)
    off, _, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, Funded=True, PayoutStop=False)
    assert on == off and on
    assert "Payout cycle: 0/5 days of $200" in dash and "(works live)" in dash
    _, _, dash_eval, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True)
    assert "Payout cycle" not in dash_eval


def test_account_position_guard(sim, tmp_path):
    """Live with orders on: while the account's own MNQ position differs from the strategy's (a position left over
    from a restart, a trade by hand), one loud alert at the second bar close apart and no new entries until they
    agree; then an all-clear and entries again. Live with the two agreeing: the same trades as the backtest."""
    bars = rth_minutes(30, 3)
    r = 15 * 390
    base = dict(minutes=1, breakout=True, EvalTarget=0)
    ref, ref_orders, _, _ = run_sim(sim, bars, tmp_path, **base)
    live, _, _, printed = run_sim(sim, bars, tmp_path, SimRealtimeFrom=r, **base)
    assert live == ref and not any("MISMATCH" in p for p in printed)
    for kind in (("Long", "Short"), ("W Long", "W Short")):  # a window over a bot entry, one over a breakout entry
        e = next(int(o[0]) for o in ref_orders if o[1] == "Enter" and o[2] in kind and int(o[0]) >= r + 390)
        f, g = e - 30, e + 60
        _, orders, dash, printed = run_sim(sim, bars, tmp_path, SimRealtimeFrom=r, SimForeignPosition=f"{f}:{g}:4",
                                           **base)
        blocked = [int(o[0]) for o in orders if o[1] == "Enter" and f + 1 <= int(o[0]) < g]
        assert not blocked, (kind, blocked)
        alerts = [p for p in printed if "ACCOUNT POSITION MISMATCH" in p]
        assert len(alerts) == 1 and "the account holds 4 MNQ, the strategy 0" in alerts[0], alerts
        assert sum("AGREE AGAIN" in p for p in printed) == 1
        later = [int(o[0]) for o in orders if o[1] == "Enter" and int(o[0]) >= g]
        assert later, "entries resume once the account and the strategy agree"
        assert "MISMATCH" not in dash


def test_payout_cycle_alerts_only(sim, tmp_path, payout_case):
    """Orders off (you click): the same payout days as with orders on, each alert telling you to close everything,
    and a restart going on from the file the same way."""
    bars, liq, withdraw, want, end = payout_case
    w = f"{withdraw[0]}:{withdraw[1]!r}"
    hits, cycle, printed = payout_run(sim, bars, liq, tmp_path, PayoutStopInHistory=True, SimWithdraw=w,
                                      PlaceOrders=False, SimUserDataDir=tmp_path / "a")
    assert hits == [k for k, _ in want], (hits, want)
    alerts = [p for p in printed if "PAYOUT-ELIGIBLE" in p]
    assert alerts and all("CLOSE EVERYTHING NOW" in p for p in alerts)
    s = want[1][0] + 30
    data = tmp_path / "b"
    payout_run(sim, bars, liq, tmp_path, n=s, PayoutStopInHistory=True, SimWithdraw=w, PlaceOrders=False,
               SimUserDataDir=data)
    hits_b, cycle_b, _ = payout_run(sim, bars, liq, tmp_path, SimRealtimeFrom=s, SimWithdraw=w, PlaceOrders=False,
                                    SimUserDataDir=data)
    assert hits_b == [k for k in hits if k >= s] and cycle_b.replace(" (remembered)", "") == cycle


def test_evaluation_target_from_the_account_after_a_restart(sim, tmp_path):
    """Orders on, the strategy (re)started in the middle of an evaluation already in profit: the target is read from
    the account's balance, so it closes everything when the account reaches it; the old count (its own P/L since
    going live) would trade on past it, aiming for the whole target again."""
    hits = 0
    for seed in (3, 5, 9, 11):
        bars = rth_minutes(60, seed)
        r = 25 * 390
        base, _, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, RoundPrices=False, EvalTarget=0,
                                SimRealtimeFrom=r)
        before = sum(float(t[6]) for t in base if int(t[3]) < r)
        if before < 300:
            continue
        best, peak = best_equity(bars, base), -1e9
        for k, (cum, fav) in enumerate(best):
            if int(base[k][1]) > r and int(base[k - 1][3]) < int(base[k][1]) and cum + fav > peak + 150:
                target = max(peak, cum) + (cum + fav - max(peak, cum)) / 2 - 25
                got, _, _, printed = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, RoundPrices=False,
                                             EvalTarget=target, SimRealtimeFrom=r)
                assert got[:k] == base[:k] and len(got) == k + 1, (seed, k, len(got))
                assert sum(float(t[6]) for t in got) >= target
                assert any("EVALUATION TARGET REACHED" in p for p in printed)
                old, _, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, RoundPrices=False,
                                       EvalTarget=target, SimRealtimeFrom=r, EvalFromAccount=False)
                assert len(old) > k + 1, "the old count trades on past the target"
                hits += 1
                break
            peak = max(peak, cum + fav, cum + float(base[k][6]))
    assert hits >= 2, hits


def test_account_type_from_the_account_name(sim, tmp_path):
    """One set of settings for the evaluation and the funded account: Apex's PA-APEX-... accounts trade the funded
    settings and its APEX-... accounts the evaluation's, whatever the FUNDED ACCOUNT switch says; any other name (a
    simulation account) and the auto setting off follow the switch. The dashboard says which and why."""
    bars = rth_minutes(30, 3)
    kw = dict(minutes=1, breakout=True)
    funded, _, _, _ = run_sim(sim, bars, tmp_path, Funded=True, **kw)
    evaluation, _, _, _ = run_sim(sim, bars, tmp_path, Funded=False, **kw)
    assert funded != evaluation
    pa, _, dash, _ = run_sim(sim, bars, tmp_path, SimAccountName="PA-APEX-123456-01", **kw)
    assert pa == funded and "Account: Funded (from the account's name, PA-APEX-123456-01)" in dash
    ev, _, dash, _ = run_sim(sim, bars, tmp_path, SimAccountName="APEX-123456-01", Funded=True, **kw)
    assert ev == evaluation and "Account: Evaluation (from the account's name, APEX-123456-01)" in dash
    sim_acct, _, dash, _ = run_sim(sim, bars, tmp_path, Funded=True, **kw)
    assert sim_acct == funded and "Account: Funded (from the FUNDED ACCOUNT setting)" in dash
    off, _, _, _ = run_sim(sim, bars, tmp_path, SimAccountName="PA-APEX-123456-01", AutoAccountType=False, **kw)
    assert off == evaluation


def test_guard_blocks_from_the_first_bar_and_messages_say_what_was_sent(sim, tmp_path):
    """A position outside the strategy that appears on the very bar of an entry signal blocks that entry (no doubling
    up, not even for one bar), and the alert says the order was NOT sent and why; with orders on and nothing in the
    way, every entry alert says the order was sent."""
    bars = rth_minutes(30, 3)
    r = 15 * 390
    base = dict(minutes=1, breakout=True, EvalTarget=0, SimRealtimeFrom=r)
    _, ref_orders, _, ref_printed = run_sim(sim, bars, tmp_path, **base)
    entries = [p for p in ref_printed if " MNQ (Evaluation) at market." in p]
    assert entries and all("The strategy sent the order." in p for p in entries)
    for kind in (("Long", "Short"), ("W Long", "W Short")):
        e = next(int(o[0]) for o in ref_orders if o[1] == "Enter" and o[2] in kind and int(o[0]) >= r + 390)
        _, orders, _, printed = run_sim(sim, bars, tmp_path, SimForeignPosition=f"{e}:{e + 60}:4", **base)
        assert not [o for o in orders if o[1] == "Enter" and e <= int(o[0]) < e + 60], kind
        assert any("NOT sent by the strategy: the account's position isn't the strategy's" in p for p in printed), kind


@pytest.mark.parametrize("refusals", [1, 2])
def test_a_rejected_exit_is_sent_again(sim, tmp_path, refusals):
    """A stop change is rejected, then the market exit sent in its place is rejected too (once, or twice in a row):
    the exit is sent again at each following bar until the position is closed, never left there."""
    bars = synth_bars(sessions=60, seed=3)
    trades, _, _, _ = run_sim(sim, bars, tmp_path, RoundPrices=False)
    b = int(next(t for t in trades if int(t[3]) - int(t[1]) >= 6)[1]) + 2
    rejects = ",".join(str(b + k) for k in range(refusals))
    got, _, _, printed = run_sim(sim, bars, tmp_path, RoundPrices=False, RejectStopsAt=str(b), RejectExitsAt=rejects)
    closed = {int(t[3]): t[5] for t in got}
    assert closed.get(b + refusals + 1) == "Close: retry", (b, refusals, closed)
    assert sum("The exit is sent again at the next bar" in p for p in printed) == refusals
    assert sum("EXIT REJECTED, SENT AGAIN" in p for p in printed) == refusals


@pytest.mark.parametrize("funded", [False, True])
def test_tighten_only_matches_the_bot_and_changes_trades(sim, tmp_path, funded):
    """Round 139: with the stop only ever tightening, the strategy's account trades are the Python bot's with
    tighten_only, and with it off, the bot's without; the rule binds (the two differ) on these bars."""
    changed = 0
    for seed in (3, 5, 9):
        bars = synth_bars(sessions=90, seed=seed)
        on, _, _, _ = run_sim(sim, bars, tmp_path, Funded=funded, RoundPrices=False)
        off, _, _, _ = run_sim(sim, bars, tmp_path, Funded=funded, RoundPrices=False, TightenOnly=False)
        assert_strategy_matches(on, run(bars, account(funded)))
        cfg = ACCOUNTS[funded] | {"tighten_only": False}
        assert_strategy_matches(off, run(bars, NoiseConfig(**cfg, target_on_fill_bar=True)))
        changed += on != off
    assert changed, "the tighten-only rule changed some trade"


def stop_sequences(trades, orders, tick=0.25):
    """Per account position of the bot: the stop prices the strategy sent, in order, from the bracket sent with the
    entry (ticks from the fill) to the last change before the exit."""
    out = []
    for d, eb, en, xb, *_ in trades:
        d, eb, en, xb = int(d), int(eb), float(en), int(xb)
        name = "Long" if d > 0 else "Short"
        sent = [o for o in orders if o[1] == "SetStopLoss" and o[2] == name and eb - 1 <= int(o[0]) < xb]
        prices = []
        for o in sent:
            v = float(o[3])
            prices.append(en - d * v * tick if o[4] == "Ticks" else v)
        if prices:
            out.append((d, prices))
    return out


@pytest.mark.parametrize("funded", [False, True])
def test_stop_ratchet_within_a_position(sim, tmp_path, funded):
    """The ratchet, as defined (docs/VERIFICATION.md): within one position a long's stop never decreases and a
    short's never increases, from the bracket sent with the entry to the exit - checked on every stop order the
    strategy sent; with the setting off the same bars do show a stop moving back (the check can fail)."""
    loosened_off = 0
    for seed in (3, 5, 9):
        bars = synth_bars(sessions=90, seed=seed)
        trades, orders, _, _ = run_sim(sim, bars, tmp_path, Funded=funded, RoundPrices=False)
        bot = [t for t in trades if t[5] not in ("Breakout: bot first",)]
        for d, prices in stop_sequences(bot, orders):
            steps = np.diff(prices) * d
            assert (steps >= -1e-9).all(), (seed, d, prices)
        trades2, orders2, _, _ = run_sim(sim, bars, tmp_path, Funded=funded, RoundPrices=False, TightenOnly=False)
        loosened_off += sum(bool((np.diff(p) * d < -1e-9).any()) for d, p in stop_sequences(trades2, orders2))
    assert loosened_off, "with the ratchet off, some stop moved back (the check is not vacuous)"


def _day_of(bars):
    return bars.index.tz_convert(NY).normalize()


def test_daily_ledger_from_fills_counts_positions_not_fills(sim, tmp_path):
    """The dashboard's 'Today (fills)' is built from NinjaTrader's trade records: it equals the day's trades, and a
    position filled in two parts (two records) is still one trade and at most one loser; the trades don't change."""
    bars = rth_minutes(40, 5)
    trades, _, dash, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True)
    split, _, dash2, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, SimSplitFills=True)
    assert split == trades
    day = _day_of(bars)
    last = day[-1]
    today = [t for t in trades if day[int(t[3])] == last]  # closed today (the ledger's definition)
    pnl = sum(float(t[6]) for t in today)
    want = (f"Today (simulated fills, both setups): {len(today)} trades, {'-' if pnl < 0 else ''}${abs(pnl):.0f}, "
            f"{sum(float(t[6]) < 0 for t in today)} losers")
    line = next(s for s in dash.split(" | ") if s.startswith("Today (simulated fills"))
    line2 = next(s for s in dash2.split(" | ") if s.startswith("Today (simulated fills"))
    assert line == want == line2, (line, want, line2)


def test_daily_gate_max_losers_both_setups(sim, tmp_path):
    """DailyMaxLosers 2: once the day has two losing trades, bot's or breakout's, no entry from either setup."""
    blocked = 0
    for seed in (3, 5, 9):
        bars = rth_minutes(40, seed)
        ref, ref_orders, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True)
        trades, orders, _, printed = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, DailyMaxLosers=2)
        day = _day_of(bars)
        for d in sorted({day[int(t[3])] for t in trades}):
            losers = sorted(int(t[3]) for t in trades if day[int(t[3])] == d and float(t[6]) < 0)
            if len(losers) >= 2:
                after = [o for o in orders if o[1] == "Enter" and day[int(o[0])] == d and int(o[0]) >= losers[1]]
                assert not after, (seed, d, after)
        blocked += sum("NOT sent by the strategy: today's 2 losing trades" in p for p in printed)
        assert len([o for o in orders if o[1] == "Enter"]) <= len([o for o in ref_orders if o[1] == "Enter"])
    assert blocked, "the gate stopped some entries"


def test_daily_gate_loss_limit_both_setups(sim, tmp_path):
    """DailyLossLimit $500: no entry (bot or breakout) whose planned risk - its stop distance plus a tick a side,
    times its contracts, times $2 - could take the day's realized P/L below -$500."""
    stopped = 0
    for seed in (3, 5, 9):
        bars = rth_minutes(40, seed)
        trades, orders, _, printed = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, DailyLossLimit=500)
        day = _day_of(bars)
        for k, o in enumerate(orders):
            if o[1] != "Enter":
                continue
            e, name, q = int(o[0]), o[2], int(o[3])
            ticks = float(next(x for x in reversed(orders[:k]) if x[1] == "SetStopLoss" and x[2] == name)[3])
            risk = (ticks * 0.25 + 0.5) * q * 2.0
            realized = sum(float(t[6]) for t in trades if day[int(t[3])] == day[e] and int(t[3]) <= e)
            assert realized - risk >= -500 - 1e-6, (seed, o, realized, risk)
        stopped += sum("could take today past the $500 loss limit" in p for p in printed)
    assert stopped, "the gate stopped some entries"


def by_position(rows):
    """Account trades merged per position and exit: {entry bar: [(exit bar, exit price, $)]}, closes at the same bar
    and price summed (a position in two lots closed together by its stop is one close)."""
    out: dict[int, dict[tuple[int, float], float]] = {}
    for eb, xb, ex, pnl in rows:
        key = (xb, round(ex, 6))
        out.setdefault(eb, {})[key] = out.get(eb, {}).get(key, 0.0) + pnl
    return {eb: sorted((xb, ex, round(p, 6)) for (xb, ex), p in v.items()) for eb, v in out.items()}


@pytest.mark.parametrize("funded", [False, True])
def test_half_off_at_1r_matches_the_bot(sim, tmp_path, funded):
    """The frozen forward-test alternative (docs/VERIFICATION.md): half the bot's contracts are their own entry ("Long
    half" / "Short half") with the same stop and their own take-profit PartialAtR x R from the fill, both sent with the
    entry as Set orders (no exit order of its own). R is the trade's initial risk: the bracket's stop distance. The
    account's trades, per position and exit, equal the Python bot's with that definition (partial_r "initial"), and
    the half's take-profit fills."""
    parts = 0
    for seed in (3, 5, 9):
        bars = synth_bars(sessions=90, seed=seed)
        trades, orders, _, _ = run_sim(sim, bars, tmp_path, Funded=funded, RoundPrices=False, PartialAtR=1.0)
        assert not any(o[1] == "ExitLimit" for o in orders)
        res = run(bars, account(funded, partial_at=1.0, partial_r="initial"))
        got = by_position([(int(t[1]), int(t[3]), float(t[4]), float(t[6])) for t in trades])
        want = by_position([(t.entry_bar, t.exit_bar + (t.reason in TIME_EXITS), t.exit, t.pnl) for t in res.trades])
        assert got.keys() == want.keys()
        for eb in got:
            assert len(got[eb]) == len(want[eb]), (eb, got[eb], want[eb])
            for (xa, pa, va), (xb, pb, vb) in zip(got[eb], want[eb], strict=True):
                assert xa == xb and math.isclose(pa, pb, abs_tol=1e-6), (eb, got[eb], want[eb])
                assert math.isclose(va, vb, abs_tol=1e-6), (eb, got[eb], want[eb])
        enters = [o for o in orders if o[1] == "Enter" and o[2] in ("Long", "Short", "Long half", "Short half")]
        assert enters and all(o[3] == "2" for o in enters)  # 4 MNQ: two lots of 2
        # the half: its own entry, 2 of 4 contracts, closed by its take-profit R from the fill
        stops = {int(o[0]): float(o[3]) for o in orders if o[1] == "SetStopLoss" and o[2] in ("Long half", "Short half")
                 and o[4] == "Ticks"}
        for t in res.trades:
            if t.reason == "Partial":
                parts += 1
                r = next(v for k, v in sorted(stops.items(), reverse=True) if k < t.entry_bar) * 0.25
                assert math.isclose(abs(t.exit - t.entry), r, abs_tol=1e-6)
    assert parts, "the half was taken on these bars"


# ── Diagnostics (docs/NINJATRADER.md, "No trades"): counting only
def funnel(printed):
    """The end-of-run funnel's numbers by step, its blocked lines and its last line."""
    start = max(k for k, p in enumerate(printed) if p.startswith("MNQ funnel, end of run"))
    lines = printed[start + 1:]
    steps = {int(p.split()[0]): p for p in lines if p.strip()[:1].isdigit()}
    num = {k: int(v.split(": ")[1].split()[0]) for k, v in steps.items()}
    blocked = [p.strip() for p in lines if p.strip().startswith("blocked")]
    last = next(p.strip() for p in reversed(lines) if "FUNNEL STOPS AT" in p or "every step has entries" in p)
    return num, blocked, last


@pytest.mark.parametrize("seed", [3, 5])
def test_diagnostics_change_no_trade_and_the_counts_add_up(sim, tmp_path, seed):
    """Diagnostics on (order trace, a line per order, fill and blocked signal): the same orders and trades as off. The
    settings are printed at the start; each step's count follows from the one before: every signal is sent or has a
    recorded reason; every entry sent is accepted and filled; the completed trades are the account's positions."""
    bars = rth_minutes(40, seed)
    off = run_sim(sim, bars, tmp_path, minutes=1, breakout=True)
    on = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, Diagnostics=True)
    assert off[0] == on[0] and off[1] == on[1]
    for printed in (off[3], on[3]):
        sets = [p for p in printed if p.startswith("MNQ settings:")]
        assert len(sets) == 3 and "1 Minute bars" in sets[0] and "Calculate OnBarClose" in sets[0]
        for key in ("PlaceOrders True", "Lookback 14", "DailyLossLimit 0", "DailyMaxLosers 0", "PartialAtR 0"):
            assert key in sets[1], key
        assert "EvalTarget 3000 in history False" in sets[2] and "PayoutStop True in history False" in sets[2]
        num, blocked, last = funnel(printed)
        step4 = sum(int(b.rsplit(": ", 1)[1].split()[0]) for b in blocked if b.startswith("blocked before step 4"))
        assert num[3] == num[4] + step4 > 0
        assert num[4] == num[5] == num[6] == num[7] > 0
        assert num[8] == len({(t[1], t[2]) for t in off[0]}) and last == "every step has entries"
    assert "TraceOrders True" in [p for p in on[3] if p.startswith("MNQ settings:")][2]
    assert sum(p.startswith("MNQ order: ") and " Filled" in p for p in on[3]) == funnel(on[3])[0][7]
    assert sum(p.startswith("MNQ execution: ") for p in on[3]) == funnel(on[3])[0][7]
    assert not any(p.startswith(("MNQ order: ", "MNQ execution: ", "MNQ blocked (")) for p in off[3])


def test_funnel_names_the_step_a_zero_trade_run_stops_at(sim, tmp_path):
    """Runs made to trade nothing, one cause each: the funnel's last line names the step and the recorded cause."""
    bars = rth_minutes(40, 3)
    n = len(bars)
    every = ",".join(map(str, range(n)))
    cases = [(dict(PlaceOrders=False), "step 4", "orders are off (alerts only)"),
             (dict(Lookback=60), "step 2", "before the engine has 60 full sessions"),
             (dict(DailyLossLimit=1), "step 4", "daily gate: the trade's risk could take today past the loss limit"),
             (dict(SimIgnoreEntriesAt=every), "step 6", "the entry call gave no order back"),
             (dict(SimRejectEntriesAt=every), "step 6", "entry rejected")]
    for props, step, cause in cases:
        trades, orders, _, printed = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, **props)
        _, _, last = funnel(printed)
        assert not trades and last.startswith(f"FUNNEL STOPS AT {step},") and cause in last, (props, last)
    # a chart the strategy can't use: 7-minute bars
    _, _, _, printed = run_sim(sim, bars, tmp_path, minutes=7, breakout=True)
    assert "THE CHART'S BARS DON'T WORK" in printed[0] and "step 1, bars used: 0" in funnel(printed)[2]


def test_a_runtime_error_is_printed_and_counted(sim, tmp_path):
    """An exception inside OnBarUpdate: printed with the bar and its stack, passed on (NinjaTrader stops the strategy
    and logs it), and the end-of-run funnel counts it."""
    bars = rth_minutes(40, 3)
    trades, _, _, printed = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, SimThrowAtBar=9000)
    err = [p for p in printed if p.startswith("MNQ RUNTIME ERROR at the bar ending")]
    assert len(err) == 1 and "test error on bar 9000" in err[0]
    assert any(p.startswith("LOG: Error on calling 'OnBarUpdate' method on bar 9000") for p in printed)
    num, blocked, _ = funnel(printed)
    assert num[1] == 9001 and "runtime errors 1" in [p for p in printed if p.strip().startswith("8 completed")][-1]
    assert any(b.startswith("blocked (error): runtime error: 1") for b in blocked)


# ── Simulated (history) and live (the account's fills) accounting, kept apart (docs/VERIFICATION.md)
def _day_with_a_loser_then_entries(sim, tmp_path, seeds=(3, 5, 9)):
    """Bars and a day on which, with no gate, a losing trade closes at bar x and the strategy enters again after x+3."""
    for seed in seeds:
        bars = rth_minutes(40, seed)
        trades, orders, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, EvalTarget=0)
        day = _day_of(bars)
        for t in trades:
            x = int(t[3])
            if float(t[6]) < 0 and day[x] != day[-1]:
                later = [int(o[0]) for o in orders
                         if o[1] == "Enter" and day[int(o[0])] == day[x] and int(o[0]) > x + 3]
                if later:
                    return bars, day, x, later
    raise AssertionError("no such day in these bars")


def test_live_gate_counts_live_fills_not_the_simulated_history(sim, tmp_path):
    """Going live just after a simulated loser (DailyMaxLosers 1): in a backtest that loser stops the day's later
    entries; live, the strategy's simulated history isn't the account's, so the live ledger starts empty and entries
    go on. The dashboard says which book it shows."""
    bars, day, x, later = _day_with_a_loser_then_entries(sim, tmp_path)
    _, hist, dash_h, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, EvalTarget=0, DailyMaxLosers=1)
    assert not [o for o in hist if o[1] == "Enter" and day[int(o[0])] == day[x] and int(o[0]) > x]
    _, live, dash_l, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, EvalTarget=0, DailyMaxLosers=1,
                                 SimRealtimeFrom=x + 1)
    assert [o for o in live if o[1] == "Enter" and day[int(o[0])] == day[x] and int(o[0]) > x]
    assert "Today (simulated fills, both setups)" in dash_h and "Today (live fills, both setups)" in dash_l


def test_live_day_survives_a_restart(sim, tmp_path):
    """Live from the day's open, a losing trade closes at bar x, the strategy is stopped two bars later and started
    again (live from x+3, the same data folder): the day's earlier live trades come back from the live-day file, so
    DailyMaxLosers 1 still stops the day's entries. Without the file, the same restart enters again."""
    bars, day, x, later = _day_with_a_loser_then_entries(sim, tmp_path)
    s = int(np.flatnonzero(day == day[x])[0])
    data = tmp_path / "userdata"
    first, _, _, _ = run_sim(sim, bars.iloc[:x + 2], tmp_path, minutes=1, breakout=True, EvalTarget=0,
                             DailyMaxLosers=1, SimRealtimeFrom=s, SimUserDataDir=data)
    assert any(int(t[3]) == x and float(t[6]) < 0 for t in first)
    kept = [t for t in first if s <= int(t[3]) and day[int(t[3])] == day[x]]
    _, orders, dash, printed = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, EvalTarget=0, DailyMaxLosers=1,
                                       SimRealtimeFrom=x + 3, SimUserDataDir=data)
    assert any(p.startswith(f"Live day: {len(kept)} live trade record(s) of {day[x]:%Y-%m-%d}") for p in printed)
    assert not [o for o in orders if o[1] == "Enter" and day[int(o[0])] == day[x] and int(o[0]) >= x + 3]
    _, fresh, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=True, EvalTarget=0, DailyMaxLosers=1,
                             SimRealtimeFrom=x + 3, SimUserDataDir=tmp_path / "empty")
    assert [o for o in fresh if o[1] == "Enter" and day[int(o[0])] == day[x] and int(o[0]) >= x + 3]
