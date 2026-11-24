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

    def make():  # |close / open - 1| at every 5-minute bar's close from 10:00 to 15:00
        return {m + 5: abs(d["c"][k] / d["o"][0] - 1) for k, m in enumerate(d["mm"]) if 600 <= m + 5 <= 900}
    return _cached(("mv", id(d)), d, make)


def _tick(x, tick):
    """A price on the tick grid, as NinjaTrader's RoundToTickSize (round half to even)."""
    return float(np.round(x / tick) * tick)


def noise(days, i, tick, vwap=True, trend=0, hard=250.0, vwap_stop=False, pv=2.0, k=1.0, last=900, max_trades=9,
          be_r=0.0, stop_slip=2, nt=True, tp_r=0.0, tp_fill_bar=True, step=30, range_pos=0.0, tp_frac=1.0,
          runner_lock=0.0, max_move=0.0, be_plus=0.0, counter_k=0.0, after_target="", move_free="", min_stretch=0.0, stretch_gap=False, move_ref="open", hard_vol=0.0, hard_lo=0.0, hard_hi=1e9, max_losses=0, strong_at=0.0, strong_tp=0.0, stale=0, band_ref="both", be_on="close", exit_at=955, trend_ema=False, check_off=0, strong_last=0, be_skip_strong=0.0, vwap_after_be=False, band_stop_at=0.0, bar_pos=0.0, bar_n=1, lad_r=0.0, lad_lock=0.0, late_at=0, late_tp=0.0, extra_checks=(), trend_gap_k=0.0, sig_n=14, vwap_until=0, limit_in=False):
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
    checks = list(range(600 + check_off, 901, step))  # research (2026-11-24): every `step` minutes from 10:00 + check_off
    checks = sorted(set(checks) | set(extra_checks))  # research (2026-11-24): extra check times (bar ends, minutes)
    # research (2026-11-24): sig_n sessions in the noise area's average (14 shipped)
    sig = {t: np.mean([_moves(days, j).get(t, np.nan) for j in range(i - sig_n, i)]) for t in checks}
    pc = prev(days, i, "c")
    up_ref, dn_ref = max(o[0], pc), min(o[0], pc)
    if band_ref == "open":  # research (2026-11-24): the band from the open alone, or half way to the prior close
        up_ref = dn_ref = o[0]
    elif band_ref == "half":
        up_ref, dn_ref = (o[0] + up_ref) / 2, (o[0] + dn_ref) / 2
    sma = np.mean([prev(days, i, "c", j) for j in range(1, trend + 1)]) if trend else np.nan
    if trend and trend_ema:  # research (2026-11-24): an exponential average of the prior closes instead (alpha 2/(n+1))
        a_ = 2.0 / (trend + 1)
        sma = prev(days, i, "c", min(i, 3 * trend))
        for j in range(min(i, 3 * trend) - 1, 0, -1):
            sma = a_ * prev(days, i, "c", j) + (1 - a_) * sma
    vw = _vwap(d)
    if hard_vol:  # research (2026-11-24): the hard stop (and so break-even and target) hard_vol x the 14-day average range
        avg14 = np.mean([(days[j]["h"].max() - days[j]["l"].min()) * d["s"] / days[j]["s"] for j in range(i - 14, i)])
        hard = pv * min(max(hard_vol * avg14, hard_lo), hard_hi)
    out = []
    pos, entry, stop, pend, pend_stop, ebar, exit_next, hard_ref = 0, 0.0, np.nan, 0, np.nan, 0, False, 0.0
    nchk, be_hit = 0, False  # research (2026-11-24, stale): checks held, break-even reached
    pend_strong = no_be = False  # research (be_skip_strong): no break-even for a strong break
    pend_tp = tp_r  # research (2026-11-24): strong_tp x the hard stop as the target on entries strong_at sigmas past
    banked = None  # research (tp_frac < 1): the part taken at the target; the rest runs on the band / break-even stop

    def done(x):  # the trade's exit price as one position: the banked part at the target, the rest at x
        return x if banked is None else entry + tp_frac * (banked - entry) + (1 - tp_frac) * (x - entry)
    be_pts = be_r * hard / pv
    for b in range(len(o)):
        end = mm[b] + 5
        if pos and exit_next:  # a market exit sent at the last bar's close
            out.append((pos, ebar, entry, done(o[b] - pos * tick), "exit", b - 1))
            pos, exit_next, banked = 0, False, None
        if pend and pos == 0 and limit_in and not ((pend > 0 and lo[b] <= pend_px) or (pend < 0 and h[b] >= pend_px)):
            pend = 0  # research (2026-11-24): a limit at the signal close that the next bar does not reach: no trade
        if pend and pos == 0:
            pos, entry, ebar = pend, (o[b] + pend * tick) if not limit_in else (min(o[b], pend_px) if pend > 0 else max(o[b], pend_px)), b
            stop = pend_stop
            nchk, be_hit = 0, False
            no_be = pend_strong
            banked = None
            tgt = _tick(entry + pos * pend_tp * hard / pv, tick) if tp_r else np.nan
            pend = 0
        if pos and nt and mm[b] >= exit_at:
            out.append((pos, ebar, entry, done(o[b] - pos * tick), "time", b - 1))
            pos = 0
        if pos:
            if (pos > 0 and lo[b] <= stop) or (pos < 0 and h[b] >= stop):
                px = (min(o[b], stop) if pos > 0 else max(o[b], stop)) if (b > ebar or nt) else stop
                out.append((pos, ebar, entry, done(px - pos * stop_slip * tick), "stop", b))
                pos = 0
            elif tp_r and banked is None and tp_frac < 1 and (tp_fill_bar or b > ebar) and pos * ((h[b] if pos > 0 else lo[b]) - tgt) >= tick:
                banked = tgt  # part off at the target; the runner's stop to at least entry + runner_lock x the target distance
                lock = _tick(entry + runner_lock * (tgt - entry), tick)
                stop = max(stop, lock) if pos > 0 else min(stop, lock)
            elif tp_r and tp_frac >= 1 and (tp_fill_bar or b > ebar) and pos * ((h[b] if pos > 0 else lo[b]) - tgt) >= tick:
                # a take-profit limit: from the fill bar in NinjaTrader (set with the entry), from the next in Pine
                out.append((pos, ebar, entry, tgt, "target", b))
                pos = 0
            elif be_r and not no_be and pos * ((c[b] if be_on == "close" else h[b] if pos > 0 else lo[b]) - entry) >= be_pts:
                be_hit = True
                lk = _tick(entry + pos * max(tick, be_plus), tick)  # be_plus: the break-even stop this many points past entry
                stop = max(stop, lk) if pos > 0 else min(stop, lk)
            if pos and lad_r and pos * (c[b] - entry) >= lad_r * hard / pv:  # research (2026-11-24): a second stop step
                lk = _tick(entry + pos * lad_lock * hard / pv, tick)         # (a close lad_r x the hard stop up)
                stop = max(stop, lk) if pos > 0 else min(stop, lk)
        if end in sig and not np.isnan(sig[end]):
            s = sig[end] * k
            up, dn = up_ref * (1 + s), dn_ref * (1 - s)
            bl, bs = (max(up, vw[b]), min(dn, vw[b])) if vwap_stop else (up, dn)
            if pos and vwap_after_be and not be_hit:  # research (2026-11-24): VWAP tightens the stop only after break-even
                bl, bs = up, dn
            if pos and vwap_until and end > vwap_until:  # research (2026-11-24): VWAP tightens the stop only until vwap_until
                bl, bs = up, dn
            if pos:
                hard_px = hard_ref - pos * hard / pv
                band = bl if pos > 0 else bs
                new = max(band, hard_px) if pos > 0 else min(band, hard_px)
                if nt:
                    new = _tick(new, tick)  # NinjaTrader: the stop is only ever tightened
                    new = max(new, stop) if pos > 0 else min(new, stop)
                nchk += 1
                if pos * (c[b] - new) <= 0 or (stale and nchk >= stale and not be_hit):
                    exit_next = True
                else:
                    stop = new
            elif end <= max(last, strong_last) and len(out) < max_trades and mm[b] < 950 and not (
                    after_target == "day" and any(t[4] == "target" for t in out)) and not (
                    max_losses and sum((t[3] - t[2]) * t[0] < 0 for t in out) >= max_losses):  # research: losers a day  # research: after a target, done for the day
                want = 1 if c[b] > up else -1 if c[b] < dn else 0
                if want and vwap and want * (c[b] - vw[b]) <= 0:
                    want = 0
                if want and trend and want * (c[b] - sma) <= 0:
                    # research (2026-11-24): against the trend only past a band counter_k x as wide (0: never), or
                    # (trend_gap_k) on a day that gapped the trade's way by trend_gap_k x the 14-session average gap
                    far = up_ref * (1 + sig[end] * counter_k) if want > 0 else dn_ref * (1 - sig[end] * counter_k)
                    gap_ok = False
                    if trend_gap_k:
                        ag = np.mean([abs(days[j]["o"][0] - prev(days, j, "c")) * d["s"] / days[j]["s"] for j in range(i - 14, i)])
                        gap_ok = want * (o[0] - pc) >= trend_gap_k * ag
                    if not gap_ok and (not counter_k or want * (c[b] - far) <= 0):
                        want = 0
                if want and after_target == "side" and any(t[4] == "target" and t[0] == want for t in out):
                    want = 0
                if want and range_pos:  # research (2026-11-24): the close still near the day's extreme its way
                    hi_s, lo_s = h[:b + 1].max(), lo[:b + 1].min()
                    pos_r = (c[b] - lo_s) / (hi_s - lo_s) if hi_s > lo_s else 0.5
                    if (want > 0 and pos_r < range_pos) or (want < 0 and pos_r > 1 - range_pos):
                        want = 0
                if want and bar_pos:  # research (2026-11-24): the signal bar(s) closing in their strong part (bar_n bars)
                    hb, lb = h[max(0, b - bar_n + 1):b + 1].max(), lo[max(0, b - bar_n + 1):b + 1].min()
                    bp = (c[b] - lb) / (hb - lb) if hb > lb else 0.5
                    if (want > 0 and bp < bar_pos) or (want < 0 and bp > 1 - bar_pos):
                        want = 0
                if want and min_stretch:  # research (2026-11-24): the close at least min_stretch x sigma past the band
                    ref = up_ref if want > 0 else dn_ref       # (stretch_gap: only for trades against the day's gap)
                    edge = up if want > 0 else dn
                    if want * (c[b] - edge) < min_stretch * sig[end] * ref and not (
                            stretch_gap and want * (o[0] - pc) > 0):
                        want = 0
                if want and max_move:  # research (2026-11-24): skip when the day has already run past max_move x its usual range
                    avg_rng = np.mean([(days[j]["h"].max() - days[j]["l"].min()) * d["s"] / days[j]["s"] for j in range(i - 14, i)])
                    free = (move_free in ("first_check", "check_target") and end == checks[0]) or (move_free == "first_trade" and not out) or (
                        move_free in ("after_target", "check_target") and any(t[4] == "target" and t[0] == want for t in out))
                    # move_ref (research 2026-11-24): from the open, the band's reference (max/min(open, prior close)), or the prior close
                    mref = o[0] if move_ref == "open" else pc if move_ref == "close" else (up_ref if want > 0 else dn_ref)
                    if want * (c[b] - mref) > max_move * avg_rng and not free:
                        want = 0
                if want and (end > last or be_skip_strong):  # research (2026-11-24): the break's stretch past the band
                    ref_ = up_ref if want > 0 else dn_ref
                    st_ = want * (c[b] - (up if want > 0 else dn)) / (sig[end] * k * ref_)
                    if end > last and st_ < 1.5:  # after `last` only strong breaks (strong_last)
                        want = 0
                    pend_strong = st_ >= be_skip_strong if be_skip_strong else False
                elif want:
                    pend_strong = False
                if want:
                    pend_tp = tp_r
                    if strong_at and strong_tp:
                        ref = up_ref if want > 0 else dn_ref
                        if want * (c[b] - (up if want > 0 else dn)) / (sig[end] * k * ref) >= strong_at:
                            pend_tp = strong_tp
                    if late_at and late_tp and end > late_at:  # research (2026-11-24): another target for later entries
                        pend_tp = late_tp
                    hard_ref = c[b] + want * tick
                    band = bl if want > 0 else bs
                    hp = hard_ref - want * hard / pv
                    pend, pend_stop = want, (max(band, hp) if want > 0 else min(band, hp))
                    pend_px = c[b]  # research (limit_in): the limit price
                    if want * (hard_ref - pend_stop) <= 0:  # VWAP on the wrong side of the fill (no VWAP entry filter):
                        raw = up if want > 0 else dn       # the band alone (a stop past the price would be rejected)
                        pend_stop = max(raw, hp) if want > 0 else min(raw, hp)
                    if band_stop_at:  # research (2026-11-24): the stop part of the way from it to the signal close
                        pend_stop = pend_stop + band_stop_at * (c[b] - pend_stop)
                    if nt:
                        pend_stop = _tick(pend_stop, tick)
        if not nt and mm[b] >= 955 and pos:
            out.append((pos, ebar, entry, c[b] - pos * tick, "time", b))
            pos = 0
    if pos:
        out.append((pos, ebar, entry, done(c[-1] - pos * tick), "time", len(o) - 1))
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
            px, x, xb, why = walk(d, b + 1, side, e - side * dist, e + side * r * dist if r else np.nan, exit_m, tick,
                                  be_at=be * dist if be else np.nan)
            return [(side, b + 1, px, x, why, xb)]
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


def gap_go(days, i, tick, k=0.5, n=14, exit_m=955, r=0.0, cap=100.0, min_body=0.0, against_yday=False, stop_at=0.0,
           stop_pc=False, max_bar=0.0):
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
    if min_body:  # research (2026-11-24): the 09:30 bar's body at least min_body x the 14-day average range
        rng = np.mean([(days[j]["h"].max() - days[j]["l"].min()) * d["s"] / days[j]["s"] for j in range(i - 14, i)])
        if side * (d["c"][0] - d["o"][0]) < min_body * rng:
            return []
    if against_yday and side * (pc - prev(days, i, "o")) > 0:  # research: only gaps against yesterday's direction
        return []
    if max_bar:  # research (2026-11-24): no gap trade when the 09:30 bar's range is over max_bar x its 14-day average
        avg_bar = np.mean([(days[j]["h"][0] - days[j]["l"][0]) * d["s"] / days[j]["s"] for j in range(i - 14, i)])
        if d["h"][0] - d["l"][0] > max_bar * avg_bar:
            return []
    e = d["c"][0] + side * tick  # the expected fill: the signal close + a tick (NinjaTrader sets the stop with the entry)
    ref = d["o"][0] + stop_at * (d["c"][0] - d["o"][0])  # research (2026-11-24): the stop part of the way to the close
    if stop_pc:  # research (2026-11-24): the stop at the prior close (the gap's own level), the cap as before
        ref = pc
    dist = min(max(abs(e - ref), 4 * tick), cap)
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
    px, x, xb, why = walk(d, k + 1, side, e - side * dist, e + side * r * dist if r else np.nan, exit_m, tick)
    return [(side, k + 1, px, x, why, xb)]  # the exit bar too (2026-11-24): S.merge frees the account after it


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


def band_fade(days, i, tick, k_sd=2.0, first=600, last=900, max_trades=2, hard=200.0, pv=2.0, no_break=True,
              tgt="vwap", stop_slip=2):
    """Inside the noise area, fade stretches back to VWAP (2026-11-24, for the days the breakout does not trade): at a
    5-minute close between `first` and `last`, with price inside today's band (sigma at that minute over the last 14
    sessions) and k_sd standard deviations of (close - VWAP) away from VWAP, enter toward VWAP at the next open; the stop
    at the band edge past the close (at most `hard` $ a contract); the target VWAP at the signal ("half": half way);
    out at 15:55. no_break: no fades once a close has left the band today (a trend day)."""
    if i < 21:
        return []
    d = days[i]
    o, h, lo, c, mm = d["o"], d["h"], d["l"], d["c"], d["mm"]
    pc = prev(days, i, "c")
    up_ref, dn_ref = max(o[0], pc), min(o[0], pc)
    vw = _vwap(d)
    dev = c - vw
    out, b, broke = [], 0, False
    n = len(c)
    while b < n - 1 and len(out) < max_trades:
        end = mm[b] + 5
        if end < first:
            b += 1
            continue
        if end > last:
            break
        sg = np.mean([_moves(days, j).get(end, np.nan) for j in range(i - 14, i)])
        if np.isnan(sg):
            b += 1
            continue
        up, dn = up_ref * (1 + sg), dn_ref * (1 - sg)
        if c[b] > up or c[b] < dn:
            broke = True
        if broke and no_break:
            break
        sd = np.sqrt(np.mean(dev[: b + 1] ** 2))
        z = dev[b] / sd if sd > 0 else 0.0
        side = -1 if z > k_sd else 1 if z < -k_sd else 0
        if not side:
            b += 1
            continue
        e_exp = c[b] + side * tick
        edge = dn if side > 0 else up
        st = max(edge, e_exp - hard / pv) if side > 0 else min(edge, e_exp + hard / pv)
        st = _tick(st, tick)
        target = vw[b] if tgt == "vwap" else (c[b] + vw[b]) / 2
        target = _tick(target, tick)
        if side * (target - e_exp) <= 2 * tick or side * (e_exp - st) <= 2 * tick:
            b += 1
            continue
        e = o[b + 1] + side * tick
        x = xb = None
        for q in range(b + 1, n):
            if (side > 0 and lo[q] <= st) or (side < 0 and h[q] >= st):
                x, why, xb = (min(o[q], st) if side > 0 else max(o[q], st)) - side * stop_slip * tick, "stop", q
                break
            if side * ((h[q] if side > 0 else lo[q]) - target) >= tick:
                x, why, xb = target, "target", q
                break
            if mm[q] >= 955:
                x, why, xb = o[q] - side * tick, "time", q - 1
                break
        if x is None:
            x, why, xb = c[-1] - side * tick, "time", n - 1
        out.append((side, b + 1, e, x, why, xb))
        b = xb + 1
    return out


def news_mom(days, i, tick, thr=3.0, min_move=0.0, mode="mom", hard=200.0, pv=2.0, exit_m=595, r=0.0, entry_bar=0,
             be=0.0):
    """The 08:30 news move into the cash open (research/zoo/news.py's d["news"] = (spike, pre-news price, move to
    09:29)): on a day whose 08:30 volume spike is at least `thr` (0: every day) and whose news move is at least
    `min_move` of the price, in at the open of bar `entry_bar` (0: 09:30) its way ("mom") or against it ("fade"); a
    hard stop $hard a contract from the fill, a target r x that (0: none), out at the close of the bar starting at
    `exit_m` (filled at the next open)."""
    d = days[i]
    spike, pre, move = d.get("news", (np.nan, np.nan, np.nan))
    if np.isnan(spike) or spike < thr or abs(move) < min_move * pre or move == 0:
        return []
    side = (1 if move > 0 else -1) * (1 if mode == "mom" else -1)
    e = d["o"][entry_bar] + side * tick
    pts = hard / pv
    px, x, xb, why = walk(d, entry_bar, side, e - side * pts, e + side * r * pts if r else np.nan, exit_m, tick,
                          be_at=be * pts if be else np.nan, at_open=True)
    return [(side, entry_bar, px, x, why, xb)]


def tjr_sweep(days, i, tick, k=3, window=6, entry="market", r=2.0, tgt="r", last=660, levels="pd+on", sweep_ticks=2,
              max_trades=2, max_losses=1, cap=60.0, min_risk=8.0):
    """A New York-morning liquidity sweep (TJR's widely taught model; 2026-11-24, the user's video, not readable here):
    liquidity = the prior session's high / low and the overnight high / low; from 09:30 to `last`, a bar trading
    `sweep_ticks` past a high level starts a short setup (a low level, a long); within `window` bars a close below the
    lowest low of the `k` bars before the sweep (a break of structure) confirms it; entry at the next open ("market") or
    a limit at the fair value gap the break left ("fvg": the gap's near edge, the next `window` bars); the stop a tick
    past the sweep's extreme; the target r x the risk ("r") or the opposite level ("opp", at least 1R); out at 15:55.
    Risk from `min_risk` to `cap` points. At most `max_trades` a day, none after `max_losses` losers."""
    if i < 1:
        return []
    d = days[i]
    o, h, lo, c, mm = d["o"], d["h"], d["l"], d["c"], d["mm"]
    pdh, pdl = prev(days, i, "h"), prev(days, i, "l")
    onh, onl = d.get("on", (np.nan, np.nan))
    highs = [pdh] + ([onh] if levels == "pd+on" and not np.isnan(onh) else [])
    lows = [pdl] + ([onl] if levels == "pd+on" and not np.isnan(onl) else [])
    n = len(c)
    out, losses, b = [], 0, 1
    taken_hi, taken_lo = set(), set()
    while b < n - 2 and len(out) < max_trades and losses < max_losses:
        if mm[b] + 5 > last:
            break
        setup = None
        for L in highs:
            if L not in taken_hi and h[b] >= L + sweep_ticks * tick:
                setup = (-1, L)
                taken_hi.add(L)
                break
        if setup is None:
            for L in lows:
                if L not in taken_lo and lo[b] <= L - sweep_ticks * tick:
                    setup = (1, L)
                    taken_lo.add(L)
                    break
        if setup is None:
            b += 1
            continue
        side, lvl = setup
        s = b
        ref = lo[max(0, s - k):s].min() if side < 0 else h[max(0, s - k):s].max()  # the structure to break back through
        ext = h[s] if side < 0 else lo[s]
        trig = None
        for q in range(s, min(n - 1, s + window + 1)):
            ext = max(ext, h[q]) if side < 0 else min(ext, lo[q])
            if mm[q] + 5 > last + 30:
                break
            if (side < 0 and c[q] < ref) or (side > 0 and c[q] > ref):
                trig = q
                break
        if trig is None:
            b = s + 1
            continue
        stop = ext + tick if side < 0 else ext - tick
        if entry == "market":
            eb, e = trig + 1, o[trig + 1] + side * tick
        else:  # a limit at the fair value gap's near edge (the gap between bars trig-2 and trig)
            gap_edge = lo[trig - 2] if side < 0 and lo[trig - 2] > h[trig] else (h[trig - 2] if side > 0 and h[trig - 2] < lo[trig] else np.nan)
            if np.isnan(gap_edge):
                b = trig + 1
                continue
            eb = None
            for q in range(trig + 1, min(n - 1, trig + 1 + window)):
                if (side < 0 and h[q] >= gap_edge) or (side > 0 and lo[q] <= gap_edge):
                    eb, e = q, gap_edge
                    break
                if (side < 0 and lo[q] <= c[trig] - 3 * abs(stop - c[trig])) or (side > 0 and h[q] >= c[trig] + 3 * abs(stop - c[trig])):
                    break
            if eb is None:
                b = trig + 1
                continue
        risk = side * (e - stop)
        if risk < min_risk or risk > cap:
            b = trig + 1
            continue
        if tgt == "opp":
            opp = [x for x in (lows if side < 0 else highs) if side * (x - e) >= risk]
            target = (max(opp) if side < 0 else min(opp)) if opp else e + side * r * risk
        else:
            target = e + side * r * risk
        target = _tick(target, tick)
        px, x, xb, why = walk(d, eb, side, stop, target, 955, tick, entry=e if entry != "market" else None, at_open=True)
        out.append((side, eb, px, x, why, xb))
        if side * (x - px) < 0:
            losses += 1
        b = xb + 1
    return out


def _pivots_tjr(o, h, lo, c, upto):
    """TJR's swing points up to bar `upto`: a high is an up candle followed by a down candle (the higher of the two
    highs), a low a down candle followed by an up candle (the lower low); each known once its second candle closes.
    Returns ([(price, known_bar)] highs, [(price, known_bar)] lows)."""
    hs, ls = [], []
    for k in range(upto):
        up0, up1 = c[k] > o[k], c[k + 1] > o[k + 1]
        if up0 and not up1:
            hs.append((max(h[k], h[k + 1]), k + 1))
        if not up0 and up1:
            ls.append((min(lo[k], lo[k + 1]), k + 1))
    return hs, ls


def tjr(days, i, tick, levels="sess+pd", cont="eq", stop_at="retrace", tgt="liq1", end=630, window=12, cap=150.0,
        min_risk=4.0, min_r=1.0, first=570):
    """TJR's strategy as his 2026 tutorial states it (the user's transcript, 2026-11-24), on 5-minute bars:
    1. draws on liquidity: Asia (18:00-03:00) and London (03:00-08:30) session highs / lows and the prior day's high / low
       ("sess+pd"; "pd" the prior day only, "sess" the sessions only);
    2. a sweep: from `first` a bar trading past such a level not taken since it formed (above a high: a short setup);
    3. confirmation: within `window` bars a 5-minute CLOSE beyond the most recent swing (his down-then-up candle low /
       up-then-down candle high), a break of structure;
    4. continuation: a retrace to equilibrium (50% of the leg from its high to its low, "eq") or into a fair value gap
       the leg left ("fvg");
    5. entry: the first 5-minute candle closing back the trade's way from there, at the next open; no entry after `end`;
    6. the stop a tick past the retrace's extreme ("retrace") or the sweep's ("sweep"); the target the nearest draw on
       liquidity at least min_r x the risk away ("liq1"), the next one ("liq2"), or 2R / 3R; out at 15:55. One trade."""
    if i < 1:
        return []
    d = days[i]
    o, h, lo, c, mm = d["o"], d["h"], d["l"], d["c"], d["mm"]
    n = len(c)
    ss = d.get("sess", {})
    pdh, pdl = prev(days, i, "h"), prev(days, i, "l")
    a_h, a_l = ss.get("asia", (np.nan, np.nan))
    l_h, l_l = ss.get("london", (np.nan, np.nan))
    p_h, p_l = ss.get("pre", (np.nan, np.nan))
    hi_lv, lo_lv = [], []
    if "sess" in levels:
        if not np.isnan(a_h) and a_h > np.nanmax([l_h, p_h]):
            hi_lv.append(a_h)  # not already taken in London / pre-market
        if not np.isnan(l_h) and l_h > np.nan_to_num(p_h, nan=-np.inf):
            hi_lv.append(l_h)
        if not np.isnan(a_l) and a_l < np.nanmin([l_l, p_l]):
            lo_lv.append(a_l)
        if not np.isnan(l_l) and l_l < np.nan_to_num(p_l, nan=np.inf):
            lo_lv.append(l_l)
    if "pd" in levels:
        on_h = np.nanmax([a_h, l_h, p_h]) if ss else -np.inf
        on_l = np.nanmin([a_l, l_l, p_l]) if ss else np.inf
        if pdh > on_h:
            hi_lv.append(pdh)
        if pdl < on_l:
            lo_lv.append(pdl)
    if not hi_lv and not lo_lv:
        return []
    for b in range(n - 2):
        if mm[b] < first:
            continue
        if mm[b] + 5 > end:
            return []
        side = -1 if any(h[b] > L for L in hi_lv) else 1 if any(lo[b] < L for L in lo_lv) else 0
        if not side:
            continue
        # 3. a close through the most recent swing on the other side, within `window` bars
        ext = h[b] if side < 0 else lo[b]
        bos = None
        for q in range(b + 1, min(n - 1, b + 1 + window)):
            ext = max(ext, h[q]) if side < 0 else min(ext, lo[q])
            hs, ls = _pivots_tjr(o, h, lo, c, q - 1)
            sw = [p for p, kb in (ls if side < 0 else hs) if kb < q]
            if not sw:
                continue
            ref = sw[-1]
            if (side < 0 and c[q] < ref) or (side > 0 and c[q] > ref):
                bos = q
                break
        if bos is None or mm[bos] + 5 > end:
            return []
        top = max(h[b:bos + 1]) if side < 0 else min(lo[b:bos + 1])  # the leg's start (the most recent high / low)
        tb = b + int(np.argmax(h[b:bos + 1]) if side < 0 else np.argmin(lo[b:bos + 1]))
        gaps = [(h[k], lo[k - 2]) if side < 0 else (h[k - 2], lo[k]) for k in range(tb + 2, bos + 1)
                if (side < 0 and lo[k - 2] > h[k]) or (side > 0 and h[k - 2] < lo[k])]
        filled, rx = None, None
        for r in range(bos + 1, n - 1):
            if mm[r] + 5 > end:
                return []
            leg_end = min(lo[tb:r]) if side < 0 else max(h[tb:r])
            if (side < 0 and c[r] > top) or (side > 0 and c[r] < top):
                return []  # the new leg failed
            if filled is None:
                if cont == "eq":
                    eq = (top + leg_end) / 2
                    hit = (side < 0 and h[r] >= eq) or (side > 0 and lo[r] <= eq)
                else:
                    hit = any((side < 0 and h[r] >= g0) or (side > 0 and lo[r] <= g1) for g0, g1 in gaps)
                if hit:
                    filled, rx = r, (h[r] if side < 0 else lo[r])
            if filled is not None:
                rx = max(rx, h[r]) if side < 0 else min(rx, lo[r])
                if (side < 0 and c[r] < o[r]) or (side > 0 and c[r] > o[r]):  # 5. a candle closing back our way
                    e_exp = c[r] + side * tick
                    stop = (rx if stop_at == "retrace" else top) - side * tick
                    risk = side * (e_exp - stop)
                    if risk < min_risk or risk > cap:
                        return []
                    if tgt in ("liq1", "liq2"):
                        pool = [pdl, a_l, l_l, p_l] + [p for p, kb in _pivots_tjr(o, h, lo, c, r - 1)[1]] if side < 0 else \
                            [pdh, a_h, l_h, p_h] + [p for p, kb in _pivots_tjr(o, h, lo, c, r - 1)[0]]
                        far = sorted([x for x in pool if not np.isnan(x) and side * (x - e_exp) >= min_r * risk], key=lambda x: side * (x - e_exp))
                        if not far:
                            return []
                        target = far[0] if tgt == "liq1" or len(far) == 1 else far[1]
                    else:
                        target = e_exp + side * float(tgt[1:]) * risk
                    target = _tick(target, tick)
                    px, x, xb, why = walk(d, r + 1, side, stop, target, 955, tick, at_open=True)
                    return [(side, r + 1, px, x, why, xb)]
        return []
    return []



def everyday(days, i, tick, legs=(), **_):
    """Several legs on one account, one position at a time (S.merge: the earlier entry first)."""
    out = []
    for name, p in legs:
        out += globals()[name](days, i, tick, **p) or []
    return merge(out)


def band_stretch(days, i, side, eb, k=1.0):
    """research (2026-11-24): how far past the band the signal close (the bar before the fill, eb - 1) was, in sigmas
    of the band's reference (max / min of the open and the prior close), as MnqCleanBand sizes it."""
    d = days[i]
    b = eb - 1
    end = d["mm"][b] + 5
    sg = np.mean([_moves(days, j).get(end, np.nan) for j in range(i - 14, i)]) * k
    pc = prev(days, i, "c")
    ref = max(d["o"][0], pc) if side > 0 else min(d["o"][0], pc)
    edge = ref * (1 + sg) if side > 0 else ref * (1 - sg)
    return side * (d["c"][b] - edge) / (sg * ref)


def backup_trade(days, i, tick, stop_pts=50.0, enter=930, exit_m=950):
    """research (2026-11-24, the user: "max 2-3 days no trading"): the must-trade day's backup, the last half hour's
    momentum (Gao et al.): at the close of the bar before `enter` (15:25-15:30) the day's way (that close against the
    open; a tie: against the prior close, then the 20-session average), a market order filled at `enter`'s open; the
    stop stop_pts from the expected fill (the close + a tick), set with the entry; out at the open after the bar starting
    at exit_m (15:55), as MnqCleanBand.cs executes it."""
    d = days[i]
    ks, ke = _bar_at(d, enter - 5), _bar_at(d, enter)
    if ks is None or ke is None or ke != ks + 1:
        return []
    c = d["c"][ks]
    pc = prev(days, i, "c")
    sma = np.mean([prev(days, i, "c", j) for j in range(1, 21)])
    side = int(np.sign(c - d["o"][0]) or np.sign(c - pc) or np.sign(c - sma) or 1)
    stop = _tick(c + side * tick - side * stop_pts, tick)
    px, x, xb, why = walk(d, ke, side, stop, np.nan, exit_m, tick, at_open=True)
    return [(side, ke, px, x, why, xb)]
