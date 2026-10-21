"""Walk-forward portfolio: each year, B's breakout weight and the pre-FOMC contracts with the best net / closed-day
drawdown over every earlier year (from 2015-03), traded that year; the chained out-of-sample years' minute equity and
intraday maximum drawdown on the full electronic session (research/portfolio_dd.py).

    python research/wf_portfolio.py <ratio_study folder> <rth bars pkl> <roll-adjusted pkl> <slippage> <first year>

Menu, fixed before any result of it: breakout off / $200 / $400 / $600 / $800 a trade, times 0 / 1 / 2 MNQ pre-FOMC.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfolio_dd as P  # noqa: E402

NAMES = ["B", "B + W risk 200", "B + Williams in the gaps", "B + W risk 600", "B + W risk 800"]
FOMC_Q = (0, 1, 2)


def closed_day_ratio(x: pd.Series) -> float:
    e = x.cumsum()
    dd = float((e.cummax().clip(lower=0) - e).max())
    return e.iloc[-1] / dd if dd else np.inf


def main() -> None:
    folder, rth, adj = Path(sys.argv[1]), pd.read_pickle(sys.argv[2]), pd.read_pickle(sys.argv[3])
    slip, first = int(sys.argv[4]), int(sys.argv[5])
    daily = {n: pd.read_csv(folder / f"trades_nq_{n.replace(' ', '_')}_{slip}t.csv", parse_dates=["day"])
             .groupby("day").pnl.sum() for n in NAMES}
    f1 = P.fomc_trades(adj[adj.index.year >= 2014], slip, 1)
    fd = f1.groupby(f1.t1.dt.tz_localize(None).dt.normalize()).pnl.sum()
    picks, legs = [], []
    for y in range(first, 2026):
        score = {}
        for n in NAMES:
            for q in FOMC_Q:
                j = pd.concat({"a": daily[n], "f": fd}, axis=1, sort=True).fillna(0)
                s = j.a + q * j.f
                score[(n, q)] = closed_day_ratio(s[s.index.year < y])
        n, q = max(score, key=score.get)
        picks.append({"year": y, "breakout": n, "FOMC MNQ": q})
        legs.append(P.bw_leg(folder, n, slip, rth, [y]))
        if q:
            fq = P.fomc_trades(adj[(adj.index.year >= y - 1) & (adj.index.year <= y)], slip, q)
            legs.append(fq[fq.t1.dt.year == y])
    timeline = adj.index.union(rth.index)
    timeline = timeline[(timeline.year >= first) & (timeline.year <= 2025)]
    eq, _ = P.minute_equity(timeline, legs)
    peak = np.concatenate([[0.0], np.maximum.accumulate(np.maximum(eq, 0.0))[:-1]])
    dd = float(np.max(peak - eq))
    net = sum(leg.pnl.sum() for leg in legs)
    gp = sum(leg.pnl[leg.pnl > 0].sum() for leg in legs)
    print(pd.DataFrame(picks).to_string(index=False))
    print(f"walk-forward {first}-2025, {slip} ticks: net {net:.0f}, gross profit {gp:.0f}, intraday DD {dd:.0f}, "
          f"net / DD {net / dd:.2f}, gross / DD {gp / dd:.1f}")


if __name__ == "__main__":
    main()
