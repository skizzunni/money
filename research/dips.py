"""Where do the worst intraday dips and the worst losing stretch come from, and what caps them?

    python research/dips.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

The strategy as now traded (resting stop 0.24 sigma past the line), 1 MNQ at today's price and costs.

Part 1, anatomy. The ten worst intraday dips in 2011-2018: trades that day, the largest risk at entry
(entry to stop), whether a stop filled at the open past its level (a gap), and the dip itself. The worst
losing stretch: its dates, length, and the sessions in it.

Part 2, protections, each with one number from 2011-2018, fixed before running:
  P1 max trades a day = the 90th percentile of trades per traded day in 2011-2018.
  P2 daily loss stop: no new entries once today's realized loss reaches 3 x the median risk at entry.
  P3 skip entries whose risk at entry (entry to stop) is above the 90th percentile of 2011-2018 risks.
  P4 hard stop: a second stop at entry +/- the 90th percentile risk, so no trade can risk more than that.
  P1+P3, P2+P3.
A protection is confirmed if on 2019-2022 it cuts both the worst intraday dip and the max drawdown by at
least 15% while keeping at least 90% of the base's $/day. The confirmed set is run once on 2023-2026.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import noise_eval as E  # noqa: E402
import postmortem as P  # noqa: E402
import published_lab as L  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

B = 0.24


@dataclass
class Guard:
    max_trades: int | None = None  # P1
    daily_loss: float | None = None  # P2, $ (positive number)
    max_risk: float | None = None  # P3, $ (skip entries riskier than this)
    hard_stop: float | None = None  # P4, $ (cap the loss per trade at this)
    cap_next_minute: bool = False  # the cap starts the minute after the fill, as the script must do it


def simulate_day(days, i, sigma, notional, g: Guard):
    """P&L, worst dip, trades, max risk at entry, gap fills for one session under the guards."""
    o0, pc = days.o[i, 0], days.prev_close[i]
    o, h, l, cf, miss = days.o[i], days.h[i], days.l[i], days.cf[i], days.missing[i]
    tick = 0.25 / 30_661 * (notional / 2.0)
    pos, entry, entry_min = 0, 0.0, 0
    line = sig = 0.0
    realized = worst = 0.0
    n, max_risk, gaps = 0, 0.0, 0
    stop_px = 0.0
    blocked = False

    def stop_level(mm_now: int = -1):
        s = line - pos * B * sig * line
        if g.hard_stop is not None and not (g.cap_next_minute and mm_now == entry_min):
            cap = entry - pos * g.hard_stop * entry / notional
            s = max(s, cap) if pos > 0 else min(s, cap)
        return s

    def close(m_exit, px):
        nonlocal realized, worst, n, pos, gaps
        seg = slice(entry_min, m_exit + 1)
        adverse = (entry - np.nanmin(l[seg])) if pos > 0 else (np.nanmax(h[seg]) - entry)
        worst = min(worst, realized - notional * adverse / entry - 2 * E.TICK_D - E.FEE_D)
        realized += notional * pos * (px - entry) / entry - 2 * E.TICK_D - E.FEE_D
        worst = min(worst, realized)
        n, pos = n + 1, 0

    for k, m in enumerate(L.CHECKS):
        p = cf[m - 1]
        sig = sigma[i, k]
        ub = max(o0, pc) * (1 + sig)
        lb = min(o0, pc) * (1 - sig)
        if pos != 0:
            line = ub if pos > 0 else lb
        elif not blocked:
            want = 1 if p > ub else -1 if p < lb else 0
            if want:
                px, mm = days.open_at(i, m)
                ln = ub if want > 0 else lb
                risk = max(want * (px - ln * (1 - want * B * sig)), tick) * notional / px
                if g.max_risk is not None and risk > g.max_risk:
                    want = 0
                elif g.max_trades is not None and n >= g.max_trades:
                    want = 0
                elif g.daily_loss is not None and realized <= -g.daily_loss:
                    want = 0
            if want:
                pos, entry, entry_min, line = want, px, mm, ln
                max_risk = max(max_risk, risk)
        m_end = L.CHECKS[k + 1] if k + 1 < len(L.CHECKS) else L.MINUTES
        for mm in range(m, m_end):
            if pos == 0:
                break
            if miss[mm]:
                continue
            stop_px = stop_level(mm)
            if mm != entry_min and ((pos > 0 and o[mm] <= stop_px) or (pos < 0 and o[mm] >= stop_px)):
                if abs(o[mm] - stop_px) / stop_px > 2 * tick / stop_px:
                    gaps += 1
                close(mm, o[mm])
                continue
            if (pos > 0 and l[mm] <= stop_px) or (pos < 0 and h[mm] >= stop_px):
                close(mm, min(o[mm], stop_px) if pos > 0 else max(o[mm], stop_px))
    if pos:
        close(L.MINUTES - 1, cf[L.MINUTES - 1])
    return realized, worst, n, max_risk, gaps


def run(days, sigma, elig, notional, g: Guard) -> pd.DataFrame:
    rows = [(days.dates[i], *simulate_day(days, i, sigma, notional, g)) for i in elig]
    df = pd.DataFrame(rows, columns=["day", "pnl", "worst", "trades", "max_risk", "gaps"]).set_index("day")
    df["year"] = df.index.map(lambda d: d.year)
    return df


def stats(df):
    eq = df.pnl.cumsum()
    dd = (eq.cummax() - eq)
    t = df.pnl.mean() / df.pnl.std(ddof=1) * math.sqrt(len(df))
    return {"$/day": df.pnl.mean(), "t": t, "worst_dip": df.worst.min(), "max_dd": dd.max(),
            "trades/day": df.trades.mean(), "dd_end": dd.idxmax()}


def fmt(s):
    return (f"${s['$/day']:+6.2f}/day  t {s['t']:+5.2f}  worst dip ${s['worst_dip']:>7,.0f}  "
            f"max DD ${s['max_dd']:>6,.0f}  trades/day {s['trades/day']:.2f}")


def main():
    raw = load_histdata(sys.argv[1])
    ref = float(raw.close.iloc[-1])
    notional = ref * 2.0
    L.SLIP, L.FEE_RT = 0.0, 0.0
    days = L.Days(raw)
    sigma = L.noise_sigma(days)
    elig = [i for i in np.flatnonzero(days.full) if not days.missing[i, : days.last[i] + 1].any()
            and days.last[i] == L.MINUTES - 1 and not np.isnan(days.prev_close[i]) and not np.isnan(sigma[i]).any()]
    base = run(days, sigma, elig, notional, Guard())
    st = base[base.year < 2019]
    print(f"1 MNQ at {ref:,.0f}; base, 2011-2018: {fmt(stats(st))}")

    # ---- part 1: anatomy
    worst10 = st.nsmallest(10, "worst")
    print("\nThe ten worst intraday dips, 2011-2018:")
    print(worst10[["pnl", "worst", "trades", "max_risk", "gaps"]].round(0).to_string())
    trades_st = P.run(days, sigma, [i for i in elig if days.dates[i].year < 2019], notional, P.Overlay(buffer_b=B))
    print(f"  risk at entry, 2011-2018: median ${trades_st.risk.median():.0f}, "
          f"90th pct ${np.percentile(trades_st.risk, 90):.0f}, max ${trades_st.risk.max():.0f}; "
          f"trades per traded day 90th pct {np.percentile(st[st.trades > 0].trades, 90):.0f}, max {st.trades.max()}")
    big = trades_st[trades_st.risk > np.percentile(trades_st.risk, 90)]
    print(f"  the riskiest 10% of entries: {len(big)} trades, ${big.pnl.sum():,.0f}, "
          f"win {100 * (big.pnl > 0).mean():.0f}%, avg loss ${big[big.pnl <= 0].pnl.mean():.0f}")
    eq = st.pnl.cumsum()
    dd = eq.cummax() - eq
    end = dd.idxmax()
    start = eq[:end].idxmax()
    stretch = st[start:end]
    print(f"  worst losing stretch 2011-2018: {start} -> {end}, {len(stretch)} sessions, ${dd.max():,.0f}; "
          f"{(stretch.pnl < 0).sum()} losing days, {(stretch.pnl > 0).sum()} winning, "
          f"worst day ${stretch.pnl.min():,.0f}")

    # ---- part 2: protections
    q90_trades = int(round(np.percentile(st[st.trades > 0].trades, 90)))
    med_risk = float(trades_st.risk.median())
    q90_risk = float(np.percentile(trades_st.risk, 90))
    guards = {
        f"P1 max {q90_trades} trades a day": Guard(max_trades=q90_trades),
        f"P2 daily loss stop ${3 * med_risk:.0f}": Guard(daily_loss=3 * med_risk),
        f"P3 skip risk > ${q90_risk:.0f}": Guard(max_risk=q90_risk),
        f"P4 hard stop ${q90_risk:.0f}": Guard(hard_stop=q90_risk),
        "P1+P3": Guard(max_trades=q90_trades, max_risk=q90_risk),
        "P2+P3": Guard(daily_loss=3 * med_risk, max_risk=q90_risk),
    }
    conf_mask = (base.year >= 2019) & (base.year < 2023)
    base_c = stats(base[conf_mask])
    print(f"\n{'':34s} 2011-18 | 2019-22")
    print(f"{'base':34s} {fmt(stats(st))}\n{'':34s} {fmt(base_c)}")
    results, confirmed = {}, []
    for name, g in guards.items():
        df = run(days, sigma, elig, notional, g)
        s_st, s_c = stats(df[df.year < 2019]), stats(df[(df.year >= 2019) & (df.year < 2023)])
        ok = (s_c["worst_dip"] >= 0.85 * base_c["worst_dip"] and s_c["max_dd"] <= 0.85 * base_c["max_dd"]
              and s_c["$/day"] >= 0.9 * base_c["$/day"])
        results[name] = (g, df)
        if ok and "+" not in name:
            confirmed.append(name)
        print(f"{name:34s} {fmt(s_st)}\n{'':34s} {fmt(s_c)}  -> {'CONFIRMED' if ok else 'no'}")
    base_t = stats(base[base.year >= 2023])
    print(f"\nFINAL TEST 2023 - Sep 2026\n{'base':34s} {fmt(base_t)}")
    if confirmed:
        g = Guard()
        for name in confirmed:
            for f in ("max_trades", "daily_loss", "max_risk", "hard_stop"):
                v = getattr(results[name][0], f)
                if v is not None:
                    g = replace(g, **{f: v})
        df = run(days, sigma, elig, notional, g)
        s = stats(df[df.year >= 2023])
        ok = (s["worst_dip"] >= 0.85 * base_t["worst_dip"] and s["max_dd"] <= 0.85 * base_t["max_dd"]
              and s["$/day"] >= 0.9 * base_t["$/day"])
        print(f"{'+'.join(n.split()[0] for n in confirmed):34s} {fmt(s)}  -> {'PASS' if ok else 'FAIL'}")
    else:
        print("  nothing confirmed on 2019-2022")
    print("For information only: every protection on 2023-2026")
    for name, (_g, df) in results.items():
        print(f"{name:34s} {fmt(stats(df[df.year >= 2023]))}")

    # ---- added after the first run: a sweep of the per-trade cap, with the cap starting the minute after the
    # fill (the script needs the fill price). Not pre-registered: chosen looking at all periods.
    print("\nPER-TRADE CAP SWEEP ($ per contract, cap from the minute after the fill)")
    for cap in (None, 35, 100, 200, 350):
        df = run(days, sigma, elig, notional, Guard(hard_stop=cap, cap_next_minute=True))
        parts = []
        for label, m in (("2011-18", df.year < 2019), ("2019-22", (df.year >= 2019) & (df.year < 2023)),
                         ("2023-26", df.year >= 2023)):
            s = stats(df[m])
            parts.append(f"{label} ${s['$/day']:+6.2f} t {s['t']:4.2f} dip {s['worst_dip']:>6,.0f} "
                         f"DD {s['max_dd']:>5,.0f}")
        print(f"  {'none' if cap is None else f'${cap}':5s} | " + " | ".join(parts))


if __name__ == "__main__":
    main()
