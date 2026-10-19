"""Frozen B (momentum only) in the Apex 50K intraday-trail evaluation, chronologically (docs/EVALUATION.md).

    python research/eval_sim.py <sim.dll> <bars.pkl> <first> <last> <label> <out.csv>

Strategy: B, the NinjaTrader strategy with UseBreakout off, every other setting at its default, run complete on the
stand-in (one rerun per size and slippage; no trade edited after the fact): 4 MNQ with $200 max loss a trade, and
2 MNQ with $100 (the same 25-point stop cap, lock and targets in points). Commission $0.95 a side; slippage 1 and 2
ticks on every market and stop fill. Sessions with missing minutes get no new trades (a retrospective data-quality
exclusion, decided before the run). The strategy's warm-up (14 full sessions) comes before the first evaluation.

The evaluation (third-party summaries of Apex's rules, docs/EVALUATION.md; the account's own terms decide):
$50,000 start, pass at +$3,000, fail when equity (closed + open, commission charged at each fill) reaches the highest
equity so far less $2,000 (the trail follows unrealized peaks; whether it stops trailing at some level is moot here:
it cannot reach that level before the target), 30 calendar days from the start, no daily loss limit (a $1,000
daily pause is run as a sensitivity: sources conflict), no minimum trading days (passes before the 7th session are
counted: one older source required 7). The strategy's own evaluation-target close (live, on by default) is applied:
everything is closed once closed + open profit reaches $3,025 (a take-profit there, filled a tick through), and a
close that leaves $3,000 or more closed is a pass. One evaluation per start session; windows starting every session
overlap heavily (not independent trials); a second count runs them back to back (the next starts the session after
an outcome).

Equity is followed along a valid price path through each position (the stand-in's own fills decide entries and
exits; the replay adds the account's view). The entry fills at its bar's open; within each bar the price goes from
the open to one extreme, then the other, so a bar has two possible paths (favourable extreme first, or adverse
first). A stop exit ends the path at its fill: on the favourable-first path the bar's favourable extreme comes before
it, on the adverse-first path nothing after the open does. A take-profit ends it at its fill: the adverse extreme comes
before it only on the adverse-first path. A market exit, or a stop crossed at the open, fills at the open and nothing
later in that bar counts. Commission is charged at each fill; the trail is checked after every price point and every
fill (so an exit commission can breach it). Each evaluation is replayed along four valid paths: every bar favourable
first, every bar adverse first, and the two mixes worst and best for the trailing threshold. An evaluation whose
outcome or outcome day differs between them is "sequencing-dependent", reported apart with its possible outcomes.
"""
from __future__ import annotations

import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import controlled as K  # noqa: E402

TARGET, TRAIL, BUFFER, DAYS, FEE = 3000.0, 2000.0, 25.0, 30, 0.95
SIZES = {"4 MNQ / $200": {"EvalQty": 4, "EvalMaxLoss": 200}, "2 MNQ / $100": {"EvalQty": 2, "EvalMaxLoss": 100}}
PATHS = ("favourable first", "adverse first", "worst mix", "best mix")


def marks(tr, o, h, lo, slip_ticks):
    """Per trade, what the replay needs: (entry bar, exit bar, direction, contracts, entry fill, exit fill, exit kind,
    net P/L, the bars' open / high / low). Exit kinds: "open" (a market exit, or a stop crossed at the bar's open,
    filled at the open), "stop", "target"."""
    slip = 0.25 * slip_ticks
    out = []
    for r in tr.itertuples():
        d, xb = r.d, r.xb
        if r.why == "Profit target":
            kind = "target"
        elif r.why == "Stop loss" and d * (o[xb] - d * slip - r.ex) > 1e-9:
            kind = "stop"  # filled at the stop, inside the bar
        else:
            kind = "open"  # a market exit or a stop crossed at the open
        idx = np.arange(r.eb, xb + 1)
        out.append((r.eb, xb, d, r.q, r.en, r.ex, kind, r.pnl, o[idx], h[idx], lo[idx]))
    return out


def _bar_points(d, op, hi, lo_, first, last, kind, favourable_first):
    """Prices the position passes through in one bar, in order, before its exit fill (if this is the exit bar)."""
    fav, adv = (hi, lo_) if d > 0 else (lo_, hi)
    pts = [] if first else [op]  # the entry bar starts at the entry fill itself
    if not last:
        return pts + ([fav, adv] if favourable_first else [adv, fav])
    if kind == "open":
        return []  # filled at the open: nothing in this bar counts after it
    if kind == "stop":
        return pts + ([fav] if favourable_first else [])
    return pts + ([] if favourable_first else [adv])  # take-profit


def _order(path, kind_of_bar):
    """Favourable-first for this bar under the given path? kind_of_bar: None (no exit), "stop", "target", "open"."""
    if path == "favourable first":
        return True
    if path == "adverse first":
        return False
    worst = path == "worst mix"  # a peak before the drop raises the threshold first; a dip before a target adds a low
    return (kind_of_bar != "target") if worst else (kind_of_bar == "target")


def evaluate(trs, start_bar, end_bar, day_of, path, dll=0.0):
    """One evaluation from start_bar to end_bar (exclusive) along a path. Returns (outcome, bar, max drawdown)."""
    return evaluate_detail(trs, start_bar, end_bar, day_of, path, dll)[:3]


def evaluate_detail(trs, start_bar, end_bar, day_of, path, dll=0.0):
    """evaluate(), also returning the equity at the outcome and the index of the trade it came in (None: after it)."""
    e = peak = dd = 0.0
    ti = None
    day_start, cur_day, paused = 0.0, -1, False
    for ti, (eb, xb, d, q, en, ex, kind, pnl, bo, bh, bl) in enumerate(trs):
        if eb < start_bar:
            continue
        if eb >= end_bar:
            break
        if day_of[eb] != cur_day:
            cur_day, day_start, paused = day_of[eb], e, False
        if paused:
            continue
        mult = q * 2.0
        tgt = TARGET + BUFFER + 0.25 * mult  # the strategy's own close: a limit filled a tick through
        base = e - FEE * q  # entry commission charged at the fill
        bar = eb
        stopped = False
        for k in range(len(bo)):
            last = k == len(bo) - 1
            kb = kind if last else None
            prices = ([en] if k == 0 else []) + _bar_points(d, bo[k], bh[k], bl[k], k == 0, last, kind,
                                                            _order(path, kb)) + ([ex] if last else [])
            bar = eb + k
            for px in prices:
                eq = base + d * (px - en) * mult
                if eq >= tgt:
                    return "pass", bar, dd, tgt, ti
                peak = max(peak, eq)
                dd = max(dd, peak - eq)
                if eq <= peak - TRAIL:
                    return "fail", bar, dd, eq, ti
                if dll > 0 and eq <= day_start - dll:  # sensitivity: the day's loss limit closes and pauses the day
                    e = day_start - dll
                    paused = stopped = True
                    break
            if stopped:
                break
        if stopped:
            continue
        e += pnl  # the exit fill, both commissions charged
        if e >= TARGET:
            return "pass", xb, dd, e, None
        peak = max(peak, e)
        dd = max(dd, peak - e)
        if e <= peak - TRAIL:
            return "fail", xb, dd, e, None
    return ("expired" if end_bar < 10**12 else "open"), None, dd, e, None


def run_windows(trs, sessions, first_ok, day_of, bar_day, dll=0.0, chain=False, limit=None):
    rows = []
    s = first_ok
    last_day = sessions[-1]
    while s < len(sessions) and (limit is None or len(rows) < limit):
        d0 = sessions[s]
        end_day = d0 + pd.Timedelta(days=DAYS)
        start_bar = int(np.searchsorted(bar_day, d0))
        end_bar = int(np.searchsorted(bar_day, end_day))
        complete = end_day <= last_day + pd.Timedelta(days=1)
        res = {}
        for path in PATHS:
            out, at, dd = evaluate(trs, start_bar, end_bar if complete else 10**12, day_of, path, dll)
            if out == "open":
                out = "unresolved (data ends)"
            res[path] = (out, bar_day[at] if at is not None else None, dd)
        outs = {v[0] for v in res.values()}
        days = {v[1] for v in res.values()}
        w_out, w_day, w_dd = res["worst mix"]
        rows.append({"start": d0.date(), "fully observed": complete, "outcome": w_out if len(outs) == 1 else
                     "/".join(sorted(outs)), "sequencing-dependent": len(outs) > 1 or len(days) > 1,
                     "possible outcomes": "/".join(sorted(outs)),
                     "calendar days": (w_day - d0).days + 1 if w_day is not None else np.nan,
                     "sessions": int(np.searchsorted(sessions, w_day) - s + 1) if w_day is not None else np.nan,
                     "intraday DD": w_dd})
        if chain:
            if w_out == "expired":
                s = int(np.searchsorted(sessions, end_day))
            elif w_day is None:
                break
            else:
                s = int(np.searchsorted(sessions, w_day)) + 1
        else:
            s += 1
    return pd.DataFrame(rows)


def summarize(w, label):
    """Counts of outcomes. A window whose outcome is the same on every path is counted under it (if only its day
    differs, it is also counted as "day depends on path"); a window whose outcome differs is counted apart, with the
    outcomes it can have."""
    n = len(w)
    res = w[w["outcome"] != "unresolved (data ends)"]
    certain = res[~res["outcome"].str.contains("/")]
    uncertain = res[res["outcome"].str.contains("/")]
    out = {"evaluations": n, "unresolved (data ends)": n - len(res), "outcome depends on path": len(uncertain),
           "only the day depends on path": int(certain["sequencing-dependent"].sum())}
    for o in ("pass", "fail", "expired"):
        out[o] = int((certain["outcome"] == o).sum())
        out[f"{o} %"] = 100 * out[o] / len(res) if len(res) else np.nan
    out["path-dependent outcomes"] = uncertain["outcome"].value_counts().to_dict() if len(uncertain) else {}
    p = certain[certain["outcome"] == "pass"]
    f = certain[certain["outcome"] == "fail"]
    e = certain[certain["outcome"] == "expired"]
    out["median days to pass"] = p["calendar days"].median()
    out["median days to fail"] = f["calendar days"].median()
    out["passes before 7th session"] = int((p["sessions"] < 7).sum())
    out["intraday DD, passes: median / max"] = f"{p['intraday DD'].median():.0f} / {p['intraday DD'].max():.0f}"
    out["intraday DD, expired: median / max"] = f"{e['intraday DD'].median():.0f} / {e['intraday DD'].max():.0f}"
    return {"case": label, **out}


def main() -> None:
    dll_, data, first, last, label, out = sys.argv[1:7]
    bars = K.rth(pd.read_pickle(data))
    m = bars.index.tz_convert(K.NY)
    bars = bars[(m >= pd.Timestamp(first, tz=K.NY)) & (m < pd.Timestamp(last, tz=K.NY) + pd.Timedelta(days=1))]
    m = bars.index.tz_convert(K.NY)
    csv = Path(tempfile.mkdtemp()) / "bars.csv"
    K.write_bars(bars, csv)
    bad = K.incomplete_sessions(bars)
    skip = K.DEFAULT_SKIP + "," + ",".join(bad)
    o, h, lo = (bars[c].to_numpy(float) for c in ("open", "high", "low"))
    bar_day = m.normalize().tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(bar_day)))
    day_of = np.searchsorted(sessions, bar_day)
    bad_set = set(pd.to_datetime(bad))
    full = [d for d in sessions if d not in bad_set]
    first_ok = int(np.searchsorted(sessions, full[13])) + 1 if len(full) > 14 else len(sessions)  # after warm-up

    def job(args):
        size, props, slip = args
        tr = K.run(dll_, csv, UseBreakout=False, SimSlippageTicks=slip, SimCommissionPerSide=FEE, SkipDates=skip,
                   **props)
        trs = marks(tr, o, h, lo, slip)
        rows = []
        for dll, chain in ((0.0, False), (0.0, True), (1000.0, False)):
            w = run_windows(trs, sessions, first_ok, day_of, bar_day, dll, chain)
            name = f"{size}, {slip} tick{'s' if slip > 1 else ''}" + (", back to back" if chain else "") + \
                   (", $1,000 daily pause" if dll else "")
            rows.append(summarize(w, name))
        return rows, (size, slip, tr.pnl.sum(), len(tr))

    jobs = [(s, p, slip) for s, p in SIZES.items() for slip in (1, 2)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(job, jobs))
    df = pd.DataFrame([r for rows, _ in results for r in rows])
    df.insert(0, "data", label)
    df.to_csv(out, index=False)
    pd.set_option("display.width", 400)
    pd.set_option("display.max_columns", 40)
    print(f"{label}: {first} to {last}; {len(sessions)} sessions, {len(bad)} with missing minutes (no new trades); "
          f"first evaluation start {sessions[first_ok].date()}")
    for _, (size, slip, net, n) in results:
        print(f"  continuous run {size}, {slip} tick(s): {n} trades, net ${net:,.2f}")
    print(df.drop(columns="data").round(1).set_index("case").T.to_string())


if __name__ == "__main__":
    main()
