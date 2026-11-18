# ruff: noqa: E402, E501, E702, F403, F405, I001
"""Focused on the user's ask (2026-11-18): profit kept, more trades, more green days, no repeat of Nov 17. Pine v4.0
(5 MNQ) with 15-minute checks, the last entry 15:30, a daily loss cap, losers a day, a stop once green late, a partial.
Each variant on W, NQ, IX (sets.py) and on the live days Nov 13, 16, 17."""
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

G = {"check_step": [30, 15], "daily_loss_limit": [0.0, 600.0, 900.0, 1250.0], "max_losers": [0, 2, 3],
     "day_stop_late_from": [0, 720, 780], "partial_at": [0.0, 1.0], "last_entry_end": [900, 930]}
V = [dict(zip(G, v)) for v in itertools.product(*G.values())]
DAYS = ("2026-11-13", "2026-11-16", "2026-11-17")

def cfg_of(v):
    c = dict(V4, **v)
    c["day_stop_late"] = 1.0 if v["day_stop_late_from"] else 0.0
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
