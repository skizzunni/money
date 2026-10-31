"""MnqNoiseV38.cs (v3.8, the 50K evaluation) against the Python reference, trade for trade, on the fixed MNQ sample.

The sample (tests/data, docs/PARITY.md): the user's MNQ bars 6/29 to 10/16/2026, 09:30-16:00 and the 16:00 bar, here
resampled to 5 and 30 minutes. The strategy's own code runs on the NinjaTrader simulator; the reference is
mnqbot.noise with v3.8's settings (pine/mnq_noise_momentum.pine's defaults) and NinjaTrader's execution
(nt_execution, round_prices, target_on_fill_bar). Every trade must agree: direction, entry and exit bar, entry and exit
price and P/L.
"""
from __future__ import annotations

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
# funded growth (docs/NINJATRADER_V38.md): v3.6's sizing at $900 a day and a $2,000 end-of-day trailing drawdown
GROW = NoiseConfig(**{**V21, "qty": 1, "lookback": 14, "max_loss_per_trade": 187.5, "after_loss_ml_mult": 250 / 187.5,
                      "trail_dd": 2000.0, "trail_from": "", "profit_step": 1500.0, "size_up_to": 15,
                      "budget_actual": True, "tv_path": False}, nt_execution=True, round_prices=True,
                   target_on_fill_bar=True)
GROW_ARGS = ["Mode=Funded growth"]  # the default; its settings are the tested ones above


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
