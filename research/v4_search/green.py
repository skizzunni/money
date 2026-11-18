# ruff: noqa: E402, E501, E702, F403, F405, I001
"""Green days on top of Pine v4.0 (5 MNQ, no cap): day-level stops, partial exits, the lock and the take-profit, on the
window W, NQ 2015-2025 and the index 2011-2025 (sets.py). Random search; one JSON row per variant."""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
import sys
import json
import random
sys.path[:0] = [HERE, ROOT + '/research', ROOT + '/tests', ROOT]
from concurrent.futures import ProcessPoolExecutor
import sets as S
from win import *
from test_pine_v4 import V4
from mnqbot.noise import NoiseConfig

SPACE = {
    "day_stop_profit": [0.0, 250.0, 500.0, 1000.0, 2000.0],
    "day_stop_late_from": [0, 660, 720, 780, 840],
    "day_lock": [(0.0, 0.0), (500.0, 100.0), (1000.0, 250.0), (1500.0, 500.0), (750.0, 0.0)],
    "partial_at": [0.0, 0.5, 1.0, 1.5],
    "max_losers": [0, 1, 2, 3],
    "lock_at": [0.35, 0.75, 1.25],
    "take_profit": [1.0, 1.5, 2.0],
    "time_stop": [30, 45, 60],
}
rng = random.Random(7)
V = [{}]; seen = {"{}"}
while len(V) < int(os.environ.get("N", "1500")):
    v = {k: rng.choice(x) for k, x in SPACE.items()}
    key = json.dumps(v, sort_keys=True)
    if key not in seen:
        seen.add(key); V.append(v)

def cfg_of(v):
    c = dict(V4)
    for k, x in v.items():
        if k == "day_lock":
            c["day_lock_at"], c["day_lock_keep"] = x
        elif k == "day_stop_late_from":
            c["day_stop_late_from"], c["day_stop_late"] = x, (1.0 if x else 0.0)
        else:
            c[k] = x
    return NoiseConfig(**c, round_prices=True)

def one(i):
    try:
        r = S.evaluate(cfg_of(V[i]))
    except Exception as e:  # noqa: BLE001
        return {"k": i, **V[i], "error": str(e)[:200]}
    return {"k": i, **V[i], **{f"{n} {m}": (float(x) if not isinstance(x, str) else x) for n, d in r.items() for m, x in d.items()}}

if __name__ == "__main__":
    out = sys.argv[1]
    with ProcessPoolExecutor(4, initializer=S.load) as ex, open(out, "w") as f:
        for r in ex.map(one, range(len(V)), chunksize=4):
            f.write(json.dumps(r, default=str) + "\n"); f.flush()
