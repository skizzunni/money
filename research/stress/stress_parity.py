"""Stress: MnqCleanBand.cs on the NinjaTrader stand-in against the Python reference, trade for trade, on years of NQ."""
import sys, pickle, warnings, time, pathlib, tempfile
warnings.filterwarnings('ignore')
sys.path.insert(0, 'tests')
import numpy as np
import test_ninjatrader_clean as T
from test_ninjatrader import build, NT
sets = pickle.load(open(__import__("os").environ["ZOO_DATA"] + '/zoo_days_news.pkl', 'rb'))
out = pathlib.Path(tempfile.mkdtemp()); build(NT / "tests" / "Sim" / "Sim.csproj", out); sim = out / "Sim.dll"
def raw(days):
    res = []
    for d in days:
        r = dict(d); s = d['s'] or 1.0
        for k in ('o', 'h', 'l', 'c'):
            r[k] = np.round(d[k] / s / 0.25) * 0.25
        r['h'] = np.maximum(r['h'], np.maximum(r['o'], r['c'])); r['l'] = np.minimum(r['l'], np.minimum(r['o'], r['c']))
        r['s'] = 1.0; r['v'] = d.get('v', np.ones(len(d['o'])))
        res.append(r)
    return res
for name, chunks in (('dev', 1), ('unseen_nq', 1), ('live', 1)):
    days = raw(sets[name][0]) if name != 'live' else sets[name][0]
    for label, props, py in (("1 contract", dict(MaxContracts=1, DayStop=0), dict()),
                             ("account rules", dict(StartProfit=0), dict(day_stop=600.0, steps=((0, 1), (2000, 2), (3500, 3)), start=0.0))):
        t0 = time.time()
        path = out / f"{name}.csv"; idx = T.write_bars(days, path)
        lines = T._run_all(sim, path, **props)
        tt = [x.split(",")[1:] for x in lines if x.startswith("T,")]
        tn = [x.split(",")[1:] for x in lines if x.startswith("TN,")]
        errs = [x for x in lines if "Error" in x or "Exception" in x]
        got = [(int(t[0]), int(t[1]), round(float(t[2]), 6), round(float(t[4]), 6), int(n[1])) for t, n in zip(tt, tn)]
        ref = T.py_trades(days, idx, **py)
        if label == "1 contract":
            ref = [(a, b, c, e, 1) for a, b, c, e, _ in ref]
        same = got == ref
        first = next((k for k, (g, r) in enumerate(zip(got, ref)) if g != r), None)
        print(f"{name:10s} {label:14s}: {len(days)} sessions, NinjaTrader {len(got)} trades, reference {len(ref)}, identical {same}"
              f"{'' if same else f' (first difference at trade {first}: {got[first] if first is not None and first < len(got) else None} vs {ref[first] if first is not None and first < len(ref) else None})'}"
              f", errors {len(errs)}, {time.time() - t0:.0f}s", flush=True)
        for e in errs[:3]: print("   ", e)
