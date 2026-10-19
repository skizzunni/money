"""Regression tests for the evaluation replay's accounting (research/eval_sim.py): execution chronology inside a bar,
and the trailing threshold checked after every fill and commission."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import eval_sim as E  # noqa: E402

DAY = np.zeros(10, dtype=int)


def trade(eb, d, q, en, ex, kind, bars):
    """A trade as eval_sim.marks returns it; bars: [(open, high, low), ...] from the entry bar to the exit bar."""
    o, h, lo = (np.array(x, float) for x in zip(*bars, strict=True))
    pnl = d * (ex - en) * q * 2.0 - 2 * E.FEE * q
    return (eb, eb + len(bars) - 1, d, q, en, ex, kind, pnl, o, h, lo)


def outcomes(trs):
    return {p: E.evaluate(trs, 0, 10**12, DAY, p)[0] for p in E.PATHS}


def test_prices_after_a_stop_exit_in_its_bar_do_not_count():
    """Long 4 MNQ from 1000. The exit bar opens at 1010, its high is 1300, its low 990; the stop fills at 995. If the
    high came before the stop, the peak (+$2,396) makes the stop a breach; if the low came first, the position was
    gone before the high, and there is no breach. The old replay counted the high either way."""
    t = trade(0, 1, 4, 1000.0, 995.0, "stop", [(1000, 1001, 999), (1010, 1300, 990)])
    out = outcomes([t])
    assert out["favourable first"] == "fail"
    assert out["adverse first"] == "open"
    assert out["worst mix"] == "fail" and out["best mix"] == "open"


def test_a_stop_crossed_at_the_open_ends_the_bar():
    """The stop is crossed at the open (filled at 899.75): nothing later in that bar, not its 1300 high, counts on any
    path."""
    t = trade(0, 1, 4, 1000.0, 899.75, "open", [(1000, 1001, 999), (900, 1300, 880)])
    out = outcomes([t])
    assert set(out.values()) == {"open"}
    _, _, dd = E.evaluate([t], 0, 10**12, DAY, "favourable first")
    assert dd < (1001 - 899.75) * 8 + 10  # the drawdown from the entry bar's high to the fill, not from 1300


def test_a_low_after_a_take_profit_does_not_count():
    """The take-profit fills at 1100 in a bar whose low is 700: if the target came first, the low is after the exit
    (no breach); if the low came first, the position saw -$2,400 (a breach)."""
    t = trade(0, 1, 4, 1000.0, 1100.0, "target", [(1000, 1001, 999), (1010, 1100.25, 700)])
    out = outcomes([t])
    assert out["favourable first"] == "open"
    assert out["adverse first"] == "fail"


def test_the_exit_commission_can_breach_the_trail():
    """A first trade closes +$1,000 (the peak). The second's stop fills where equity, with the entry commission only,
    is $2 above the threshold; the exit commission ($3.80) takes it $1.80 below: a breach, on every path."""
    first = trade(0, 1, 4, 1000.0, 1000.0 + (1000 + 7.6) / 8, "open", [(1000, 1000, 1000), (1125.95, 1125.95, 1125.95)])
    assert abs(first[7] - 1000.0) < 1e-9
    ex = 1000.0 - (1994.2 / 8)  # equity at the fill before the exit commission: 1000 - 3.8 - 1994.2 = -998
    second = trade(2, 1, 4, 1000.0, ex, "stop", [(1000, 1000, 1000), (1000, 1000, ex - 0.5)])
    for p in E.PATHS:
        out, bar, _ = E.evaluate([first, second], 0, 10**12, DAY, p)
        assert out == "fail" and bar == 3, (p, out, bar)


def test_a_pass_at_the_strategys_own_target_close():
    """Open profit reaching $3,025 and a tick closes everything: a pass, before a later drop in the same bar on the
    favourable-first path."""
    hi = 1000 + (3025 + 3.8 + 2.0 + 1.0) / 8
    t = trade(0, 1, 4, 1000.0, 990.0, "stop", [(1000, 1001, 999), (1001, hi, 990)])
    out = outcomes([t])
    assert out["favourable first"] == "pass" and out["adverse first"] == "open"
