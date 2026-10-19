"""Explain a NinjaTrader run from its NinjaScript Output (docs/CANDIDATE_C.md, item 3).

    python research/output_audit.py <NinjaScript_Output.txt> [trades.csv]

Splits the Output into runs (each starts with its settings lines) and reports for each:
- the strategy and its settings;
- data coverage, complete sessions and the warm-up (candidate C's audit, B's funnel);
- qualifying signals, entries, and signals not taken by reason, with the first and last date of each reason;
- whether trading effectively stopped: the last signal taken, and how many qualifying signals came after it and why
  they were refused.

Formats read:
- candidate C: "C settings", "C check ...", "C audit ...";
- the rejected runner: "MNQ runner settings", "MNQ runner: signal <time> not taken: <reason>", its end line;
- frozen B: "MNQ settings", the "MNQ funnel, end of run" block.

The runner prints no line for the signals it takes, so its entries and first/last trades need the run's Trades export
(optional second argument: NinjaTrader's Trades grid exported as CSV).
"""
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

C_LINE = re.compile(r"C check (\d{4}-\d\d-\d\d \d\d:\d\d) (long|short): (.*)")
R_LINE = re.compile(r"MNQ runner: signal (\d{4}-\d\d-\d\d \d\d:\d\d) not taken: (.*)")


def split_runs(lines):
    runs, cur = [], None
    for x in lines:
        starts = x.startswith(("C settings:", "MNQ runner settings:")) or (
            x.startswith("MNQ settings:") and (cur is None or cur["kind"] != "B" or cur["closed"]))
        if starts:
            kind = "C" if x.startswith("C ") else "runner" if "runner" in x else "B"
            cur = {"kind": kind, "lines": [], "closed": False}
            runs.append(cur)
        if cur is not None:
            cur["lines"].append(x)
            if x.startswith("MNQ funnel, end of run"):
                cur["closed"] = True
    return runs


def explain(run):
    lines, kind = run["lines"], run["kind"]
    out = [f"== {kind} run", *[x for x in lines if "settings:" in x][:3]]
    events = []  # (time, 'taken' or reason)
    if kind == "C":
        for x in lines:
            m = C_LINE.search(x)
            if m:
                w = m.group(3)
                events.append((m.group(1), "taken" if w.startswith("entry sent") else w.split("not taken: ", 1)[1]))
        out += [x for x in lines if x.startswith("C audit")]
    elif kind == "runner":
        for x in lines:
            m = R_LINE.search(x)
            if m:
                events.append((m.group(1), m.group(2)))
        out += [x for x in lines if x.startswith("MNQ runner:") and "entries;" in x]
    else:
        i = next((k for k, x in enumerate(lines) if x.startswith("MNQ funnel, end of run")), None)
        if i is not None:
            out += lines[i:i + 14]
    refusals = [(t, w) for t, w in events if w != "taken"]
    if refusals:
        out.append("signals not taken, by reason (first / last):")
        for w, n in Counter(w for _, w in refusals).most_common():
            ts = [t for t, x in refusals if x == w]
            out.append(f"  {w}: {n} ({ts[0]} / {ts[-1]})")
    taken = [t for t, w in events if w == "taken"]
    if kind == "C" and events:
        after = [w for t, w in events if not taken or t > taken[-1]]
        out.append(f"last signal taken: {taken[-1] if taken else 'none'}; qualifying signals after it: {len(after)} "
                   f"({dict(Counter(after))})")
    if kind == "runner" and refusals:
        out.append(f"last refused signal: {refusals[-1][0]}; the runner does not print the signals it takes: use the "
                   "Trades export for the last entry")
    return out


def trades_summary(path):
    df = pd.read_csv(path)
    cols = {c.lower().strip(): c for c in df.columns}
    entry = df[cols["entry time"]] if "entry time" in cols else None
    exit_ = df[cols["exit time"]] if "exit time" in cols else None
    if entry is None or exit_ is None:
        return [f"trades: {len(df)} (no entry/exit time columns)"]
    e, x = pd.to_datetime(entry), pd.to_datetime(exit_)
    es = e.sort_values()
    gaps = es.diff().dt.total_seconds() / 86400
    end = es.iloc[int(gaps.values.argmax())]
    return [f"trades: {len(df)}, first entry {e.min()}, last exit {x.max()}",
            f"longest gap between entries: {gaps.max():.1f} days, ending {end}"]


def main():
    lines = Path(sys.argv[1]).read_text(errors="replace").splitlines()
    for run in split_runs(lines):
        print("\n".join(explain(run)))
    if len(sys.argv) > 2:
        print("\n".join(trades_summary(sys.argv[2])))


if __name__ == "__main__":
    main()
