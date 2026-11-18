# ruff: noqa: E402, E501, E702, F403, F405, I001
import os as _os

HERE = _os.path.dirname(_os.path.abspath(__file__))
ROOT = _os.path.abspath(_os.path.join(HERE, '..', '..'))
import sys; import time; sys.path.insert(0,HERE); sys.path.insert(0,ROOT + '/tests')
import sets as S
from pine_interpreter import PineRuntime, load_pine
from win import *

S.load(); w=S.SETS['W'][0]
t0=time.time()
rt=PineRuntime(load_pine(ROOT + '/pine/' + sys.argv[1]), w, {}, timeframe_seconds=300)
rt.run(lambda i,g: None)
tr=[t for t in rt.strategy.closed if w.index[t['entry_bar']]>=pd.Timestamp('2026-08-21',tz=NY)]
pnl=pd.Series([t['pnl'] for t in tr]); days=pd.Series([w.index[t['exit_bar']].date() for t in tr])
day=pnl.groupby(days).sum(); eq=day.cumsum()
print(sys.argv[1], 'Aug21-Nov17: net', round(pnl.sum()), 'trades', len(tr), 'win', round((pnl>0).mean(),2), 'green days', round((day>0).mean(),2), 'worst day', round(day.min()), 'dd', round((eq.cummax().clip(lower=0)-eq).max()), f'{time.time()-t0:.0f}s')
import collections; print(collections.Counter(t['reason'] for t in tr))
