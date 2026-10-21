"""The measurements behind docs/NET_VS_DRAWDOWN.md, on hand-computed cases: the portfolio's minute equity and
intraday drawdown (research/portfolio_dd.py), the pre-FOMC leg priced on a rescaled series (its continuous units times
the exit day's factor), the closed-trade ratio of the walk-forward choice (research/walk_forward.py) and the exact
P/L scaling of volatility-sized contracts (research/vol_overlay.py)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import portfolio_dd as P  # noqa: E402
import walk_forward as W  # noqa: E402

from mnqbot.fomc import trades  # noqa: E402

NY = "America/New_York"


def leg(rows):
    return pd.DataFrame(rows)


def test_minute_equity_and_drawdown_by_hand():
    """Minutes 0-5. A long of 1 at 100 from minute 1 to 3 (lows 99, 98; exit 101, +$2 x 1 - $1.90 = +$0.10); a long
    of 2 at 50 from minute 2 to 5 (lows 49, 47, 48; exit 46, 2 x (-4 x $2 - $1.90) = -$19.80).
    Worst-price equity: m0 0; m1 (99-100) x 2 = -2; m2 (98-100) x 2 + (49-50) x 4 = -8; m3 0.10 + (47-50) x 4 =
    -11.90; m4 0.10 + (48-50) x 4 = -7.90; m5 0.10 - 19.80 = -19.70. The drawdown from the peak (0) is 19.70."""
    t = pd.date_range("2026-03-10 10:00", periods=6, freq="min", tz=NY)
    a = leg([{"t0": t[1], "t1": t[3], "d": 1, "q": 1, "en": 100.0, "ex": 101.0, "pnl": 0.10,
              "low_path": np.array([99.0, 98.0]), "high_path": np.array([101.0, 101.0])}])
    b = leg([{"t0": t[2], "t1": t[5], "d": 1, "q": 2, "en": 50.0, "ex": 46.0, "pnl": -19.80,
              "low_path": np.array([49.0, 47.0, 48.0]), "high_path": np.array([51.0, 51.0, 51.0])}])
    eq, closed = P.minute_equity(t, [a, b])
    assert np.allclose(eq, [0, -2, -8, -11.9, -7.9, -19.7])
    assert np.allclose(closed, [0, 0, 0, 0.1, 0.1, -19.7])
    peak = np.concatenate([[0.0], np.maximum.accumulate(np.maximum(eq, 0.0))[:-1]])
    assert np.isclose(np.max(peak - eq), 19.7)


def eth(days, price, scale):
    rows = []
    for d in days:
        t, end = pd.Timestamp(d, tz=NY) - pd.Timedelta(hours=6), pd.Timestamp(d, tz=NY) + pd.Timedelta(hours=17)
        while t < end:
            rows.append((t, price, price + 0.25, price - 0.25, price, scale))
            t += pd.Timedelta(minutes=1)
    f = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "scale"]).set_index("t")
    return f


def test_fomc_leg_on_a_rescaled_series_crossing_a_month(monkeypatch, tmp_path):
    """An announcement on 2026-04-01: entry 3/31 14:00, exit 4/1 13:55. March is scaled by 1, April by 2, and the
    underlying price is 10000 throughout, so the rescaled prices jump from 10000 to 20000 at the month turn. Priced in
    continuous units times April's factor the trade is flat, 20000.50 in and 19999.50 out after the slippage:
    2 x ((-1.00) x $2 - $1.90) = -$7.80. Read off the rescaled prices it would claim over +$10,000."""
    a = eth(["2026-03-31"], 10000.0, 1.0)
    b = eth(["2026-04-01"], 20000.0, 2.0)
    adj = pd.concat([a, b])
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "fomc_dates.csv").write_text("date\n2026-04-01\n")
    monkeypatch.setattr(P, "ROOT", tmp_path)
    f = P.fomc_trades(adj, 2, 2)
    assert len(f) == 1
    r = f.iloc[0]
    assert (r.en, r.ex) == (20000.5, 19999.5)
    assert np.isclose(r.pnl, 2 * ((19999.5 - 20000.5) * 2 - 1.9))
    direct = trades(adj, {"2026-04-01"}, qty=2)
    assert direct[0]["pnl"] > 10000  # what the unconverted prices would claim


def test_closed_ratio():
    """Closed P/L +100, -50, +30, -60, +200: equity 100, 50, 80, 20, 220; the deepest fall from a peak is 100 - 20 = 80;
    net 220 / 80 = 2.75."""
    tr = pd.DataFrame({"xb": [1, 2, 3, 4, 5], "pnl": [100.0, -50.0, 30.0, -60.0, 200.0]})
    assert W.closed_ratio(tr) == pytest.approx(2.75)
    assert W.closed_ratio(tr.iloc[:0]) == -np.inf


def test_vol_sizes_are_causal_and_clipped():
    """sizes() uses the 14 sessions before today: changing today's bars never changes today's size."""
    import vol_overlay as V
    rng = np.random.default_rng(3)
    rows = []
    for d in pd.bdate_range("2025-01-01", periods=320):
        for m in (0, 389):
            t = pd.Timestamp(d.date()).tz_localize(NY) + pd.Timedelta(hours=9, minutes=30 + m)
            p = 100 + rng.normal()
            rows.append((t, p, p + 1, p - 1, p))
    bars = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close"]).set_index("t")
    q = V.sizes(bars)
    bumped = bars.copy()
    bumped.iloc[-1, bumped.columns.get_loc("close")] *= 1.5
    q2 = V.sizes(bumped)
    assert q.iloc[-1] == q2.iloc[-1]
    assert q.dropna().between(1, 8).all()
