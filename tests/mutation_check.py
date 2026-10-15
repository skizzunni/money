"""Plant one bug at a time in the Pine scripts; the parity tests must catch every one.

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
# (script, original text, buggy replacement)
MUTANTS = {
    "target fills on touch": (
        "indicator", "        else if low <= posTarget - thru\n", "        else if low <= posTarget\n"
    ),
    "entry fills on touch": ("indicator", "pendDir < 0 ? high >= pendEntry + thru", "pendDir < 0 ? high >= pendEntry"),
    "breakeven on fill bar": (
        "indicator", "if posDir != 0 and posBar < bar_index\n", "if posDir != 0 and posBar <= bar_index\n"
    ),
    "target before stop": ("indicator", STOP_FIRST, TARGET_FIRST),
    "expiry off by one": ("indicator", "bar_index - pendBar >= expiryBars", "bar_index - pendBar > expiryBars"),
    "daily room sign": (
        "indicator",
        "math.min(riskPerTrade, dailyMaxLoss + dayPnl,",
        "math.min(riskPerTrade, dailyMaxLoss - dayPnl,",
    ),
    "all-in-one: breakeven on fill bar": (
        "all_in_one",
        "if posDir != 0 and bar_index > posBar and beAtR > 0",
        "if posDir != 0 and bar_index >= posBar and beAtR > 0",
    ),
    "all-in-one: expiry off by one": (
        "all_in_one", "bar_index - pendBar >= expiryBars", "bar_index - pendBar > expiryBars"
    ),
    "all-in-one: breakeven exit labelled stop": ("all_in_one", 'comment_loss = "breakeven"', 'comment_loss = "stop"'),
    "all-in-one: daily room sign": (
        "all_in_one",
        "math.min(riskPerTrade, dailyMaxLoss + dayPnlNow,",
        "math.min(riskPerTrade, dailyMaxLoss - dayPnlNow,",
    ),
    "all-in-one: backtest ignores simulated room": (
        "all_in_one",
        "buffer = evalMode ? relNow - threshold() : roomToLine",
        "buffer = roomToLine",
    ),
}


def _tests(T, script):
    """The parity checks that run against one script, as (name, zero-argument callable)."""
    if script == "indicator":
        return [(case, lambda c=case: T.test_edge_cases_indicator(c)) for case in T.EDGE]
    tests = [
        (f"{case} [{mode}]", lambda c=case, m=mode: T.test_all_in_one_edge_cases(c, m))
        for case in T.EDGE
        for mode in ("live", "eval")
    ]
    tests.append(("eval sizes from simulated room", lambda: T.test_eval_mode_sizes_from_simulated_room("all_in_one")))
    return tests


def check(args):
    name, tmp = args
    import test_pine_parity as T
    from pine_interpreter import PineError

    script, old, new = MUTANTS[name]
    attr = {"indicator": "INDICATOR", "all_in_one": "AIO"}[script]
    src = getattr(T, attr).read_text()
    assert src.count(old) == 1, f"mutation anchor not found: {name}"
    mutant = Path(tmp) / f"mutant_{list(MUTANTS).index(name)}.pine"
    mutant.write_text(src.replace(old, new))
    setattr(T, attr, mutant)
    caught = []
    for label, test in _tests(T, script):
        try:
            test()
        except (AssertionError, PineError):
            caught.append(label)
    return name, caught


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp, ProcessPoolExecutor(6) as ex:
        results = list(ex.map(check, [(m, tmp) for m in MUTANTS]))
    for name, caught in results:
        print(f"{'CAUGHT' if caught else 'MISSED'}  {name:44s} {caught[:2]}")
    missed = [n for n, c in results if not c]
    return 1 if missed else 0


if __name__ == "__main__":
    raise SystemExit(main())
