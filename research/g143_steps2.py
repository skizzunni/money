"""G143 (docs/NINJATRADER_V38.md): the faster steps' threshold and size around U34; G135's screen against U34.

    python research/g143_steps2.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

G.U33 = {**G.U33, "profit_step_fast": 750.0}  # U34
G.VARIANTS = [{}, {"profit_step_fast_from": 6000.0}, {"profit_step_fast": 500.0, "profit_step_fast_from": 15000.0}]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(3) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps(r), flush=True)
