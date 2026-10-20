"""NinjaTrader against Python, trade for trade, on a fixed three-month MNQ sample at 2 ticks (docs/PARITY.md).

The sample: the user's MNQ bars, traded contracts (09-26 to the 9/10 roll session, back-adjusted, then 12-26),
09:30-16:00 and the 16:00 bar, 6/29 to 10/16/2026: 14 sessions of warm-up, then 7/20 to 10/16 traded. Frozen B's
settings (4 MNQ, $200, 3 losers, lock 1.0 / +2.5, take-profit 1.5, line stop 0.24, tighten-only), $0.95 a side, 2
ticks of slippage, prices on the tick grid.
- The NinjaTrader strategy's own code (MnqNoiseMomentum.cs on the simulator) and the Python reference
  (mnqbot.noise with nt_execution and round_prices) must agree exactly: every trade's direction, entry and exit bar,
  entry and exit price and P/L.
- Against the user's native NinjaTrader run at 2 ticks (B_L2, MNQ DEC26 unmerged): every trade from 7/20 the same
  entry minute, direction, contracts, exit minute and exit kind; dollars identical from 10/1, where both run on the
  same bars and noise history (prices too, but for one trade native filled 0.50 point higher at both ends); at most
  $4.00 a trade apart before it (docs/B_NATIVE.md).
"""
from __future__ import annotations

import gzip
import hashlib
import math
import subprocess
from pathlib import Path

import pandas as pd
import pytest
from test_ninjatrader import DOTNET, ENV, sim  # noqa: F401

from mnqbot.noise import NoiseConfig, run

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "tests" / "data" / "mnq_traded_2026-06-29_2026-10-16.csv.gz"
SAMPLE_SHA256 = "ad73d17ab1abc11e7a4507680fe4774d4b5159f3117efbeb20c1eeafaa0f003b"
NATIVE_2T = ROOT / "verification" / "native_long" / "B_L2_trades_from_output.csv"
CFG = NoiseConfig(qty=4, max_loss_per_trade=200.0, max_losers=3, tighten_only=True, target_on_fill_bar=True,
                  commission_per_side=0.95, slippage_ticks=2, nt_execution=True, round_prices=True)
KIND = {"Target": "Profit target", "16:00 close": "Flat 16:00", "Stop passed": "Stop passed"}


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    raw = gzip.decompress(SAMPLE.read_bytes())
    assert hashlib.sha256(raw).hexdigest() == SAMPLE_SHA256, "the fixed sample changed"
    path = tmp_path_factory.mktemp("parity") / "bars.csv"
    path.write_bytes(raw)
    bars = pd.read_csv(path, header=None, names=["t", "open", "high", "low", "close"])
    bars.index = pd.to_datetime(bars.pop("t")).dt.tz_localize("America/New_York")
    return path, bars.assign(volume=0.0)


@pytest.fixture(scope="module")
def python_trades(sample):
    _, bars = sample
    return run(bars, CFG, minutes=1).trades


def nt_trades(sim, path):  # noqa: F811
    r = subprocess.run([DOTNET, str(sim), str(path), "1", "UseBreakout=False", "SimSlippageTicks=2",
                        "SimCommissionPerSide=0.95"], capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr[-2000:]
    rows = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
    return [(int(a[0]), int(a[1]), float(a[2]), int(a[3]), float(a[4]), a[5], float(a[6])) for a in rows]


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
def test_ninjatrader_code_and_python_agree_trade_for_trade(sim, sample, python_trades):  # noqa: F811
    path, _ = sample
    nt = nt_trades(sim, path)
    assert len(nt) == len(python_trades) == 97
    for (d, eb, en, xb, ex, _, pnl), t in zip(nt, python_trades, strict=True):
        assert (d, eb, xb) == (t.direction, t.entry_bar, t.exit_bar), (d, eb, xb, t)
        assert en == t.entry and ex == t.exit, (en, ex, t)
        assert math.isclose(pnl, t.pnl, abs_tol=1e-6), (pnl, t)
    assert math.isclose(sum(x[6] for x in nt), 13030.80, abs_tol=1e-6)
    # every price on the MNQ tick grid, every P/L at $2 a point less $0.95 a side
    for t in python_trades:
        assert t.entry * 4 == round(t.entry * 4) and t.exit * 4 == round(t.exit * 4)
        assert math.isclose(t.pnl, t.direction * (t.exit - t.entry) * 4 * 2.0 - 2 * 0.95 * 4, abs_tol=1e-6)


def test_python_matches_the_native_ninjatrader_run(sample, python_trades):
    _, bars = sample
    idx = bars.index.tz_localize(None)
    one = pd.Timedelta(minutes=1)  # NinjaTrader stamps a fill with its bar's end
    py = pd.DataFrame([{"entry_time": idx[t.entry_bar] + one, "dir": t.direction, "qty": t.qty, "entry": t.entry,
                        "exit_time": idx[t.exit_bar] + one, "exit": t.exit, "kind": KIND.get(t.reason, "Stop loss"),
                        "net": t.pnl} for t in python_trades])
    nat = pd.read_csv(NATIVE_2T, parse_dates=["entry_time", "exit_time"])
    nat = nat[nat.entry_time >= "2026-07-20"]
    m = nat.merge(py, on=["entry_time", "dir", "qty"], how="outer", suffixes=("_nt", "_py"), indicator=True)
    assert (m._merge == "both").all() and len(m) == 97
    assert (m.exit_time_nt == m.exit_time_py).all()
    assert (m.exit_name == m.kind).all()
    late = m[m.entry_time >= "2026-10-01"]
    assert len(late) == 20 and ((late.net_nt - late.net_py).abs() < 1e-6).all()
    # identical prices, except the one trade docs/MNQ_NATIVE.md records (10/16 11:31): native filled entry and exit
    # the same 0.50 point higher, so the same dollars
    moved = late[(late.entry_nt != late.entry_py) | (late.exit_nt != late.exit_py)]
    assert len(moved) <= 1 and ((moved.entry_nt - moved.entry_py) == (moved.exit_nt - moved.exit_py)).all()
    assert (m.net_nt - m.net_py).abs().max() <= 4.0 + 1e-9
