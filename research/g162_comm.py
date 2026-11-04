"""G162 (docs/NINJATRADER_V38.md): the commission saving of minis, an upper bound; G135's screen against U34.

    python research/g162_comm.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

G.U33 = {**G.U33, "profit_step_fast": 750.0}  # U34
G.VARIANTS = [{}, {"commission_per_side": 0.30}]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(2) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps(r), flush=True)
