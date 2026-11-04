"""G116 (docs/NINJATRADER_V38.md): one setting at a time, settings not re-checked on U29, chart's execution, 5-minute.

    python research/g116_sweep.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import g115_search as G
import v24_scan as S

VARIANTS = [{}, {"max_loss_per_trade": 150.0}, {"max_loss_per_trade": 225.0}, {"max_loss_per_trade": 250.0},
            {"after_loss_ml_mult": 1.0}, {"after_loss_ml_mult": 1.6667}, {"profit_step": 1250.0},
            {"profit_step": 1750.0}, {"last_entry_end": 870}, {"last_entry_end": 930}, {"squeeze_min": 15.0},
            {"squeeze_min": 25.0}, {"trend_n": 40}, {"trend_n": 60}, {"max_losers": 3}, {"lookback": 10},
            {"lookback": 20}, {"entry_k": 0.9}, {"entry_k": 1.1}]


def one(k: int) -> dict:
    G.combos = lambda n=32: [VARIANTS[k]] * len(VARIANTS)  # reuse G115's runner with this variant
    return G.one(k)


if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(one, range(len(VARIANTS))):
            print(json.dumps(r), flush=True)
