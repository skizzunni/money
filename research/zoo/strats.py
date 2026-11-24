# ruff: noqa: E501
"""Strategy families for research/zoo/harness.py (2026-11-23). Each: f(days, i, tick, **params) -> [(side, entry bar,
entry px, exit px, why)]. Regular-hours 5-minute bars; bar k starts at mm[k] (minutes from midnight New York) and
closes 5 minutes later; a signal at a bar's close fills at the next bar's open plus a tick (harness.walk)."""
from __future__ import annotations

import numpy as np
from harness import prev, walk

_cache: dict = {}


def _cached(key, obj, make):
    """A per-object cache that keeps the object alive and checks it, so a reused id() never serves stale values."""
    hit = _cache.get(key)
    if hit is None or hit[0] is not obj:
        hit = _cache[key] = (obj, make())
    return hit[1]


def _vwap(day):
    def make():
        typ = (day["h"] + day["l"] + day["c"]) / 3
        v = np.where(day["v"] > 0, day["v"], 1.0)
        return np.cumsum(typ * v) / np.cumsum(v)
    return _cached(("vwap", id(day)), day, make)


def _bar_at(day, minute):
    """The index of the bar starting at `minute` (or the first after it)."""
    k = np.searchsorted(day["mm"], minute)
    return int(k) if k < len(day["mm"]) else None


CHECKS = list(range(600, 901, 30))


def _moves(days, j):
    d = days[j]

    def make():
        return {m + 5: abs(d["c"][k] / d["o"][0] - 1) for k, m in enumerate(d["mm"]) if m + 5 in CHECKS}
    return _cached(("mv", id(d)), d, make)


def _tick(x, tick):
    """A price on the tick grid, as NinjaTrader's RoundToTickSize (round half to even)."""
    return float(np.round(x / tick) * tick)


def noise(days, i, tick, vwap=True, trend=0, hard=250.0, vwap_stop=False, pv=2.0, k=1.0, last=900, max_trades=9,
          be_r=0.0, stop_slip=2, nt=True, tp_r=0.0, tp_fill_bar=True):
    """The user's Clean Noise-Band spec (research/clean_noise_band.py): checks 10:00-15:00, the band (k x sigma) past
    max/min(open, prior close), the session VWAP agreeing, the band as a stop moved at the checks, a hard stop $hard a
    contract, out at 15:55. trend: also the close past the `trend`-session average of closes. be_r: the stop to entry +
    a tick once a bar closes be_r x the hard stop in profit. Returns (side, entry bar, entry, exit, why, exit bar).
    nt (as NinjaTrader executes it, research/zoo NinjaTrader parity): the hard stop measured from the expected fill
    (the signal close + a tick) and set with the entry; a check whose new stop is at or past the close exits at the next
    bar's open (a stop there would be rejected); the 15:55 exit at the open of the bar starting 15:55; stop fills
    stop_slip ticks worse."""
    if i < max(21, trend + 1):
        return []
    d = days[i]
    o, h, lo, c, mm = d["o"], d["h"], d["l"], d["c"], d["mm"]
    sig = {t: np.mean([_moves(days, j).get(t, np.nan) for j in range(i - 14, i)]) for t in CHECKS}
    pc = prev(days, i, "c")
    up_ref, dn_ref = max(o[0], pc), min(o[0], pc)
    sma = np.mean([prev(days, i, "c", j) for j in range(1, trend + 1)]) if trend else np.nan
    vw = _vwap(d)
    out = []
    pos, entry, stop, pend, pend_stop, ebar, exit_next, hard_ref = 0, 0.0, np.nan, 0, np.nan, 0, False, 0.0
    be_pts = be_r * hard / pv
    for b in range(len(o)):
        end = mm[b] + 5
        if pos and exit_next:  # a market exit sent at the last bar's close
            out.append((pos, ebar, entry, o[b] - pos * tick, "exit", b - 1))
            pos, exit_next = 0, False
        if pend and pos == 0:
            pos, entry, ebar = pend, o[b] + pend * tick, b
            stop = pend_stop
            tgt = _tick(entry + pos * tp_r * hard / pv, tick) if tp_r else np.nan
            pend = 0
        if pos and nt and mm[b] >= 955:
            out.append((pos, ebar, entry, o[b] - pos * tick, "time", b - 1))
            pos = 0
        if pos:
            if (pos > 0 and lo[b] <= stop) or (pos < 0 and h[b] >= stop):
                px = (min(o[b], stop) if pos > 0 else max(o[b], stop)) if (b > ebar or nt) else stop
                out.append((pos, ebar, entry, px - pos * stop_slip * tick, "stop", b))
                pos = 0
            elif tp_r and (tp_fill_bar or b > ebar) and pos * ((h[b] if pos > 0 else lo[b]) - tgt) >= tick:
                # a take-profit limit: from the fill bar in NinjaTrader (set with the entry), from the next in Pine
                out.append((pos, ebar, entry, tgt, "target", b))
                pos = 0
            elif be_r and pos * (c[b] - entry) >= be_pts:
                stop = max(stop, _tick(entry + pos * tick, tick)) if pos > 0 else min(stop, _tick(entry + pos * tick, tick))
        if end in sig and not np.isnan(sig[end]):
            s = sig[end] * k
            up, dn = up_ref * (1 + s), dn_ref * (1 - s)
            bl, bs = (max(up, vw[b]), min(dn, vw[b])) if vwap_stop else (up, dn)
            if pos:
                hard_px = hard_ref - pos * hard / pv
                band = bl if pos > 0 else bs
                new = max(band, hard_px) if pos > 0 else min(band, hard_px)
                if nt:
                    new = _tick(new, tick)  # NinjaTrader: the stop is only ever tightened
                    new = max(new, stop) if pos > 0 else min(new, stop)
                if pos * (c[b] - new) <= 0:
                    exit_next = True
                else:
                    stop = new
            elif end <= last and len(out) < max_trades and mm[b] < 950:
                want = 1 if c[b] > up else -1 if c[b] < dn else 0
                if want and vwap and want * (c[b] - vw[b]) <= 0:
                    want = 0
                if want and trend and want * (c[b] - sma) <= 0:
                    want = 0
                if want:
                    hard_ref = c[b] + want * tick
                    band = bl if want > 0 else bs
                    hp = hard_ref - want * hard / pv
                    pend, pend_stop = want, (max(band, hp) if want > 0 else min(band, hp))
                    if want * (hard_ref - pend_stop) <= 0:  # VWAP on the wrong side of the fill (no VWAP entry filter):
                        raw = up if want > 0 else dn       # the band alone (a stop past the price would be rejected)
                        pend_stop = max(raw, hp) if want > 0 else min(raw, hp)
                    if nt:
                        pend_stop = _tick(pend_stop, tick)
        if not nt and mm[b] >= 955 and pos:
            out.append((pos, ebar, entry, c[b] - pos * tick, "time", b))
            pos = 0
    if pos:
        out.append((pos, ebar, entry, c[-1] - pos * tick, "time", len(o) - 1))
    return out


def orb(days, i, tick, n=30, stop="far", r=0.0, cap=80.0, last=900, exit_m=955, be=0.0):
    """Opening-range breakout: the high / low of the first n minutes; the first 5-minute close beyond it before `last`
    enters; stop the other side ("far") or the middle, at most `cap` points; target r x the stop (0 none)."""
    d = days[i]
    mm, c = d["mm"], d["c"]
    rng = mm < 570 + n
    hi, lw = d["h"][rng].max(), d["l"][rng].min()
    for b in np.flatnonzero(~rng):
        if mm[b] + 5 > last or b + 1 >= len(c):
            return []
        side = 1 if c[b] > hi else -1 if c[b] < lw else 0
        if side:
            e = d["o"][b + 1] + side * tick
            ref = (lw if side > 0 else hi) if stop == "far" else (hi + lw) / 2
            dist = min(max(abs(e - ref), 4 * tick), cap)
            px, x, _, why = walk(d, b + 1, side, e - side * dist, e + side * r * dist if r else np.nan, exit_m, tick,
                                 be_at=be * dist if be else np.nan)
            return [(side, b + 1, px, x, why)]
    return []


def gap_fade(days, i, tick, k=1.0, stop_mult=1.0, exit_m=715, n=20, fill=1.0):
    """Fade an opening gap bigger than k x the n-session average |gap| toward the prior close (target `fill` of the gap),
    entered at 09:35's open, stop stop_mult x the gap beyond the 09:30 open."""
    if i < n + 1:
        return []
    d = days[i]
    pc = prev(days, i, "c")
    gap = d["o"][0] - pc
    avg = np.mean([abs(days[j]["o"][0] - prev(days, j, "c")) * d["s"] / days[j]["s"] for j in range(i - n, i)])
    if abs(gap) < k * avg or abs(gap) < 8 * tick:
        return []
    side = -1 if gap > 0 else 1
    st = d["o"][0] - side * stop_mult * abs(gap)
    tg = d["o"][0] + side * fill * abs(gap)
    px, x, _, why = walk(d, 1, side, st, tg, exit_m, tick)
    if side * (px - st) <= 0:
        return []
    return [(side, 1, px, x, why)]


def gap_go(days, i, tick, k=0.5, n=14, exit_m=955, r=0.0, cap=100.0):
    """Gap and go: a gap over k x the average with the 09:30 bar closing the gap's way; in at 09:35, stop at the 09:30
    open (at most cap points), target r x risk."""
    if i < n + 1:
        return []
    d = days[i]
    pc = prev(days, i, "c")
    gap = d["o"][0] - pc
    avg = np.mean([abs(days[j]["o"][0] - prev(days, j, "c")) * d["s"] / days[j]["s"] for j in range(i - n, i)])
    side = 1 if gap > 0 else -1
    if abs(gap) < k * avg or side * (d["c"][0] - d["o"][0]) <= 0:
        return []
    e = d["c"][0] + side * tick  # the expected fill: the signal close + a tick (NinjaTrader sets the stop with the entry)
    dist = min(max(abs(e - d["o"][0]), 4 * tick), cap)
    px, x, xb, why = walk(d, 1, side, e - side * dist, e + side * r * dist if r else np.nan, exit_m, tick, at_open=True)
    return [(side, 1, px, x, why, xb)]


def vwap_rev(days, i, tick, k=2.0, ks=3.5, first=600, last=900, exit_m=955, max_trades=2, trend_only=False):
    """VWAP reversion: a 5-minute close k standard deviations (of close - VWAP so far today) from VWAP fades back to
    VWAP; stop at ks deviations; trend_only: only against a stretch that is against the day's open-to-now direction."""
    d = days[i]
    c, mm = d["c"], d["mm"]
    vw = _vwap(d)
    dev = c - vw
    out, b = [], 0
    while b < len(c) - 1 and len(out) < max_trades:
        if mm[b] + 5 < first or mm[b] + 5 > last or b < 6:
            b += 1
            continue
        sd = np.sqrt(np.mean(dev[: b + 1] ** 2))
        if sd <= 0:
            b += 1
            continue
        z = dev[b] / sd
        side = -1 if z > k else 1 if z < -k else 0
        if side and trend_only and side * (c[b] - d["o"][0]) < 0:
            side = 0
        if side:
            st = vw[b] - side * ks * sd
            px, x, xb, why = walk(d, b + 1, side, st, vw[b], exit_m, tick)
            if side * (px - st) > 0:
                out.append((side, b + 1, px, x, why))
            b = xb + 1
        else:
            b += 1
    return out


def _rsi(x, n=2):
    dlt = np.diff(x, prepend=x[0])
    up, dn = np.clip(dlt, 0, None), np.clip(-dlt, 0, None)
    a = 1.0 / n
    ru, rd = np.zeros_like(x), np.zeros_like(x)
    for t in range(1, len(x)):
        ru[t] = ru[t - 1] + a * (up[t] - ru[t - 1])
        rd[t] = rd[t - 1] + a * (dn[t] - rd[t - 1])
    return 100 * ru / np.maximum(ru + rd, 1e-12)


def rsi2(days, i, tick, lo_th=10.0, hi_th=90.0, stop_pts=40.0, exit_rsi=60.0, first=600, last=900, max_trades=3):
    """RSI(2) pullbacks with the day's trend (the close on VWAP's side): long when RSI(2) < lo_th above VWAP, short when
    > hi_th below; out when RSI(2) crosses exit_rsi (100 - for shorts) at a bar's close, a stop of stop_pts, or 15:55."""
    d = days[i]
    c, mm = d["c"], d["mm"]
    vw = _vwap(d)
    r = _rsi(c)
    out, b = [], 0
    while b < len(c) - 1 and len(out) < max_trades:
        if not (first <= mm[b] + 5 <= last):
            b += 1
            continue
        side = 1 if (r[b] < lo_th and c[b] > vw[b]) else -1 if (r[b] > hi_th and c[b] < vw[b]) else 0
        if not side:
            b += 1
            continue
        e = d["o"][b + 1] + side * tick
        st = e - side * stop_pts
        x = None
        for k in range(b + 1, len(c)):
            if (side > 0 and d["l"][k] <= st) or (side < 0 and d["h"][k] >= st):
                f = (min(d["o"][k], st) if side > 0 else max(d["o"][k], st)) if k > b + 1 else st
                x, why = f - side * tick, "stop"
                break
            if (side > 0 and r[k] > exit_rsi) or (side < 0 and r[k] < 100 - exit_rsi) or mm[k] >= 955:
                x, why = c[k] - side * tick, "exit"
                break
        if x is None:
            k, x, why = len(c) - 1, c[-1] - side * tick, "time"
        out.append((side, b + 1, e, x, why))
        b = k + 1
    return out


def imom(days, i, tick, sig_end=600, enter=930, exit_m=955, stop_pts=60.0, from_close=True, min_move=0.0):
    """Intraday momentum (Gao, Han, Li & Zhou 2018): the return from the prior close (or today's open) to sig_end's
    close predicts the last half hour; in at `enter`'s open its way, out at exit_m's close, stop stop_pts."""
    if i < 2:
        return []
    d = days[i]
    ks, ke = _bar_at(d, sig_end - 5), _bar_at(d, enter)
    if ks is None or ke is None:
        return []
    ref = prev(days, i, "c") if from_close else d["o"][0]
    ret = d["c"][ks] / ref - 1
    if abs(ret) <= min_move:
        return []
    side = 1 if ret > 0 else -1
    e = d["o"][ke] + side * tick
    px, x, _, why = walk(d, ke, side, e - side * stop_pts, np.nan, exit_m, tick)
    return [(side, ke, px, x, why)]


def pdhl(days, i, tick, mode="break", buf=0.0, stop_pts=40.0, first=600, last=900, exit_m=955, r=0.0):
    """The prior day's high / low. break: the first close beyond it (from `first`) enters its way, stop stop_pts;
    fade: a bar trading through it and closing back inside enters back toward the range."""
    if i < 2:
        return []
    d = days[i]
    ph, pl = prev(days, i, "h"), prev(days, i, "l")
    c, h, lo, mm = d["c"], d["h"], d["l"], d["mm"]
    for b in range(len(c) - 1):
        if mm[b] + 5 < first:
            continue
        if mm[b] + 5 > last:
            return []
        side = 0
        if mode == "break":
            side = 1 if c[b] > ph + buf else -1 if c[b] < pl - buf else 0
        else:
            side = -1 if (h[b] > ph + buf and c[b] < ph) else 1 if (lo[b] < pl - buf and c[b] > pl) else 0
        if side:
            e = d["o"][b + 1] + side * tick
            px, x, _, why = walk(d, b + 1, side, e - side * stop_pts, e + side * r * stop_pts if r else np.nan, exit_m, tick)
            return [(side, b + 1, px, x, why)]
    return []


def _ema(x, n):
    a = 2 / (n + 1)
    out = np.empty_like(x)
    out[0] = x[0]
    for t in range(1, len(x)):
        out[t] = out[t - 1] + a * (x[t] - out[t - 1])
    return out


def ema_vwap(days, i, tick, f=9, s=21, stop_pts=40.0, first=600, last=900, max_trades=3):
    """EMA f / s crosses on 5-minute closes, only on VWAP's side; out at the opposite cross, the stop, or 15:55."""
    d = days[i]
    c, mm = d["c"], d["mm"]
    vw = _vwap(d)
    ef, es_ = _ema(c, f), _ema(c, s)
    out, b = [], 1
    while b < len(c) - 1 and len(out) < max_trades:
        if not (first <= mm[b] + 5 <= last):
            b += 1
            continue
        cu = ef[b] > es_[b] and ef[b - 1] <= es_[b - 1]
        cd = ef[b] < es_[b] and ef[b - 1] >= es_[b - 1]
        side = 1 if (cu and c[b] > vw[b]) else -1 if (cd and c[b] < vw[b]) else 0
        if not side:
            b += 1
            continue
        e = d["o"][b + 1] + side * tick
        st = e - side * stop_pts
        x = None
        for k in range(b + 1, len(c)):
            if (side > 0 and d["l"][k] <= st) or (side < 0 and d["h"][k] >= st):
                f_ = (min(d["o"][k], st) if side > 0 else max(d["o"][k], st)) if k > b + 1 else st
                x, why = f_ - side * tick, "stop"
                break
            if side * (ef[k] - es_[k]) < 0 or mm[k] >= 955:
                x, why = c[k] - side * tick, "exit"
                break
        if x is None:
            k, x, why = len(c) - 1, c[-1] - side * tick, "time"
        out.append((side, b + 1, e, x, why))
        b = k + 1
    return out


def drive(days, i, tick, n=30, top=0.8, stop="low", exit_m=955, r=0.0, cap=100.0):
    """Opening drive: the first n minutes close in the top (bottom) `top` share of their range and past the prior
    close; in at the next bar's open that way, stop at the range's other end (at most cap points)."""
    if i < 2:
        return []
    d = days[i]
    rng = d["mm"] < 570 + n
    k = int(np.flatnonzero(rng)[-1])
    hi, lw, cl = d["h"][rng].max(), d["l"][rng].min(), d["c"][k]
    if hi - lw <= 0:
        return []
    pos = (cl - lw) / (hi - lw)
    pc = prev(days, i, "c")
    side = 1 if (pos >= top and cl > pc) else -1 if (pos <= 1 - top and cl < pc) else 0
    if not side:
        return []
    e = d["o"][k + 1] + side * tick
    ref = lw if side > 0 else hi
    if stop == "mid":
        ref = (hi + lw) / 2
    dist = min(max(abs(e - ref), 4 * tick), cap)
    px, x, _, why = walk(d, k + 1, side, e - side * dist, e + side * r * dist if r else np.nan, exit_m, tick)
    return [(side, k + 1, px, x, why)]


def squeeze(days, i, tick, n=20, kb=2.0, stop_pts=40.0, first=600, last=900, exit_m=955):
    """A Bollinger(n, kb) breakout after the bands were at their narrowest of the day so far; one trade."""
    d = days[i]
    c, mm = d["c"], d["mm"]
    hist = np.concatenate([days[i - 1]["c"][-n:] * d["s"] / days[i - 1]["s"], c]) if i else c
    off = len(hist) - len(c)
    for b in range(len(c) - 1):
        if not (first <= mm[b] + 5 <= last):
            continue
        w = hist[off + b - n + 1: off + b + 1]
        m, sd = w.mean(), w.std()
        if c[b] > m + kb * sd or c[b] < m - kb * sd:
            widths = [hist[off + j - n + 1: off + j + 1].std() for j in range(max(0, b - 12), b)]
            if widths and sd * 0 + min(widths) <= np.percentile(widths, 25):
                side = 1 if c[b] > m else -1
                e = d["o"][b + 1] + side * tick
                px, x, _, why = walk(d, b + 1, side, e - side * stop_pts, np.nan, exit_m, tick)
                return [(side, b + 1, px, x, why)]
    return []


def merge(trades):
    """One position at a time: trades sorted by entry bar, one starting while an earlier one is open is dropped."""
    kept, busy_to = [], -1
    for t in sorted(trades, key=lambda t: t[1]):
        if t[1] <= busy_to:
            continue
        kept.append(t)
        busy_to = t[5] if len(t) > 5 else 10**9
    return kept


def combo(days, i, tick, legs=(), **_):
    """Several strategies on one account: each leg (function name, params); a leg's trade is skipped when it would
    overlap an earlier-starting trade of another leg (one position at a time), legs in the order given win ties."""
    out = []
    for name, p in legs:
        for t in globals()[name](days, i, tick, **p) or []:
            out.append(t)
    out.sort(key=lambda t: t[1])
    kept, busy_to = [], -1
    for t in out:
        if t[1] <= busy_to:
            continue
        kept.append(t)
        busy_to = t[5] if len(t) > 5 else _exit_bar(days[i], t)
    return kept


def _exit_bar(day, t):
    """The bar a trade closed on, found from its exit price path (the first bar from entry that trades its exit)."""
    side, b, _, x, _ = t
    for k in range(b, len(day["c"])):
        if day["l"][k] - 1 <= x <= day["h"][k] + 1:
            if k > b or True:
                return k
    return len(day["c"]) - 1
