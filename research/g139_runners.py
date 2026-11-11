"""G139 (docs/NINJATRADER_V38.md): letting the winners run, on U33; G135's screen.

    python research/g139_runners.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

G.VARIANTS = [{"take_profit": 0.0}, {"take_profit": 2.5}, {"take_profit": 3.0}, {"tp_keep": 0.5}, {"tp_keep": 0.5,
    "runner_lock": 0.5}]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps(r), flush=True)
