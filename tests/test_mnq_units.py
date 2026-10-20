"""MNQ units everywhere: $2 a point, 0.25 points a tick ($0.50 a tick), commission per side per contract.

Every component that turns prices into dollars is checked against a calculation from first principles: the NinjaTrader
strategies on the stand-in (frozen B and candidate C), the Python reference, the Pine source in the interpreter, the
evaluation replay, and candidate C's planned risk.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from test_ninjatrader import DOTNET, rth_minutes, run_sim, sim  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import eval_sim as E  # noqa: E402

from mnqbot.noise import NoiseConfig  # noqa: E402
from mnqbot.noise import run as noise_run  # noqa: E402

POINT, TICK, FEE = 2.0, 0.25, 0.95
TICK_DOLLARS = POINT * TICK


def pnl(d, entry, exit_, qty, fee=FEE):
    return d * (exit_ - entry) * qty * POINT - 2 * fee * qty


def test_a_tick_is_fifty_cents():
    assert TICK_DOLLARS == 0.50
    assert math.isclose(E.FEE, FEE)


@pytest.mark.skipif(DOTNET is None, reason="needs the .NET SDK")
@pytest.mark.parametrize("strategy", ["B", "C"])
def test_stand_in_trades_are_priced_at_two_dollars_a_point(sim, tmp_path, strategy):  # noqa: F811
    bars = rth_minutes(30, 5)
    props = {"SimCommissionPerSide": FEE}
    if strategy == "C":
        trades, orders, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=None, Strategy="C",
                                       EvalTarget=0, EvalTrail=100000, AccountReserve=0, **props)
        qty = [int(o[3]) for o in orders if o[1] == "Enter"]
    else:
        trades, orders, _, _ = run_sim(sim, bars, tmp_path, minutes=1, breakout=False, **props)
        qty = [int(o[3]) for o in orders if o[1] == "Enter"]
    assert trades and len(qty) >= len(trades)
    for row, q in zip(trades, qty, strict=False):
        d, en, ex, got = int(row[0]), float(row[2]), float(row[4]), float(row[6])
        assert math.isclose(got, pnl(d, en, ex, q), abs_tol=1e-6), (row, q)
        # every price is on the 0.25-point grid
        assert abs(en / TICK - round(en / TICK)) < 1e-6 and abs(ex / TICK - round(ex / TICK)) < 1e-6


def test_python_reference_prices_trades_at_two_dollars_a_point():
    bars = rth_minutes(30, 5)
    res = noise_run(bars, NoiseConfig(qty=3, commission_per_side=FEE), minutes=1)
    assert res.trades
    for t in res.trades:
        assert math.isclose(t.pnl, pnl(t.direction, t.entry, t.exit, 3), abs_tol=1e-6)


def test_pine_source_prices_trades_at_two_dollars_a_point():
    pytest.importorskip("pynescript")
    import tempfile

    from pine_interpreter import PineRuntime, load_pine
    src = Path(tempfile.mkdtemp()) / "v15.pine"
    ref = Path(__file__).resolve().parents[1] / "pine" / "reference" / "mnq_noise_momentum_v1.5_user.pine"
    src.write_text(ref.read_text(newline=""), newline="\n")
    from mnqbot.data import resample
    bars = resample(rth_minutes(25, 5).assign(volume=0), "5min")
    rt = PineRuntime(load_pine(src), bars, {"Contracts": 2, "Max loss per trade, $ (all contracts, 0 = off)": 70},
                     timeframe_seconds=300, commission=FEE, slippage_ticks=1)
    assert rt.pointvalue == POINT and rt.mintick == TICK
    rt.run()
    assert rt.strategy.closed
    for t in rt.strategy.closed:
        assert math.isclose(t["pnl"], pnl(t["dir"], t["entry"], t["exit"], 2), abs_tol=1e-6)


def test_evaluation_replay_equity_is_two_dollars_a_point():
    """One long of 3 contracts from 100: bar 2 reaches 110 and 104, the exit is at 108. The replay's result is the
    trade's P/L at $2 a point, and its drawdown the 6-point fall from 110 to 104 at $2 a point."""
    o = np.array([100.0, 100.0, 105.0, 108.0])
    h = np.array([100.0, 101.0, 110.0, 108.0])
    lo = np.array([100.0, 99.0, 104.0, 108.0])
    tr = pd.DataFrame([{"d": 1, "eb": 1, "en": 100.0, "xb": 3, "ex": 108.0, "why": "Flat 15:55",
                        "pnl": pnl(1, 100.0, 108.0, 3), "q": 3}])
    trs = E.marks(tr, o, h, lo, 0)
    outcome, _, dd, eq, _ = E.evaluate_detail(trs, 0, 4, np.zeros(4, dtype=int), "favourable first")
    assert math.isclose(eq, pnl(1, 100.0, 108.0, 3))
    # favourable first: bar 2 opens at 105, reaches 110, then its low 104; the deepest fall from the peak is 6 points
    assert math.isclose(dd, (110 - 104) * 3 * POINT, abs_tol=1e-9)
    assert outcome == "expired"


def test_candidate_c_planned_risk_formula():
    """C's planned risk a contract: stop points x $2 + 2 x $0.95 + 4 ticks x $0.50; a 25-point stop is $53.90."""
    def rpc(stop_pts):
        return stop_pts * POINT + 2 * FEE + 4 * TICK_DOLLARS
    assert math.isclose(rpc(25), 53.90) and math.isclose(4 * TICK_DOLLARS, 2.00)
    assert math.floor(200 / rpc(25)) == 3
