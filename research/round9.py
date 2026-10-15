"""Round nine: the account, and the exit. Two more levers on the edge-to-swing ratio.

    python research/round9.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Fixed before running:
  A. Continuous exit. Noise-area momentum as traded, except that once in a trade the exit is a resting
     stop at the current noise line (updated at each half hour) instead of a check at the half hour:
     a long exits the minute price trades at or below the upper line, a short the minute it trades at or
     above the lower line, filled at the line or at the minute's open if it gapped through. Entries are
     unchanged (at the half hours only). No new parameters. Compared with the strategy as traded on
     2011-2022 first: it is a candidate only if the evaluation pass rate from every start (125 sessions)
     is at least 3 points higher and the t-stat is not more than 0.3 lower. Then confirmed on 2023-2026
     the same way, once.
  B. Account size. The same 1-contract sessions run through the evaluation rules of larger account tiers
     (target / drawdown: $25K 1,500/1,500; $50K 3,000/2,000; $100K 6,000/3,000; $150K 9,000/4,500,
     as I understand Take Profit Trader's tiers; verify before paying), with 1, 2 and 3 contracts,
     from every start day, for 125, 250 and 500 sessions.
Prices and costs as in noise_eval.py.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import noise_eval as E  # noqa: E402
import published_lab as L  # noqa: E402
import round8 as R8  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

from mnqbot.config import PropRules  # noqa: E402
from mnqbot.report import run_eval  # noqa: E402

TIERS = {"$25K": (25_000, 1_500, 1_500), "$50K": (50_000, 3_000, 2_000),
         "$100K": (100_000, 6_000, 3_000), "$150K": (150_000, 9_000, 4_500)}


def simulate_session(days: L.Days, i: int, sigma: np.ndarray, notional: float) -> tuple[float, float, int]:
    """One session with the resting stop: (P&L, worst intraday dip, trades) for 1 MNQ at today's price."""
    o0, pc = days.o[i, 0], days.prev_close[i]
    o, h, l, cf, miss = days.o[i], days.h[i], days.l[i], days.cf[i], days.missing[i]
    pos, entry, entry_min = 0, 0.0, 0
    realized = worst = 0.0
    n = 0

    def close(m_exit: int, px: float) -> None:
        nonlocal realized, worst, n, pos
        seg = slice(entry_min, m_exit + 1)
        adverse = (np.nanmin(l[seg]) - entry) if pos > 0 else (entry - np.nanmax(h[seg]))
        worst = min(worst, realized + notional * adverse / entry - 2 * E.TICK_D - E.FEE_D)
        realized += notional * pos * (px - entry) / entry - 2 * E.TICK_D - E.FEE_D
        worst = min(worst, realized)
        n, pos = n + 1, 0

    for k, m in enumerate(L.CHECKS):
        p = cf[m - 1]
        ub = max(o0, pc) * (1 + sigma[i, k])
        lb = min(o0, pc) * (1 - sigma[i, k])
        if pos == 0:
            want = 1 if p > ub else -1 if p < lb else 0
            if want:
                px, mm = days.open_at(i, m)
                pos, entry, entry_min = want, px, mm
        m_end = L.CHECKS[k + 1] if k + 1 < len(L.CHECKS) else L.MINUTES
        for mm in range(m, m_end):
            if pos == 0:
                break
            if miss[mm]:
                continue
            if pos > 0 and l[mm] <= ub:
                close(mm, min(o[mm], ub))
            elif pos < 0 and h[mm] >= lb:
                close(mm, max(o[mm], lb))
    if pos:
        close(L.MINUTES - 1, cf[L.MINUTES - 1])
    return realized, worst, n


def sessions_continuous(days: L.Days, sigma: np.ndarray, elig: list[int], notional: float) -> pd.DataFrame:
    rows = []
    for i in elig:
        if days.missing[i, : days.last[i] + 1].any():
            continue
        realized, worst, n = simulate_session(days, i, sigma, notional)
        rows.append((days.dates[i], realized, worst, n > 0, n))
    return pd.DataFrame(rows, columns=["day", "pnl", "worst", "traded", "n"]).set_index("day")


def odds(df: pd.DataFrame, prop: PropRules, horizon: int) -> tuple[float, float, float, float]:
    recs = list(zip(df.pnl, df.worst, df.trades > 0, strict=True))
    res = [run_eval(recs[s : s + horizon], prop) for s in range(len(recs) - horizon)]
    out = [r[0] for r in res]
    days = [r[1] for r in res if r[0] == "passed"]
    return (out.count("passed") / len(out), out.count("failed") / len(out), out.count("timeout") / len(out),
            float(np.median(days)) if days else math.nan)


def main() -> None:
    raw = load_histdata(sys.argv[1])
    ref = float(raw.close.iloc[-1])
    notional = ref * 2.0
    L.SLIP, L.FEE_RT = 0.0, 0.0
    days = L.Days(raw)
    sigma = L.noise_sigma(days)
    full = np.flatnonzero(days.full)
    elig = [i for i in full if not np.isnan(sigma[i]).any() and not np.isnan(days.prev_close[i])]
    base = E.sessions(days, sigma, elig, notional, None)
    base = pd.DataFrame({"pnl": base.pnl, "worst": base.worst, "trades": base.traded.astype(int)})
    cont = sessions_continuous(days, sigma, elig, notional)
    cont = pd.DataFrame({"pnl": cont.pnl, "worst": cont.worst, "trades": cont.n})
    common = base.index.intersection(cont.index)
    base, cont = base.loc[common], cont.loc[common]
    years = pd.Index(common).map(lambda d: d.year)
    print(f"A. continuous exit vs half-hour check, 1 MNQ at {ref:,.0f}, {len(common)} sessions; "
          f"trades/day as traded {base.trades.mean():.2f}, continuous {cont.trades.mean():.2f}")
    for label, mask in (("2011-2022", (years >= 2011) & (years < 2023)), ("2023-2026", years >= 2023)):
        print(f" {label}")
        R8.describe(base[mask], "as traded (half-hour check)")
        R8.describe(cont[mask], "continuous exit at the line")
    prop25 = PropRules()
    fit = (years >= 2011) & (years < 2023)
    pb, pc = odds(base[fit], prop25, 125)[0], odds(cont[fit], prop25, 125)[0]
    tb, tc = R8.tstat(base[fit].pnl.to_numpy()), R8.tstat(cont[fit].pnl.to_numpy())
    candidate = pc >= pb + 0.03 and tc >= tb - 0.3
    print(f"  2011-2022: eval pass {100 * pb:.0f}% -> {100 * pc:.0f}%, t {tb:.2f} -> {tc:.2f}: "
          f"{'candidate, confirm on 2023-2026' if candidate else 'not a candidate'}")
    if candidate:
        test = years >= 2023
        pb2, pc2 = odds(base[test], prop25, 125)[0], odds(cont[test], prop25, 125)[0]
        tb2, tc2 = R8.tstat(base[test].pnl.to_numpy()), R8.tstat(cont[test].pnl.to_numpy())
        ok = pc2 >= pb2 + 0.03 and tc2 >= tb2 - 0.3
        print(f"  2023-2026: eval pass {100 * pb2:.0f}% -> {100 * pc2:.0f}%, t {tb2:.2f} -> {tc2:.2f}: "
              f"{'CONFIRMED' if ok else 'not confirmed'}")

    print("\nB. account tiers, the strategy as traded, from every start day 2011-2026")
    print(f"  {'account':8s} {'MNQ':>3s} {'sessions':>8s} {'pass':>5s} {'fail':>5s} {'open':>5s} "
          f"{'median days to pass':>20s}")
    for name, (start, target, dd) in TIERS.items():
        prop = PropRules(start_balance=start, profit_target=target, max_drawdown=dd)
        for c in (1, 2, 3):
            df = pd.DataFrame({"pnl": base.pnl * c, "worst": base.worst * c, "trades": base.trades})
            for horizon in (125, 250, 500):
                p, q, o, med = odds(df, prop, horizon)
                print(f"  {name:8s} {c:>3d} {horizon:>8d} {100 * p:>4.0f}% {100 * q:>4.0f}% {100 * o:>4.0f}% "
                      f"{med:>20.0f}")


if __name__ == "__main__":
    main()
