"""Research (2026-11-25, docs section 107): MNQ's contracts by the day's 14-session average range.

The ratio (realizable before the open): the mean daily range of the 14 sessions before today against the median of
that same 14-session mean over the year before (250 sessions). Tested within the 3-contract cap, on the shipped
trades (gap + band, the size steps, the news rule, the $600 day stop), each period on its own:
  - one contract fewer (at least 1) when the ratio is over 1.4 / 1.7 / 2.0, or 1 contract over 1.7;
  - one contract more (at most 3) when the ratio is under 0.8-1.1;
  - a placebo: one contract more on random days at the same rate as "under 0.9" (20 draws).
Run from research/: python zoo/range_sizing.py
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


def ratio(d, look=250):
    rg = np.array([(np.max(x["h"]) - np.min(x["l"])) / x["s"] for x in d])  # each day's range, today's scale
    out = {}
    for i in range(14 + 60, len(d)):
        ar = [np.mean(rg[j - 14:j]) for j in range(max(14, i - look), i + 1)]
        out[d[i]["d"]] = ar[-1] / np.median(ar[:-1])
    return out


def main():
    sets = pickle.load(open(B.PK, "rb"))
    T = {}
    for n in ("dev", "unseen_nq"):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
        T[n] = (d, t, ratio(d))

    def score(n, hi=0.0, lo=0.0, mode="cut", rand=None):
        d, t, r = T[n]
        nf = B._news(d)

        def f(day, q):
            q = nf(day, q)
            if q == 0:
                return 0
            x = r.get(day, np.nan)
            if rand is not None:
                return min(q + 1, 3) if day in rand else q
            if hi and x == x and x > hi:
                q = max(1, q - 1) if mode == "cut" else min(q, 1)
            if lo and x == x and x < lo:
                q = min(q + 1, 3)
            return q
        res = H.account(t, d, steps=B.STEPS, day_stop=600.0, day_qty=f)
        p = np.array([x[1] for x in res])
        return np.mean([x[0] for x in res]), np.median(p), np.percentile(p, 25)

    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25")):
        d, t, r = T[n]
        b = score(n)
        print(f"{lab} shipped: lost {b[0]:.1%} median ${b[1]:,.0f} p25 ${b[2]:,.0f}")
        rows = [(f"one fewer over {h}", dict(hi=h)) for h in (1.4, 1.7, 2.0)]
        rows += [("1 contract over 1.7", dict(hi=1.7, mode="one"))]
        rows += [(f"one more under {lo}", dict(lo=lo)) for lo in (0.8, 0.85, 0.9, 0.95, 1.0, 1.1)]
        for name, kw in rows:
            x = score(n, **kw)
            v_ = np.array(list(r.values()))
            frac = np.mean(v_ > kw["hi"]) if "hi" in kw else np.mean(v_ < kw["lo"])
            print(f"  {name}: {frac:.0%} of days, lost {x[0]:.1%} median {x[1] - b[1]:+,.0f} p25 {x[2] - b[2]:+,.0f}")
        frac = np.mean([v < 0.9 for v in r.values()])
        rng, keys, M, P = np.random.default_rng(7), np.array(list(r.keys()), dtype=object), [], []
        for _ in range(20):
            x = score(n, rand=set(keys[rng.random(len(keys)) < frac]))
            M.append(x[1] - b[1])
            P.append(x[2] - b[2])
        print(f"  placebo, one more on random {frac:.0%} of days (20 draws): median {np.mean(M):+,.0f} "
              f"({min(M):+,.0f} to {max(M):+,.0f}) p25 {np.mean(P):+,.0f} ({min(P):+,.0f} to {max(P):+,.0f})",
              flush=True)


if __name__ == "__main__":
    main()
