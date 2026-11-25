"""Research (2026-11-25, docs section 139): the band's break-even, hard stop, move cap and range rule by period.

Sections 63-65 checked them with 61 in on the pooled 104 starts (the per-set trade PF only by period). Here each
period's fresh 50K starts on their own (the shipped account rules) and the TradingView window, one step each way.
--widen (docs 150): the hard stop only widened on wild days. Run from research/: python zoo/risk_settings_by_period.py
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


def score(sets, n, band):
    d, s = sets[n]
    t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, **band})))
    t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
    r = H.account(t, d, steps=B.STEPS, day_stop=600.0, day_qty=B._news(d))
    p = np.array([x[1] for x in r])
    return f"lost {np.mean([x[0] for x in r]):.1%} median ${np.median(p):,.0f} p25 ${np.percentile(p, 25):,.0f}"


def main():
    sets = pickle.load(open(B.PK, "rb"))
    rows = (("shipped", {}), ("break-even 0.3R", {"be_r": 0.3}), ("break-even 0.5R", {"be_r": 0.5}),
            ("hard stop $175", {"hard": 175.0}), ("hard stop $225", {"hard": 225.0}),
            ("move cap 1.0", {"max_move": 1.0}), ("move cap 1.2", {"max_move": 1.2}),
            ("range rule 0.6", {"range_pos": 0.6}), ("range rule 0.7", {"range_pos": 0.7}))
    if "--widen" in sys.argv:  # docs 150: the hard stop only widened on wild days (hard_vol, never under 100 points)
        rows = (("shipped", {}),) + tuple(
            (f"hard stop max(100, {hv} x 14-day range) up to {hi:.0f} points",
             {"hard_vol": hv, "hard_lo": 100.0, "hard_hi": hi})
            for hv in (0.25, 0.3) for hi in (125.0, 150.0))
    for lab, band in rows:
        tv = B.line("", B.run(band=band)).split("|")[1].strip()
        print(f"{lab}: 2015-19 {score(sets, 'dev', band)} | 2020-25 {score(sets, 'unseen_nq', band)} | {tv}",
              flush=True)


if __name__ == "__main__":
    main()
