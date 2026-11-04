"""G142 (docs/NINJATRADER_V38.md): faster contract steps once the account is well up, on U33; G135's screen.

    python research/g142_fast_steps.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

G.VARIANTS = [{}, {"profit_step_fast": 750.0}, {"profit_step_fast": 500.0}, {"profit_step_fast": 750.0, "profit_step_fast_from": 20000.0}]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps(r), flush=True)
