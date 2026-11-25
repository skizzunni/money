"""Research (2026-11-25, docs section 140): two settings at once, by period (3 x 3, the shipped cell in the middle).

Grid "be_hard": break-even 0.35 / 0.4 / 0.45R x the hard stop $190 / $200 / $210. Grid "tp_lad": the target 2.25 /
2.5 / 2.75R x the second stop step from 1.25 / 1.5 / 1.75R. Fresh 50K starts per period (the shipped account rules)
and the TradingView window. Docs 141: "k_move" the band width 0.95 / 1.0 / 1.05 sigma x the move cap 1.0 / 1.1 / 1.2;
"range_trend" the range rule 0.6 / 0.65 / 0.7 x the trend 15 / 20 / 25 sessions. Docs 142 (the gap trade): "gap_cap"
the gap 0.55 / 0.6 / 0.65x x the stop cap 25 / 30 / 35 points; "body_bar" the body 2 / 3 / 4% x the wild open 1.5 /
1.75 / 2.0x.
Run from research/: python zoo/pair_grids.py be_hard|tp_lad|k_move|range_trend|gap_cap|body_bar
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

GRIDS = {"be_hard": ("be_r", (0.35, 0.4, 0.45), "hard", (190.0, 200.0, 210.0)),
         "tp_lad": ("tp_r", (2.25, 2.5, 2.75), "lad_r", (1.25, 1.5, 1.75)),
         "k_move": ("k", (0.95, 1.0, 1.05), "max_move", (1.0, 1.1, 1.2)),  # docs 141
         "range_trend": ("range_pos", (0.6, 0.65, 0.7), "trend", (15, 20, 25)),
         "gap_cap": ("gap:k", (0.55, 0.6, 0.65), "gap:cap", (25.0, 30.0, 35.0)),  # docs 142: gap-trade settings
         "body_bar": ("gap:min_body", (0.02, 0.03, 0.04), "gap:max_bar", (1.5, 1.75, 2.0))}


def split(kw):
    """{"gap:k": x, "be_r": y} -> (band settings, gap settings)."""
    return ({k: v for k, v in kw.items() if not k.startswith("gap:")},
            {k[4:]: v for k, v in kw.items() if k.startswith("gap:")})


def score(sets, n, kw):
    d, s = sets[n]
    band, gap = split(kw)
    t = H.trades_of(S.everyday, d, s, legs=(("gap_go", {**B.GAP, **gap}), ("noise", {**B.BAND, **band})))
    t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
    r = H.account(t, d, steps=B.STEPS, day_stop=600.0, day_qty=B._news(d))
    p = np.array([x[1] for x in r])
    return f"{np.mean([x[0] for x in r]):.1%} ${np.median(p):,.0f} / ${np.percentile(p, 25):,.0f}"


def main():
    sets = pickle.load(open(B.PK, "rb"))
    a, av, b, bv = GRIDS[sys.argv[1]]
    print(f"{a} x {b}: 2015-19 lost / median / p25 | 2020-25 lost / median / p25 | TradingView window")
    for x in av:
        for y in bv:
            band = {a: x, b: y}
            bd, gp = split(band)
            tv = B.line("", B.run(band=bd, gap=gp)).split("|")[1].strip()
            mark = " (shipped)" if (x, y) == (av[1], bv[1]) else ""
            print(f"{a} {x} {b} {y}{mark}: {score(sets, 'dev', band)} | {score(sets, 'unseen_nq', band)} | {tv}",
                  flush=True)


if __name__ == "__main__":
    main()
