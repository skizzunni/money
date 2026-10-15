"""Load OHLCV bars and tag each bar with its CME trading day and session.

Bars are labeled by their open time (TradingView, NinjaTrader and most
exports do this). Times are converted to America/New_York.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

NY = "America/New_York"
RTH_START, RTH_END = 930, 1600

_TIME_COLS = ("time", "datetime", "timestamp", "date_time", "date")


def load_csv(path: str | Path, tz: str = NY) -> pd.DataFrame:
    """Read a bar CSV (TradingView export, NinjaTrader export, yfinance dump, ...).

    Needs open/high/low/close columns plus either a single time column (unix
    seconds/ms or a datetime string) or separate date and time columns.
    Naive timestamps are assumed to be in ``tz``.
    """
    raw = pd.read_csv(path)
    raw.columns = [str(c).strip().lower().replace(" ", "_") for c in raw.columns]

    if "date" in raw.columns and "time" in raw.columns:
        stamps = raw["date"].astype(str) + " " + raw["time"].astype(str)
    else:
        col = next((c for c in _TIME_COLS if c in raw.columns), None)
        if col is None:
            raise ValueError(f"no time column found in {path}; columns are {list(raw.columns)}")
        stamps = raw[col]

    index = _parse_times(stamps, tz)
    missing = [c for c in ("open", "high", "low", "close") if c not in raw.columns]
    if missing:
        raise ValueError(f"missing columns {missing} in {path}")

    df = pd.DataFrame(
        {
            "open": raw["open"].astype(float).to_numpy(),
            "high": raw["high"].astype(float).to_numpy(),
            "low": raw["low"].astype(float).to_numpy(),
            "close": raw["close"].astype(float).to_numpy(),
            "volume": raw["volume"].astype(float).to_numpy() if "volume" in raw.columns else 0.0,
        },
        index=index,
    )
    df = df[~df.index.isna()]
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df.dropna(subset=["open", "high", "low", "close"])


def _parse_times(stamps: pd.Series, tz: str) -> pd.DatetimeIndex:
    if pd.api.types.is_numeric_dtype(stamps):
        unit = "ms" if float(stamps.iloc[0]) > 1e12 else "s"
        return pd.DatetimeIndex(pd.to_datetime(stamps, unit=unit, utc=True)).tz_convert(tz)
    stamps = stamps.astype(str)
    if pd.Timestamp(stamps.iloc[0]).tzinfo is not None:
        return pd.DatetimeIndex(pd.to_datetime(stamps, utc=True, format="ISO8601")).tz_convert(tz)
    naive = pd.DatetimeIndex(pd.to_datetime(stamps))
    return naive.tz_localize(tz, ambiguous="NaT", nonexistent="shift_forward")


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Aggregate to a coarser timeframe, e.g. ``resample(df_1m, "5min")``."""
    out = df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return out.dropna(subset=["open"])


def annotate(df: pd.DataFrame) -> pd.DataFrame:
    """Add trade_date, hhmm, is_rth and is_overnight columns.

    The CME trading day starts at 18:00 ET, so a bar at 18:00 on Sunday
    belongs to Monday's trading day.
    """
    if df.index.tz is None:
        raise ValueError("index must be timezone-aware; use load_csv or tz_localize first")
    idx = df.index.tz_convert(NY)
    out = df.copy()
    out.index = idx
    out["trade_date"] = (idx + pd.Timedelta(hours=6)).date
    hhmm = (idx.hour * 100 + idx.minute).to_numpy()
    out["hhmm"] = hhmm
    out["is_rth"] = (hhmm >= RTH_START) & (hhmm < RTH_END)
    out["is_overnight"] = (hhmm >= 1800) | (hhmm < RTH_START)
    return out


def fetch_yfinance(symbol: str = "MNQ=F", interval: str = "5m", period: str = "59d") -> pd.DataFrame:
    """Download recent bars from Yahoo Finance (needs ``pip install yfinance``).

    Yahoo keeps ~60 days of 5m bars and ~7 days of 1m bars, and its futures
    data has gaps. Good enough for a first look; use a TradingView or broker
    export for anything you'd bet money on.
    """
    try:
        import yfinance as yf
    except ImportError as e:  # pragma: no cover - optional dependency
        raise SystemExit("yfinance is not installed: pip install yfinance") from e

    raw = yf.download(symbol, interval=interval, period=period, progress=False, auto_adjust=False)
    if raw.empty:
        raise SystemExit(f"no data returned for {symbol} {interval} {period}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw.columns = [c.lower() for c in raw.columns]
    df = raw[["open", "high", "low", "close", "volume"]].astype(float)
    df.index = pd.DatetimeIndex(df.index).tz_convert(NY)
    return df


def rma(values: np.ndarray, length: int) -> np.ndarray:
    """Wilder's moving average, matching TradingView's ta.rma."""
    out = np.full(len(values), np.nan)
    if len(values) < length:
        return out
    out[length - 1] = np.mean(values[:length])
    alpha = 1.0 / length
    for i in range(length, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, length: int) -> np.ndarray:
    """Average true range, matching TradingView's ta.atr."""
    prev_close = np.concatenate(([np.nan], close[:-1]))
    tr = np.nanmax(np.vstack([high - low, np.abs(high - prev_close), np.abs(low - prev_close)]), axis=0)
    return rma(tr, length)
