"""G140 (docs/NINJATRADER_V38.md): the trend rules on both sides, on U33; G135's screen.

    python research/g140_trend.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import g135_gap_screen as G
import v24_scan as S

G.VARIANTS = [{"trend_side": 0}, {"trend_n": 100}, {"trend_n": 100, "trend_side": 0}, {"giveback_brake": 0.6}]

if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(G.one, range(len(G.VARIANTS))):
            print(json.dumps(r), flush=True)
