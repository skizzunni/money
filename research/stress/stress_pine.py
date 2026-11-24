import sys, pickle, warnings, time; warnings.filterwarnings('ignore'); sys.path.insert(0, 'tests')
import numpy as np, pandas as pd
import test_ninjatrader_clean as T
from test_pine_clean import bars_of, PINE
from pine_interpreter import PineRuntime, load_pine
sets = pickle.load(open('" + __import__("os").environ["ZOO_DATA"] + "/zoo_days_news.pkl', 'rb'))
def raw(days):
    res = []
    for d in days:
        r = dict(d); s = d['s'] or 1.0
        for k in ('o', 'h', 'l', 'c'): r[k] = np.round(d[k] / s / 0.25) * 0.25
        r['h'] = np.maximum(r['h'], np.maximum(r['o'], r['c'])); r['l'] = np.minimum(r['l'], np.minimum(r['o'], r['c'])); r['s'] = 1.0
        r['v'] = d.get('v', np.ones(len(d['o']))); res.append(r)
    return res
for label, days in (("NQ 2024 - Jun 2025", raw([d for d in sets['unseen_nq'][0] if d['d'].year >= 2024])),
                    ("NQ 2018-2019", raw([d for d in sets['dev'][0] if d['d'].year >= 2018]))):
    t0 = time.time()
    bars, idx = bars_of(days)
    for name, inputs, kw in (("1 contract", {"Most contracts": 1, "Day stop: no new entry once the day is down $ (0 = off)": 0}, {}),
                             ("account rules", {}, {"day_stop": 600.0, "steps": ((0, 1), (2000, 2), (3500, 3))})):
        rt = PineRuntime(load_pine(PINE), bars, inputs, timeframe_seconds=300); rt.run(lambda i, g: None)
        got = [(t["dir"], t["entry_bar"], round(t["entry"], 6), round(t["exit"], 6), t["qty"]) for t in rt.strategy.closed]
        ref = T.py_trades(days, idx, tp_fill_bar=False, max_q=(1 if name == "1 contract" else 3), **kw)
        print(f"Pine {label:20s} {name:14s}: {len(days)} sessions, Pine {len(got)} trades, reference {len(ref)}, identical {got == ref}, {time.time() - t0:.0f}s", flush=True)
