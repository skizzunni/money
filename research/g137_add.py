"""G137 (docs/NINJATRADER_V38.md): contracts added once the lock arms, on U33; G135's screen.

    python research/g137_add.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

G.VARIANTS = [{"add_at_lock": 2}, {"add_at_lock": 4}, {"add_at_lock": 8}]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(3) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps(r), flush=True)
