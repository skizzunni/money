"""Market-specific intraday setups for gold and crude (2026-11-24, the user: "if you can't trade MNQ, trade other
stuff; the same strategy is not going to work on all"). Minute bars from zoo/mk_full.py (minutes from 18:00 New York:
08:00 = 840, 08:20 = 860, 08:30 = 870, 09:00 = 900, 10:30 = 990, 13:30 = 1170, 14:30 = 1230, 16:00 = 1320). Every trade:
in at a minute's open + 1 tick, the stop resting (filled 1 tick worse; checked before the target), out at the exit
minute's open, $1.24 a round turn. Returns per-trade $ for one micro contract (MGC $10 a point, MCL $100)."""
from __future__ import annotations

import numpy as np

SPEC = {"gold": dict(tick=0.1, pv=10.0, s=860, settle=1170, last=1320),
        "crude": dict(tick=0.01, pv=100.0, s=900, settle=1230, last=1320)}


def at(d, m):
    k = np.searchsorted(d["mm"], m)
    return int(k) if k < len(d["mm"]) else None


def sim(d, k, side, stop, target, exit_m, tick):
    """Enter at bar k's open; the stop / target from bar k on; out at the open of the first bar at or after exit_m."""
    ke = at(d, exit_m)
    if ke is None or ke <= k:
        return None
    e = d["o"][k] + side * tick
    lo, hi = d["l"][k:ke], d["h"][k:ke]
    hs = np.flatnonzero(lo <= stop) if side > 0 else np.flatnonzero(hi >= stop)
    ht = (np.flatnonzero(hi >= target) if side > 0 else np.flatnonzero(lo <= target)) if target == target else np.array([], int)
    js, jt = (hs[0] if len(hs) else 10**9), (ht[0] if len(ht) else 10**9)
    if js <= jt and js < 10**9:
        o = d["o"][k + js]
        x = (min(o, stop) if side > 0 else max(o, stop)) - side * tick
    elif jt < 10**9:
        x = target
    else:
        x = d["o"][ke]
    return (x - e) * side


def avg_range(days, i, n=14, a=None, b=None):
    out = []
    for j in range(i - n, i):
        d = days[j]
        ka, kb = (at(d, a) if a is not None else 0), (at(d, b) if b is not None else len(d["mm"]))
        if ka is None or kb is None or kb <= ka:
            continue
        out.append(d["h"][ka:kb].max() - d["l"][ka:kb].min())
    return np.mean(out) if out else np.nan


def close_at(d, m):
    k = at(d, m)
    return d["c"][k - 1] if k else np.nan


# --- setups: each (days, i, spec, avg, **p) -> list of point results -------------------------------------------------
def on_break(days, i, sp, avg, start=None, until=120, stop="mid", exit_m=None, fade=False, buf=0.0):
    """The overnight range (18:00 to the session start): the first minute closing beyond it from the start to start +
    until enters its way (fade: a close back inside after trading `buf` x avg beyond enters against it); stop the range
    middle / the other side / 0.25 avg; out at exit_m."""
    d = days[i]
    s = start or sp["s"]
    ks, kl = at(d, s), at(d, s + until)
    if ks is None or kl is None or ks < 30:
        return []
    hi, lo = d["h"][:ks].max(), d["l"][:ks].min()
    mid = (hi + lo) / 2
    c = d["c"]
    if not fade:
        for k in range(ks, kl):
            side = 1 if c[k] > hi else -1 if c[k] < lo else 0
            if side:
                st = mid if stop == "mid" else (lo if side > 0 else hi) if stop == "far" else c[k] - side * 0.25 * avg
                r = sim(d, k + 1, side, st, np.nan, exit_m or sp["last"], sp["tick"])
                return [r] if r is not None else []
        return []
    ext_h = ext_l = False
    for k in range(ks, kl):
        if d["h"][k] > hi + buf * avg:
            ext_h = True
        if d["l"][k] < lo - buf * avg:
            ext_l = True
        if ext_h and c[k] < hi:
            r = sim(d, k + 1, -1, d["h"][ks:k + 1].max() + sp["tick"], mid, exit_m or sp["last"], sp["tick"])
            return [r] if r is not None else []
        if ext_l and c[k] > lo:
            r = sim(d, k + 1, 1, d["l"][ks:k + 1].min() - sp["tick"], mid, exit_m or sp["last"], sp["tick"])
            return [r] if r is not None else []
    return []


def gap(days, i, sp, avg, k_gap=0.5, mode="fade", stop_m=1.0, exit_m=None, confirm=15):
    """The session open against the prior settle (gold 13:30, crude 14:30): fade toward the settle (stop stop_m x the
    gap past the open), or go its way once the first `confirm` minutes close its way (stop the session open)."""
    d, p = days[i], days[i - 1]
    ks = at(d, sp["s"])
    pc = close_at(p, sp["settle"])
    if ks is None or pc != pc:
        return []
    g = d["o"][ks] - pc
    gaps = [abs(close_at(days[j], sp["s"] + 1) - close_at(days[j - 1], sp["settle"])) for j in range(i - 14, i)]
    ag = np.nanmean(gaps)
    if not ag or abs(g) < k_gap * ag:
        return []
    side = -np.sign(g) if mode == "fade" else np.sign(g)
    if mode == "fade":
        r = sim(d, ks, side, d["o"][ks] - side * stop_m * abs(g), pc, exit_m or sp["last"], sp["tick"])
        return [r] if r is not None else []
    kc = at(d, sp["s"] + confirm)
    if kc is None or side * (d["c"][kc - 1] - d["o"][ks]) <= 0:
        return []
    r = sim(d, kc, side, d["o"][ks] - side * sp["tick"], np.nan, exit_m or sp["last"], sp["tick"])
    return [r] if r is not None else []


def event(days, i, sp, avg, at_m=870, mins=5, k=2.0, mode="mom", stop_m=1.0, hold=60, weekday=None):
    """A scheduled release (08:30 data, crude's Wednesday 10:30 inventories): the first `mins` minutes' move against
    the 14-day average of the same window; past k x: with it ("mom") or against it ("fade"), stop stop_m x the move
    from the entry, out after `hold` minutes."""
    d = days[i]
    if weekday is not None and np.datetime64(d["d"], "D").astype("datetime64[D]").item().weekday() != weekday:
        return []
    k0, k1 = at(d, at_m), at(d, at_m + mins)
    if k0 is None or k1 is None or k1 <= k0:
        return []
    mv = d["c"][k1 - 1] - d["o"][k0]
    ref = []
    for j in range(i - 14, i):
        a0, a1 = at(days[j], at_m), at(days[j], at_m + mins)
        if a0 is not None and a1 is not None and a1 > a0:
            ref.append(abs(days[j]["c"][a1 - 1] - days[j]["o"][a0]))
    am = np.mean(ref) if ref else np.nan
    if not am or abs(mv) < k * am:
        return []
    side = np.sign(mv) * (1 if mode == "mom" else -1)
    e = d["o"][k1]
    r = sim(d, k1, side, e - side * stop_m * abs(mv), np.nan, at_m + mins + hold, sp["tick"])
    return [r] if r is not None else []


def pdhl(days, i, sp, avg, until=240, buf=0.1, target="mid", exit_m=None):
    """Yesterday's session high / low (from the session start to the settle): a trade beyond it by buf x avg that
    closes back inside, from the start to start + until, is faded; stop the extreme; target yesterday's middle."""
    d, p = days[i], days[i - 1]
    a, b = at(p, sp["s"]), at(p, sp["settle"])
    ks, kl = at(d, sp["s"]), at(d, sp["s"] + until)
    if None in (a, b, ks, kl) or b <= a:
        return []
    ph, pl = p["h"][a:b].max(), p["l"][a:b].min()
    mid = (ph + pl) / 2
    up = dn = False
    for k in range(ks, kl):
        up |= d["h"][k] > ph + buf * avg
        dn |= d["l"][k] < pl - buf * avg
        if up and d["c"][k] < ph:
            r = sim(d, k + 1, -1, d["h"][ks:k + 1].max() + sp["tick"], mid if target == "mid" else np.nan, exit_m or sp["last"], sp["tick"])
            return [r] if r is not None else []
        if dn and d["c"][k] > pl:
            r = sim(d, k + 1, 1, d["l"][ks:k + 1].min() - sp["tick"], mid if target == "mid" else np.nan, exit_m or sp["last"], sp["tick"])
            return [r] if r is not None else []
    return []


def five_min(days):
    """research (2026-11-24): the minute days as 5-minute bars (minutes from 18:00, the bar's start), as a 5-minute
    chart shows them, for MgcOvernightCarry's reference."""
    out = []
    for d in days:
        k5 = d["mm"] // 5
        u, first = np.unique(k5, return_index=True)
        last = np.r_[first[1:] - 1, len(k5) - 1]
        out.append({"d": d["d"], "mm": u * 5, "o": d["o"][first], "c": d["c"][last],
                    "h": np.maximum.reduceat(d["h"], first), "l": np.minimum.reduceat(d["l"], first)})
    return out


def carry(days, i, tick=0.1, k=1.5, open_m=860, confirm=15, settle=1170, exit_m=1170, n=14):
    """Gold's overnight move carried on (MgcOvernightCarry.cs, 2026-11-24), on 5-minute bars: the move = the 08:20 bar's
    open less the prior session's 13:25 bar close; at least k x the last n sessions' average |move| and the bars from
    08:20 to 08:20 + confirm closing its way (the last one's close against the 08:20 open): a market order at that
    close, filled at the next bar's open + a tick; the stop a tick past the 08:20 open, set with the entry; out at the
    open of the bar starting at exit_m (13:30). A stop fills at the bar's open when it opens through, a tick worse.
    Returns [(side, entry bar, entry, exit, why, exit bar)]."""
    def move(j):
        d, p = days[j], days[j - 1]
        ko, kp = at(d, open_m), at(p, settle - 5)
        if ko is None or kp is None or d["mm"][ko] != open_m or p["mm"][kp] != settle - 5:
            return np.nan
        return d["o"][ko] - p["c"][kp]
    if i < n + 1:
        return []
    mv = move(i)
    ref = [abs(m) for m in (move(j) for j in range(i - n, i)) if m == m]
    if mv != mv or len(ref) < n or abs(mv) < k * np.mean(ref):
        return []
    d = days[i]
    ko, kc = at(d, open_m), at(d, open_m + confirm)
    if kc is None or d["mm"][kc] != open_m + confirm:
        return []
    side = 1 if mv > 0 else -1
    if side * (d["c"][kc - 1] - d["o"][ko]) <= 0:
        return []
    stop = np.round((d["o"][ko] - side * tick) / tick) * tick  # as NinjaTrader's RoundToTickSize
    e = d["o"][kc] + side * tick
    # as NinjaTrader acts (on a bar's close): the exit at the close of the first bar from exit_m - 5 on, filled at the
    # next open; a session that ends first (a holiday's early close): at the close of the next day's first bar
    nx = days[i + 1] if i + 1 < len(days) else None
    seq = [(d, b) for b in range(kc, len(d["o"]))] + ([(nx, b) for b in range(min(2, len(nx["o"])))] if nx else [])
    trig = next((j for j, (dd, b) in enumerate(seq) if dd is not d or dd["mm"][b] >= exit_m - 5), None)
    if trig is None or trig + 1 >= len(seq):
        return []
    for j in range(trig + 1):
        dd, b = seq[j]
        if (side > 0 and dd["l"][b] <= stop) or (side < 0 and dd["h"][b] >= stop):
            x = (min(dd["o"][b], stop) if side > 0 else max(dd["o"][b], stop)) - side * tick
            return [(side, kc, e, x, "stop", b)]
    dd, b = seq[trig + 1]
    return [(side, kc, e, dd["o"][b] - side * tick, "time" if dd is d else "session", b - 1)]
