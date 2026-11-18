# ruff: noqa: E402, E501, E702, F403, F405, I001
"""Evaluation sets: W = the user's chart window (MNQ Aug 21 - Nov 17 2026), NQ 2015-2025 (exact), IX = the index
2011-2025-03 (HF mirror). Each run is one continuous account with no trailing floor (raw strategy), 1 MNQ sizing rules
as configured."""
import os
import os as _os

HERE = _os.path.dirname(_os.path.abspath(__file__))
ROOT = _os.path.abspath(_os.path.join(HERE, '..', '..'))

import sys
import time

sys.path[:0] = [HERE, ROOT + '/research', ROOT + '/tests', ROOT]
from g241_nt_search import with_1600
from win import *

D = os.environ.get('MNQ_DATA', 'data')
SETS = {}

def load():
    w = bars()
    t = w.index.hour * 60 + w.index.minute
    SETS['W'] = (with_1600(w, 5), '2026-08-21')
    for name, f, lo, hi in (('NQ', 'nq5m_scaled.pkl', '2015-01-01', '2025-07-01'), ('IX', 'bars5_scaled.pkl', '2011-01-01', '2025-03-21')):
        b = pd.read_pickle(f'{D}/{f}')
        b = b[(b.index >= pd.Timestamp(lo, tz=NY)) & (b.index < pd.Timestamp(hi, tz=NY))]
        t = b.index.tz_convert(NY); tm = t.hour * 60 + t.minute
        b = b[(tm >= 570) & (tm < 960)][['open', 'high', 'low', 'close', 'volume']]
        SETS[name] = (with_1600(b, 5), None)

def evaluate(cfg, names=('W', 'NQ', 'IX')):
    out = {}
    for n in names:
        b, start = SETS[n]
        c = dataclasses.replace(cfg, trail_dd=0.0, trail_from=start or "")
        if n != 'W':
            c = dataclasses.replace(c, gap_go_skip_month_first=True)
        tf = run(b, c, minutes=5).trades_frame()
        if start:
            tf = tf[tf.entry_time >= pd.Timestamp(start, tz=NY)]
        day = tf.groupby(tf.exit_time.dt.date).pnl.sum()
        eq = day.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
        yr = tf.groupby(tf.exit_time.dt.year).pnl.sum()
        out[n] = dict(net=round(tf.pnl.sum()), n=len(tf), win=round((tf.pnl > 0).mean(), 3),
                      green=round((day > 0).mean(), 3), worst_day=round(day.min()), dd=round(dd),
                      per_day=round(tf.pnl.sum() / max(1, len(set(b.index.date)) if not start else 62), 2),
                      yrs_up=f"{(yr > 0).sum()}/{len(yr)}")
    return out

if __name__ == '__main__':
    load()
    for n in ('W', 'NQ', 'IX'):
        t0 = time.time(); print(n, evaluate(grow(), (n,)), f"{time.time()-t0:.0f}s", flush=True)
