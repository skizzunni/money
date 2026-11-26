"""Research (2026-11-26, docs section 165): how many trades and traded days a normal week brings, by period.

Analysis only (the shipped strategy, MNQ, 1 contract, NQ dev + unseen + live): per calendar week the trades, the
days with a trade and the $; the median and the quiet / busy 10%, and the share of weeks with no trade at all. A live
expectation for the user's "more trades" goal. Run from research/: python zoo/weekly_activity.py
"""
import pickle
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import harness as H  # noqa: E402
import strats as S  # noqa: E402


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("live", "live 2026")):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        days = pd.to_datetime(pd.Series([x["d"] for x in d]))
        wk = days.dt.to_period("W")
        t["w"] = pd.to_datetime(t.d).dt.to_period("W")
        g = t.groupby("w").agg(trades=("usd", "size"), days=("d", "nunique"), usd=("usd", "sum"))
        g = g.reindex(wk.unique(), fill_value=0)
        q = g.quantile([0.1, 0.5, 0.9])
        print(f"{lab}: {len(g)} weeks | trades a week median {q.trades[0.5]:.0f} (quiet 10% {q.trades[0.1]:.0f}, "
              f"busy 10% {q.trades[0.9]:.0f}) | days with a trade median {q.days[0.5]:.0f} of 5 | weeks with no "
              f"trade {np.mean(g.trades == 0):.0%} | weeks up {np.mean(g.usd > 0):.0%}, $ a week median "
              f"{q.usd[0.5]:.0f} at 1 MNQ", flush=True)


if __name__ == "__main__":
    main()
