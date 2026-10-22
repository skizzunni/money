"""pine/mnq_daily_g.pine against the Python model (mnqbot/candidate_d.py, variant G-D cap line) on the same bars.

    python research/pine_g_parity.py <raw NQ parquet> <first day> <last day> [check step]

Bars: raw NQ 1-minute (prices on the 0.25 grid, no rescaling, treated as MNQ: $2 a point), 09:30-16:00 only, from a
development year (docs/CANDIDATE_G.md: the holdout is never used here). The Pine source runs in
tests/pine_interpreter.py with $0.95 a side and 2 ticks; the model with the same skip and FOMC dates. Prints the
campaigns matched by entry bar and direction, and any whose P/L differs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "research"))
import eval_d as ED  # noqa: E402
from pine_interpreter import PineRuntime, load_pine  # noqa: E402

from mnqbot.candidate_d import DConfig, run  # noqa: E402

NY = "America/New_York"


def rth_bars(parquet: str, first: str, last: str) -> pd.DataFrame:
    raw = pd.read_parquet(parquet)
    raw.index = pd.to_datetime(raw.timestamp, utc=True).dt.tz_convert(NY)
    raw = raw[~raw.index.duplicated()].sort_index()
    t = raw.index.hour * 60 + raw.index.minute
    raw = raw[(t >= 570) & (t < 960)]
    days = raw.index.strftime("%Y-%m-%d")
    return raw[(days >= first) & (days <= last)][["open", "high", "low", "close"]]


def compare(bars: pd.DataFrame, step: int = 30):
    days = sorted(set(bars.index.strftime("%Y-%m-%d")))
    per = pd.Series(bars.index.strftime("%Y-%m-%d")).value_counts()
    skip = sorted(d for d in days if per[d] < 390)  # half days and gaps, as the evaluation's skip set
    fomc = sorted(d for d in ED.FOMC if days[0] <= d <= days[-1])
    cfg = DConfig(e1=False, stop_fit="cap", runner_trail="line", check_step=step, skip_dates=frozenset(skip),
                  fed_dates=frozenset(fomc))
    m = run(bars.assign(scale=1.0), cfg)
    py = {(min(lt.fill_bar for lt in c.lots), c.d): (c.sleeve, round(c.pnl, 2)) for c in m.campaigns}
    rt = PineRuntime(load_pine(ROOT / "pine" / "mnq_daily_g.pine"), bars,
                     {"Don't trade on these dates (holidays, half days)": ",".join(skip),
                      "Fed announcement days (no noise shorts before 14:00)": ",".join(fomc),
                      "Noise check every, minutes": step},
                     timeframe_seconds=60, commission=0.95, slippage_ticks=2)
    rt.run()
    pine: dict = {}
    for t in rt.strategy.closed:
        k = (t["entry_bar"], t["dir"])
        pine[k] = round(pine.get(k, 0.0) + t["pnl"], 2)
    keys = sorted(set(py) | set(pine))
    rows = [{"entry_bar": k[0], "time": bars.index[k[0]], "d": k[1], "sleeve": py.get(k, ("-",))[0],
             "python $": py[k][1] if k in py else None, "pine $": pine.get(k)} for k in keys]
    return pd.DataFrame(rows)


def main() -> None:
    bars = rth_bars(sys.argv[1], sys.argv[2], sys.argv[3])
    t = compare(bars, int(sys.argv[4]) if len(sys.argv) > 4 else 30)
    same = t[(t["python $"].notna()) & (t["pine $"].notna()) & ((t["python $"] - t["pine $"]).abs() < 0.005)]
    n_py, n_pine = int(t["python $"].notna().sum()), int(t["pine $"].notna().sum())
    print(f"{len(bars)} bars; Python {n_py} campaigns, Pine {n_pine}; identical {len(same)}")
    pd.set_option("display.width", 200)
    print(t[~t.index.isin(same.index)].to_string(index=False))


if __name__ == "__main__":
    main()
