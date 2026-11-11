"""G388 (docs/NINJATRADER_V38.md): one funded account: U48 plus Larry Williams' volatility breakout in the bot's gaps
(rounds 97-101 in docs/RESULTS.md, rebuilt on 5-minute bars): stop orders at today's 09:30 open +/- 0.5 x yesterday's
regular-hours range, the first side triggered only, entries by 15:00; stop 0.25 x yesterday's range from the fill;
contracts floor($R / (stop x $2)), 1-10 MNQ (1 if that risks at most 1.5 x $R, else no trade); out at the 15:55 bar's
close less a tick; a tick of slippage on the entry and the stop; $0.62 a side a contract; the stop counts on the fill
bar. A Williams trade is kept only if no U48 trade is open at any time between its entry and exit (the bot first).
G372's measure (U48 does not see the Williams P/L when it sizes).

    python research/g388_williams_gaps.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import math

import g250_test_week as G
import g372_faster_growth as M
import numpy as np
from g367_fade import Res, Tr

from mnqbot.noise import run as noise_run

TICK, PV, FEE = 0.25, 2.0, 0.62
M.VARIANTS = {"U48": {}, "U48 + Williams in the gaps, $200 risk": {"_w": 200.0},
              "U48 + Williams in the gaps, $400 risk": {"_w": 400.0}}


def williams(b, risk):
    t = b.index.tz_convert(G.NY)
    mins = t.hour.to_numpy() * 60 + t.minute.to_numpy()
    o, h, l, c = (b[x].to_numpy() for x in ("open", "high", "low", "close"))
    dates = np.array(t.date)
    out, prev_rng = [], math.nan
    starts = np.flatnonzero(np.r_[True, dates[1:] != dates[:-1]])
    ends = np.r_[starts[1:], len(b)]
    for a, z in zip(starts, ends, strict=False):
        rth = [k for k in range(a, z) if 570 <= mins[k] < 960]
        if not rth:
            continue
        if not math.isnan(prev_rng) and prev_rng > 0:
            op = o[rth[0]]
            up, dn = op + 0.5 * prev_rng, op - 0.5 * prev_rng
            for k in rth:
                if mins[k] >= 900:
                    break
                d = 1 if h[k] >= up else -1 if l[k] <= dn else 0
                if not d:
                    continue
                lvl = up if d > 0 else dn
                px = (max(o[k], lvl) if d > 0 else min(o[k], lvl)) + d * TICK
                sd = 0.25 * prev_rng
                q = math.floor(risk / (sd * PV))
                if q < 1:
                    if sd * PV > 1.5 * risk:
                        break
                    q = 1
                q = min(q, 10)
                stp = px - d * sd
                ex = None
                for j in range(k, rth[-1] + 1):
                    if (l[j] <= stp) if d > 0 else (h[j] >= stp):
                        gap = (o[j] < stp) if d > 0 else (o[j] > stp)
                        ex = (j, (o[j] if gap and j > k else stp) - d * TICK)
                        break
                    if mins[j] >= 955:
                        ex = (j, c[j] - d * TICK)
                        break
                if ex is None:
                    ex = (rth[-1], c[rth[-1]] - d * TICK)
                j, x = ex
                out.append(Tr(b.index[k], b.index[j], k, j, q, px, d, d * (x - px) * q * PV - 2 * FEE * q))
                break
        prev_rng = h[rth].max() - l[rth].min()
    return out


def run_with_w(b, cfg, minutes=5):
    res = noise_run(b, cfg, minutes=minutes)
    w = getattr(cfg, "_w", 0.0)
    if not w:
        return res
    busy = [(t.entry_bar, t.exit_bar) for t in res.trades]
    extra = [t for t in williams(b, w) if not any(e <= t.exit_bar and t.entry_bar <= x for e, x in busy)]
    return Res(sorted(list(res.trades) + extra, key=lambda t: t.entry_bar))


_job = M.job


def job(a):
    tag = a[0]
    w = M.VARIANTS[tag].get("_w", 0.0)
    M.VARIANTS[tag] = {k: v for k, v in M.VARIANTS[tag].items() if k != "_w"}

    def patched(b, cfg, minutes=5):
        cfg._w = w
        return run_with_w(b, cfg, minutes)

    M.run = patched
    try:
        return _job(a)
    finally:
        M.VARIANTS[tag]["_w"] = w


M.job = job
if __name__ == "__main__":
    M.main()
