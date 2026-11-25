"""Research (2026-11-25, docs section 159): days with missing 5-minute bars in the NQ sets, and the trades on them.

Analysis only: per set, the days with fewer than the 78 regular-hours bars (09:30-15:55) or a gap of more than 5
minutes between bars, where the gaps are, and the shipped strategy's trades on those days (1 contract) against the
average day. Run from research/: python zoo/data_gaps.py
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


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("unseen_es", "ES 2020-24"), ("live", "live 2026")):
        d, s = sets[n]
        bad = {}
        for x in d:
            mm = np.asarray(x["mm"])
            holes = [(int(a), int(b)) for a, b in zip(mm[:-1], mm[1:], strict=True) if b - a > 5]
            short = mm[0] != 570 or mm[-1] < 955
            if len(mm) < 78 or holes:
                bad[x["d"]] = (len(mm), holes, short)
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        on = t[t.d.isin(list(bad))]
        early = sum(1 for v in bad.values() if v[2])
        print(f"{lab}: {len(d)} days, {len(bad)} with missing bars ({early} of them end early or start late: half days "
              f"or a short session), {sum(1 for v in bad.values() if v[1])} with a hole inside the session")
        holes = {k: v for k, v in bad.items() if v[1]}
        for k, v in list(holes.items())[:12]:
            hs = ", ".join(f"{a // 60}:{a % 60:02d}-{b // 60}:{b % 60:02d}" for a, b in v[0:1] and v[1])
            print(f"   {k}: {v[0]} bars, gaps after {hs}")
        if len(holes) > 12:
            print(f"   ... and {len(holes) - 12} more")
        per = t.groupby("d").usd.sum()
        print(f"   trades on those days: {len(on)} (${on.usd.sum():,.0f}), "
              f"${on.groupby('d').usd.sum().mean():.1f} a traded day against ${per.mean():.1f} on all", flush=True)


if __name__ == "__main__":
    main()
