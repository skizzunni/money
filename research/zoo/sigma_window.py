# ruff: noqa
import sys, pickle
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import bench as B, harness as H, strats as S
sets = pickle.load(open(B.PK, "rb"))
def score(n, band):
    d, s = sets[n]
    t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, **band})))
    t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
    r = H.account(t, d, steps=B.STEPS, day_stop=600.0, day_qty=B._news(d))
    p = np.array([x[1] for x in r])
    return f"lost {np.mean([x[0] for x in r]):.1%} med ${np.median(p):,.0f} p25 ${np.percentile(p, 25):,.0f} {len(t)/(len(d)/252):.0f} tr/yr"
for lab, band in (("shipped (14)", {}), ("10 sessions", {"sig_n": 10}), ("20 sessions", {"sig_n": 20}), ("30 sessions", {"sig_n": 30})):
    tv = B.line("", B.run(band=band)).split("|")[1].strip()
    print(f"{lab}: 2015-19 {score('dev', band)} | 2020-25 {score('unseen_nq', band)} | {tv}", flush=True)
