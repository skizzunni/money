"""Research (2026-11-26, docs section 176): the pre-open move (preopen_align.py) as a size or skip rule, on the
account with the cushion guard (bad_runs.runs: calendar starts from $50,000 / $48,806 / $48,998; near_floor_tiers
.shuffled: 2,000 runs of 252 days drawn from each period), each period on its own:
  - one more contract (the extra slot, at most 3) on band trades the pre-open move's way;
  - placebos: one more on random band trades at the same rate (5 draws);
  - no band trade against the pre-open move.
Run from research/: python zoo/preopen_add.py
"""
import pickle
import sys
import warnings

import numpy as np

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bad_runs as BR  # noqa: E402
import bench as B  # noqa: E402
import harness as H  # noqa: E402
import near_floor_tiers as NF  # noqa: E402
import preopen_align as PA  # noqa: E402
import strats as S  # noqa: E402


def run(lab, t, st, d):
    cal = []
    for start in NF.STARTS:
        r = BR.runs(t, d, B.STEPS, 600.0, B._news(d), strong=st, guard=1500.0, strong_below=1000.0, start=start)
        cal.append(f"${start:,.0f} {r.lost.mean():.1%} / ${r.profit.median():,.0f}")
    sh = NF.shuffled(t, st, d)
    print(f"  {lab}:\n     calendar: {' | '.join(cal)}\n     shuffled years: "
          + " ".join(f"${k:,.0f} {v[0]:.1%} / ${v[1]:,.0f}" for k, v in sh.items()), flush=True)


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25")):
        d, s = sets[n]
        print(lab)
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
        st = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, "min_stretch": 1.5})))
        al = np.array(PA.tag(d, t, 0.0))
        band = (t.bar > 1).to_numpy()
        base = t["add"].to_numpy().copy()
        run("shipped", t, st, d)
        sel = band & (al == "agree")
        t["add"] = np.where(sel, 1, base)
        run(f"one more on band trades the pre-open move's way ({sel.mean():.0%} of trades)", t, st, d)
        rng = np.random.default_rng(11)
        rate = sel.sum() / band.sum()
        for k in range(5):
            m = band & (rng.random(len(t)) < rate)
            t["add"] = np.where(m, 1, base)
            run(f"placebo {k + 1}: one more on random band trades at that rate", t, st, d)
        t["add"] = base
        keep = ~(band & (al == "against"))
        sal = np.array(PA.tag(d, st, 0.0))
        skeep = ~((st.bar > 1).to_numpy() & (sal == "against"))
        run("no band trade against the pre-open move", t[keep], st[skeep], d)


if __name__ == "__main__":
    main()
