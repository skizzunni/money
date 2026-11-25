"""Research (2026-11-25, docs section 137): the gap trade's exit time, each period on its own.

gap_go exit_m (the shipped 590: the exit sent at the close of the 09:50 bar, filled at the 09:55 open), out
at 09:45-10:05, everything else shipped;
fresh 50K starts per period (the shipped account rules), the gap trade's own PF and $ by period, and the TradingView
window. Section 41 checked 10:00 / 10:10 / 10:15 pooled. Run from research/: python zoo/gap_exit_by_period.py
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
    for em in (580, 585, 590, 595, 600):
        gap = {**B.GAP, "exit_m": em}
        parts = []
        for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25")):
            d, s = sets[n]
            t = H.trades_of(S.everyday, d, s, legs=(("gap_go", gap), ("noise", B.BAND)))
            t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
            g = t[t.bar <= 1].usd
            r = H.account(t, d, steps=B.STEPS, day_stop=600.0, day_qty=B._news(d))
            p = np.array([x[1] for x in r])
            parts.append(f"{lab} gap PF {g[g > 0].sum() / -g[g < 0].sum():.2f} ${g.sum():,.0f}, lost "
                         f"{np.mean([x[0] for x in r]):.1%} median ${np.median(p):,.0f} "
                         f"p25 ${np.percentile(p, 25):,.0f}")
        tv = B.line("", B.run(gap={"exit_m": em})).split("|")[1].strip()
        lab = f"out {(em + 5) // 60}:{(em + 5) % 60:02d}" + (" (shipped)" if em == 590 else "")
        print(f"{lab}: " + " | ".join(parts) + f" | {tv}", flush=True)


if __name__ == "__main__":
    main()
