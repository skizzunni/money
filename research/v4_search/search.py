# ruff: noqa: E402, E501, E702, F403, F405, I001
"""Random search around today's Funded growth: every variant on the window (W), NQ 2015-25 and the index 2011-25."""
import os
import os as _os

HERE = _os.path.dirname(_os.path.abspath(__file__))
ROOT = _os.path.abspath(_os.path.join(HERE, '..', '..'))

import json
import random
import sys

sys.path[:0] = [HERE, ROOT + '/research', ROOT + '/tests', ROOT]
from concurrent.futures import ProcessPoolExecutor

import sets as S
from win import grow

SPACE = {
    "take_profit": [1.25, 1.5, 1.75, 2.25, 2.5, 3.0], "lock_at": [0.0, 0.25, 0.5, 0.75, 1.0, 1.5],
    "lock_plus": [1.0, 5.0, 10.0, 20.0], "stop_buffer": [0.0, 0.12, 0.36, 0.5], "time_stop": [0, 30, 60, 90],
    "entry_k": [0.8, 0.9, 1.1, 1.25, 1.5], "lookback": [10, 20, 30], "max_losers": [1, 2, 3, 4],
    "last_entry_end": [780, 840, 870, 930], "skip_checks": ["600", "600,630", "780,810,840", "720,750,780"],
    "max_loss_per_trade": [125.0, 150.0, 250.0, 300.0], "trend_n": [20, 30, 60, 90], "trend_side": [0, 1],
    "calm_k": [0.0, 0.5, 0.9], "entry_k_regime": [0.0, 0.6, 1.0], "big_day_k": [0.0, 1.2, 2.0],
    "squeeze_min": [0.0, 10.0, 30.0], "range_pos_min": [0.5, 0.65, 0.8], "first_check": [630, 660],
    "gap_go": [False], "daily_loss_limit": [400.0, 600.0], "after_loss_tp": [1.0, 3.0],
}
rng = random.Random(int(os.environ.get("SEED", "520")))
V = [{}]
seen = {"{}"}
while len(V) < int(os.environ.get("N", "2000")):
    v = {k: rng.choice(SPACE[k]) for k in rng.sample(sorted(SPACE), rng.choice([1, 1, 2, 2, 3, 4]))}
    if json.dumps(v, sort_keys=True) not in seen:
        seen.add(json.dumps(v, sort_keys=True)); V.append(v)

def one(i):
    try:
        r = S.evaluate(S.dataclasses.replace(grow(), **V[i]))
    except Exception as e:  # noqa: BLE001
        return {"k": i, **V[i], "error": str(e)[:200]}
    return {"k": i, **V[i], **{f"{n} {m}": (float(x) if not isinstance(x, str) else x) for n, d in r.items() for m, x in d.items()}}

if __name__ == "__main__":
    out = sys.argv[1]
    done = {json.loads(l)["k"] for l in open(out)} if os.path.exists(out) else set()
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4")), initializer=S.load) as ex, open(out, "a") as f:
        for r in ex.map(one, [i for i in range(len(V)) if i not in done], chunksize=4):
            f.write(json.dumps(r, default=str) + "\n"); f.flush()
