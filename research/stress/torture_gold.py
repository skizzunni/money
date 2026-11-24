# ruff: noqa
"""Torture scenarios for MgcOvernightCarry on the NinjaTrader stand-in: every trade checked (no errors, the stop set
with every entry on the right side, one trade a day, out the same trading day by 14:15 or on the next day's first bar,
at most 3 contracts)."""
import sys, copy, pathlib, tempfile, warnings
warnings.filterwarnings('ignore'); sys.path.insert(0, 'tests')
import numpy as np
import test_ninjatrader_gold as G
from test_ninjatrader import build, NT
out = pathlib.Path(tempfile.mkdtemp()); build(NT / "tests" / "Sim" / "Sim.csproj", out); sim = out / "Sim.dll"
def drop(d, ks):
    keep = np.ones(len(d['o']), bool); keep[ks] = False
    for k in ('o', 'h', 'l', 'c', 'mm'): d[k] = d[k][keep]
def scen():
    base = G.synthetic_gold(n=160, seed=9)
    yield "baseline", base
    s = copy.deepcopy(base)
    for i in range(30, 150, 7): drop(s[i], [int(np.searchsorted(s[i]['mm'], 860))])  # no 08:20 bar
    yield "missing 08:20 bars", s
    s = copy.deepcopy(base)
    for i in range(30, 150, 9): drop(s[i], np.flatnonzero(s[i]['mm'] >= 1110))  # the session ends at 12:30
    yield "early closes (12:30)", s
    s = copy.deepcopy(base)
    for i in (40, 41, 80):
        px = s[i - 1]['c'][-1]; n = len(s[i]['o'])
        for k in ('o', 'h', 'l', 'c'): s[i][k] = np.full(n, px)
    yield "flat days", s
    s = copy.deepcopy(base)
    for i in range(50, 60):
        o0 = s[i]['o'][0]
        for k in ('o', 'h', 'l', 'c'): s[i][k] = np.round(o0 + (s[i][k] - o0) * 5, 1)
        s[i]['h'] = np.maximum(s[i]['h'], np.maximum(s[i]['o'], s[i]['c'])); s[i]['l'] = np.minimum(s[i]['l'], np.minimum(s[i]['o'], s[i]['c']))
    yield "5x volatility", s
for name, days in scen():
    path = out / "g.csv"; idx = G.write_gold(days, path)
    for props in (dict(MaxContracts=1), dict(StartProfit=5000)):
        lines = G.run(sim, path, **props)
        tt = [x.split(",")[1:] for x in lines if x.startswith("T,")]
        tn = [x.split(",")[1:] for x in lines if x.startswith("TN,")]
        orders = [x.split(",")[1:] for x in lines if x.startswith("O,")]
        bad = [x for x in lines if "Error" in x or "Exception" in x or "LOG:" in x]
        stops = {(o[0], o[2]): float(o[3]) for o in orders if o[1] == "SetStopLoss"}
        nostop = wrong = 0
        for o in orders:
            if o[1] == "Enter":
                if (o[0], o[2]) not in stops: nostop += 1; continue
                di, k = idx[int(o[0])]; side = 1 if "Long" in o[2] else -1
                if side * (days[di]['c'][k] + side * 0.1 - stops[(o[0], o[2])]) <= 0: wrong += 1
        late = 0
        for t in tt:
            (d0, _), (d1, k1) = idx[int(t[1])], idx[int(t[3])]
            if not (d1 == d0 and days[d1]['mm'][k1] <= 1215) and not (d1 == d0 + 1 and k1 <= 1) and not (d1 == d0 and k1 == len(days[d1]['o']) - 1):
                late += 1
        perday = len({idx[int(t[1])][0] for t in tt}) == len(tt)
        maxq = max([int(n[1]) for n in tn] or [0])
        ok = not bad and not nostop and not wrong and not late and perday and maxq <= 3
        print(f"{'PASS' if ok else 'FAIL'} {name:22s} {'1 contract' if 'MaxContracts' in props else 'account   '}: {len(tt)} trades, errors {len(bad)}, "
              f"no stop {nostop}, wrong side {wrong}, late exits {late}, one a day {perday}, most contracts {maxq}", flush=True)
