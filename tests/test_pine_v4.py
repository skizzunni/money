"""pine/mnq_noise_v4.pine (v4.0, docs/V4_SEARCH.md): its default settings are the Python model's V4 below, trade for
trade, on the user's MNQ bars (6/29-10/16/2026, 5-minute), and they trade indefinitely: no daily cap, no trailing
drawdown, no evaluation stop."""
from __future__ import annotations

import gzip
import re
from pathlib import Path

import pandas as pd
import pytest
from test_noise import V21
from test_parity_mnq import SAMPLE

from mnqbot.data import resample
from mnqbot.noise import NoiseConfig, run

ROOT = Path(__file__).resolve().parents[1]
V4_PINE = ROOT / "pine" / "mnq_noise_v4.pine"
# v4.0's defaults: v3.8's rules (V21) with the lock at 1.25 max losses, the stop 0.5 noise units past the line, a
# 45-minute time stop, the trend over 45 sessions, 5 MNQ at $250 each, no daily cap and no trailing drawdown
V4 = {**V21, "lookback": 14, "trail_from": "", "tv_path": False, "lock_at": 1.25, "stop_buffer": 0.5,
      "max_loss_per_trade": 1250.0, "time_stop": 45, "trend_n": 45, "qty": 5, "daily_loss_limit": 0.0, "trail_dd": 0.0}
V4.update(lock_at=0.75, max_losers=3)  # v4.1: the lock at 0.75, 3 losers a day
V4.update(qty=8, max_loss_per_trade=1200.0)  # v4.3: 8 MNQ at $150 each


def test_v4_defaults_in_the_script():
    src = V4_PINE.read_text()
    for pattern in (r'strategy\("MNQ Noise-Area Momentum v4\.3"', r'preset = input\.string\("Custom"',
                    r'fundQty  = input\.int\(8,', r'maxLossIn = input\.float\(1200,',
                    r'dailyLimitIn = input\.float\(0,',
                    r'trailDDIn = input\.float\(0,', r'trendN = input\.int\(45,', r'stopBuf = input\.float\(0\.5,',
                    r'lockAt = input\.float\(0\.75,',
                    r'maxLosers = input\.int\(3,', r'timeStopIn = input\.int\(45,', r'evalStart = input\.int\(0,'):
        assert re.search(pattern, src), pattern


@pytest.mark.slow
def test_v4_script_matches_the_model_on_the_users_bars():
    pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")
    from pine_interpreter import PineRuntime, load_pine

    one = pd.read_csv(gzip.open(SAMPLE, "rt"), header=None, names=["t", "open", "high", "low", "close"])
    one.index = pd.to_datetime(one.pop("t")).dt.tz_localize("America/New_York")
    bars = resample(one.assign(volume=0.0), "5min")
    py = run(bars, NoiseConfig(**V4, round_prices=True), minutes=5).trades
    rt = PineRuntime(load_pine(V4_PINE), bars, {}, timeframe_seconds=300)
    rt.run(lambda i, g: None)
    pine = rt.strategy.closed
    assert len(py) >= 25 and len(pine) == len(py)
    for a, t in zip(pine, py, strict=True):
        assert (a["entry_bar"], a["exit_bar"], a["dir"]) == (t.entry_bar, t.exit_bar, t.direction), (a, t)
        assert round(a["entry"], 6) == round(t.entry, 6) and round(a["exit"], 6) == round(t.exit, 6), (a, t)
        assert abs(a["pnl"] - t.pnl) < 1e-6, (a, t)
    assert max(t.qty for t in py) == 8 and any(t.reason == "Time stop" for t in py)
