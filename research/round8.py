"""Round eight: the evaluation is a race between a small edge and large swings. Two fixes, tested.

    python research/round8.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Diagnosis. Passing a $25K / $1,500 evaluation with a strategy that averages m dollars a day with a
swing of s dollars a day is close to a gambler's-ruin problem: the pass probability rises with
m / s^2, not with the number of trades. Noise-area momentum on 1 MNQ: m ~ $18, s ~ $300. More
price-only edge has been searched for and not found (rounds six and seven). What's left is the ratio.

Fixed before running:
  A. Volatility-targeted sizing of noise-area momentum, as in the original paper. Contracts for a
     session = clip(round(K / (notional x vol20)), 0, 2), where vol20 is the standard deviation of the
     previous 20 sessions' open-to-close index returns and K is the 2011-2018 median of notional x vol20
     (so the median session trades 1 contract, calm sessions 2, wild sessions 0). A second variant only
     skips: 0 contracts when vol20 is above twice its 2011-2018 median, else 1. Judged on the evaluation
     pass rate from every start day (125 sessions), all years and 2020-2026, against flat 1 contract.
  B. The 24-hour return clock. The CME day (18:00 to 16:00 New York) in 44 half-hour bins; the mean
     return of each bin over 2011-2018, Benjamini-Hochberg 5% false discovery rate over the 44 tests,
     confirmation in 2019-2022 (same sign, one-sided p < 5%). Confirmed overnight bins (before 09:30)
     that touch each other form one trade in the direction of their mean: enter at the first bin's open,
     exit at the last bin's close, 1 MNQ, $1.24 fees + 1 tick each way. Final test on 2023 - Sep 2026,
     run once, passes at t >= 2.
  C. If B passes: the night trade and the day strategy together (never both open at once), evaluation
     odds from every start day, with and without A's sizing.
Costs and prices as in noise_eval.py: 1 MNQ at the last price in the data, today's costs.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import discovery as D  # noqa: E402
import noise_eval as E  # noqa: E402
import noise_tuning as T  # noqa: E402
import published_lab as L  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

BINS = 44  # half hours from 18:00 to 16:00 New York
OVERNIGHT_BINS = 23  # bins 0..22 end at 09:30
MIN_MINUTES = 20  # a bin needs this many of its 30 minutes


def tstat(x: np.ndarray) -> float:
    x = x[~np.isnan(x)]
    return x.mean() / x.std(ddof=1) * math.sqrt(len(x)) if len(x) > 1 and x.std(ddof=1) > 0 else 0.0


def describe(df: pd.DataFrame, label: str) -> None:
    yr = df.pnl.groupby(df.index.map(lambda d: d.year)).sum()
    recent = df[df.index.map(lambda d: d.year) >= 2020]
    p_all, q_all = T.eval_odds(df)
    p_rec, q_rec = T.eval_odds(recent)
    stretch = (df.pnl.cumsum().cummax() - df.pnl.cumsum()).max()
    t = tstat(df.pnl.to_numpy())
    print(f"  {label:34s} ${df.pnl.mean():+6.2f}/day  sd ${df.pnl.std():5.0f}  t {t:+5.2f}  "
          f"years up {int((yr > 0).sum()):2d}/{len(yr)}  worst dip ${df.worst.min():>7,.0f}  "
          f"stretch ${stretch:>7,.0f}  "
          f"eval all {100 * p_all:3.0f}%/{100 * q_all:3.0f}%  2020-26 {100 * p_rec:3.0f}%/{100 * q_rec:3.0f}%")


def part_a(raw, days, sigma, elig, notional, ref):
    L.SLIP, L.FEE_RT = 0.0, 0.0
    one = E.sessions(days, sigma, elig, notional, None)  # 1 MNQ per session: pnl, worst, traded
    full_idx = np.flatnonzero(days.full)
    day_ret = pd.Series(days.cf[full_idx, -1] / days.o[full_idx, 0] - 1, index=pd.Index(days.dates[full_idx]))
    vol20 = day_ret.rolling(20, min_periods=20).std().shift(1).reindex(one.index)
    years = one.index.map(lambda d: d.year)
    disc = (years >= 2011) & (years < 2019)
    K = np.nanmedian((notional * vol20)[disc])
    target = np.clip(np.round(K / (notional * vol20)), 0, 2)
    skip = np.where(vol20 > 2 * np.nanmedian(vol20[disc]), 0.0, 1.0)
    out = {}
    for label, c in (("flat 1 contract", np.ones(len(one))), ("volatility-targeted 0-2", target.to_numpy()),
                     ("skip wild days only", skip)):
        c = np.nan_to_num(c, nan=1.0)
        df = pd.DataFrame({"pnl": one.pnl * c, "worst": one.worst * c, "trades": one.traded * (c > 0)}, index=one.index)
        out[label] = df
    print(f"A. noise-area momentum sizing, 1 MNQ = ${notional:,.0f} at {ref:,.0f}; "
          f"contracts by volatility: {pd.Series(target).value_counts().sort_index().to_dict()}")
    for label, df in out.items():
        describe(df, label)
    return out


def bin_table(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    idx = raw.index
    m = ((idx.hour * 60 + idx.minute) - 18 * 60) % 1440
    date = pd.Index((idx + pd.Timedelta(hours=6)).date)
    keep = m < BINS * 30
    df = pd.DataFrame({"date": date[keep], "bin": (m[keep] // 30), "open": raw.open.to_numpy()[keep],
                       "high": raw.high.to_numpy()[keep], "low": raw.low.to_numpy()[keep],
                       "close": raw.close.to_numpy()[keep]})
    g = df.groupby(["date", "bin"])
    agg = g.agg(open=("open", "first"), close=("close", "last"), high=("high", "max"), low=("low", "min"),
                n=("close", "size"))
    agg = agg[agg.n >= MIN_MINUTES]
    ret = (agg.close / agg.open - 1).unstack("bin").reindex(columns=range(BINS))
    return ret, agg.open.unstack("bin"), agg.high.unstack("bin"), agg.low.unstack("bin")


def part_b(raw, notional, cost):
    ret, opens, highs, lows = bin_table(raw)
    years = ret.index.map(lambda d: d.year)
    disc, conf = (years >= 2011) & (years < 2019), (years >= 2019) & (years < 2023)
    rows = []
    for b in range(BINS):
        x, y = ret.loc[disc, b].to_numpy(), ret.loc[conf, b].to_numpy()
        rows.append((b, 1e4 * np.nanmean(x), tstat(x), 1e4 * np.nanmean(y), tstat(y)))
    tb = pd.DataFrame(rows, columns=["bin", "mean_bps", "t", "mean_bps_confirm", "t_confirm"])
    tb["time"] = tb.bin.map(lambda b: f"{(18 * 60 + 30 * b) // 60 % 24:02d}:{(30 * b) % 60:02d}")
    tb["p"] = D.two_sided_p(tb.t.to_numpy())
    tb["fdr_keep"] = D.bh(tb.p, D.FDR)
    tb["confirmed"] = tb.fdr_keep & (np.sign(tb.t) == np.sign(tb.t_confirm)) & (tb.t_confirm.abs() >= D.Z95)
    print(f"\nB. 24-hour clock: {BINS} half-hour bins, {int(tb.fdr_keep.sum())} pass the luck filter in 2011-2018, "
          f"{int(tb.confirmed.sum())} confirmed in 2019-2022")
    print(tb[tb.fdr_keep][["time", "mean_bps", "t", "mean_bps_confirm", "t_confirm", "confirmed"]].round(2)
          .to_string(index=False))
    # contiguous confirmed overnight bins -> trades
    conf_bins = [b for b in range(OVERNIGHT_BINS) if tb.loc[b, "confirmed"]]
    groups: list[list[int]] = []
    for b in conf_bins:
        if groups and b == groups[-1][-1] + 1 and np.sign(tb.loc[b, "t"]) == np.sign(tb.loc[groups[-1][0], "t"]):
            groups[-1].append(b)
        else:
            groups.append([b])
    if not groups:
        print("  No confirmed overnight window: nothing goes to the final test.")
        return None
    pnl = pd.Series(0.0, index=ret.index)
    worst = pd.Series(0.0, index=ret.index)
    traded = pd.Series(False, index=ret.index)
    for grp in groups:
        d = int(np.sign(tb.loc[grp[0], "t"]))
        entry = opens[grp[0]] * (1 + d * 0.25 / notional * 2)  # one tick of slippage on entry
        exit_px = (opens[grp[-1] + 1] if grp[-1] + 1 < BINS else None)
        if exit_px is None:
            continue
        exit_px = exit_px * (1 - d * 0.25 / notional * 2)
        ok = entry.notna() & exit_px.notna() & ret[grp].notna().all(axis=1)
        trade = (d * (exit_px / entry - 1) * notional - 1.24).where(ok, 0.0)
        hi, lo = highs[grp].max(axis=1), lows[grp].min(axis=1)
        adverse = ((lo / entry - 1) if d > 0 else (1 - hi / entry)).where(ok, 0.0) * notional - 1.24
        pnl += trade
        worst += np.minimum(adverse, np.minimum(trade, 0.0))
        traded |= ok
        print(f"  window {tb.loc[grp[0], 'time']} -> {tb.loc[grp[-1], 'time']}+30min, "
              f"{'long' if d > 0 else 'short'}")
    df = pd.DataFrame({"pnl": pnl, "worst": worst, "trades": traded.astype(int)})
    df = df[df.trades > 0]
    final = df[df.index.map(lambda d: d.year) >= 2023]
    t = tstat(final.pnl.to_numpy())
    yrs = final.pnl.groupby(final.index.map(lambda d: d.year)).sum().round(0).astype(int)
    print(f"  FINAL TEST 2023 - Sep 2026: {len(final)} nights, ${final.pnl.mean():+.2f}/night, t {t:+.2f}, "
          f"win {100 * (final.pnl > 0).mean():.0f}%, by year {yrs.to_dict()} -> {'PASS' if t >= 2 else 'FAIL'}")
    describe(df[df.index.map(lambda d: d.year) >= 2011], "overnight window, all years")
    return df if t >= 2 else None


def part_c(day_variants, night):
    print("\nC. day strategy + overnight window, 1 MNQ each, never both open at once")
    for label, day in day_variants.items():
        both = day.join(night, how="left", rsuffix="_n").fillna({"pnl_n": 0.0, "worst_n": 0.0, "trades_n": 0})
        df = pd.DataFrame({"pnl": both.pnl + both.pnl_n,
                           "worst": np.minimum(both.worst_n, both.pnl_n + both.worst),
                           "trades": both.trades + both.trades_n}, index=both.index)
        describe(df, f"night + day ({label})")


def main() -> None:
    raw = load_histdata(sys.argv[1])
    ref = float(raw.close.iloc[-1])
    notional, cost = ref * 2.0, 2 * 0.25 * 2.0 + 1.24
    days = L.Days(raw)
    sigma = L.noise_sigma(days)
    full = np.flatnonzero(days.full)
    elig = [i for i in full if not np.isnan(sigma[i]).any() and not np.isnan(days.prev_close[i])]
    day_variants = part_a(raw, days, sigma, elig, notional, ref)
    night = part_b(raw, notional, cost)
    if night is not None:
        part_c(day_variants, night)


if __name__ == "__main__":
    main()
