"""Research (2026-11-25, docs section 146): MNQ's closest near-misses by year (1 contract, all trades, NQ sets).

The shipped settings against: the move cap 1.0 (139), the stop step from 1.75R (140), the gap 0.65x (142-143) and
the trend 15 sessions (141); $ a year at 1 MNQ on dev + unseen NQ + live, and the years each beats the shipped.
Analysis only. Run from research/: python zoo/near_miss_years.py
"""
import pickle
import sys
import warnings

import pandas as pd

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import harness as H  # noqa: E402
import strats as S  # noqa: E402

ROWS = (("shipped", {}, {}), ("move cap 1.0", {"max_move": 1.0}, {}), ("stop step 1.75R", {"lad_r": 1.75}, {}),
        ("gap 0.65x", {}, {"k": 0.65}), ("trend 15", {"trend": 15}, {}))


def main():
    sets = pickle.load(open(B.PK, "rb"))
    cols = {}
    for lab, band, gap in ROWS:
        ys = []
        for n in ("dev", "unseen_nq", "live"):
            d, s = sets[n]
            t = H.trades_of(S.everyday, d, s, legs=(("gap_go", {**B.GAP, **gap}), ("noise", {**B.BAND, **band})))
            ys.append(t.groupby(pd.to_datetime(t.d).dt.year).usd.sum())
        cols[lab] = pd.concat(ys).groupby(level=0).sum()
    df = pd.DataFrame(cols).round(0)
    print(df.astype(int).to_string())
    for lab in df.columns[1:]:
        diff = df[lab] - df["shipped"]
        up = ", ".join(str(y) for y in diff[diff > 0].index)
        print(f"{lab}: beats the shipped in {int((diff > 0).sum())} of {len(diff)} years ({up}); "
              f"total {diff.sum():+,.0f}; largest year {diff.idxmax()} {diff.max():+,.0f}; "
              f"without it {diff.sum() - diff.max():+,.0f}")


if __name__ == "__main__":
    main()
