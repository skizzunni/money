"""G87 (docs/NINJATRADER_V38.md): the shadow gate's closed days.

A shadow (paper) record of the bot's own signals at 1 contract: the account's settings with no contract steps, no
fill-ins, gap and go at 1 contract and no trailing floor. Its end-of-day equity is carried over every session. The gate
is closed on a session whose previous session's shadow equity closed below its average of the last n sessions.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # the repository root, for mnqbot
from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"
SHADOW = {"profit_step": 0.0, "qty": 1, "size_up_to": 1, "trail_dd": 0.0, "gap_go_locked_qty": 0, "gap_go_max_qty": 1,
          "gap_go_small_k": -1.0, "trend_small": False, "gap_go_drive_k": 0.0, "fill_after_lock": False,
          "fill_min_room": 0.0, "protect_room": 0.0, "protect_dates": ""}


def closed_days(bars: pd.DataFrame, cfg: NoiseConfig, minutes: int, n: int = 20) -> str:
    """The sessions (YYYY-MM-DD, comma separated) on which the shadow gate is closed."""
    shadow = dataclasses.replace(cfg, **SHADOW)
    tf = run(bars, shadow, minutes=minutes).trades_frame()
    t = bars.index.tz_convert(NY)
    sessions = sorted(set(t[(t.hour == 9) & (t.minute == 30)].date))
    daily = tf.groupby(tf.exit_time.dt.tz_convert(NY).dt.date).pnl.sum() if len(tf) else pd.Series(dtype=float)
    eq = daily.reindex(sessions, fill_value=0.0).cumsum()
    below = eq < eq.rolling(n, min_periods=n).mean()
    closed = below.shift(1, fill_value=False)  # decided at the previous session's close
    return ",".join(d.strftime("%Y-%m-%d") for d, c in closed.items() if c)
