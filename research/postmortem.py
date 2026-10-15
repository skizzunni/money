"""Why do noise-area momentum's trades lose? A trade-level post-mortem, and overlays built from it.

    python research/postmortem.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Every trade of the strategy as traded (resting stop at the line) on 1-minute data, 1 MNQ at today's
price and costs, with its maximum adverse and favourable excursion (MAE, MFE) in units of the initial
risk (entry to the line), how far price went on after a stop-out, the entry time, whether it was a
re-entry, how far the close was past the line at entry, and, for stop-outs that then went on at least
one risk in our direction, how far price overshot the line before resuming.

Fixed before running:
  * Periods: study 2011-2018, confirm 2019-2022, final test 2023 - Sep 2026 (run once).
  * Overlays, each with one number taken from the 2011-2018 trades:
      O1 tighter initial stop at f x initial risk, f = the 80th percentile of winners' MAE/risk (so 80% of
         winners keep their room); the stop still trails the line if the line is closer.
      O2 breakeven: once MFE >= 1 x initial risk, the stop moves to the entry price (no number to pick).
      O3 entry cutoff: no new entries at or after the first half hour whose own and later entries have a
         negative combined P&L in 2011-2018 (none if there is no such half hour).
      O4 no re-entry: after a stop-out, no new entry on the same side that day, if same-side re-entries
         lose money in 2011-2018 (otherwise no change).
      O5 minimum push: skip entries whose close is less than d past the line (d in units of that check's
         sigma), d = the 25th percentile of 2011-2018 entries, if those entries lose money in 2011-2018.
    Added after the first run showed that 77% of losers are premature stop-outs that die within minutes:
      O6 continuation entry: a stop order at the signal bar's close instead of a market order at the next
         open, good until the next check. No number to pick.
      O7 buffered stop: the stop sits b x sigma below the line (above it for a short), b = the 75th
         percentile of the overshoot of 2011-2018's premature stop-outs; it trails the line as before.
      O6+O7 together.
    Added after the second run (the buffered stop was confirmed and the year table showed 2025-2026 as the
    least trending years):
      O8 trend filter: no new entries unless the mean trendiness of the previous 20 complete sessions is at
         least 1.0, trendiness = |open-to-close move| / that day's 15:30 noise (1.0 = days move as much as
         their noise; the threshold is the definition, not a choice). O7+O8 together.
      A sensitivity check of O7's number: b = 0.12 and 0.36 on the study and confirmation periods only.
  * An overlay is confirmed if on 2019-2022 it raises $/day by at least 10% and does not lower the t-stat.
    The confirmed overlays together are run once on 2023-2026 and pass if they beat the base on $/day
    and t there too.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import noise_eval as E  # noqa: E402
import published_lab as L  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

PERIODS = {"study": (2011, 2019), "confirm": (2019, 2023), "test": (2023, 2100)}


@dataclass
class Overlay:
    tight_f: float | None = None  # O1
    breakeven: bool = False  # O2
    cutoff_k: int | None = None  # O3: no entries at check index >= cutoff_k
    no_reentry: bool = False  # O4
    min_push: float | None = None  # O5, in sigma units
    cont_entry: bool = False  # O6
    buffer_b: float | None = None  # O7, in sigma units
    trend_filter: bool = False  # O8


@dataclass
class Trade:
    day: object
    direction: int
    k_entry: int
    entry: float
    exit: float
    reason: str
    risk: float  # $ from entry to the stop at entry (at least one tick)
    mae: float  # $, most adverse while open
    mfe: float  # $, most favourable while open
    after: float  # $, most favourable from the exit to the close (how far it went on without us)
    overshoot: float  # sigma units past the line before resuming, premature stop-outs only (else nan)
    minutes: int
    reentry: bool
    push: float  # (close - line) / line / sigma at entry, in sigma units
    pnl: float


def simulate(days: L.Days, i: int, sigma: np.ndarray, notional: float, ov: Overlay) -> list[Trade]:
    o0, pc = days.o[i, 0], days.prev_close[i]
    o, h, l, cf, miss = days.o[i], days.h[i], days.l[i], days.cf[i], days.missing[i]
    tick = 0.25 / 30_661 * (notional / 2.0)  # one tick as a share of price, scaled to the data's level
    trades: list[Trade] = []
    pos, entry, entry_min, k_entry, risk_px, push = 0, 0.0, 0, 0, 0.0, 0.0
    line = tight = math.nan
    sig = 0.0
    mae_px = mfe_px = 0.0
    stopped_sides: set[int] = set()
    pending: tuple[int, float, float, float] | None = None  # (direction, trigger, line, push)
    close_px = cf[L.MINUTES - 1]

    def stop_level() -> float:
        s = line - pos * (ov.buffer_b or 0.0) * sig * line
        if not math.isnan(tight):
            s = max(s, tight) if pos > 0 else min(s, tight)
        if ov.breakeven and mfe_px >= risk_px:
            s = max(s, entry) if pos > 0 else min(s, entry)
        return s

    def finish(m_exit: int, px: float, reason: str) -> None:
        nonlocal pos
        d = pos
        seg_after = slice(m_exit, L.MINUTES)
        after_px = (np.nanmax(h[seg_after]) - px) if d > 0 else (px - np.nanmin(l[seg_after]))
        overshoot = math.nan
        if reason == "stop" and after_px >= risk_px:  # premature: how far past the line before resuming?
            resume = np.flatnonzero((h[m_exit:] >= px + risk_px) if d > 0 else (l[m_exit:] <= px - risk_px))
            m_res = m_exit + int(resume[0]) if len(resume) else L.MINUTES - 1
            seg = slice(m_exit, m_res + 1)
            over = (line - np.nanmin(l[seg])) if d > 0 else (np.nanmax(h[seg]) - line)
            overshoot = max(over, 0.0) / (line * sig)
        scale = notional / entry
        pnl = d * (px - entry) * scale - 2 * E.TICK_D - E.FEE_D
        trades.append(Trade(days.dates[i], d, k_entry, entry, px, reason, risk_px * scale, mae_px * scale,
                            mfe_px * scale, max(after_px, 0.0) * scale, overshoot, m_exit - entry_min,
                            d in stopped_sides, push, pnl))
        if reason == "stop":
            stopped_sides.add(d)
        pos = 0

    def open_trade(mm: int, px: float, d: int, ln: float, k: int, push_now: float) -> None:
        nonlocal pos, entry, entry_min, k_entry, line, push, risk_px, tight, mae_px, mfe_px
        pos, entry, entry_min, k_entry, line, push = d, px, mm, k, ln, push_now
        risk_px = max(d * (entry - (ln - d * (ov.buffer_b or 0.0) * sig * ln)), tick)
        tight = (entry - d * ov.tight_f * risk_px) if ov.tight_f is not None else math.nan
        mae_px = mfe_px = 0.0

    for k, m in enumerate(L.CHECKS):
        p = cf[m - 1]
        sig = sigma[i, k]
        ub = max(o0, pc) * (1 + sig)
        lb = min(o0, pc) * (1 - sig)
        pending = None  # an unfilled continuation order expires at the next check
        if pos != 0:
            line = ub if pos > 0 else lb
        elif ov.cutoff_k is None or k < ov.cutoff_k:
            want = 1 if p > ub else -1 if p < lb else 0
            if want and ov.no_reentry and want in stopped_sides:
                want = 0
            if want:
                ln = ub if want > 0 else lb
                push_now = abs(p / ln - 1) / sig
                if ov.min_push is not None and push_now < ov.min_push:
                    want = 0
            if want:
                if ov.cont_entry:
                    pending = (want, p, ln, push_now)
                else:
                    px, mm = days.open_at(i, m)
                    open_trade(mm, px, want, ln, k, push_now)
        m_end = L.CHECKS[k + 1] if k + 1 < len(L.CHECKS) else L.MINUTES
        for mm in range(m, m_end):
            if miss[mm]:
                continue
            if pos == 0 and pending is not None:
                d, trig, ln, push_now = pending
                if (d > 0 and h[mm] >= trig) or (d < 0 and l[mm] <= trig):
                    fill = (max(o[mm], trig) if d > 0 else min(o[mm], trig))
                    open_trade(mm, fill, d, ln, k, push_now)
                    pending = None
            if pos == 0:
                continue
            stop = stop_level()
            if mm != entry_min and ((pos > 0 and o[mm] <= stop) or (pos < 0 and o[mm] >= stop)):
                finish(mm, o[mm], "stop")
                continue
            adverse = (entry - l[mm]) if pos > 0 else (h[mm] - entry)
            favourable = (h[mm] - entry) if pos > 0 else (entry - l[mm])
            mae_px, mfe_px = max(mae_px, adverse), max(mfe_px, favourable)
            if (pos > 0 and l[mm] <= stop) or (pos < 0 and h[mm] >= stop):
                finish(mm, min(o[mm], stop) if pos > 0 else max(o[mm], stop), "stop")
    if pos:
        finish(L.MINUTES - 1, close_px, "close")
    return trades


TREND_OK: dict[int, bool] = {}  # session index -> trailing trendiness >= 1 (set in main)


def run(days, sigma, elig, notional, ov: Overlay) -> pd.DataFrame:
    rows = [t.__dict__ for i in elig if not ov.trend_filter or TREND_OK.get(i, False)
            for t in simulate(days, i, sigma, notional, ov)]
    df = pd.DataFrame(rows)
    df["year"] = df.day.map(lambda d: d.year)
    return df


def stats(df: pd.DataFrame, sessions: pd.Index) -> dict:
    daily = df.groupby("day").pnl.sum().reindex(sessions, fill_value=0.0)
    wins, losses = df[df.pnl > 0], df[df.pnl <= 0]
    return {"trades": len(df), "$/day": daily.mean(), "t": daily.mean() / daily.std(ddof=1) * math.sqrt(len(daily)),
            "win%": 100 * len(wins) / max(len(df), 1), "avg win": wins.pnl.mean(), "avg loss": losses.pnl.mean(),
            "PF": wins.pnl.sum() / max(-losses.pnl.sum(), 1e-9),
            "max DD": (daily.cumsum().cummax() - daily.cumsum()).max()}


def fmt(s: dict) -> str:
    return (f"{s['trades']:5d} trades  ${s['$/day']:+6.2f}/day  t {s['t']:+5.2f}  win {s['win%']:4.1f}%  "
            f"avg win ${s['avg win']:6.0f}  avg loss ${s['avg loss']:6.0f}  PF {s['PF']:4.2f}  "
            f"max DD ${s['max DD']:7,.0f}")


def main() -> None:
    raw = load_histdata(sys.argv[1])
    ref = float(raw.close.iloc[-1])
    notional = ref * 2.0
    L.SLIP, L.FEE_RT = 0.0, 0.0
    days = L.Days(raw)
    sigma = L.noise_sigma(days)
    elig = [i for i in np.flatnonzero(days.full) if not days.missing[i, : days.last[i] + 1].any()
            and days.last[i] == L.MINUTES - 1 and not np.isnan(days.prev_close[i]) and not np.isnan(sigma[i]).any()]
    years = np.array([days.dates[i].year for i in elig])
    sessions = {nm: pd.Index([days.dates[i] for i, y in zip(elig, years, strict=True) if a <= y < b])
                for nm, (a, b) in PERIODS.items()}
    base = run(days, sigma, elig, notional, Overlay())
    st = base[base.year < 2019]
    print(f"1 MNQ at {ref:,.0f}. Study period 2011-2018: {len(st)} trades on {len(sessions['study'])} sessions")
    print("  base:", fmt(stats(st, sessions["study"])))

    # ---- anatomy of the losses
    losers, winners = st[st.pnl <= 0], st[st.pnl > 0]
    print(f"\nLOSSES ({len(losers)} trades, {100 * len(losers) / len(st):.0f}% of trades, ${losers.pnl.sum():,.0f}):")
    print(f"  stopped at the line {100 * (losers.reason == 'stop').mean():.0f}%, negative at the 16:00 close "
          f"{100 * (losers.reason == 'close').mean():.0f}%")
    prem = losers[(losers.reason == "stop") & (losers.after >= losers.risk)]
    print(f"  premature: stopped, then price went on >= 1 risk in our direction: {len(prem)} "
          f"({100 * len(prem) / len(losers):.0f}% of losers), ${prem.pnl.sum():,.0f}")
    print(f"  their overshoot past the line before resuming (sigma units) quantiles: "
          f"{np.round(np.nanpercentile(prem.overshoot, [25, 50, 75, 90]), 2).tolist()}")
    print(f"  re-entries (after a stop-out on the same side): {100 * losers.reentry.mean():.0f}% of losers; "
          f"re-entries overall: {len(st[st.reentry])} trades, ${st[st.reentry].pnl.sum():,.0f}, "
          f"win {100 * (st[st.reentry].pnl > 0).mean():.0f}%")
    print(f"  losers' MFE/risk quantiles (how far they went our way first): "
          f"{np.round(np.percentile(losers.mfe / losers.risk, [25, 50, 75, 90]), 2).tolist()}")
    reached = 100 * (losers.mfe >= losers.risk).mean()
    print(f"  losers that reached >= 1 risk in our favour before losing: {reached:.0f}%")
    print(f"  winners' MAE/risk quantiles (how far they went against us first): "
          f"{np.round(np.percentile(winners.mae / winners.risk, [50, 80, 90, 95]), 2).tolist()}")
    print(f"  average risk at entry ${st.risk.mean():.0f}, average loss ${losers.pnl.mean():.0f}, "
          f"average win ${winners.pnl.mean():.0f}, median minutes in trade: winners {winners.minutes.median():.0f}, "
          f"losers {losers.minutes.median():.0f}")
    by_k = st.groupby("k_entry").pnl.agg(["size", "sum", "mean"])
    by_k["time"] = [f"{(570 + L.CHECKS[k]) // 60:02d}:{(570 + L.CHECKS[k]) % 60:02d}" for k in by_k.index]
    print("  by entry time:\n" + by_k[["time", "size", "sum", "mean"]].round(0).to_string())
    q = np.percentile(st.push, [25, 50, 75])
    low_push = st[st.push < q[0]]
    print(f"  push past the line at entry (sigma units) quartiles {np.round(q, 2).tolist()}; the weakest quarter: "
          f"{len(low_push)} trades, ${low_push.pnl.sum():,.0f}, win {100 * (low_push.pnl > 0).mean():.0f}%")
    rem = by_k["sum"][::-1].cumsum()[::-1]  # P&L of this check's entries and all later ones

    # ---- the regime, year by year (why is it losing now?)
    print("\nBY YEAR (base): $/day, trades/day, win %, noise at 12:00 (bps), "
          "trendiness = |open-to-close| / noise at 15:30")
    trend = np.abs(days.cf[:, -1] / days.o[:, 0] - 1) / sigma[:, -1]
    full = np.flatnonzero(days.full)
    for j in range(20, len(full)):  # trailing mean over the previous 20 complete sessions, today excluded
        TREND_OK[full[j]] = bool(np.nanmean(trend[full[j - 20 : j]]) >= 1.0)
    for y in sorted(set(years)):
        rows = [i for i, yy in zip(elig, years, strict=True) if yy == y]
        d = base[base.year == y]
        sess = pd.Index([days.dates[i] for i in rows])
        s = stats(d, sess)
        print(f"  {y}  ${s['$/day']:+6.2f}  {len(d) / len(sess):4.2f}  {s['win%']:4.1f}%  "
              f"{1e4 * np.mean(sigma[rows, 4]):5.1f}  {np.mean(trend[rows]):4.2f}")

    # ---- overlays from the study period
    f = float(np.percentile(winners.mae / winners.risk, 80))
    cutoff = next((int(k) for k in by_k.index if rem[k] < 0), None)
    reentry_bad = st[st.reentry].pnl.sum() < 0
    push_bad = low_push.pnl.sum() < 0
    b = float(np.nanpercentile(prem.overshoot, 75))
    overlays = {
        "O1 tighter stop": Overlay(tight_f=f),
        "O2 breakeven at 1 risk": Overlay(breakeven=True),
        "O3 entry cutoff": Overlay(cutoff_k=cutoff) if cutoff is not None else None,
        "O4 no re-entry": Overlay(no_reentry=True) if reentry_bad else None,
        "O5 minimum push": Overlay(min_push=float(q[0])) if push_bad else None,
        "O6 continuation entry": Overlay(cont_entry=True),
        "O7 buffered stop": Overlay(buffer_b=b),
        "O6+O7": Overlay(cont_entry=True, buffer_b=b),
        "O8 trend filter": Overlay(trend_filter=True),
        "O7+O8": Overlay(buffer_b=b, trend_filter=True),
    }
    print(f"\nOVERLAYS: O1 f = {f:.2f}; O3 cutoff = {by_k.time[cutoff] if cutoff is not None else 'none'}; "
          f"O4 {'on' if reentry_bad else 'off (re-entries make money)'}; "
          f"O5 d = {q[0]:.2f} sigma {'on' if push_bad else 'off (weak pushes make money)'}; "
          f"O7 b = {b:.2f} sigma")
    results = {}
    confirmed = []
    base_c = stats(base[(base.year >= 2019) & (base.year < 2023)], sessions["confirm"])
    print(f"  {'':24s} study 2011-18 | confirm 2019-22")
    print(f"  {'base':24s} {fmt(stats(st, sessions['study']))}\n  {'':24s} {fmt(base_c)}")
    for name, ov in overlays.items():
        if ov is None:
            continue
        df = run(days, sigma, elig, notional, ov)
        s_study = stats(df[df.year < 2019], sessions["study"])
        s_conf = stats(df[(df.year >= 2019) & (df.year < 2023)], sessions["confirm"])
        ok = s_conf["$/day"] >= 1.1 * base_c["$/day"] and s_conf["t"] >= base_c["t"]
        results[name] = (ov, df, ok)
        if ok and "+" not in name:
            confirmed.append(name)
        print(f"  {name:24s} {fmt(s_study)}\n  {'':24s} {fmt(s_conf)}  -> {'CONFIRMED' if ok else 'no'}")

    # ---- final test
    base_t = stats(base[base.year >= 2023], sessions["test"])
    print(f"\nFINAL TEST 2023 - Sep 2026\n  {'base':24s} {fmt(base_t)}")
    if confirmed:
        combo = Overlay()
        for name in confirmed:
            ov = results[name][0]
            for field in ("tight_f", "breakeven", "cutoff_k", "no_reentry", "min_push", "cont_entry", "buffer_b"):
                v = getattr(ov, field)
                if v not in (None, False):
                    setattr(combo, field, v)
        df = run(days, sigma, elig, notional, combo) if len(confirmed) > 1 else results[confirmed[0]][1]
        s = stats(df[df.year >= 2023], sessions["test"])
        passed = s["$/day"] > base_t["$/day"] and s["t"] > base_t["t"]
        print(f"  {'+'.join(n.split()[0] for n in confirmed):24s} {fmt(s)}  -> {'PASS' if passed else 'FAIL'}")
    else:
        print("  No overlay confirmed on 2019-2022: nothing goes to the final test.")
    print("  For information only (not pre-registered): every overlay on 2023-2026")
    for name, (_ov, df, _ok) in results.items():
        print(f"  {name:24s} {fmt(stats(df[df.year >= 2023], sessions['test']))}")
    print("\nSENSITIVITY of O7's number (study | confirm only):")
    for bb in (0.12, b, 0.36):
        df = run(days, sigma, elig, notional, Overlay(buffer_b=bb))
        print(f"  b = {bb:.2f}  {fmt(stats(df[df.year < 2019], sessions['study']))}\n"
              f"           {fmt(stats(df[(df.year >= 2019) & (df.year < 2023)], sessions['confirm']))}")
    share = np.mean([TREND_OK.get(i, False) for i in elig])
    print(f"  O8 allows trading on {100 * share:.0f}% of sessions")


if __name__ == "__main__":
    main()
