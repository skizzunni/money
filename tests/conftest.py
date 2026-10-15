"""Test helpers. Synthetic bars here exist only to exercise the machinery;
they say nothing about whether the strategy makes money."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnqbot.data import NY, annotate  # noqa: E402


def bars_from_rows(start: str, rows: list[tuple[float, float, float, float]], freq: str = "5min") -> pd.DataFrame:
    idx = pd.date_range(start=start, periods=len(rows), freq=freq, tz=NY)
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    df["volume"] = 100.0
    return annotate(df)


def synth_bars(sessions: int = 60, seed: int = 1, start: str = "2026-03-02") -> pd.DataFrame:
    """Random-walk 5m bars on CME hours (18:00 prior day to 16:55) for weekday sessions."""
    rng = np.random.default_rng(seed)
    price = 20_000.0
    frames = []
    for day in pd.bdate_range(start, periods=sessions):
        prev = day - pd.Timedelta(days=1)
        idx = pd.date_range(f"{prev.date()} 18:00", f"{day.date()} 16:55", freq="5min", tz=NY)
        hhmm = idx.hour * 100 + idx.minute
        rth = (hhmm >= 930) & (hhmm < 1600)
        rows = []
        for is_rth in rth:
            sigma = 3.0 if is_rth else 1.2
            steps = rng.standard_t(3, size=5) * sigma
            if is_rth and rng.random() < 0.05:  # occasional impulsive bar
                steps += rng.choice([-1, 1]) * sigma * 1.5
            path = price + np.cumsum(steps)
            o = price
            c = float(np.round(path[-1] * 4) / 4)
            hi = float(np.ceil(max(o, path.max()) * 4) / 4)
            lo = float(np.floor(min(o, path.min()) * 4) / 4)
            rows.append((o, hi, lo, c))
            price = c
        frames.append(pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx))
    df = pd.concat(frames)
    df["volume"] = 100.0
    return annotate(df)


@pytest.fixture(scope="session")
def random_bars() -> pd.DataFrame:
    return synth_bars()
