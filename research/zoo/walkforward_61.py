# ruff: noqa
"""Walk-forward of docs section 61: pick the stop-step / wild-open settings on 2015-19 (dev) starts only, score the
pick on 2020-25 (unseen NQ) starts it never saw."""
import sys, pickle
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import bench as B, harness as H, strats as S
sets = pickle.load(open(B.PK, "rb"))
LAD = [(0.0, 0.0), (1.25, 0.4), (1.5, 0.5), (1.75, 0.5)]
SKIP = [0.0, 1.5, 1.75, 2.0]
def score(n, lad, skip):
    d, s = sets[n]
    band = {**B.BAND, "lad_r": lad[0], "lad_lock": lad[1]}; gap = {**B.GAP, "max_bar": skip}
    t = H.trades_of(S.everyday, d, s, legs=(("gap_go", gap), ("noise", band)))
    t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
    r = H.account(t, d, steps=B.STEPS, day_stop=600.0, day_qty=B._news(d))
    p = np.array([x[1] for x in r])
    return np.mean([x[0] for x in r]), np.median(p), np.percentile(p, 25), t.usd.sum() / (len(d) / 252)
rows = []
for lad in LAD:
    for sk in SKIP:
        dv = score("dev", lad, sk); un = score("unseen_nq", lad, sk)
        rows.append((lad, sk, dv, un))
        print(f"ladder {lad} skip {sk}: dev lost {dv[0]:.1%} med ${dv[1]:,.0f} p25 ${dv[2]:,.0f} ${dv[3]:,.0f}/yr | unseen lost {un[0]:.1%} med ${un[1]:,.0f} p25 ${un[2]:,.0f} ${un[3]:,.0f}/yr", flush=True)
for key, name in ((lambda r: r[2][1], "dev median"), (lambda r: r[2][2], "dev 25th pct"), (lambda r: r[2][1] + r[2][2], "dev median + 25th")):
    best = max((r for r in rows if r[2][0] == 0), key=key)
    off = rows[0]
    print(f"picked on {name}: ladder {best[0]} skip {best[1]} -> unseen med ${best[3][1]:,.0f} p25 ${best[3][2]:,.0f} lost {best[3][0]:.1%} "
          f"(off: med ${off[3][1]:,.0f} p25 ${off[3][2]:,.0f} lost {off[3][0]:.1%})")
