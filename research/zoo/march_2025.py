"""Research (2026-11-25, docs section 148): March 2025, the band's worst month, and the rules aimed at it.

Analysis: the month's trades, then two already-tested rules that target its pattern (repeated stops the same day):
strong breaks only after a stop the same day (noise reentry_min, section 106) and at most N losers a day (noise
max_losses, section 5), at 1 contract by year (NQ dev + unseen + live) and on March 2025 itself.
Run from research/: python zoo/march_2025.py
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

ROWS = (("shipped", {}), ("strong only after a stop (1.0 sigma)", {"reentry_min": 1.0}),
        ("at most 2 losers a day", {"max_losses": 2}), ("at most 3 losers a day", {"max_losses": 3}))


def main():
    sets = pickle.load(open(B.PK, "rb"))
    cols, mar = {}, {}
    for lab, band in ROWS:
        parts = []
        for n in ("dev", "unseen_nq", "live"):
            d, s = sets[n]
            t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, **band})))
            t["d"] = pd.to_datetime(t.d)
            parts.append(t)
        t = pd.concat(parts)
        cols[lab] = t.groupby(t.d.dt.year).usd.sum()
        m = t[(t.d >= "2025-03-01") & (t.d < "2025-04-01")]
        mar[lab] = (len(m), m.usd.sum())
    df = pd.DataFrame(cols).round(0)
    print(df.astype(int).to_string())
    for lab in df.columns:
        diff = df[lab] - df["shipped"]
        print(f"{lab}: March 2025 {mar[lab][0]} trades ${mar[lab][1]:+,.0f}; vs shipped in all years "
              f"{diff.sum():+,.0f}, up in {int((diff > 0).sum())} of {len(diff)} years")


if __name__ == "__main__":
    main()
