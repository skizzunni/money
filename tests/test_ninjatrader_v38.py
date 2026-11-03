"""MnqNoiseV38.cs (v3.8, the 50K evaluation) against the Python reference, trade for trade, on the fixed MNQ sample.

The sample (tests/data, docs/PARITY.md): the user's MNQ bars 6/29 to 10/16/2026, 09:30-16:00 and the 16:00 bar, here
resampled to 5 and 30 minutes. The strategy's own code runs on the NinjaTrader simulator; the reference is
mnqbot.noise with v3.8's settings (pine/mnq_noise_momentum.pine's defaults) and NinjaTrader's execution
(nt_execution, round_prices, target_on_fill_bar). Every trade must agree: direction, entry and exit bar, entry and exit
price and P/L.
"""
from __future__ import annotations

import dataclasses
import gzip
import math
import subprocess

import pandas as pd
import pytest
from test_ninjatrader import DOTNET, ENV, sim  # noqa: F401
from test_noise import V21
from test_parity_mnq import SAMPLE

from mnqbot.data import resample
from mnqbot.noise import NoiseConfig, run

CFG = NoiseConfig(**{**V21, "qty": 1, "lookback": 14, "trail_from": "", "tv_path": False}, nt_execution=True,
                  round_prices=True, target_on_fill_bar=True)
# funded growth (docs/NINJATRADER_V38.md): v3.6's sizing at $900 a day and a $2,000 end-of-day trailing drawdown, and
# G6's 60-minute time stop
GROW = NoiseConfig(**{**V21, "qty": 1, "lookback": 14, "max_loss_per_trade": 187.5, "after_loss_ml_mult": 250 / 187.5,
                      "trail_dd": 2000.0, "trail_from": "", "profit_step": 1500.0, "size_up_to": 15,
                      "budget_actual": True, "time_stop": 60, "tv_path": False}, nt_execution=True, round_prices=True,
                   target_on_fill_bar=True)
GROW_ARGS = ["Mode=Funded growth"]  # the default; its settings are the tested ones above


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("minutes", [5, 30])
def test_v38_time_stop_agrees(sim, sample_1m, minutes, tmp_path):  # noqa: F811
    """G6's time stop (60 minutes, on in growth mode): the same trades in NinjaTrader's code and the Python model, and
    the time stop really fires; with it switched off, the trades change."""
    bars = resample(sample_1m, f"{minutes}min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    args = [DOTNET, str(sim), str(path), str(minutes), "Strategy=V38", *GROW_ARGS]
    r = subprocess.run(args, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
    py = run(bars, GROW, minutes=minutes).trades
    assert len(nt) == len(py) >= 20
    for a, t in zip(nt, py, strict=True):
        assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
        assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
        assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
    assert sum(t.reason == "Time stop" for t in py) >= 1
    off = run(bars, dataclasses.replace(GROW, time_stop=0), minutes=minutes).trades
    assert [(t.entry_bar, t.exit_bar) for t in off] != [(t.entry_bar, t.exit_bar) for t in py]


@pytest.fixture(scope="module")
def sample_1m():
    bars = pd.read_csv(gzip.open(SAMPLE, "rt"), header=None, names=["t", "open", "high", "low", "close"])
    bars.index = pd.to_datetime(bars.pop("t")).dt.tz_localize("America/New_York")
    return bars.assign(volume=0.0)


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("grow", [False, True])
@pytest.mark.parametrize("minutes", [5, 30])
def test_v38_ninjatrader_code_and_python_agree(sim, sample_1m, minutes, grow, tmp_path):  # noqa: F811
    assert CFG.max_loss_per_trade == 260.0 and CFG.daily_loss_limit == 900.0 and CFG.take_profit == 2.0
    cfg = GROW if grow else CFG
    bars = resample(sample_1m, f"{minutes}min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    args = [DOTNET, str(sim), str(path), str(minutes), "Strategy=V38", *(GROW_ARGS if grow else ["Mode=Evaluation"])]
    r = subprocess.run(args, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
    py = run(bars, cfg, minutes=minutes).trades
    assert len(nt) == len(py) and len(py) >= 20
    for a, t in zip(nt, py, strict=True):
        assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
        assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
        assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
        assert grow or t.pnl > -300.0  # the $260 cap holds, with fees and a tick of slippage
    if grow:
        assert max(t.qty for t in py) >= 2  # the contract steps were reached


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("minutes", [5, 30])
def test_v38_journal_logs_every_trade_and_day(sim, sample_1m, minutes, tmp_path):  # noqa: F811
    """The journal (Documents\\NinjaTrader 8\\MnqNoiseV38_backtest.csv): one line per closed trade of the account, the
    same P/L to the cent, every trade in exactly one day, and the days adding up to the total."""
    bars = resample(sample_1m, f"{minutes}min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    data = tmp_path / "nt8"
    data.mkdir()
    r = subprocess.run([DOTNET, str(sim), str(path), str(minutes), "Strategy=V38", f"SimUserDataDir={data}"],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    trades = [float(x.split(",")[7]) for x in r.stdout.splitlines() if x.startswith("T,")]
    j = pd.read_csv(data / "MnqNoiseV38_backtest.csv")
    logged, days = j[j.kind == "TRADE"], j[j.kind == "DAY"]
    assert len(logged) == len(trades) >= 20
    for a, b in zip(logged["P/L"], trades, strict=True):
        assert math.isclose(a, b, abs_tol=0.006)
    assert int(days["trades today"].sum()) == len(trades)
    assert math.isclose(days["day P/L"].sum(), sum(trades), abs_tol=0.01 * len(days))
    assert math.isclose(float(days["total P/L"].iloc[-1]), sum(trades), abs_tol=0.006)
    assert (data / "MnqNoiseV38_live_Sim101.csv").exists()  # the live journal is there, empty in a backtest
    assert len(pd.read_csv(data / "MnqNoiseV38_live_Sim101.csv")) == 0
    assert "Goal $50000" in [x for x in r.stdout.splitlines() if x.startswith("D,")][0]  # the dashboard was drawn


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("minutes", [5, 30])
def test_v38_gentle_start_agrees(sim, sample_1m, minutes, tmp_path):  # noqa: F811
    """G30's gentle start (off by default; on, no contract steps until the trailing floor has stopped): the same
    trades in NinjaTrader's code and the Python model, and the switch changes the sizes."""
    bars = resample(sample_1m, f"{minutes}min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    args = [DOTNET, str(sim), str(path), str(minutes), "Strategy=V38", *GROW_ARGS, "StepsAfterLock=True"]
    r = subprocess.run(args, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
    py = run(bars, dataclasses.replace(GROW, steps_after_lock=True), minutes=minutes).trades
    assert len(nt) == len(py) >= 20
    for a, t in zip(nt, py, strict=True):
        assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
        assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
        assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
    plain = run(bars, GROW, minutes=minutes).trades
    assert [t.qty for t in py] != [t.qty for t in plain], "the gentle start changes the sizes"


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_dashboard_shows_the_open_trade(sim, sample_1m, tmp_path):  # noqa: F811
    """The dashboard at every bar: the trades today, and while a trade is open its side, size, entry, stop, target,
    lock and time-stop countdown; "none" when flat. The trades are the same as without the dashboard history."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    base = [DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS]
    r = subprocess.run([*base, "DashHistory"], capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    plain = subprocess.run(base, capture_output=True, text=True, env=ENV)
    trades = [x for x in r.stdout.splitlines() if x.startswith("T,")]
    assert trades == [x for x in plain.stdout.splitlines() if x.startswith("T,")]
    dash = [x for x in r.stdout.splitlines() if x.startswith("DH,v38_dash,")]
    assert len(dash) > 1000 and all("Trades today: " in x for x in dash)
    open_ = [x for x in dash if "Open trade: LONG" in x or "Open trade: SHORT" in x]
    assert len(open_) >= 20 and sum("Open trade: none" in x for x in dash) >= 100
    assert all(" MNQ @ " in x and ", stop " in x and " min in, " in x for x in open_)
    assert any("time stop in " in x for x in open_), "the countdown while a trade is losing room to run"
    assert any("locked (can't lose)" in x for x in open_)


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_live_loss_guard(sim, sample_1m, tmp_path):  # noqa: F811
    """The live loss guard: with a tight guard ($150, to make it fire on the sample), live from the first month on,
    today's closed + open loss at the guard closes the position ("Loss guard") and no new entry is taken that day.
    Off (0), or in a backtest, the trades are exactly the model's."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    base = [DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS]

    def trades(*extra):
        r = subprocess.run([*base, *extra], capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        return [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")], r.stdout

    hist, _ = trades()
    off, _ = trades("SimRealtimeFrom=1000", "LossGuard=0")
    assert off == hist, "live with the guard off: the same trades"
    nt = [x.split(",")[1:] for x in subprocess.run(base, capture_output=True, text=True, env=ENV).stdout.splitlines()
          if x.startswith("T,")]
    py = run(bars, GROW, minutes=5).trades
    assert len(nt) == len(py), "a backtest (never live): the model's trades, guard or not"
    guarded, out = trades("SimRealtimeFrom=1000", "LossGuard=150")
    fired = [t for t in guarded if t[5] == "Loss guard"]
    assert fired, "the guard fired at least once on the sample"
    assert "P,MnqNoiseV38: loss guard at -" in out
    day = [ts.date() for ts in bars.index]
    for g in fired:  # no new entry later on the day the guard fired
        xb = int(g[3])
        assert not [t for t in guarded if int(t[1]) > xb and day[int(t[1])] == day[xb]], g


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_startup_checks(sim, sample_1m, tmp_path):  # noqa: F811
    """The startup check: the mode read whatever its case or spaces (a typo once ran Custom's settings unnoticed);
    a warning in the Output window and on the dashboard for an unknown mode, a non-MNQ instrument, RTH trading
    hours and a loss guard that is off; "Setup: OK" when all is right."""
    bars = resample(sample_1m, "30min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")

    def go(*extra):
        r = subprocess.run([DOTNET, str(sim), str(path), "30", "Strategy=V38", *extra], capture_output=True, text=True,
                           env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        lines = r.stdout.splitlines()
        return ([x for x in lines if x.startswith("T,")], [x for x in lines if "WARNING" in x and x.startswith("P,")],
                [x for x in lines if x.startswith("D,")][0])

    ok_trades, ok_warn, ok_dash = go("Mode=Funded growth")
    assert ok_warn == [] and "Setup: OK" in ok_dash
    loose, warn, _ = go("Mode=  funded GROWTH ")
    assert loose == ok_trades and warn == [], "the mode is read whatever its case and spaces"
    _, warn, dash = go("Mode=Funded")
    assert any("isn't Funded growth (50K, 100K, 150K, Apex 100K or Apex 150K), Evaluation or Custom" in x for x in warn)
    assert "SETUP WARNING (1)" in dash
    _, warn, _ = go("Mode=Funded growth", "SimInstrument=NQ 12-26")
    assert any("the bot was built and tested on MNQ" in x for x in warn)
    _, warn, _ = go("Mode=Funded growth", "SimTradingHours=CME US Index Futures RTH")
    assert any("use CME US Index Futures ETH" in x for x in warn)
    _, warn, _ = go("Mode=Funded growth", "LossGuard=0")
    assert any("no live backstop" in x for x in warn)
    _, warn, _ = go("Mode=Funded growth", "LossGuard=500")
    assert any("below the daily budget" in x for x in warn)


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_alerts(sim, sample_1m, tmp_path):  # noqa: F811
    """Alerts, live only: an entry ("BUY/SELL n MNQ ..."), every closed trade with its P/L, the time stop; setup
    warnings once on going live; with a sound unless SoundAlerts is off; none with AlertsOn off, and the trades the
    same either way."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")

    def go(*extra):
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS, *extra], capture_output=True,
                           text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        lines = r.stdout.splitlines()
        return [x for x in lines if x.startswith("T,")], [x.split(",", 4) for x in lines if x.startswith("A,")]

    live = 1000
    trades, alerts = go(f"SimRealtimeFrom={live}")
    assert alerts and all(int(a[1]) >= live for a in alerts), "alerts only once live"
    kinds = {a[2] for a in alerts}
    assert {"v38_entry", "v38_exit"} <= kinds
    assert any(a[4].startswith(("BUY ", "SELL ")) and " MNQ at market" in a[4] for a in alerts)
    assert any(a[4].startswith("Closed ") and "today" in a[4] for a in alerts)
    closed_live = sum(int(t.split(",")[4]) >= live for t in trades)  # trades whose exit bar is live
    assert abs(sum(a[2] == "v38_exit" for a in alerts) - closed_live) <= 1, "one alert per closed trade"
    assert all(a[3] == "sound" for a in alerts)
    quiet_trades, quiet = go(f"SimRealtimeFrom={live}", "AlertsOn=False")
    assert quiet == [] and quiet_trades == trades
    _, silent = go(f"SimRealtimeFrom={live}", "SoundAlerts=False")
    assert silent and all(a[3] == "silent" for a in silent)
    _, warned = go(f"SimRealtimeFrom={live}", "LossGuard=0")
    setup = [a for a in warned if a[2] == "v38_setup"]
    assert len(setup) == 1 and int(setup[0][1]) in (live - 1, live) and "no live backstop" in setup[0][4]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_progress_matches_the_journal(sim, sample_1m, tmp_path):  # noqa: F811
    """The dashboard's progress (this week, this month, the real win rate, the pace) agrees with the journal's own
    trades to the cent, and research/journal_report.py prints the weeks and the pace."""
    import re
    import sys

    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    data = tmp_path / "nt8"
    data.mkdir()
    r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS, f"SimUserDataDir={data}"],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    dash = [x for x in r.stdout.splitlines() if x.startswith("D,")][0]
    week, month = (float(v) for v in re.search(r"This week \$(-?[\d.]+), this month \$(-?[\d.]+)", dash).groups())
    n, pct = re.search(r"real fills: (\d+) trades, ([\d.]+)% winners", dash).groups()
    j = pd.read_csv(data / "MnqNoiseV38_backtest.csv")
    tr = j[j.kind == "TRADE"].copy()
    tr["exit"] = pd.to_datetime(tr["exit time"])
    last = tr["exit"].max()
    monday = (last - pd.Timedelta(days=last.weekday())).normalize()
    assert math.isclose(month, tr.loc[tr["exit"].dt.strftime("%Y-%m") == last.strftime("%Y-%m"), "P/L"].sum(),
                        abs_tol=0.02)
    assert math.isclose(week, tr.loc[tr["exit"] >= monday, "P/L"].sum(), abs_tol=0.02)
    assert int(n) == len(tr) and math.isclose(float(pct), 100 * (tr["P/L"] > 0).mean(), abs_tol=0.05)
    assert re.search(r"Pace: \$-?\d+ a month since \d{4}-\d{2}-\d{2}", dash)
    rep = subprocess.run([sys.executable, "research/journal_report.py", str(data / "MnqNoiseV38_backtest.csv")],
                         capture_output=True, text=True)
    assert rep.returncode == 0, rep.stderr[-2000:]
    assert "**Weeks**" in rep.stdout and "**Pace:**" in rep.stdout and "NO" not in rep.stdout.split("## Checks")[1]
    live = rep.stdout.split("## Live vs tested")[1].split("## Checks")[0]  # U11
    wr = 100 * (tr["P/L"] > 0).mean()
    assert f"| win % | {round(wr, 1)} | 61.2 to 62.2 |" in live, live
    assert "in line with the tests" in live or "WARNING" in live or "too few" in live


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_fill_quality(sim, sample_1m, tmp_path):  # noqa: F811
    """Fill quality: each trade's entry slip (ticks paid past the close the order was sent at) and stop slip (past the
    resting stop) in the journal match the simulator's fills exactly; the dashboard averages them; at 3 ticks of
    slippage it warns to consider Gentle start. The trades themselves are unchanged."""
    import re

    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    closes = bars["close"].to_numpy()

    def go(slip):
        data = tmp_path / f"nt8_{slip}"
        data.mkdir()
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS, f"SimUserDataDir={data}",
                            f"SimSlippageTicks={slip}"], capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        lines = r.stdout.splitlines()
        trades = [x.split(",")[1:] for x in lines if x.startswith("T,")]
        return trades, pd.read_csv(data / "MnqNoiseV38_backtest.csv"), [x for x in lines if x.startswith("D,")][0]

    trades, j, dash = go(1)
    tr = j[j.kind == "TRADE"].reset_index(drop=True)
    assert len(tr) == len(trades)
    for (d, eb, entry, *_), slip in zip(trades, tr["entry slip ticks"], strict=True):
        want = int(d) * (float(entry) - closes[int(eb) - 1]) / 0.25
        assert math.isclose(slip, want, abs_tol=1e-6), (eb, slip, want)
    stops = tr[tr["exit kind"] == "Stop loss"]["exit slip ticks"].dropna()
    assert len(stops) >= 10 and (stops >= 1 - 1e-9).all() and math.isclose(stops.median(), 1.0)
    assert tr[tr["exit kind"] == "Profit target"]["exit slip ticks"].isna().all(), "a limit has no slippage"
    m = re.search(r"Fills vs plan: entries ([+-]?[\d.]+) ticks \((\d+)\)", dash)
    assert m and int(m.group(2)) == len(tr)
    assert math.isclose(float(m.group(1)), tr["entry slip ticks"].mean(), abs_tol=0.05)
    assert "consider Gentle start" not in dash
    _, j3, dash3 = go(3)
    stops3 = j3[(j3.kind == "TRADE") & (j3["exit kind"] == "Stop loss")]["exit slip ticks"].dropna()
    assert (stops3 >= 3 - 1e-9).all() and "consider Gentle start" in dash3
    plain = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS], capture_output=True,
                           text=True, env=ENV)
    assert [x.split(",")[1:] for x in plain.stdout.splitlines() if x.startswith("T,")] == trades


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_day_summary(sim, sample_1m, tmp_path):  # noqa: F811
    """The day's summary: live, once a session, after its 16:00 exit, with the day's P/L and trades exactly as the
    journal's DAY line has them; and the DAY lines carry the room above the floor and the next day's contracts."""
    import re

    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    data = tmp_path / "nt8"
    data.mkdir()
    live = 1000
    r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS, f"SimUserDataDir={data}",
                        f"SimRealtimeFrom={live}"], capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    days = [x.split(",", 4)[4] for x in r.stdout.splitlines() if x.startswith("A,") and ",v38_day," in x]
    j = pd.read_csv(data / "MnqNoiseV38_backtest.csv")
    dl = j[j.kind == "DAY"].set_index("entry time")  # a DAY line's date sits in the "entry time" column
    assert dl["room above floor"].notna().all() and dl["next contracts"].notna().all()
    live_days = sorted({ts.strftime("%Y-%m-%d") for ts in bars.index[live:] if ts.hour * 60 + ts.minute >= 960})
    assert len(days) == len(live_days) >= 20
    for msg in days:
        d, sign, amt, n = re.match(r"Day done (\S+): ([+-])\$([\d.]+) in (\d+) trades", msg).groups()
        assert math.isclose(float(sign + amt), float(dl.loc[d, "day P/L"]), abs_tol=0.006), msg
        assert int(n) == int(dl.loc[d, "trades today"]), msg


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_milestones(sim, sample_1m, tmp_path):  # noqa: F811
    """U8: live, at a day's close, one alert for the highest new multiple of the milestone step of profit since the
    start (none for levels passed before going live), and one when the goal is reached; the same trades on or off."""
    import re

    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")

    def go(*args):
        data = tmp_path / f"nt8_{len(list(tmp_path.iterdir()))}"
        data.mkdir()
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS, f"SimUserDataDir={data}",
                            "SimRealtimeFrom=1000", *args], capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        alerts = [x.split(",", 4)[4] for x in r.stdout.splitlines() if x.startswith("A,")]
        trades = [x for x in r.stdout.splitlines() if x.startswith("T,")]
        return alerts, trades, pd.read_csv(data / "MnqNoiseV38_backtest.csv")

    off, t_off, _ = go("MilestoneStep=0", "Goal=0")
    assert not [a for a in off if "Milestone" in a or "GOAL" in a]
    step = 250
    j = None
    alerts, t_on, j = go(f"MilestoneStep={step}", "Goal=0")
    assert t_on == t_off, "milestones never change the trades"
    days = j[j.kind == "DAY"]
    totals = days["total P/L"].astype(float).to_numpy()
    ms = [int(re.search(r"Milestone: \+\$(\d+) since the start", a).group(1)) for a in alerts if "Milestone" in a]
    assert len(ms) >= 2, alerts[-5:]
    assert ms == sorted(set(ms)) and all(m % step == 0 for m in ms), "each level once, rising, on the step"
    assert ms[-1] == int(max(totals.max(), 0) // step) * step, "the highest level reached is the last alerted"
    assert ms[0] > int(max(totals[0], 0) // step) * step, "nothing for the levels before going live"
    goal = ms[0] + step // 2  # between two levels: the goal alert must still come, once
    alerts, _, j = go(f"MilestoneStep={step}", f"Goal={goal}")
    g = [a for a in alerts if a.startswith("GOAL REACHED")]
    assert len(g) == 1, g
    assert float(re.search(r"\+\$(\d+)", g[0]).group(1)) >= goal


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize(("mode", "daily", "trail"), [("Funded growth 100K", 1800.0, 3000.0),
                                                      ("Funded growth 150K", 2700.0, 4500.0),
                                                      ("Funded growth Apex 100K", 1350.0, 3000.0),
                                                      ("Funded growth Apex 150K", 1800.0, 4000.0)])
@pytest.mark.parametrize("minutes", [5, 30])
def test_v38_bigger_accounts_agree(sim, sample_1m, minutes, mode, daily, trail, tmp_path):  # noqa: F811
    """G40's modes: a 100K / 150K account at the 50K's size, its limits as cushion. NinjaTrader's code agrees with the
    Python model trade for trade, and the mode applies its limits (the daily budget and the loss guard)."""
    bars = resample(sample_1m, f"{minutes}min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    r = subprocess.run([DOTNET, str(sim), str(path), str(minutes), "Strategy=V38", f"Mode={mode}"],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    assert not [x for x in r.stdout.splitlines() if x.startswith("P,") and "WARNING" in x]
    nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
    py = run(bars, dataclasses.replace(GROW, daily_loss_limit=daily, trail_dd=trail), minutes=minutes).trades
    assert len(nt) == len(py) >= 20
    for a, t in zip(nt, py, strict=True):
        assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
        assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
        assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
    printed = "\n".join(x for x in r.stdout.splitlines() if x.startswith(("P,", "D,")))
    assert f"${daily:.0f} a day" in printed, "the startup line shows the mode's daily budget"
    assert f"flat at -${daily / 1800 * 1900:.0f} today" in printed, "the loss guard follows the account"
