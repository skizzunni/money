"""Research (2026-11-25, docs section 110): gold and MNQ on the same day, each period on its own.

Gold (mk_search.carry, as shipped) enters at 08:35, before MNQ's 09:35 gap trade, so no gold rule can use MNQ's day.
The other way: does gold's early result (stopped out by 09:30, or still open) say anything about MNQ's day (gap + band,
1 contract)? Also how often both lose, the correlation of the two days' $, and the size of gold's losses.
Run from research/: python zoo/gold_mnq_same_day.py PATH/gold5.pkl
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
import mk_search as K  # noqa: E402
import strats as S  # noqa: E402


def main():
    G = pickle.load(open(sys.argv[1], "rb"))
    for g in G:
        for k in ("o", "h", "l", "c"):
            g[k] = np.round(np.asarray(g[k]), 1)
    gi = {}
    for i in range(15, len(G)):
        for side, _e, e, x, why, xb in K.carry(G, i, 0.1):
            gi[G[i]["d"]] = ((x - e) * side * 10 - 1.24, why, int(G[i]["mm"][xb]) - 360)  # New York minutes
    gs = pd.DataFrame([(k, *v) for k, v in gi.items()], columns=["d", "usd", "why", "xt"])
    print(f"gold, all {len(gs)} trades 2009 - Mar 2025: {np.mean(gs.usd > 0):.0%} win, mean ${gs.usd.mean():.1f}; "
          f"losers ${gs.usd[gs.usd < 0].mean():.1f} on average (worst ${gs.usd.min():.0f}), "
          f"winners ${gs.usd[gs.usd > 0].mean():.0f}; "
          f"stopped by 09:30: {np.mean((gs.why == 'stop') & (gs.xt < 570)):.0%}")
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25")):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        mnq = pd.Series(0.0, index=[x["d"] for x in d]).add(t.groupby("d").usd.sum(), fill_value=0.0)
        g = gs.set_index("d").reindex(mnq.index).dropna()
        m = mnq[g.index]
        early = (g.why == "stop") & (g.xt < 570)
        both = (m < 0) & (g.usd < 0)
        print(f"{lab}: {len(g)} gold days; MNQ $ a day (1 contract) on all days {mnq.mean():.1f}, on gold days "
              f"{m.mean():.1f}; gold stopped by 09:30 ({early.sum()} days) {m[early].mean():.1f}, gold still open "
              f"({(~early).sum()} days) {m[~early].mean():.1f}; both lose {np.mean(both):.0%} of gold "
              f"days; correlation {np.corrcoef(m, g.usd)[0, 1]:.2f}; worst both-lose day "
              f"${(m + g.usd)[both].min():.0f}")


if __name__ == "__main__":
    main()
