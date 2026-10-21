"""Walk-forward choice among a fixed menu of configurations, by net / drawdown.

    python research/walk_forward.py <ratio_study folder> <rth bars pkl> <kind> <slippage> <first year> <variant ...>

Each test year, the configuration with the highest net / closed-trade drawdown over every earlier year (from the first
traded year) is chosen and traded that year; the chosen years' trades are concatenated, and that out-of-sample record
is compared with every fixed configuration over the same years (intraday drawdown with open P/L, as
research/ratio_study.py). Nothing about a test year is used to choose its configuration.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ratio_study as R  # noqa: E402


def closed_ratio(tr: pd.DataFrame) -> float:
    if tr.empty:
        return -np.inf
    eq = tr.sort_values("xb").pnl.cumsum().to_numpy()
    dd = float(np.max(np.maximum.accumulate(np.maximum(eq, 0.0)) - eq))
    return eq[-1] / dd if dd else np.inf


def main() -> None:
    folder, rth = Path(sys.argv[1]), pd.read_pickle(sys.argv[2])
    kind, slip, first = sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
    names = sys.argv[6:]
    trades = {n: pd.read_csv(folder / f"trades_{kind}_{n.replace(' ', '_')}_{slip}t.csv", parse_dates=["day"])
              for n in names}
    years = sorted(set().union(*[set(t.day.dt.year) for t in trades.values()]))
    picks, oos = [], []
    for y in [x for x in years if x >= first]:
        score = {n: closed_ratio(t[t.day.dt.year < y]) for n, t in trades.items()}
        best = max(score, key=score.get)
        picks.append({"year": y, "chosen": best, **{f"score {n}": round(v, 2) for n, v in score.items()}})
        oos.append(trades[best][trades[best].day.dt.year == y])
    wf = pd.concat(oos)
    rows = []
    for n, t in [("walk-forward", wf)] + [(n, t[t.day.dt.year >= first]) for n, t in trades.items()]:
        rows.append({"configuration": n, **R.summary(t, rth)})
    pd.set_option("display.width", 250)
    print(pd.DataFrame(picks).to_string(index=False))
    print(pd.DataFrame(rows).round(2).to_string(index=False))
    pd.DataFrame(picks).to_csv(folder / f"wf_picks_{kind}_{slip}t.csv", index=False)
    pd.DataFrame(rows).to_csv(folder / f"wf_result_{kind}_{slip}t.csv", index=False)


if __name__ == "__main__":
    main()
