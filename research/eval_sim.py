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

Equity is followed minute by minute through each open position: a bar's high and low (a stop exit's worst point is
its fill, a take-profit's best is its fill, a market exit is its fill). A 1-minute bar does not say whether its high
or low came first, so each bar is taken both ways; an evaluation whose outcome or day differs between the two is
"sequencing-dependent" and reported apart, with the outcome under each.
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


def marks(tr, o, h, lo):
    """Per trade: the bars it is open on, and the open P/L at each bar's best and worst point (commission of the
    entry side charged), and its net result (both sides)."""
    out = []
    for r in tr.itertuples():
        d, q, en = r.d, r.q, r.en
        idx = np.arange(r.eb, r.xb + 1)
        fav = (h[idx] if d > 0 else lo[idx]).astype(float)
        adv = (lo[idx] if d > 0 else h[idx]).astype(float)
        if r.why == "Stop loss":
            adv[-1] = r.ex
        elif r.why == "Profit target":
            fav[-1] = r.ex
        else:  # a market exit fills at its bar's open
            fav[-1] = adv[-1] = r.ex
        f = d * (fav - en) * q * 2.0 - FEE * q
        a = d * (adv - en) * q * 2.0 - FEE * q
        out.append((r.eb, r.xb, f, a, r.pnl, q))
    return out


def evaluate(trs, start_bar, end_bar, day_of, worst, dll=0.0):
    """One evaluation from start_bar, to end_bar (exclusive). worst: within a bar the order worse for the trader
    (best point first, so the peak rises, then the worst; a breach beats a pass); else the better one."""
    e = peak = 0.0
    dd = 0.0
    day_start, cur_day, paused = 0.0, -1, False
    for eb, xb, f, a, pnl, q in trs:
        if eb < start_bar:
            continue
        if eb >= end_bar:
            break
        if day_of[eb] != cur_day:
            cur_day, day_start, paused = day_of[eb], e, False
        if paused:
            continue
        tick = 0.25 * q * 2.0
        for k in range(len(f)):
            fe, ae = e + f[k], e + a[k]
            hit_target = fe >= TARGET + BUFFER + tick
            if worst:
                p2 = max(peak, fe)
                if ae <= p2 - TRAIL:
                    return "fail", eb + k, max(dd, p2 - ae)
                if hit_target:
                    return "pass", eb + k, dd
                peak = p2
            else:
                if hit_target:
                    return "pass", eb + k, dd
                if ae <= peak - TRAIL:
                    return "fail", eb + k, max(dd, peak - ae)
                peak = max(peak, fe)
            dd = max(dd, peak - ae)
            if dll > 0 and ae <= day_start - dll:  # sensitivity: the day's loss limit closes and pauses the day
                e = day_start - dll
                paused = True
                break
        else:
            e += pnl
            if e >= TARGET:
                return "pass", xb, dd
            continue
    return ("expired" if end_bar < 10**12 else "open"), None, dd


def run_windows(trs, sessions, first_ok, day_of, bar_day, dll=0.0, chain=False):
    rows = []
    s = first_ok
    last_day = sessions[-1]
    while s < len(sessions):
        d0 = sessions[s]
        end_day = d0 + pd.Timedelta(days=DAYS)
        start_bar = int(np.searchsorted(bar_day, d0))
        end_bar = int(np.searchsorted(bar_day, end_day))
        complete = end_day <= last_day + pd.Timedelta(days=1)
        res = {}
        for worst in (True, False):
            out, at, dd = evaluate(trs, start_bar, end_bar if complete else 10**12, day_of, worst, dll)
            if out == "open" or (out == "expired" and not complete):
                out = "unresolved (data ends)"
            res[worst] = (out, at, dd)
        (ow, aw, ddw), (ob, ab, _) = res[True], res[False]
        same = ow == ob and (aw is None or bar_day[aw] == bar_day[ab])
        when = aw if aw is not None else ab
        rows.append({"start": d0.date(), "outcome worst-order": ow, "outcome best-order": ob,
                     "sequencing-dependent": not same,
                     "calendar days": (bar_day[aw] - d0).days + 1 if aw is not None else np.nan,
                     "sessions": int(np.searchsorted(sessions, bar_day[aw]) - s + 1) if aw is not None else np.nan,
                     "intraday DD": ddw})
        if chain:
            if ow == "expired" and ob == "expired":
                s = int(np.searchsorted(sessions, end_day))
            elif when is None:
                break
            else:
                s = int(np.searchsorted(sessions, bar_day[when])) + 1
        else:
            s += 1
    return pd.DataFrame(rows)


def summarize(w, label):
    n = len(w)
    res = w[w["outcome worst-order"] != "unresolved (data ends)"]
    det = res[~res["sequencing-dependent"]]
    out = {"evaluations": n, "unresolved (data ends)": n - len(res),
           "sequencing-dependent": int(res["sequencing-dependent"].sum())}
    for o in ("pass", "fail", "expired"):
        out[o] = int((det["outcome worst-order"] == o).sum())
    for o in ("pass", "fail", "expired"):
        out[f"{o} % (worst order)"] = 100 * (res["outcome worst-order"] == o).mean() if len(res) else np.nan
        out[f"{o} % (best order)"] = 100 * (res["outcome best-order"] == o).mean() if len(res) else np.nan
    p = res[res["outcome worst-order"] == "pass"]
    f = res[res["outcome worst-order"] == "fail"]
    out["median days to pass"] = p["calendar days"].median()
    out["median days to fail"] = f["calendar days"].median()
    out["passes before 7th session"] = int((p["sessions"] < 7).sum())
    e = res[res["outcome worst-order"] == "expired"]
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
        trs = marks(tr, o, h, lo)
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
