# ruff: noqa: E402, E501, E702, F403, F405, I001
"""Keeping more of the move (2026-11-18): trades averaged +$890 in favour against -$249 against on the user's chart.
Pine v4.0 (5 MNQ) with a partial take-profit (partial_at R, half the position), a trailing stop once the lock has armed
(trail_points) and the lock trigger. Each variant on W, NQ, IX and on the live days Nov 13, 16, 17."""
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

G = {"partial_at": [0.0, 0.5, 0.75, 1.0, 1.5], "trail_points": [0.0, 20.0, 40.0, 60.0, 100.0], "lock_at": [0.75, 1.25]}
V = [dict(zip(G, v, strict=True)) for v in itertools.product(*G.values())]
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
