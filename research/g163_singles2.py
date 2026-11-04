"""G163 (docs/NINJATRADER_V38.md): four more single settings on U34; G135's screen against U34.

    python research/g163_singles2.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

G.U33 = {**G.U33, "profit_step_fast": 750.0}  # U34
G.VARIANTS = [{}, {"max_losers": 2}, {"after_loss_qty_div": 2.0}, {"fed_no_shorts": False}, {"lock_intrabar": True}]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps(r), flush=True)
