# ruff: noqa: E402, E501, E702, F403, F405, I001
"""The user's chart window: MNQ 5-minute RTH, 2026-06-28 .. 2026-11-17 (repo series to 10/16, Yahoo after)."""
import os
import os as _os

HERE = _os.path.dirname(_os.path.abspath(__file__))
ROOT = _os.path.abspath(_os.path.join(HERE, '..', '..'))

import dataclasses
import sys

sys.path[:0] = [ROOT + '/research', ROOT + '/tests', ROOT]
import controlled as K
import pandas as pd

from mnqbot.data import resample
from mnqbot.noise import run

NY = "America/New_York"
D = os.environ.get('MNQ_DATA', 'data')

def bars():
    s = pd.read_csv(ROOT + '/tests/data/mnq_traded_eth_2026-06-28_2026-10-16.csv.gz', header=None,
                    names=['t', 'open', 'high', 'low', 'close'])
    s.index = pd.to_datetime(s.t).dt.tz_localize(NY); s = s.drop(columns='t').assign(volume=0.0)
    a = resample(K.rth(s), "5min")
    y = pd.read_pickle(f'{D}/yahoo_mnq_5m.pkl')
    y = y[y.index >= pd.Timestamp('2026-10-17', tz=NY)]
    t = y.index.hour * 60 + y.index.minute
    y = y[(t >= 570) & (t < 960)].assign(volume=0.0)
    y = clean(y)
    return pd.concat([a, y[['open', 'high', 'low', 'close', 'volume']]]).sort_index()

def clean(y):
    """Yahoo bad ticks: an open, high or low more than 400 points from both the previous close and the bar's close
    is replaced by the nearer of those (Oct 30 15:00 opened at 29,562 between bars at about 28,300)."""
    y = y.copy()
    pc = y.close.shift(1).fillna(y.open)
    for c in ("open", "high", "low"):
        bad = ((y[c] - pc).abs() > 400) & ((y[c] - y.close).abs() > 400)
        y.loc[bad, c] = pc[bad]
    y["high"] = y[["open", "high", "low", "close"]].max(axis=1)
    y["low"] = y[["open", "high", "low", "close"]].min(axis=1)
    return y

def grow(**kw):
    import test_ninjatrader_v38 as T
    return dataclasses.replace(T.GROW, **kw)

def result(cfg, b, start='2026-08-21'):
    cfg = dataclasses.replace(cfg, trail_from=start)
    tf = run(b, cfg, minutes=5).trades_frame()
    tf = tf[tf.entry_time >= pd.Timestamp(start, tz=NY)]
    day = tf.groupby(tf.exit_time.dt.date).pnl.sum()
    eq = day.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
    return dict(net=round(tf.pnl.sum()), trades=len(tf), win=round((tf.pnl > 0).mean(), 3),
                green_days=round((day > 0).mean(), 3), worst_day=round(day.min()), max_dd=round(dd))

if __name__ == '__main__':
    b = bars()
    print(b.index[0], b.index[-1], len(b))
    print('Funded growth (live):', result(grow(), b))
