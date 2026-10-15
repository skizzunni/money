"""Plant one bug at a time in the signals indicator; the parity edge cases must catch every one.

    python tests/mutation_check.py      (about 1-2 minutes: each mutant is parsed once)

This checks the checker: if a mutant survives, the tests have a blind spot.
"""
from __future__ import annotations

import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

STOP_FIRST = (
    "        if open >= posStop\n            exitPx := open + slip\n            exitWhy := stopWhy\n"
    "        else if high >= posStop\n            exitPx := posStop + slip\n            exitWhy := stopWhy\n"
    "        else if low <= posTarget - thru\n            exitPx := posTarget\n            exitWhy := \"TARGET\"\n"
)
TARGET_FIRST = (
    "        if low <= posTarget - thru\n            exitPx := posTarget\n            exitWhy := \"TARGET\"\n"
    "        else if open >= posStop\n            exitPx := open + slip\n            exitWhy := stopWhy\n"
    "        else if high >= posStop\n            exitPx := posStop + slip\n            exitWhy := stopWhy\n"
)
MUTANTS = {
    "target fills on touch": ("        else if low <= posTarget - thru\n", "        else if low <= posTarget\n"),
    "entry fills on touch": ("pendDir < 0 ? high >= pendEntry + thru", "pendDir < 0 ? high >= pendEntry"),
    "breakeven on fill bar": ("if posDir != 0 and posBar < bar_index\n", "if posDir != 0 and posBar <= bar_index\n"),
    "target before stop": (STOP_FIRST, TARGET_FIRST),
    "expiry off by one": ("bar_index - pendBar >= expiryBars", "bar_index - pendBar > expiryBars"),
    "daily room sign": (
        "math.min(riskPerTrade, dailyMaxLoss + dayPnl,",
        "math.min(riskPerTrade, dailyMaxLoss - dayPnl,",
    ),
}


def check(args):
    name, tmp = args
    import test_pine_parity as T

    from mnqbot.engine import backtest

    old, new = MUTANTS[name]
    src = T.INDICATOR.read_text()
    assert src.count(old) == 1, f"mutation anchor not found: {name}"
    mutant = Path(tmp) / f"mutant_{list(MUTANTS).index(name)}.pine"
    mutant.write_text(src.replace(old, new))
    T.INDICATOR = mutant
    caught = []
    for case, (bars, extra, risk) in T.EDGE.items():
        res = backtest(bars, T._edge_cfg(risk, evals=False))
        inputs = {"Watch latest swing high/low": False, "Your room to the drawdown line $": 1e9} | extra
        orders, trades, _ = T.run_indicator(bars, inputs)
        if orders != T.engine_orders(res) or trades != T.engine_trades(res, bars):
            caught.append(case)
    return name, caught


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp, ProcessPoolExecutor(len(MUTANTS)) as ex:
        results = list(ex.map(check, [(m, tmp) for m in MUTANTS]))
    for name, caught in results:
        print(f"{'CAUGHT' if caught else 'MISSED'}  {name:24s} {caught[:2]}")
    missed = [n for n, c in results if not c]
    return 1 if missed else 0


if __name__ == "__main__":
    raise SystemExit(main())
