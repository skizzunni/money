"""Candidates D, D + E1, D + E2 against frozen B, as pre-registered in docs/CANDIDATE_D.md (sections 4 and 5); with
--f, candidate F (docs/CANDIDATE_F.md): D, D + F1, D + F2, F1 alone and F2 alone, the same way.

    python research/eval_d.py nq <nq1m_scaled.pkl> <nq1m raw folder> <B sim.dll> <out folder> [--f]
    python research/eval_d.py mnq <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <B sim.dll> <out folder> [--f]

A pickle that has its own "scale" column (research/nq_rolls.py's roll-adjusted series) is used as it is.

NQ decides the gates; MNQ is the execution check. Candidates: the Python model (mnqbot/candidate_d.py, held to the
NinjaScript by tests/test_candidate_d.py) on the full electronic session; frozen B: its NinjaScript on the stand-in, on
09:30-16:00 bars, as every earlier B result. Every candidate gets the same skip dates (holidays, half days and sessions
with missing 09:30-16:00 minutes), FOMC dates (research/fomc_dates.csv) and NFP dates (research/nfp_dates.csv), $0.95
a side, and 2 ticks (base) and 3 ticks (stress) of slippage.

The evaluation replay (Apex 50K: $3,000 target, closed by the strategy at $3,025 plus a tick a contract; a $2,000 trail
of the highest equity including open P/L, across days; 30 calendar days) works on positions of one or more contracts:
along each bar's price path (four orders of the high and the low, as research/eval_sim.py) each contract opens at its
fill and closes at its exit where the path crosses that price; equity is checked at every point. Commission is
charged at each fill (so a breach found at a stop's price includes that exit's commission; research/eval_sim.py checks
the stop's price before it, a difference of one side's commission at a breach and nothing elsewhere).
"""
from __future__ import annotations

import glob
import math
import os
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import controlled as K  # noqa: E402
import mnq_bars as M  # noqa: E402

from mnqbot.candidate_d import DConfig, run  # noqa: E402

NY = "America/New_York"
TARGET, BUFFER, TRAIL, DAYS, FEE, PV, TICK = 3000.0, 25.0, 2000.0, 30, 0.95, 2.0, 0.25
PATHS = ("favourable first", "adverse first", "worst mix", "best mix")
CANDIDATES = {"D": {}, "D+E1": {"e1": True}, "D+E2": {"e1": True, "e2": True}}
STAGES = (("D", "D+E1"), ("D+E1", "D+E2"))
F_CANDIDATES = {"D": {}, "D+F1": {"e1": True, "e_stop": "fvg"}, "D+F2": {"e1": True, "e2": True, "e_stop": "fvg"},
                "F1 only": {"noise": False, "williams": False, "e1": True, "e_stop": "fvg"},
                "F2 only": {"noise": False, "williams": False, "e1": True, "e2": True, "e_stop": "fvg"}}
F_STAGES = (("D", "D+F1"), ("D+F1", "D+F2"))
HERE = Path(__file__).resolve().parent
FOMC = frozenset(pd.read_csv(HERE / "fomc_dates.csv").date)
NFP = frozenset(pd.read_csv(HERE / "nfp_dates.csv").date)


# ---- positions ------------------------------------------------------------------------------------------------
@dataclass
class LotX:
    qty: int
    fill_bar: int
    fill: float
    entry_kind: str  # "open": at the bar's open (market, or a limit the bar opened past); "limit": inside the bar
    exit_bar: int
    exit: float
    exit_kind: str  # "open": at the bar's open (market exit, gap through a stop); "stop" / "target": inside the bar
    level: float  # where the path crosses for an inside exit (stop, target); an inside fill crosses at fill


@dataclass
class Pos:
    d: int
    lots: list = field(default_factory=list)
    sleeve: str = ""
    r_dollars: float = math.nan  # 1R in $ for the whole position (R points x $2 x contracts)
    planned: float = math.nan
    pnl: float = 0.0

    @property
    def first(self) -> int:
        return min(x.fill_bar for x in self.lots)

    @property
    def last(self) -> int:
        return max(x.exit_bar for x in self.lots)


def exit_kind(why: str, d: int, exit_px: float, o_bar: float, slip: float) -> tuple[str, float]:
    if why == "Profit target":
        return "target", exit_px
    if why == "Stop loss":
        level = exit_px + d * slip
        if abs(exit_px - (o_bar - d * slip)) < 1e-9 and d * (o_bar - level) <= 1e-9:
            return "open", exit_px  # the bar opened at or past the stop
        return "stop", level
    return "open", exit_px  # market exits fill at the open


def positions_from_model(m, o: np.ndarray, slip: float) -> list[Pos]:
    out = []
    for c in m.campaigns:
        p = Pos(c.d, sleeve=c.sleeve, r_dollars=c.r * PV * len(c.lots), planned=c.planned, pnl=c.pnl)
        for lt in c.lots:
            ek = "open" if (c.kind == "market" or abs(lt.fill - o[lt.fill_bar]) < 1e-9) else "limit"
            xk, lvl = exit_kind(lt.why, c.d, lt.exit, o[lt.exit_bar], slip)
            p.lots.append(LotX(lt.qty, lt.fill_bar, lt.fill, ek, lt.exit_bar, lt.exit, xk, lvl))
        out.append(p)
    return out


def positions_from_b(tr: pd.DataFrame, o: np.ndarray, slip: float) -> list[Pos]:
    out = []
    for r in tr.itertuples():
        xk, lvl = exit_kind(r.why if r.why != "Profit target" else "Profit target", r.d, r.ex, o[r.xb], slip)
        p = Pos(r.d, sleeve="B", r_dollars=200.0, planned=200.0, pnl=r.pnl)
        p.lots.append(LotX(r.q, r.eb, r.en, "open", r.xb, r.ex, xk, lvl))
        out.append(p)
    return out


# ---- the replay -----------------------------------------------------------------------------------------------
def _fav_first(path: str, target_bar: bool) -> bool:
    if path == "favourable first":
        return True
    if path == "adverse first":
        return False
    return (not target_bar) if path == "worst mix" else target_bar


def replay(positions: list[Pos], o, h, l, start_bar: int, end_bar: int, path: str, target: float = TARGET,
           trail: float = TRAIL):
    """One evaluation from start_bar to end_bar (exclusive): (outcome, bar, max drawdown, equity)."""
    e = peak = dd = 0.0
    for p in positions:
        if p.first < start_bar:
            continue
        if p.first >= end_bar:
            break
        d = p.d
        open_lots: list[LotX] = []
        for k in range(p.first, p.last + 1):
            # at the open: exits at the open, then fills at the open
            pts = []  # (price, events): equity is checked after the events at each price
            for lt in p.lots:
                if lt.exit_bar == k and lt.exit_kind == "open" and lt in open_lots:
                    pts.append(("x", lt, lt.exit))
            for lt in p.lots:
                if lt.fill_bar == k and lt.entry_kind == "open":
                    pts.append(("f", lt, lt.fill))
            target_bar = any(lt.exit_bar == k and lt.exit_kind == "target" for lt in p.lots)
            fav, adv = (h[k], l[k]) if d > 0 else (l[k], h[k])
            seq = [o[k]] + ([fav, adv] if _fav_first(path, target_bar) else [adv, fav])
            inside = [lt for lt in p.lots if (lt.fill_bar == k and lt.entry_kind == "limit")
                      or (lt.exit_bar == k and lt.exit_kind in ("stop", "target"))]
            done: set = set()
            for kind, lt, _px in pts:
                if kind == "x":
                    e += d * (lt.exit - lt.fill) * lt.qty * PV - FEE * lt.qty
                    open_lots.remove(lt)
                else:
                    e -= FEE * lt.qty
                    open_lots.append(lt)
            out = _check(e, open_lots, d, o[k], peak, dd, target, trail)
            if out[0]:
                return out[0], k, out[2], out[3]
            peak, dd = out[1], out[2]
            for a, b in zip(seq[:-1], seq[1:], strict=True):
                lo_, hi_ = min(a, b), max(a, b)
                evs = []
                for lt in inside:
                    if id(lt) in done:
                        continue
                    is_fill = lt.fill_bar == k and lt.entry_kind == "limit" and lt not in open_lots
                    lvl = lt.fill if is_fill else lt.level
                    if lo_ - 1e-9 <= lvl <= hi_ + 1e-9:
                        if is_fill:
                            evs.append((abs(lvl - a), 0, lt))
                        elif lt in open_lots and lt.exit_bar == k:
                            evs.append((abs(lvl - a), 1, lt))
                for _, kind, lt in sorted(evs, key=lambda x: (x[0], x[1])):
                    done.add(id(lt))
                    if kind == 0:
                        e -= FEE * lt.qty
                        open_lots.append(lt)
                        px = lt.fill
                    else:
                        e += d * (lt.exit - lt.fill) * lt.qty * PV - FEE * lt.qty
                        open_lots.remove(lt)
                        px = lt.level
                    out = _check(e, open_lots, d, px, peak, dd, target, trail)
                    if out[0]:
                        return out[0], k, out[2], out[3]
                    peak, dd = out[1], out[2]
                out = _check(e, open_lots, d, b, peak, dd, target, trail)
                if out[0]:
                    return out[0], k, out[2], out[3]
                peak, dd = out[1], out[2]
            # contracts whose inside event the path did not reach (cannot happen for consistent data): settle them
            for lt in list(open_lots):
                if lt.exit_bar == k:
                    e += d * (lt.exit - lt.fill) * lt.qty * PV - FEE * lt.qty
                    open_lots.remove(lt)
            for lt in p.lots:
                if lt.fill_bar == k and lt.entry_kind == "limit" and id(lt) not in done and lt not in open_lots \
                        and lt.exit_bar > k:
                    e -= FEE * lt.qty
                    open_lots.append(lt)
        out = _check(e, [], d, 0.0, peak, dd, target, trail)
        if out[0]:
            return out[0], p.last, out[2], out[3]
        peak, dd = out[1], out[2]
    return ("expired" if end_bar < 10**12 else "open"), None, dd, e


def _check(e, open_lots, d, px, peak, dd, target, trail):
    eq = e + sum(d * (px - lt.fill) * lt.qty * PV for lt in open_lots)
    q = sum(lt.qty for lt in open_lots)
    if eq >= target + BUFFER + TICK * q * PV:
        return "pass", peak, dd, eq
    peak = max(peak, eq)
    dd = max(dd, peak - eq)
    if eq <= peak - trail:
        return "fail", peak, dd, eq
    return "", peak, dd, eq


def windows(positions, o, h, l, bar_day, starts, last_day):
    rows = []
    for d0 in starts:
        end_day = d0 + pd.Timedelta(days=DAYS)
        sb, eb = int(np.searchsorted(bar_day, d0)), int(np.searchsorted(bar_day, end_day))
        complete = observed(d0, end_day, last_day)
        res = {}
        for path in PATHS:
            out, at, dd, _ = replay(positions, o, h, l, sb, eb if complete else 10**12, path)
            res[path] = ("unresolved" if out == "open" else out, bar_day[at] if at is not None else None, dd)
        outs = {v[0] for v in res.values()}
        w_out, w_day, w_dd = res["worst mix"]
        rows.append({"start": d0.date(), "fully observed": complete,
                     "outcome": w_out if len(outs) == 1 else "/".join(sorted(outs)),
                     "path-dependent": len(outs) > 1, "day": w_day, "worst-path DD": w_dd})
    return pd.DataFrame(rows)


def observed(d0, end_day, last_day) -> bool:
    """Fully observed: no trading session falls between the end of the data and the window's end
    (docs/CANDIDATE_D.md section 4): every weekday after the last session up to the window's end is a weekend day."""
    if end_day <= last_day + pd.Timedelta(days=1):
        return True
    gap = pd.bdate_range(last_day + pd.Timedelta(days=1), end_day - pd.Timedelta(days=1))
    return len(gap) == 0


def non_overlapping(starts: pd.DatetimeIndex) -> pd.DatetimeIndex:
    picks, nxt = [], starts[0]
    for s in starts:
        if s >= nxt:
            picks.append(s)
            nxt = s + pd.Timedelta(days=DAYS)
    return pd.DatetimeIndex(picks)


# ---- statistics -------------------------------------------------------------------------------------------------
def continuous(positions, o, h, l, bar_day, eligible, entries_day) -> dict:
    pnl = np.array([p.pnl for p in positions])
    r = np.array([p.r_dollars for p in positions])
    b_like = bool(positions) and all(p.sleeve == "B" for p in positions)
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    scratch = np.abs(pnl) < 0.1 * r
    days = pd.Series([bar_day[p.first] for p in positions], dtype="datetime64[ns]")
    per_day = days.value_counts().reindex(eligible, fill_value=0)
    _, _, idd, final = replay(positions, o, h, l, 0, 10**12, "worst mix", target=1e18, trail=1e18)
    if abs(final - pnl.sum()) > 1e-6 * max(1.0, abs(pnl.sum())):  # the replay's contract accounting = the ledger's
        raise AssertionError(f"replay equity {final} against the ledger's {pnl.sum()}")
    top5 = np.sort(wins)[-5:].sum() if len(wins) else 0.0
    yearly = pd.Series(pnl, index=days).groupby(days.dt.year.values).sum() if len(pnl) else pd.Series(dtype=float)
    return {
        "positions": len(positions), "net $": pnl.sum(), "expectancy $": pnl.mean() if len(pnl) else math.nan,
        "expectancy R": (pnl / r).mean() if len(pnl) else math.nan,
        "avg win R": (pnl[pnl > 0] / r[pnl > 0]).mean() if len(wins) else math.nan,
        "avg loss R": (pnl[pnl < 0] / r[pnl < 0]).mean() if len(losses) else math.nan,
        "win rate %": 100 * len(wins) / len(pnl) if len(pnl) else math.nan,
        "scratches %": 100 * scratch.mean() if len(pnl) else math.nan,
        "win rate excl. scratches %": 100 * (pnl[~scratch] > 0).mean() if (~scratch).any() else math.nan,
        "profit factor": wins.sum() / -losses.sum() if len(losses) else math.inf,
        "intraday DD $": idd, "net / intraday DD": pnl.sum() / idd if idd else math.nan,
        "5 largest winners, share of net %": 100 * top5 / pnl.sum() if pnl.sum() > 0 else math.nan,
        "trades / eligible session": len(positions) / len(eligible),
        "zero-trade sessions %": 100 * (per_day == 0).mean(),
        "sessions with 0/1/2/3 entries %": " / ".join(f"{100 * (per_day == k).mean():.0f}" for k in range(4)),
        # B's $200 is a price cap, not an all-in planned budget: overruns apply to the position manager only
        "overruns": "n/a" if b_like else int(sum(p.pnl < -p.planned - 1e-9 for p in positions)),
        "worst overrun $": "n/a" if b_like else min([p.pnl + p.planned for p in positions
                                                     if p.pnl < -p.planned - 1e-9], default=0.0),
        "by year": "; ".join(f"{y} {v:+.0f}" for y, v in yearly.items()),
        "by sleeve": "; ".join(f"{s} {n} / {v:+.0f}" for s, n, v in _by_sleeve(positions)),
    }


def _by_sleeve(positions):
    s = pd.DataFrame({"sleeve": [p.sleeve.split(":")[0] for p in positions], "pnl": [p.pnl for p in positions]})
    if s.empty:
        return []
    g = s.groupby("sleeve").pnl
    return [(k, int(g.size()[k]), float(g.sum()[k])) for k in g.size().index]


def gates(w_non: pd.DataFrame, cont: dict) -> list[dict]:
    fo = w_non[w_non["fully observed"]]
    n = len(fo)
    certain = fo[~fo["path-dependent"]]
    passes = int((certain.outcome == "pass").sum())
    expired = int((fo.outcome == "expired").sum())
    worst = float(fo["worst-path DD"].max()) if n else math.nan
    rows = [("G1", "evaluation pass rate", ">= 60%", 100 * passes / n if n else math.nan, lambda v: v >= 60),
            ("G2", "expiry", "<= 15%", 100 * expired / n if n else math.nan, lambda v: v <= 15),
            ("G3", "worst window drawdown", "<= $1,500", worst, lambda v: v <= 1500),
            ("G4", "win rate (completed positions)", ">= 50%", cont["win rate %"], lambda v: v >= 50),
            ("G5", "profit factor", ">= 1.35", cont["profit factor"], lambda v: v >= 1.35)]
    return [{"gate": g, "measure": m, "threshold": t, "result": v,
             "verdict": "PASS" if (v == v and ok(v)) else "FAIL"} for g, m, t, v, ok in rows]


# ---- data -------------------------------------------------------------------------------------------------------
def nq_bars(pkl: str, raw_folder: str, first: str = "2015-03-01", last: str = "2025-06-30") -> pd.DataFrame:
    s = pd.read_pickle(pkl)
    lo = pd.Timestamp(first, tz=NY) - pd.Timedelta(days=35)
    s = s[(s.index >= lo) & (s.index < pd.Timestamp(last, tz=NY) + pd.Timedelta(days=1))]
    if "scale" in s.columns:  # the roll-adjusted series carries its own month factors (research/nq_rolls.py)
        return s[["open", "high", "low", "close", "scale"]]
    files = sorted(glob.glob(f"{raw_folder}/*.parquet"))
    raw = pd.concat([pd.read_parquet(f, columns=["timestamp", "close"]) for f in files])
    raw.index = pd.to_datetime(raw.timestamp, utc=True).dt.tz_convert(NY)
    raw = raw[~raw.index.duplicated()].close
    ratio = (s.close / raw.reindex(s.index)).dropna()
    month = ratio.index.tz_localize(None).to_period("M")
    factor = ratio.groupby(month).median()
    s = s.assign(scale=factor.reindex(s.index.tz_localize(None).to_period("M")).to_numpy())
    if s.scale.isna().any():
        raise ValueError("a month without a scale factor")
    return s[["open", "high", "low", "close", "scale"]]


def mnq_series(sep: str, dec: str) -> pd.DataFrame:
    series, _ = M.traded_series(M.load(sep), M.load(dec))
    return series[["open", "high", "low", "close"]].assign(scale=1.0)


def skip_set(bars: pd.DataFrame) -> frozenset:
    rth = K.rth(bars)
    return frozenset(K.DEFAULT_SKIP.split(",")) | frozenset(K.incomplete_sessions(rth))


# ---- runs -------------------------------------------------------------------------------------------------------
def run_candidate(args):
    name, kw, slip, path, skip = args
    bars = pd.read_pickle(path)
    cfg = DConfig(slippage_ticks=slip, skip_dates=skip, fed_dates=FOMC, nfp_dates=NFP, **kw)
    m = run(bars, cfg)
    return name, slip, m.campaigns, m.log, m.sweep_seen


def run_b(dll, rth: pd.DataFrame, slip: int, skip: frozenset) -> pd.DataFrame:
    csv = Path(tempfile.mkdtemp()) / "b.csv"
    K.write_bars(rth, csv)
    return K.run(dll, csv, UseBreakout=False, SimSlippageTicks=slip, SimCommissionPerSide=FEE,
                 SkipDates=",".join(sorted(skip)), FedDates=",".join(sorted(FOMC)))


class Shim:  # a model-like holder for positions_from_model
    def __init__(self, campaigns):
        self.campaigns = campaigns


def main():
    use_f = "--f" in sys.argv
    argv = [a for a in sys.argv if a != "--f"]
    kind, out = argv[1], Path(argv[-1])
    candidates, stages = (F_CANDIDATES, F_STAGES) if use_f else (CANDIDATES, STAGES)
    out.mkdir(parents=True, exist_ok=True)
    if kind == "nq":
        bars = nq_bars(argv[2], argv[3])
        dll, first = argv[4], pd.Timestamp("2015-03-01")
    else:
        bars = mnq_series(argv[2], argv[3])
        dll, first = argv[4], pd.Timestamp("2026-07-20")
    skip = skip_set(bars)
    pkl = out / "bars.pkl"
    bars.to_pickle(pkl)
    jobs = [(n, kw, slip, str(pkl), skip) for slip in (2, 3) for n, kw in candidates.items()]
    with ProcessPoolExecutor(max_workers=min(10, os.cpu_count() or 2)) as ex:
        results = list(ex.map(run_candidate, jobs))
    pd.to_pickle({"results": results, "skip": skip, "candidates": candidates}, out / "runs.pkl")
    o, h, l = (bars[c].to_numpy(float) for c in ("open", "high", "low"))
    bar_day = (bars.index + pd.Timedelta(hours=6)).tz_localize(None).normalize()  # the trading day (18:00 start)
    rth = K.rth(bars[["open", "high", "low", "close"]])
    ro, rh, rl = (rth[c].to_numpy(float) for c in ("open", "high", "low"))
    rday = rth.index.tz_localize(None).normalize()
    opens = pd.DatetimeIndex(sorted(set(rday[(rth.index.hour == 9) & (rth.index.minute == 30)])))
    eligible = pd.DatetimeIndex([d for d in opens if d >= first and d.strftime("%Y-%m-%d") not in skip])
    starts = eligible
    last_day = rday.max()
    non = non_overlapping(starts)
    rows, gate_rows, ledgers = [], [], {}
    sets: dict = {}
    for name, slip, campaigns, _, _ in results:
        pos = positions_from_model(Shim(campaigns), o, slip * TICK)
        pos = [p for p in pos if bar_day[p.first] >= first]
        sets[(name, slip)] = pos
    for slip in (2, 3):
        tr = run_b(dll, rth, slip, skip)
        pb = [p for p in positions_from_b(tr, ro, slip * TICK) if rday[p.first] >= first]
        sets[("B", slip)] = pb
    for (name, slip), pos in sorted(sets.items(), key=lambda x: (x[0][1], x[0][0])):
        if name == "B":
            oo, hh, ll, bd = ro, rh, rl, rday
        else:
            oo, hh, ll, bd = o, h, l, bar_day
        cont = continuous(pos, oo, hh, ll, bd, eligible, None)
        w_all = windows(pos, oo, hh, ll, bd, starts, last_day)
        w_non = w_all[pd.to_datetime(w_all.start).isin(non)]
        w_all.assign(candidate=name, slippage=slip).to_csv(out / f"windows_{name}_{slip}t.csv", index=False)

        def counts(w):
            fo = w[w["fully observed"]]
            c = {x: int((fo.outcome == x).sum()) for x in ("pass", "fail", "expired")}
            return f"{c['pass']} / {c['fail']} / {c['expired']} / {int(fo['path-dependent'].sum())} of {len(fo)}"
        row = {"candidate": name, "slippage": slip, **cont,
               "non-overlapping: pass / breach / expired / path-dependent": counts(w_non),
               "overlapping: pass / breach / expired / path-dependent": counts(w_all),
               "reserve halts": "0 (no reserve rule)"}
        rows.append(row)
        for g in gates(w_non, cont):
            gate_rows.append({"candidate": name, "slippage": slip, **g})
        ledgers[(name, slip)] = pos
    pd.DataFrame(rows).to_csv(out / "comparison.csv", index=False)
    pd.DataFrame(gate_rows).to_csv(out / "gates.csv", index=False)
    led = []
    for (name, slip), pos in ledgers.items():
        days = bar_day if name != "B" else rday
        for p in pos:
            led.append({"candidate": name, "slippage": slip, "sleeve": p.sleeve, "d": p.d,
                        "entry_day": days[p.first].date(), "first_bar": p.first, "last_bar": p.last,
                        "contracts": sum(x.qty for x in p.lots), "price risk $": p.r_dollars,
                        "planned $": p.planned,
                        "pnl $": p.pnl, "overrun": p.pnl < -p.planned - 1e-9,
                        "lots": "; ".join(f"{x.qty}@{x.fill}->{x.exit} ({x.exit_kind})" for x in p.lots)})
    pd.DataFrame(led).to_csv(out / "ledger.csv", index=False)
    # each sleeve's increment and the trades it displaces (profitable trades of the earlier stage not taken later)
    disp = []
    for slip in (2, 3):
        for a, b in stages:
            ka = {(p.first, p.sleeve): p for p in sets[(a, slip)]}
            kb = {(p.first, p.sleeve): p for p in sets[(b, slip)]}
            gone = [p for k, p in ka.items() if k not in kb]
            new = [p for k, p in kb.items() if k not in ka]
            disp.append({"slippage": slip, "from": a, "to": b, "new positions": len(new),
                         "new net $": sum(p.pnl for p in new),
                         "new sweep positions": sum(p.sleeve[:2] in ("E:", "F:") for p in new),
                         "displaced positions": len(gone), "displaced net $": sum(p.pnl for p in gone),
                         "displaced profitable": sum(p.pnl > 0 for p in gone),
                         "displaced profit $": sum(p.pnl for p in gone if p.pnl > 0)})
    pd.DataFrame(disp).to_csv(out / "increments.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 120)
    print(f"{kind}: {len(eligible)} eligible sessions {eligible[0].date()}..{eligible[-1].date()}; "
          f"{len(starts)} starts, {len(non)} non-overlapping; data to {last_day.date()}")
    print(pd.DataFrame(rows).set_index(["candidate", "slippage"]).T.to_string())
    print(pd.DataFrame(gate_rows).to_string(index=False))
    print(pd.DataFrame(disp).to_string(index=False))


if __name__ == "__main__":
    main()
