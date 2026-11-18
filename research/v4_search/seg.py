# ruff: noqa: E402, E501, E702, F403, F405, I001
"""Per-period results for a list of variants: NQ 2015-19 / 2020-23 / 2024-25, IX 2011-18 / 2019-25-03, MNQ 2026-07-16..08-20
(never used to choose), the window W 2026-08-21..11-17. Raw strategy (no floor), 1 MNQ rules as configured."""
import os as _os

HERE = _os.path.dirname(_os.path.abspath(__file__))
ROOT = _os.path.abspath(_os.path.join(HERE, '..', '..'))

import json
import sys

sys.path[:0] = [HERE, ROOT + '/research', ROOT + '/tests', ROOT]
from concurrent.futures import ProcessPoolExecutor

import sets as S
from win import *

V = json.load(open(sys.argv[1]))
CUTS = {'NQ': [('NQ15-19', 2015, 2019), ('NQ20-23', 2020, 2023), ('NQ24-25', 2024, 2025)],
        'IX': [('IX11-18', 2011, 2018), ('IX19-25', 2019, 2025)]}

def one(i):
    cfg = dataclasses.replace(grow(), **V[i]); out = {'k': i, **V[i]}
    for s, cuts in CUTS.items():
        b, _ = S.SETS[s]
        tf = run(b, dataclasses.replace(cfg, trail_dd=0.0, gap_go_skip_month_first=True), minutes=5).trades_frame()
        y = tf.exit_time.dt.year
        for name, a, z in cuts:
            out[name] = round(float(tf.pnl[(y >= a) & (y <= z)].sum()))
    w = S.SETS['W'][0]
    for name, a, z in (('Jul-Aug', '2026-07-16', '2026-08-21'), ('W', '2026-08-21', '2026-11-18')):
        tf = run(w, dataclasses.replace(cfg, trail_dd=0.0, trail_from=a), minutes=5).trades_frame()
        tf = tf[(tf.entry_time >= pd.Timestamp(a, tz=NY)) & (tf.entry_time < pd.Timestamp(z, tz=NY))]
        out[name] = round(float(tf.pnl.sum()))
        if name == 'W':
            day = tf.groupby(tf.exit_time.dt.date).pnl.sum(); eq = day.cumsum()
            out['W dd'] = round(float((eq.cummax().clip(lower=0) - eq).max())); out['W win'] = round(float((tf.pnl > 0).mean()), 3)
            out['W green'] = round(float((day > 0).mean()), 3)
    return out

if __name__ == '__main__':
    with ProcessPoolExecutor(4, initializer=S.load) as ex, open(sys.argv[2], 'w') as f:
        for r in ex.map(one, range(len(V)), chunksize=2):
            f.write(json.dumps(r) + '\n'); f.flush()
