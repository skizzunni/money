# ruff: noqa: E402, E501, E702, F403, F405, I001
"""Stage 2: given variant dicts (a JSON list file), evaluate each on W / NQ / IX (same output rows as search.py)."""
import os
import os as _os

HERE = _os.path.dirname(_os.path.abspath(__file__))
ROOT = _os.path.abspath(_os.path.join(HERE, '..', '..'))

import json
import sys

sys.path[:0] = [HERE, ROOT + '/research', ROOT + '/tests', ROOT]
from concurrent.futures import ProcessPoolExecutor

import sets as S
from win import grow

V = json.load(open(sys.argv[1]))

def one(i):
    try:
        r = S.evaluate(S.dataclasses.replace(grow(), **V[i]))
    except Exception as e:  # noqa: BLE001
        return {"k": i, **V[i], "error": str(e)[:200]}
    return {"k": i, **V[i], **{f"{n} {m}": (float(x) if not isinstance(x, str) else x) for n, d in r.items() for m, x in d.items()}}

if __name__ == "__main__":
    out = sys.argv[2]
    done = {json.loads(l)["k"] for l in open(out)} if os.path.exists(out) else set()
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4")), initializer=S.load) as ex, open(out, "a") as f:
        for r in ex.map(one, [i for i in range(len(V)) if i not in done], chunksize=2):
            f.write(json.dumps(r, default=str) + "\n"); f.flush()
