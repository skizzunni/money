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
from pathlib import Path

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
                      "trail_dd": 2000.0, "trail_from": "", "profit_step": 1500.0, "size_up_to": 60,  # G247: the firm's 60 (G212: 75)
                      "budget_actual": True, "time_stop": 45, "tv_path": False, "gap_go": True, "gap_go_max_qty": 1,
                      "gap_go_locked_qty": 10, "trail_cap": 0.0,
                      # G79: More trading days and the 2-point sizing allowance
                      "gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.6, "fill_after_lock": True,
                      "fill_min_room": 2750.0, "size_slip_pts": 4.0, "fill_qty2_room": 5000.0,  # G243: 4 points
                      "giveback_brake": 0.45,  # G243 (G99c: 0.5)
                      # G191: no gap-slot trade while the giveback brake is on
                      "gap_skip_braked": True,
                      # G204: at most three losers a day, a $750 day budget until the floor has stopped, a 45-minute
                      # time stop, the top 70% of the day's range, the gap trade from 0.6x
                      "max_losers": 3, "early_daily_loss": 750.0, "range_pos_min": 0.7, "gap_go_k": 0.65,  # G242: 0.65
                      # G241: the trend over 45 sessions, the fill-ins from $2,750, 2 MNQ from $5,000
                      "trend_n": 45,
                      # G242: the gap trade's stop to break-even once a bar closes 1.5x its risk in profit
                      "gap_go_be": 1.5,
                      # G119: once the floor has stopped, the trade after a loser risks $187.50 like the others
                      "after_loss_ml_locked": 1.0,
                      # G125: no entries at 13:00 and 14:30 until the floor has stopped
                      "skip_checks": "780,870", "skip_checks_early": True,
                      # G142: a contract per $750 above $10,000 of profit
                      "profit_step_fast": 650.0,
                      # G210: $700 steps above $8,000, and 3-MNQ fill-ins from $9,000 above the floor
                      "profit_step_fast_from": 9000.0, "fill_qty3_room": 8000.0,  # G243: from 9,000; G212: 650 / 8,000 / 2 MNQ from 4,000 / 75
                      # G165 / G167 / G168: the after-loss max loss as every trade's ($187.50) on 5-minute bars
                      "after_loss_ml_mult5": 1.0,
                      # G422 (U58): every check, no range filter, no loser limit, entry lines at 0.8 on a calm stretch
                      "max_losers": 0, "range_pos_min": 0.0, "skip_checks": "", "entry_k_regime": 0.8},
                   nt_execution=True, round_prices=True, target_on_fill_bar=True)
# the bigger accounts' modes keep the settings from before G204
PRE_G204 = {"max_losers": 0, "early_daily_loss": 0.0, "range_pos_min": 0.65, "gap_go_k": 0.5, "time_stop": 60, "trend_n": 50,
            "gap_go_be": 0.0}
PRE_G204_ARGS = ["MaxLosersPerDay=0", "EarlyDayBudget=0", "RangePos=0.65", "GapTrigger=0.5", "TimeStop=60", "TrendSessions=50", "GapBreakEven=0"]
# the bigger accounts' modes also keep G125's skipped checks and no calm entry width (U58 is the 50K's)
BIG = {**PRE_G204, "skip_checks": "780,870", "entry_k_regime": 0.0}
GROW_ARGS = ["Mode=Funded growth"]


def grow_cfg(minutes: int) -> NoiseConfig:
    """Funded growth on this chart: U58 (G422) on 5-minute bars; the 30-minute chart keeps U48's G204 / G125 settings."""
    if minutes == 5:
        return GROW
    return dataclasses.replace(GROW, max_losers=3, range_pos_min=0.7, skip_checks="780,870", entry_k_regime=0.0)  # the default; its settings are the tested ones above
# G72's fill-in trades off (NinjaTrader's More trading days needs gap and go on)
NO_FILL = {"gap_go_small_k": -1.0, "trend_small": False, "gap_go_drive_k": 0.0, "fill_after_lock": False,
           "fill_min_room": 0.0}


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
    py = run(bars, grow_cfg(minutes), minutes=minutes).trades
    assert len(nt) == len(py) >= 20
    for a, t in zip(nt, py, strict=True):
        assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
        assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
        assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
    assert sum(t.reason == "Time stop" for t in py) >= 1
    off = run(bars, dataclasses.replace(grow_cfg(minutes), time_stop=0), minutes=minutes).trades
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
    cfg = grow_cfg(minutes) if grow else CFG
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
    if grow and minutes == 30:
        assert max(t.qty for t in py) >= 2  # the contract steps were reached
    # (on 5-minute bars U46's sample stays at 1 MNQ; the steps are tested with ProfitStep=300 and by test_v38_fill_qty3)


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
    py = run(bars, dataclasses.replace(grow_cfg(minutes), steps_after_lock=True), minutes=minutes).trades
    assert len(nt) == len(py) >= 20
    for a, t in zip(nt, py, strict=True):
        assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
        assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
        assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
    plain = run(bars, grow_cfg(minutes), minutes=minutes).trades
    if max(t.qty for t in plain) >= 2:  # (U46's 5-minute sample stays at 1 MNQ, so there is nothing to hold back)
        assert [t.qty for t in py] != [t.qty for t in plain], "the gentle start changes the sizes"
    else:
        assert minutes == 5


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
def test_v38_today_line(sim, sample_1m, tmp_path):  # noqa: F811
    """U15: the dashboard's "Today" line at every bar. No entry is ever taken against it: a long only when it says
    "longs yes", a short only when "shorts yes" (or after 14:00 on a Fed day); none on a "no entries" day. The next
    entry check it names is the next half hour from 10:00 to 15:00. The trades are unchanged."""
    import re

    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    base = [DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS]
    r = subprocess.run([*base, "DashHistory"], capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    today = {}
    for x in r.stdout.splitlines():
        if x.startswith("DH,v38_dash,"):
            _, _, b, text = x.split(",", 3)
            m = re.search(r"Today: (.*?); (next entry check [^|]*|no more entry checks today[^|]*)\s*\|", text)
            assert m, text
            today[int(b)] = (m.group(1), m.group(2).strip())
    names = [x.split(",")[1] for x in r.stdout.splitlines() if x.startswith("TN,")]
    trades = [x.split(",") for x, n in zip([y for y in r.stdout.splitlines() if y.startswith("T,")], names, strict=True)
              if not n.startswith("Gap")]  # gap and go (G60) is outside the day's filters, by design
    assert len(trades) >= 20
    for t in trades:
        d, signal = int(t[1]), int(t[2]) - 1  # the entry is sent at the close of the bar before its fill
        rule = today[signal][0]
        hhmm = bars.index[signal] + pd.Timedelta(minutes=5)
        if d > 0:
            assert "longs yes" in rule, (t, rule)
        else:
            assert "shorts yes" in rule or ("shorts after 14:00" in rule and hhmm.hour >= 14), (t, rule)
    rules = {v[0] for v in today.values()}
    assert any("shorts no (uptrend" in x for x in rules) and any("longs yes; shorts yes" in x for x in rules), rules
    # U58 (G422): every check takes entries, so the line names no skipped checks (U33's note is for EarlyNoEntryChecks)
    assert not any("no entries at" in x for x in rules), rules
    for b, (_, nxt) in today.items():
        end = bars.index[b] + pd.Timedelta(minutes=5)
        m = end.hour * 60 + end.minute
        if 600 <= m < 900:
            n = (m // 30 + 1) * 30
            assert nxt == f"next entry check {n // 60}:{n % 60:02d} (in {n - m} min)", (end, nxt)
        elif 900 <= m < 960:
            assert nxt.startswith("no more entry checks today"), (end, nxt)
    plain = subprocess.run(base, capture_output=True, text=True, env=ENV)
    assert [x for x in plain.stdout.splitlines() if x.startswith("T,")] == [x for x in r.stdout.splitlines()
                                                                             if x.startswith("T,")]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_data_check(sim, sample_1m, tmp_path):  # noqa: F811
    """U17: the data check. On the full sample the dashboard says "Data check: n sessions, all complete" and nothing is
    warned. With bars missing in most sessions (a thin contract's history), the dashboard and the Output window warn,
    and name the fix; with too little data before the start date, it says so."""
    bars = resample(sample_1m, "5min")

    def go(b, *args):
        path = tmp_path / f"bars_{len(list(tmp_path.iterdir()))}.csv"
        with path.open("w") as f:
            for t, r in zip(b.index, b.itertuples(), strict=True):
                f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS, *args],
                           capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        dash = [x for x in r.stdout.splitlines() if x.startswith("D,")][0]
        warn = [x for x in r.stdout.splitlines() if x.startswith("P,") and "WARNING" in x]
        return dash, warn

    dash, warn = go(bars)
    assert "Data check: " in dash and "all complete" in dash and not warn, (dash, warn)
    thin = bars[(bars.index.minute % 15 != 5) | (bars.index.hour >= 16)]  # every third bar gone
    dash, warn = go(thin)
    assert "DATA WARNING: the price data has bars missing in " in dash
    assert any("MNQ ##-##" in x for x in warn), warn
    first = bars.index[0].strftime("%Y-%m-%d")
    later = (bars.index[0] + pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    dash, warn = go(bars, f"TrailFrom={later}")
    assert "sessions of data before the start date " + later in dash and "the filters need 50" in dash, dash
    assert first < later
    dash, _ = go(bars, "TrailFrom=2020-01-02")  # all the data is after the start date
    assert f"the data starts on {first}, after the start date 2020-01-02" in dash, dash


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_gap_go(sim, sample_1m, tmp_path):  # noqa: F811
    """G60: gap and go (on in Funded growth, 5-minute bars). NinjaTrader's code and the Python model agree trade for
    trade, gap trades included; each is 1 contract, opened at 09:35 and closed by its stop or at 09:55. With the switch
    off, no gap trades, and the trades are the model's without it."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")

    def go(*args):
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS, *args], capture_output=True,
                           text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        lines = r.stdout.splitlines()
        return [x.split(",")[1:] for x in lines if x.startswith("T,")], [x.split(",")[1:] for x in lines if
                                                                          x.startswith("TN,")]

    for on in (True, False):
        nt, names = go(f"GapGo={on}")
        py = run(bars, dataclasses.replace(GROW, gap_go=on, **({} if on else NO_FILL)), minutes=5).trades
        assert len(nt) == len(py) >= 20
        for a, t in zip(nt, py, strict=True):
            assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
            assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
            assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
        gaps = [t for t in py if t.reason.startswith("Gap")]
        nt_gaps = [n for n in names if n[0].startswith("Gap")]
        if on:
            assert len(gaps) >= 3 and len(nt_gaps) == len(gaps)
            for t in gaps:
                assert t.qty <= 10 and t.entry_time.strftime("%H:%M") == "09:35"
                assert t.reason == "Gap stop" or t.exit_time.strftime("%H:%M") == "09:55"
        else:
            assert not gaps and not nt_gaps


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
    assert alerts and all(int(a[1]) >= live - (a[2] == "v38_setup") for a in alerts), "alerts only once live"
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
    setup = [a for a in warned if a[2] == "v38_setup" and "no live backstop" in a[4]]
    assert len(setup) == 1 and int(setup[0][1]) in (live - 1, live)
    # U16: live with the trailing drawdown counted from the chart's first bar (TrailFrom blank), one more warning;
    # with the account's first day set, none
    blank = [a for a in warned if a[2] == "v38_setup" and "is blank" in a[4]]
    assert len(blank) == 1 and "the account's first trading day" in blank[0][4]
    _, dated = go(f"SimRealtimeFrom={live}", "TrailFrom=2026-08-03")
    assert not [a for a in dated if a[2] == "v38_setup"]


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
    slippage it warns to check the connection. The trades themselves are unchanged."""
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
    assert math.isclose(float(m.group(1)), tr["entry slip ticks"].mean(), abs_tol=0.0501)  # shown to 0.1
    assert "worse than 2 ticks" not in dash
    _, j3, dash3 = go(3)
    stops3 = j3[(j3.kind == "TRADE") & (j3["exit kind"] == "Stop loss")]["exit slip ticks"].dropna()
    assert (stops3 >= 3 - 1e-9).all() and "worse than 2 ticks" in dash3
    # G158: live, one alert once 20 trades average more than 2 ticks worse than planned (none at 1 tick)
    for slip, want in ((3, 1), (1, 0)):
        rr = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS, "SimRealtimeFrom=1",
                             f"SimSlippageTicks={slip}"], capture_output=True, text=True, env=ENV)
        assert rr.returncode == 0, rr.stderr[-2000:]
        alerts = [x for x in rr.stdout.splitlines() if x.startswith("A,") and "Fills are" in x]
        assert len(alerts) == want, (slip, alerts[:3])
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
    # U14: on each live Friday, the week's summary: its P/L and trades are the sum of that week's journal days
    weeks = [x.split(",", 4)[4] for x in r.stdout.splitlines() if x.startswith("A,") and ",v38_week," in x]
    fridays = [d for d in live_days if pd.Timestamp(d).dayofweek == 4]
    assert len(weeks) == len(fridays) >= 3
    dd = dl.copy()
    dd.index = pd.to_datetime(dd.index)
    for msg, fri in zip(weeks, fridays, strict=True):
        mon, sign, amt, n, w = re.match(r"Week done \(from (\S+)\): ([+-])\$([\d.]+) in (\d+) trades \((\d+) winners\)",
                                        msg).groups()
        assert pd.Timestamp(mon) == pd.Timestamp(fri) - pd.Timedelta(days=4), msg
        wk = dd[(dd.index >= pd.Timestamp(mon)) & (dd.index <= pd.Timestamp(fri))]
        assert math.isclose(float(sign + amt), wk["day P/L"].astype(float).sum(), abs_tol=0.02), msg
        assert int(n) == int(wk["trades today"].sum()), msg


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
def test_v38_win_rate_check(sim, sample_1m, tmp_path):  # noqa: F811
    """U13: the dashboard's win-rate check equals research/journal_report.py's binomial tail for the journal's trades;
    in line at the tested 49.3% (U46), a warning (and one live alert) when the tested rate is set far above the real one."""
    import re
    import sys

    sys.path.insert(0, "research")
    from journal_report import below_tested

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
        dash = [x for x in r.stdout.splitlines() if x.startswith("D,")][0]
        alerts = [x for x in r.stdout.splitlines() if x.startswith("A,") and ",v38_winrate," in x]
        tr = pd.read_csv(data / "MnqNoiseV38_backtest.csv").query("kind == 'TRADE'")
        return dash, alerts, tr, [x for x in r.stdout.splitlines() if x.startswith("T,")]

    dash, alerts, tr, t1 = go()
    n, wins = len(tr), int((tr["P/L"] > 0).sum())
    assert n >= 30 and not alerts
    assert f"Win rate in line with the tests: {100 * wins / n:.1f}% in {n} trades (tested 49.3%)" in dash, dash
    dash, alerts, _, t2 = go("TestedWinRate=90")
    m = re.search(r"WIN RATE WARNING: ([\d.]+)% in (\d+) trades, below the tested 90.0% \(([\d.]+)% chance\)", dash)
    assert m and int(m.group(2)) == n, dash
    assert float(m.group(3)) == pytest.approx(100 * below_tested(wins, n, 0.9), abs=0.05)
    assert len(alerts) == 1 and t2 == t1, "one alert, live; the trades unchanged"
    dash, alerts, _, _ = go("TestedWinRate=0")
    assert "Win rate" not in dash and not alerts


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
    # G204's settings are the 50K's only
    py = run(bars, dataclasses.replace(GROW, daily_loss_limit=daily, trail_dd=trail, **BIG), minutes=minutes).trades
    assert len(nt) == len(py) >= 20
    for a, t in zip(nt, py, strict=True):
        assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
        assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
        assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
    printed = "\n".join(x for x in r.stdout.splitlines() if x.startswith(("P,", "D,")))
    assert f"${daily:.0f} a day" in printed, "the startup line shows the mode's daily budget"
    assert f"flat at -${daily / 1800 * 1900:.0f} today" in printed, "the loss guard follows the account"


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_gap_go_locked(sim, sample_1m, tmp_path):  # noqa: F811
    """G67b: once the trailing floor has stopped at the start, a gap trade takes up to GapGoLocked contracts (3 in
    Funded growth), 1 before. A $600 trailing drawdown (Custom mode) makes the floor stop within the sample. NinjaTrader's code and
    the model agree trade for trade at 3 and at 0 (1 contract always), and only the locked account's gap trades grow."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    sizes = {}
    for lq in (3, 0):
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", "Mode=Custom", "TrailDD=600", "EarlyNoEntryChecks=", *PRE_G204_ARGS,
                            f"GapGoLocked={lq}"], capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
        py = run(bars, dataclasses.replace(GROW, trail_dd=600.0, skip_checks="", **PRE_G204, gap_go_locked_qty=lq), minutes=5).trades
        assert len(nt) == len(py) >= 20
        for a, t in zip(nt, py, strict=True):
            assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
            assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
            assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
        sizes[lq] = [t.qty for t in py if t.reason.startswith("Gap")]
    assert max(sizes[0]) == 1 and max(sizes[3]) > 1 and max(sizes[3]) <= 3


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_more_days(sim, sample_1m, tmp_path):  # noqa: F811
    """G72's "More trading days" switch: 1-MNQ fill-in trades (small gaps, opening drives, uptrend shorts) once the
    floor has stopped and while the account is MoreDaysCushion above it. With a $600 trailing drawdown and a $100
    cushion (Custom mode) they fire within the sample; NinjaTrader's code and the model agree trade for trade, the
    fill-ins are 1 contract, and the switch adds trading days. Off, the trades are exactly the default's."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    fill = {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.6, "fill_after_lock": True,
            "fill_min_room": 100.0}
    days = {}
    for on in (True, False):
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", "Mode=Custom", "TrailDD=600", "EarlyNoEntryChecks=", *PRE_G204_ARGS,
                            f"MoreDays={on}", "MoreDaysCushion=100"], capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
        py = run(bars, dataclasses.replace(GROW, trail_dd=600.0, skip_checks="", **PRE_G204, **(fill if on else NO_FILL)), minutes=5).trades
        assert len(nt) == len(py) >= 20
        for a, t in zip(nt, py, strict=True):
            assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
            assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
            assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
        days[on] = len({t.entry_time.date() for t in py})
    assert days[True] > days[False]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_giveback_brake(sim, sample_1m, tmp_path):  # noqa: F811
    """G99's giveback brake: once the floor has stopped, while the profit is under GivebackBrake x the best end-of-day
    profit, every trade takes 1 MNQ. A $600 trailing drawdown (Custom mode) stops the floor within the sample, and a
    0.9 brake makes it act; NinjaTrader's code and the model agree trade for trade with it on and off, and on, the
    trades are never bigger than off's."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    qtys = {}
    for gb in (0.9, 0.0):
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", "Mode=Custom", "TrailDD=600", "EarlyNoEntryChecks=", *PRE_G204_ARGS,
                            f"GivebackBrake={gb}"], capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
        py = run(bars, dataclasses.replace(GROW, trail_dd=600.0, skip_checks="", **PRE_G204, giveback_brake=gb), minutes=5).trades
        assert len(nt) == len(py) >= 20
        for a, t in zip(nt, py, strict=True):
            assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
            assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
            assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
        qtys[gb] = sum(t.qty for t in py)
    assert qtys[0.9] < qtys[0.0]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_gap_skip_braked(sim, sample_1m, tmp_path):  # noqa: F811
    """G191: no gap-slot trade while the giveback brake is on. A $600 trailing drawdown (Custom mode) and a 0.9 brake
    make it act within the sample; NinjaTrader's code and the model agree trade for trade with it on and off, and on,
    there are fewer gap trades."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    gaps = {}
    for on in (True, False):
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", "Mode=Custom", "TrailDD=600", "EarlyNoEntryChecks=", *PRE_G204_ARGS,
                            "GivebackBrake=0.9", f"GapSkipBraked={on}"], capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
        py = run(bars, dataclasses.replace(GROW, trail_dd=600.0, skip_checks="", **PRE_G204, giveback_brake=0.9,
                                           gap_skip_braked=on), minutes=5).trades
        assert len(nt) == len(py) >= 20
        for a, t in zip(nt, py, strict=True):
            assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
            assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
            assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
        gaps[on] = sum(t.reason.startswith("Gap") for t in py)
    assert gaps[True] < gaps[False]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize(("args", "kw", "changes"), [(["MaxLosersPerDay=1"], {"max_losers": 1}, True),
                                                     (["MaxLosersPerDay=0"], {"max_losers": 0}, False),
                                                     (["EarlyDayBudget=300"], {"early_daily_loss": 300.0}, True),
                                                     (["EarlyDayBudget=0"], {"early_daily_loss": 0.0}, False)])
def test_v38_g204_rules(sim, sample_1m, args, kw, changes, tmp_path):  # noqa: F811
    """G204: no new entry after MaxLosersPerDay losers in a day, and EarlyDayBudget as the day's budget until the floor
    has stopped. NinjaTrader's code and the model agree trade for trade at other values than the defaults (Custom
    mode, the 50K's limits); one loser a day and a $300 early budget change the trades (the sample never has three
    losers in a day)."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", "Mode=Custom", *args],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
    py = run(bars, dataclasses.replace(GROW, **kw), minutes=5).trades
    assert len(nt) == len(py) >= 20
    for a, t in zip(nt, py, strict=True):
        assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
        assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
        assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
    base = run(bars, GROW, minutes=5).trades
    assert ([(t.entry_bar, t.qty) for t in py] != [(t.entry_bar, t.qty) for t in base]) == changes


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_fill_qty3(sim, sample_1m, tmp_path):  # noqa: F811
    """G210: the fill-in trades at 3 MNQ while the account is MoreDaysQty3Room above the floor. A $600 trailing
    drawdown (Custom mode) stops the floor within the sample, a $100 cushion lets the fill-ins trade, and a $700
    threshold makes it act; NinjaTrader's code and
    the model agree trade for trade with it at $700 and off, and at $700 the trades take more contracts."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    qtys = {}
    for q3 in (700.0, 0.0):
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", "Mode=Custom", "TrailDD=600", "EarlyNoEntryChecks=",
                            *PRE_G204_ARGS, "MoreDaysCushion=100", f"MoreDaysQty3Room={q3}"], capture_output=True,
                           text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
        py = run(bars, dataclasses.replace(GROW, trail_dd=600.0, skip_checks="", **PRE_G204, fill_min_room=100.0,
                                           fill_qty3_room=q3),
                 minutes=5).trades
        assert len(nt) == len(py) >= 20
        for a, t in zip(nt, py, strict=True):
            assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
            assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
            assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
        qtys[q3] = sum(t.qty for t in py)
    assert qtys[700.0] > qtys[0.0]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("be", [0.5, 0.0])
def test_v38_gap_break_even(sim, sample_1m, be, tmp_path):  # noqa: F811
    """G242: once a bar closes with the gap trade up GapBreakEven x its risk, its stop goes to the entry plus a tick.
    NinjaTrader's code and the model agree trade for trade at 0.5 and off, and at 0.5 some gap trade ends at
    break-even (its exit a tick from its entry)."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", "Mode=Custom", f"GapBreakEven={be}"],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
    py = run(bars, dataclasses.replace(GROW, gap_go_be=be), minutes=5).trades
    assert len(nt) == len(py) >= 20
    for a, t in zip(nt, py, strict=True):
        assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
        assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
        assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
    be_exits = [t for t in py if t.reason == "Gap stop" and abs(t.exit - t.entry) < 0.75]
    assert bool(be_exits) == (be > 0)


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_after_loss_locked(sim, sample_1m, tmp_path):  # noqa: F811
    """G119: once the floor has stopped, the trade after a loser risks AfterLossLocked ($187.50) instead of $250. A $600
    trailing drawdown (Custom mode) stops the floor within the sample; NinjaTrader's code and the model agree trade for
    trade with it on and off, and it changes the trades."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    nets = {}
    for usd, k in ((187.5, 1.0), (0.0, 0.0)):
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", "Mode=Custom", "TrailDD=600", "EarlyNoEntryChecks=", *PRE_G204_ARGS,
                            "AfterLossMaxLoss=250", f"AfterLossLocked={usd}"], capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
        py = run(bars, dataclasses.replace(GROW, trail_dd=600.0, skip_checks="", **PRE_G204, after_loss_ml_mult5=250 / 187.5,
                                                 after_loss_ml_locked=k), minutes=5).trades
        assert len(nt) == len(py) >= 20
        for a, t in zip(nt, py, strict=True):
            assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
            assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
            assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
        nets[usd] = [(t.qty, round(t.pnl, 6)) for t in py]
    assert nets[187.5] != nets[0.0]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_early_no_entry_checks(sim, sample_1m, tmp_path):  # noqa: F811
    """G125: no entries at the 13:00 and 14:30 checks until the floor has stopped. NinjaTrader's code and the model agree
    trade for trade with it on (13:00,14:30) and off (blank, U58's default), it changes the trades, and before the floor stops no
    entry fills at 13:00 or 14:30."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    got = {}
    for arg, sk in (("EarlyNoEntryChecks=13:00,14:30", "780,870"), (None, "")):  # G422 (U58): every check by default
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS, *([arg] if arg else [])],
                           capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
        py = run(bars, dataclasses.replace(GROW, skip_checks=sk), minutes=5).trades
        assert len(nt) == len(py) >= 20
        for a, t in zip(nt, py, strict=True):
            assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
            assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
            assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
        got[sk] = py
    assert [(t.entry_bar, t.pnl) for t in got["780,870"]] != [(t.entry_bar, t.pnl) for t in got[""]]
    ny = [t.entry_time.tz_convert("America/New_York") for t in got["780,870"] if not t.reason.startswith("Gap")]
    assert not any((x.hour, x.minute) in ((13, 0), (14, 30)) for x in ny)  # the sample's floor never stops


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_fast_steps(sim, sample_1m, tmp_path):  # noqa: F811
    """G142: above FastStepsFrom of profit, a contract per FastSteps. The sample makes about $2,000, so the test scales
    it down (Custom mode: a contract per $300, faster per $100 above $600); NinjaTrader's code and the model agree
    trade for trade on and off, and it changes the trades."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    got = {}
    for fs in (100.0, 0.0):
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", "Mode=Custom", "ProfitStep=300",
                            "MaxContracts=50", f"FastSteps={fs}", "FastStepsFrom=600"], capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
        py = run(bars, dataclasses.replace(GROW, profit_step=300.0, profit_step_fast=fs, profit_step_fast_from=600.0),
                 minutes=5).trades
        assert len(nt) == len(py) >= 20
        for a, t in zip(nt, py, strict=True):
            assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
            assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
            assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
        got[fs] = [(t.qty, round(t.pnl, 6)) for t in py]
    assert got[100.0] != got[0.0]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_after_loss_same(sim, sample_1m, tmp_path):  # noqa: F811
    """G168: on the 5-minute chart the trade after a loser risks $187.50 like every trade, not $250, until the floor
    stops. Custom mode with AfterLossMaxLoss 187.5 (the default) and 250; NinjaTrader's code and the model agree trade
    for trade with each, and it changes the trades."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    got = {}
    for usd in (187.5, 250.0):
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", "Mode=Custom", f"AfterLossMaxLoss={usd}"],
                           capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
        py = run(bars, dataclasses.replace(GROW, after_loss_ml_mult5=usd / 187.5), minutes=5).trades
        assert len(nt) == len(py) >= 20
        for a, t in zip(nt, py, strict=True):
            assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
            assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
            assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
        got[usd] = [(t.qty, round(t.pnl, 6)) for t in py]
    assert got[187.5] != got[250.0]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_live_account_dashboard(sim, sample_1m, tmp_path):  # noqa: F811
    """Live, the dashboard tracks the account itself: its name, balance and net liquidation, today's realized and open
    P/L, the trades closed live, and the prop floor from the account's own balance (the higher of its starting balance
    and its balance at go-live, less the trailing drawdown, never above the start) with the room above it. With an
    account $1,850 below its start (net liquidation $48,150 on a 50K: $150 of room, less than one contract's risk), the dashboard flags the
    difference from the strategy's own count, and no trade risks more than the account's room: the trades shrink.
    With the room check off, live trades are the backtest's."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    base = [DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS]

    def go(*extra):
        r = subprocess.run([*base, *extra], capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        out = r.stdout.splitlines()
        return [x.split(",")[1:] for x in out if x.startswith("T,")], [x.split(",")[1:] for x in out
                                                                        if x.startswith("TN,")], r.stdout

    hist, hist_q, _ = go()
    live, live_q, out = go("SimRealtimeFrom=1000", "SimNetLiq=48150")
    dash = [x for x in out.splitlines() if x.startswith("D,")][0]
    assert "LIVE account Sim101: balance $" in dash and "net liq $48150.00" in dash
    assert "Today on the account: realized $" in dash and "Live trades since enabled: " in dash
    assert "Prop floor (from the account): $48000.00, room $150.00, profit $-1850.00" in dash
    assert "CHECK: the strategy counts $" in dash and "(trades are sized to the account's)" in dash
    late = [int(q[1]) for t, q in zip(live, live_q, strict=True) if int(t[1]) >= 1000]
    late_hist = [int(q[1]) for t, q in zip(hist, hist_q, strict=True) if int(t[1]) >= 1000]
    assert sum(late) < sum(late_hist), "live with $150 of room: fewer or smaller trades than the backtest's"
    off, _, _ = go("SimRealtimeFrom=1000", "SimNetLiq=48150", "SizeToAccountRoom=False")
    assert off == hist, "the room check off: live trades are the backtest's"


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_live_without_account_values(sim, sample_1m, tmp_path):  # noqa: F811
    """A connection that reports no account balance (net liquidation 0) must not stop the trading: the account-room
    check is not used, the trades are the backtest's, and the dashboard says it is waiting for the balance."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    base = [DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS]
    hist = [x for x in subprocess.run(base, capture_output=True, text=True, env=ENV).stdout.splitlines()
            if x.startswith("T,")]
    r = subprocess.run([*base, "SimRealtimeFrom=1000", "SimNetLiq=-1"], capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    live = [x for x in r.stdout.splitlines() if x.startswith("T,")]
    assert live == hist
    assert "Prop floor: waiting for the account's balance" in [x for x in r.stdout.splitlines() if x.startswith("D,")][0]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_sprint(sim, sample_1m, tmp_path):  # noqa: F811
    """G103's sprint: for the first 5 sessions from the start date, until +$3,000, every bot and gap trade takes
    SprintContracts (cut to the day's and the floor's room). From a start date mid-sample, NinjaTrader's code and the
    model agree trade for trade with it on (5) and off, and on, the sprint week's trades are bigger."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    days = sorted({ts.date() for ts in bars.index})
    start = str(days[len(days) // 3])
    qty = {}
    for sq in (5, 0):
        r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", *GROW_ARGS, f"TrailFrom={start}",
                            f"SprintContracts={sq}"], capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr[-2000:]
        nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
        py = run(bars, dataclasses.replace(GROW, trail_from=start, sprint_qty=sq), minutes=5).trades
        assert len(nt) == len(py) >= 20
        for a, t in zip(nt, py, strict=True):
            assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
            assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
            assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
        qty[sq] = [t.qty for t in py if str(t.entry_time.date()) >= start][:6]
    assert sum(qty[5]) > sum(qty[0]), qty


# G256 k317 with G269's +$5,000 sprint target: the two-week Test sprint (G253's k61 before)
SPRINT = {"daily_loss_limit": 2000.0, "early_daily_loss": 0.0, "max_losers": 3, "time_stop": 30, "range_pos_min": 0.7,
          "trend_n": 0, "big_day_k": 0.0, "calm_k": 0.7, "take_profit": 0.75, "lock_at": 0.2, "skip_checks": "", "entry_k_regime": 0.0,
          "sprint_qty": 4, "sprint_days": 10, "sprint_target": 5000.0, "sprint_gap_qty": 2, "gap_go_be": 0.0, "day_stop_profit": 1500.0, "lookback": 18,
          "entry_k": 0.7, "squeeze_min": 0.0, "last_entry_end": 930, "gap_go_k": 0.5, "stop_buffer": 0.24,
          "lock_plus": 2.5, "day_cap_exit": True,  # U55: G289's day cap
          # U56: G321's k30, the streak pause, the big-day rule, the day guard, 1.5x on the jobs-report days
          "streak_k": 4, "streak_skip": 2, "big_day_k": 1.5, "big_day_n": 10, "day_guard": 1200.0, "day_guard_grid": True,
          "news_dates": ",".join(pd.read_csv(Path(__file__).parent.parent / "research" / "nfp_dates.csv").date),
          "news_mult": 1.5,
          "day_lock_at": 800.0, "day_lock_keep": 300.0}  # U57: G329's day lock


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_test_sprint(sim, sample_1m, tmp_path):  # noqa: F811
    """G256 / U55: Mode "Test sprint" (k317: 4 MNQ for the first 10 sessions until +$5,000, a $1,500 day profit stop
    that also closes the open trade (G289), the
    noise area over 18 sessions, entries at 0.7x it, and the rest of k317's settings). NinjaTrader's code and the model
    agree trade for trade, and the sprint's 4 MNQ trades are there."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    ny = bars.index.tz_convert("America/New_York") if bars.index.tz is not None else bars.index
    start = sorted(set(ny.date))[20].strftime("%Y-%m-%d")  # past the 16 sessions the noise area needs
    r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", "Mode=Test sprint", f"TrailFrom={start}"],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
    py = run(bars, dataclasses.replace(GROW, **SPRINT, trail_from=start), minutes=5).trades
    assert len(nt) == len(py) >= 10
    for a, t in zip(nt, py, strict=True):
        assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
        assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
        assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
    assert any(t.qty == 4 for t in py)
    assert any(t.reason == "Day cap" for t in py)  # U55: the sample reaches G289's day cap, so the parity covers it
    assert any(t.reason == "Day lock" for t in py)  # U57: and G329's day lock


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_v38_test_sprint_day_guard(sim, sample_1m, tmp_path):  # noqa: F811
    """U56: G321's day guard. With a $300 guard (so it fires on the sample), NinjaTrader's code and the model agree trade
    for trade, and the guard's exits are there."""
    bars = resample(sample_1m, "5min")
    path = tmp_path / "bars.csv"
    with path.open("w") as f:
        for t, r in zip(bars.index, bars.itertuples(), strict=True):
            f.write(f"{t:%Y-%m-%d %H:%M},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    ny = bars.index.tz_convert("America/New_York") if bars.index.tz is not None else bars.index
    start = sorted(set(ny.date))[20].strftime("%Y-%m-%d")
    r = subprocess.run([DOTNET, str(sim), str(path), "5", "Strategy=V38", "Mode=Test sprint", f"TrailFrom={start}",
                        "SprintDayGuard=300"], capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    nt = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
    py = run(bars, dataclasses.replace(GROW, **{**SPRINT, "day_guard": 300.0}, trail_from=start), minutes=5).trades
    assert len(nt) == len(py) >= 10
    for a, t in zip(nt, py, strict=True):
        assert (int(a[0]), int(a[1]), int(a[3])) == (t.direction, t.entry_bar, t.exit_bar), (a, t)
        assert float(a[2]) == t.entry and float(a[4]) == t.exit, (a, t)
        assert math.isclose(float(a[6]), t.pnl, abs_tol=1e-6), (a, t)
    assert any(t.reason == "Day guard" for t in py)
