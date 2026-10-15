"""Run the real .pine files through tests/pine_interpreter.py and require the
same orders and trades as the Python engine (mnqbot), bar for bar.

The first run parses both scripts (about a minute each); the trees are then
cached in tests/.pine_cache/.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("pynescript", reason="pip install pynescript to check the .pine files")

from conftest import synth_bars  # noqa: E402
from pine_interpreter import PineRuntime, is_na, load_pine  # noqa: E402
from test_engine import loose_cfg  # noqa: E402

from mnqbot.config import BotConfig  # noqa: E402
from mnqbot.engine import backtest  # noqa: E402

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[1]
INDICATOR = ROOT / "pine" / "mnq_liquidity_sweep_signals.pine"
STRATEGY = ROOT / "pine" / "mnq_liquidity_sweep_bot.pine"

# Same settings as test_engine.loose_cfg(), by input title.
LOOSE = {
    "Entry window (New York time)": "0935-1500",
    "Displacement must come within N bars": 30,
    "Displacement body >= ATR x": 0.3,
    "Min fair value gap (ticks)": 1,
    "Min stop (points)": 4.0,
    "Max stop (points)": 100.0,
}


@pytest.fixture(scope="module")
def bars():
    return synth_bars(sessions=120, seed=3)


def _r(x):
    return round(float(x), 6)


def engine_orders(res, upto=None):
    return [
        (s.bar, s.direction, _r(s.entry), _r(s.stop), _r(s.target), q)
        for s, q in res.orders
        if upto is None or s.bar < upto
    ]


def engine_trades(res, bars):
    loc = {t: k for k, t in enumerate(bars.index)}
    return [
        (loc[t.entry_time], loc[t.exit_time], t.direction, t.qty, _r(t.entry), _r(t.exit), _r(t.pnl))
        for t in res.trades
        if t.reason != "end_of_data"
    ]


def run_indicator(bars, inputs):
    rt = PineRuntime(load_pine(INDICATOR), bars, inputs)
    orders, trades, fill_bar = [], [], {}

    def on_bar(i, g):
        if g["signalNow"]:
            setup = (_r(g["setupEntry"]), _r(g["setupStop"]), _r(g["setupTarget"]))
            orders.append((i, g["signalDir"], *setup, g["signalQty"]))
        if g["fillNow"]:
            fill_bar["i"] = i
        if not is_na(g["exitPnl"]):
            trades.append(
                (fill_bar["i"], i, g["exitDir"], g["posQty"], _r(g["posEntry"]), _r(g["exitPx"]), _r(g["exitPnl"]))
            )

    rt.run(on_bar)
    assert len(rt.globals["tradePnls"]) == len(trades), "unexpected day-end exits in test data"
    return orders, trades, rt


def run_strategy(bars, inputs):
    rt = PineRuntime(load_pine(STRATEGY), bars, inputs)
    orders, evals = [], {}

    def on_bar(i, g):
        if g["pendDir"] != 0 and g["pendBar"] == i:
            orders.append((i, g["pendDir"], _r(g["pendEntry"]), _r(g["pendStop"]), _r(g["pendTarget"]), g["pendQty"]))
        evals.update(passed=g["evalsPassed"], failed=g["evalsFailed"])

    rt.run(on_bar)
    trades = [
        (t["entry_bar"], t["exit_bar"], t["dir"], t["qty"], _r(t["entry"]), _r(t["exit"]), _r(t["pnl"]))
        for t in rt.strategy.closed
    ]
    return orders, trades, evals, rt


# ------------------------------------------------------------------ indicator
def test_indicator_matches_engine(bars):
    cfg = loose_cfg()
    cfg.prop.max_drawdown = 1e9  # the indicator has no evaluation simulation; take it out of the engine too
    cfg.prop.profit_target = 1e12
    res = backtest(bars, cfg)
    orders, trades, rt = run_indicator(bars, LOOSE | {"Your room to the drawdown line $": 1e9})

    assert len(trades) >= 20, "not enough trades to compare"
    assert orders == engine_orders(res)
    assert trades == engine_trades(res, bars)
    assert any("SELL LIMIT" in m for _, m in rt.alerts) and any("BUY LIMIT" in m for _, m in rt.alerts)


def test_indicator_room_input_shrinks_size(bars):
    cfg = loose_cfg()
    cfg.prop.max_drawdown = 1e9
    cfg.prop.profit_target = 1e12
    orders, _, _ = run_indicator(bars.iloc[: len(bars) // 4], LOOSE | {"Your room to the drawdown line $": 200.0})
    # 25% of $200 = $50 per trade at most
    for _, _, entry, stop, _, qty in orders:
        per = abs(entry - stop) * 2 + 2 * 0.62 + 0.25 * 2
        assert qty * per <= 50 + 1e-9


# ------------------------------------------------------------------ strategy
def test_strategy_matches_engine_including_eval_rules(bars):
    cfg = loose_cfg()  # default prop rules: $25K, $1,500 EOD trailing drawdown, 5 days, 50% consistency
    res = backtest(bars, cfg)
    orders, trades, evals, _ = run_strategy(bars, LOOSE)

    liq = [t for t in res.trades if t.reason == "liquidated"]
    assert not liq, "a liquidation would make the scripts diverge on purpose (documented); pick other data"
    assert len(trades) >= 20
    assert orders == engine_orders(res)
    assert trades == engine_trades(res, bars)

    last_day = bars.trade_date.iloc[-1]
    done = [a for a in res.attempts if a.outcome != "open" and a.end_date != last_day]
    assert evals == {
        "passed": sum(a.outcome == "passed" for a in done),
        "failed": sum(a.outcome == "failed" for a in done),
    }
    assert evals["passed"] + evals["failed"] >= 1, "test data should finish at least one evaluation"


def test_default_settings_run_clean():
    b = synth_bars(sessions=40, seed=11)
    run_indicator(b, {})  # raises on any interpreter/script error
    _, strat_trades, _, _ = run_strategy(b, {})
    res = backtest(b)
    assert strat_trades == engine_trades(res, b)


# ------------------------------------------------------------------ shared code
def _section(path: Path, number: int) -> str:
    text = path.read_text()
    m = re.search(rf"// ─+ {number}\. [^\n]*\n(.*?)(?=// ─+ )", text, re.S)
    assert m, f"section {number} not found in {path.name}"
    return m.group(1)


def test_signal_logic_is_identical_in_both_scripts():
    assert _section(INDICATOR, 6) == _section(STRATEGY, 6)


# ------------------------------------------------------------------ edge cases
# Hand-built bars that sit exactly on every fill boundary. Random data rarely
# lands a price exactly on a level, so these are what catch off-by-one bugs.
# Each case: (bars, extra Pine inputs, matching engine settings).
def _edge_cases():
    from test_engine import two_setup_day
    from test_strategy import short_day

    fill = (19993, 19999, 19992, 19996)  # short limit 19998 fills (19998.25 traded)
    wait = (19993, 19996, 19990, 19994)  # no fill, no target
    after = {
        "entry touched, not through": [(19993, 19998, 19992, 19996)] * 7,
        "entry one tick through": [(19993, 19998.25, 19992, 19996)] + [(19996, 19997, 19990, 19992)] * 3,
        "fills on the last allowed bar": [wait] * 5 + [fill],
        "fills one bar after expiry": [wait] * 6 + [fill],
        "target touched, not through": [fill, (19996, 19997, 19964, 19970), (19970, 19972, 19963.75, 19965)],
        "stop and target same bar": [fill, (19996, 19997, 19985, 19990), (19990, 20016, 19960, 19970)],
        "stop touched exactly": [fill, (19996, 20015, 19990, 19995)],
        "target on fill bar": [(19993, 19999, 19960, 19962)],
        "breakeven then back to entry": [fill, (19996, 19997, 19980, 19985), (19985, 19998, 19984, 19997)],
        "breakeven trigger exact": [fill, (19996, 19997, 19981, 19985), (19985, 19999, 19984, 19998)],
        "target hit before fill": [(19993, 19995, 19963, 19966)],
        "gap through stop": [fill, (20020, 20025, 20018, 20022)],
        "held to the flatten": [fill] + [(19995, 19997, 19993, 19995)] * 80,
    }
    cases = {name: (short_day(after=rows), {}, {}) for name, rows in after.items()}
    two = two_setup_day()[0]
    cases["stop, then long at full size"] = (two, {}, {})
    cases["stop, then long shrunk to daily room"] = (
        two, {"Daily max loss $ (done for the day)": 250.0}, {"daily_max_loss": 250.0}
    )
    cases["max one trade per day"] = (two, {"Max trades per day": 1}, {"max_trades_per_day": 1})
    return cases


EDGE = _edge_cases()


def _edge_cfg(risk_overrides, evals=True):
    cfg = BotConfig()
    cfg.strategy.use_swings = False
    for k, v in risk_overrides.items():
        setattr(cfg.risk, k, v)
    if not evals:
        cfg.prop.max_drawdown = 1e9
        cfg.prop.profit_target = 1e12
    return cfg


@pytest.mark.parametrize("name", list(EDGE))
def test_edge_cases_indicator(name):
    bars, extra, risk = EDGE[name]
    res = backtest(bars, _edge_cfg(risk, evals=False))
    inputs = {"Watch latest swing high/low": False, "Your room to the drawdown line $": 1e9} | extra
    orders, trades, _ = run_indicator(bars, inputs)
    assert orders == engine_orders(res)
    assert trades == engine_trades(res, bars)


@pytest.mark.parametrize("name", list(EDGE))
def test_edge_cases_strategy(name):
    bars, extra, risk = EDGE[name]
    res = backtest(bars, _edge_cfg(risk))
    orders, trades, _, _ = run_strategy(bars, {"Watch latest swing high/low": False} | extra)
    assert orders == engine_orders(res)
    assert trades == engine_trades(res, bars)


def test_edge_cases_cover_every_exit_type_and_rail():
    reasons, qtys = set(), set()
    for bars, _, risk in EDGE.values():
        res = backtest(bars, _edge_cfg(risk))
        reasons |= {t.reason for t in res.trades}
        qtys |= {t.qty for t in res.trades}
    assert {"stop", "target", "breakeven", "flatten"} <= reasons
    assert {4, 3, 2} <= qtys  # full size, and shrunk by the daily-loss room
