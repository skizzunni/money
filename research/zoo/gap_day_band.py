"""Research (2026-11-25, docs section 118): the band's entries on days the gap trade traded, each period on its own.

Band trades by check (the 10:00 check, bar 6, against later) and by whether the gap trade traded that day; then the
account (fresh 50K starts, the shipped rules) with the later band trades on gap days dropped (an approximation: the
trades removed from the list, the rest unchanged; the day stop and trade cap then see fewer trades).
Run from research/: python zoo/gap_day_band.py
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
        gd = set(t[t.bar <= 1].d)
        band, on_gap = t.bar > 1, t.d.isin(gd)
        first, later = band & (t.bar == 6), band & (t.bar > 6)
        cells = (("10:00, gap day", first & on_gap), ("10:00, no gap trade", first & ~on_gap),
                 ("later, gap day", later & on_gap), ("later, no gap trade", later & ~on_gap))
        print(f"{lab}: " + " | ".join(f"{k} {m.sum()} tr ${t.usd[m].mean():.1f} PF {pf(t.usd[m]):.2f}"
                                      for k, m in cells))
        if n not in ("dev", "unseen_nq"):
            continue
        for name, keep in (("shipped", np.ones(len(t), bool)), ("later band trades on gap days dropped",
                                                                 ~(band & (t.bar > 6) & on_gap).values)):
            r = H.account(t[keep], d, steps=B.STEPS, day_stop=600.0, day_qty=B._news(d))
            p = np.array([x[1] for x in r])
            print(f"   {name}: lost {np.mean([x[0] for x in r]):.1%} median ${np.median(p):,.0f} "
                  f"p25 ${np.percentile(p, 25):,.0f}", flush=True)


if __name__ == "__main__":
    main()
