"""Plant one bug at a time in the Pine scripts; the parity tests must catch every one.

    python tests/mutation_check.py          (a few minutes: each mutant is parsed once)
    python tests/mutation_check.py noise    (only the noise-momentum script's mutants)

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
    "all-in-one: breakout entry at the close": (
        "all_in_one", "        float e = d > 0 ? orHi : orLo\n", "        float e = close\n"
    ),
    "all-in-one: breakout stop at the far side": (
        "all_in_one",
        "float s = roundTick(e - d * orStopFrac * (orHi - orLo))",
        "float s = roundTick(e - d * (orHi - orLo))",
    ),
    "all-in-one: second breakout allowed": (
        "all_in_one", "    orbUsed := true\n    brokeOut := true\n", "    brokeOut := true\n"
    ),
    "all-in-one: range includes the breakout bar": (
        "all_in_one", "if isRth and nyHHMM < orEndHHMM\n", "if isRth and nyHHMM <= orEndHHMM\n"
    ),
    "noise: upper line from the lower of open and previous close": (
        "noise", "ub := math.max(dayOpen, prevClose)", "ub := math.min(dayOpen, prevClose)"
    ),
    "noise: average divided by one session too few": ("noise", "sigma = s / lookback", "sigma = s / (lookback - 1)"),
    "noise: long exits only below the lower line": (
        "noise", "if not inPosStop and pos > 0 and close < ub", "if not inPosStop and pos > 0 and close < lb"
    ),
    "noise: checks on the bar that opens at the half hour": (
        "noise", "(endMin - FIRST_CHECK) % 30 == 0", "(tMin - FIRST_CHECK) % 30 == 0"
    ),
    "noise: short sessions stored in the history": ("noise", "        if complete\n", "        if true\n"),
    "noise: no reversal from long": (
        "noise",
        "                if close < lb\n                    strategy.entry",
        "                if false\n                    strategy.entry",
    ),
    "noise: date list ignored": (
        "noise",
        'skipToday := str.contains(skipDates, str.format_time(time, "yyyy-MM-dd", TZ))',
        "skipToday := false",
    ),
    "noise: no label when a long exits": ("noise", '                    mark("EXIT", false, color.gray)\n', ""),
    "noise: long stop at the lower line": (
        "noise",
        'strategy.exit("Long exit", "Long", stop = longStop,',
        'strategy.exit("Long exit", "Long", stop = shortStop,',
    ),
    "noise: stop buffer ignored": ("noise", "longStop = ub * (1 - stopBuf * sig)\n", "longStop = ub\n"),
    "noise: stop not moved with the line": (
        "noise", "    if strategy.position_size > 0 or longPlaced\n", "    if longPlaced\n"
    ),
    "noise: open position kept into the next session": (
        "noise", "(not inRth or tMin == RTH_OPEN)", "not inRth"
    ),
}


def _tests(T, script):
    """The parity checks that run against one script, as (name, zero-argument callable)."""
    if script == "noise":
        import test_noise as N

        return [(f"{case} [{mode}]", lambda c=case, m=mode: N.test_pine_hand_built(c, m))
                for case in N.HAND_BUILT for mode in N.MODES] + [
            ("short session", N.test_pine_short_session_cases),
            ("skips listed dates", N.test_pine_skips_listed_dates),
        ] + [(f"random {mins}m [{mode}]", lambda mi=mins, mo=mode: N.test_pine_random_sessions(mi, mo))
             for mins, mode in N.RANDOM_CASES] + [
            ("RTH-only chart", N.test_pine_rth_only_chart_and_shorter_lookback),
        ]
    if script == "indicator":
        return [(case, lambda c=case: T.test_edge_cases_indicator(c)) for case in T.EDGE]
    tests = [
        (f"{case} [{mode}]", lambda c=case, m=mode: T.test_all_in_one_edge_cases(c, m))
        for case in T.EDGE
        for mode in ("live", "eval")
    ]
    tests.append(("eval sizes from simulated room", lambda: T.test_eval_mode_sizes_from_simulated_room("all_in_one")))
    tests += [
        (f"ORB {case} [{mode}]", lambda c=case, m=mode: T.test_orb_all_in_one(c, m))
        for case in T.ORB_EDGE
        for mode in ("live", "eval")
    ]
    return tests


def check(args):
    name, tmp = args
    import test_pine_parity as T
    from pine_interpreter import PineError

    script, old, new = MUTANTS[name]
    attr = {"indicator": "INDICATOR", "all_in_one": "AIO", "noise": "NOISE_PINE"}[script]
    # Always mutate the original file: worker processes are reused, and T.<attr> may still
    # point at the previous mutant.
    original = {"INDICATOR": "mnq_liquidity_sweep_signals.pine", "AIO": "mnq_liquidity_sweep_all_in_one.pine",
                "NOISE_PINE": "mnq_noise_momentum.pine"}[attr]
    src = (HERE.parent / "pine" / original).read_text()
    assert src.count(old) == 1, f"mutation anchor not found: {name}"
    mutant = Path(tmp) / f"mutant_{list(MUTANTS).index(name)}.pine"
    mutant.write_text(src.replace(old, new))
    if script == "noise":
        import test_noise as N

        N.NOISE_PINE = mutant
    else:
        setattr(T, attr, mutant)
    caught = []
    for label, test in _tests(T, script):
        try:
            test()
        except (AssertionError, PineError):
            caught.append(label)
    return name, caught


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else ""  # e.g. "noise" runs only the noise-script mutants
    names = [m for m in MUTANTS if m.startswith(only)]
    with tempfile.TemporaryDirectory() as tmp, ProcessPoolExecutor(6) as ex:
        results = list(ex.map(check, [(m, tmp) for m in names]))
    for name, caught in results:
        print(f"{'CAUGHT' if caught else 'MISSED'}  {name:44s} {caught[:2]}")
    missed = [n for n, c in results if not c]
    return 1 if missed else 0


if __name__ == "__main__":
    raise SystemExit(main())
