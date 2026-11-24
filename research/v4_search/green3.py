# ruff: noqa: E402, E501, E702, F403, F405, I001
"""Losing streaks (2026-11-18): Pine v4.0 (5 MNQ) with side_run (after k losers in a row on one side, skip that side's
next signals until a winner on it), streak_k (after k losers in a row, skip the next signals) and losers a day. Each
variant on W, NQ, IX (sets.py) and on the live days Nov 13, 16, 17."""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
import sys
import json
import itertools
sys.path[:0] = [HERE, ROOT + '/research', ROOT + '/tests', ROOT]
from concurrent.futures import ProcessPoolExecutor
import sets as S
from win import *
from test_pine_v4 import V4
from mnqbot.noise import NoiseConfig

G = {"side_run_k": [0, 2, 3, 4], "side_run_skip": [1, 2, 4], "streak_k": [0, 3, 4, 5], "streak_skip": [1, 2], "max_losers": [0, 3]}
V = [dict(zip(G, v, strict=True)) for v in itertools.product(*G.values()) if (v[0] or v[1] == 1) and (v[2] or v[3] == 1)]
DAYS = ("2026-11-13", "2026-11-16", "2026-11-17")

def cfg_of(v):
    c = dict(V4, **v)
    return NoiseConfig(**c, round_prices=True)

def one(i):
    cfg = cfg_of(V[i])
    try:
        r = S.evaluate(cfg)
    except Exception as e:  # noqa: BLE001
        return {"k": i, **V[i], "error": str(e)[:200]}
    out = {"k": i, **V[i], **{f"{n} {m}": (float(x) if not isinstance(x, str) else x) for n, d in r.items() for m, x in d.items()}}
    b = S.SETS['W'][0]
    tf = run(b, dataclasses.replace(cfg, trail_from='2026-11-12'), minutes=5).trades_frame()
    for d in DAYS:
        out[d] = round(float(tf[tf.exit_time.dt.date.astype(str) == d].pnl.sum()))
    return out

if __name__ == "__main__":
    with ProcessPoolExecutor(4, initializer=S.load) as ex, open(sys.argv[1], "w") as f:
        for r in ex.map(one, range(len(V)), chunksize=2):
            f.write(json.dumps(r, default=str) + "\n"); f.flush()
