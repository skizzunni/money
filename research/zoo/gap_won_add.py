"""Research (2026-11-25, docs section 113): the band trades after the morning gap trade, each period on its own.

The band's trades split by today's gap trade (none / won / lost; same way or the other way), per set; then one
contract more (the existing extra-contract slot, at most 3) on band trades the same way as a gap trade that won by at
least $X a contract, on the account (fresh 50K starts, the shipped steps, news rule and $600 day stop), against a
placebo: the extra contract on random band trades at the same rate (20 draws).
Run from research/: python zoo/gap_won_add.py
"""
import pickle
import sys
import warnings

import numpy as np

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import harness as H  # noqa: E402
import strats as S  # noqa: E402


def pf(s):
    return s[s > 0].sum() / -s[s < 0].sum() if (s < 0).any() else np.inf


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("unseen_es", "ES 2020-24"), ("live", "live 2026")):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
        g = t[t.bar <= 1].groupby("d").agg(gu=("usd", "sum"), gs=("side", "first"))
        t = t.join(g, on="d")
        band = t.bar > 1
        won, lost = band & (t.gu > 0) & (t.side == t.gs), band & (t.gu < 0) & (t.side == t.gs)
        none = band & t.gu.isna()
        print(f"{lab}: band trades same way after a gap win {won.sum()} PF {pf(t.usd[won]):.2f}, after a gap loss "
              f"{lost.sum()} PF {pf(t.usd[lost]):.2f}, no gap trade {none.sum()} PF {pf(t.usd[none]):.2f}")
        if n not in ("dev", "unseen_nq"):
            continue

        def score(extra, t=t, d=d):
            u = t.copy()
            u["add"] = np.maximum(u["add"], extra.astype(int))
            r = H.account(u, d, steps=B.STEPS, day_stop=600.0, day_qty=B._news(d))
            p = np.array([x[1] for x in r])
            return np.mean([x[0] for x in r]), np.median(p), np.percentile(p, 25)
        base = score(np.zeros(len(t), bool))
        print(f"  account, shipped: lost {base[0]:.1%} median ${base[1]:,.0f} p25 ${base[2]:,.0f}")
        for x in (0, 25, 50, 100):
            sel = band & (t.gu > x) & (t.side == t.gs)
            r = score(sel.values)
            print(f"  +1 after a gap win over ${x}: {sel.sum()} trades, lost {r[0]:.1%} median {r[1] - base[1]:+,.0f} "
                  f"p25 {r[2] - base[2]:+,.0f}")
        rate = won.sum() / band.sum()
        rng, M, P = np.random.default_rng(3), [], []
        for _ in range(20):
            r = score((band & (rng.random(len(t)) < rate)).values)
            M.append(r[1] - base[1])
            P.append(r[2] - base[2])
        print(f"  placebo, +1 on random band trades at the same rate ({rate:.0%}): median {np.mean(M):+,.0f} "
              f"({min(M):+,.0f} to {max(M):+,.0f}) p25 {np.mean(P):+,.0f} ({min(P):+,.0f} to {max(P):+,.0f})",
              flush=True)


if __name__ == "__main__":
    main()
