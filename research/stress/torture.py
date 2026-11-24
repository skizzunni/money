# ruff: noqa
import sys, copy, pathlib, tempfile, warnings
warnings.filterwarnings('ignore'); sys.path.insert(0, 'tests')
import numpy as np
import test_ninjatrader_clean as T
from test_ninjatrader import build, NT
out = pathlib.Path(tempfile.mkdtemp()); build(NT / "tests" / "Sim" / "Sim.csproj", out); sim = out / "Sim.dll"
rng = np.random.default_rng(11)
def fix(d):
    for k in ('o', 'h', 'l', 'c'): d[k] = np.round(np.asarray(d[k], float) / 0.25) * 0.25
    d['h'] = np.maximum(d['h'], np.maximum(d['o'], d['c'])); d['l'] = np.minimum(d['l'], np.minimum(d['o'], d['c']))
    return d
def flat(d, px):
    n = len(d['o']); d.update(o=np.full(n, px), h=np.full(n, px), l=np.full(n, px), c=np.full(n, px)); return d
def shift(days, i, f):  # day i and later move by factor f (a gap)
    for d in days[i:]:
        for k in ('o', 'h', 'l', 'c'): d[k] = d[k] * f
def crash(d, frac):  # a steady fall of frac through the day
    n = len(d['o']); path = d['o'][0] * (1 - frac * np.arange(n + 1) / n)
    d.update(o=path[:-1], c=path[1:], h=np.maximum(path[:-1], path[1:]) * 1.0005, l=np.minimum(path[:-1], path[1:]) * 0.9995); return d
def scale_dev(d, m):
    o0 = d['o'][0]
    for k in ('o', 'h', 'l', 'c'): d[k] = o0 + (d[k] - o0) * m
    return d
def drop(d, ks):
    keep = np.ones(len(d['o']), bool); keep[ks] = False
    for k in ('o', 'h', 'l', 'c', 'v', 'mm'): d[k] = d[k][keep]
    return d
def scen():
    base = T.synthetic_days()
    yield "baseline", base, True
    s = copy.deepcopy(base); [flat(s[i], s[i - 1]['c'][-1]) for i in (30, 31, 60)]; yield "flat days (zero range)", [fix(d) for d in s], True
    s = copy.deepcopy(base); shift(s, 50, 1.08); shift(s, 90, 0.93); yield "gaps +8% / -7%", [fix(d) for d in s], True
    s = copy.deepcopy(base); crash(s[70], 0.10); shift(s, 71, s[70]['c'][-1] / s[71]['o'][0]); yield "crash day -10%", [fix(d) for d in s], True
    s = copy.deepcopy(base)
    for i in (80, 81):
        k = 40; s[i]['h'][k] = s[i]['o'][k] * 1.05; s[i]['c'][k] = s[i]['o'][k] * 1.04
        shift_after = s[i]['c'][k] / s[i]['o'][k + 1]
        for kk in ('o', 'h', 'l', 'c'): s[i][kk][k + 1:] = s[i][kk][k + 1:] * shift_after
    yield "5% one-bar spikes", [fix(d) for d in s], True
    s = copy.deepcopy(base); [scale_dev(s[i], 5) for i in range(100, 111)]; yield "5x volatility days", [fix(d) for d in s], True
    s = copy.deepcopy(base); [scale_dev(s[i], 0.05) for i in range(120, 131)]; yield "near-dead days", [fix(d) for d in s], True
    s = copy.deepcopy(base); [drop(s[i], sorted(rng.choice(np.arange(1, 77), 6, replace=False))) for i in range(40, 80, 3)]; yield "missing bars", s, False
    s = copy.deepcopy(base); [drop(s[i], np.arange(45, 78)) for i in (45, 100, 140)]; yield "half days", s, False
    s = copy.deepcopy(base); drop(s[0], np.arange(0, 30)); yield "data starts mid-session", s, False
for name, days, comparable in scen():
    path = out / "b.csv"; idx = T.write_bars(days, path)
    for props in (dict(MaxContracts=1, DayStop=0), dict(StartProfit=5000)):
        lines = T._run_all(sim, path, **props)
        tt = [x.split(",")[1:] for x in lines if x.startswith("T,")]
        tn = [x.split(",")[1:] for x in lines if x.startswith("TN,")]
        orders = [x.split(",")[1:] for x in lines if x.startswith("O,")]
        bad = [x for x in lines if ("Error" in x or "Exception" in x or "LOG:" in x)]
        overnight = [t for t in tt if idx[int(t[1])][0] != idx[int(t[3])][0]]
        stops = {(o[0], o[2]): float(o[3]) for o in orders if o[1] == "SetStopLoss"}
        nostop = wrong = 0
        for o in orders:
            if o[1] == "Enter":
                b, name_ = o[0], o[2]
                if (b, name_) not in stops: nostop += 1; continue
                di, k = idx[int(b)]; c = days[di]['c'][k]; side = 1 if "Long" in name_ else -1
                if side * (c + side * 0.25 - stops[(b, name_)]) <= 0: wrong += 1  # against the expected fill
        maxq = max([int(n[1]) for n in tn] or [0])
        daypl, late = {}, 0
        for t in tt:
            di = idx[int(t[1])][0]
            if daypl.get(di, 0) <= -600 and "StartProfit" in props: late += 1
            daypl[di] = daypl.get(di, 0) + float(t[6])
        par = ""
        if comparable:
            py = dict() if "MaxContracts" in props else dict(day_stop=600.0, steps=((0, 1), (2000, 2), (3500, 3)), start=5000.0)
            ref = T.py_trades(days, idx, **py)
            got = [(int(t[0]), int(t[1]), round(float(t[2]), 6), round(float(t[4]), 6), int(n[1])) for t, n in zip(tt, tn)]
            ref = [(a, b, c, e, (q if "StartProfit" in props else 1)) for a, b, c, e, q in ref]
            par = f", matches reference {got == ref}"
        ok = not bad and not overnight and not nostop and not wrong and maxq <= 3 and not late
        print(f"{'PASS' if ok else 'FAIL'} {name:24s} {'1 contract' if 'MaxContracts' in props else 'account   '}: {len(tt)} trades, errors {len(bad)}, overnight {len(overnight)}, "
              f"entries without a stop {nostop}, stop on the wrong side {wrong}, most contracts {maxq}, entries after the day stop {late}{par}", flush=True)
        for b in bad[:2]: print("    ", b)
