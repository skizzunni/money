"""Round seventy-six: size on the rejection-wick signals, on one 50K Apex account.

    python research/wick_size.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round seventy-five (research/cue_replicate.py) replicated round seventy's cue B8 on data it had not seen: when the
5-minute signal bar's wick against the trade is more than half its range (for a long, the bar closed in the lower half
below its high; for a short, the mirror), the bot's trade does far better. Checked again on the 5-minute bars the
NinjaTrader strategy trades: about 40% of the trades, $31-53 a trade against $7-15 for the rest at 4 MNQ, 58-84% of the
bot's profit, on 2011-18, 2019-26 and NQ futures.

The question here is only how to size it on a 50K intraday-trail Apex account ($3,000 target, $2,000 drawdown trailing
open profit; funded rules as research/apex_payouts.py). Every trade keeps the bot's 25-point max loss; only the
contracts change, set at the signal from the signal bar (known before the entry fills). A size of 0 means the order is
not placed, while the bot's own state (position, losers today) runs on as if it had been, as the NinjaTrader engine
would. Splits, fixed before running (wick trades / other trades, MNQ; the evaluation and the funded account use the
same split):
  S0 4 / 4 (the bot now)       S1 6 / 2       S2 8 / 2       S3 6 / 0
  S4 8 / 0                     S5 10 / 0      S6 10 / 2
Measures, 2011-18, 2019-25 and NQ futures 2015-24 (as round sixty-one): evaluation pass / bust %, expected payouts per
evaluation (base caps), the chance of all six payouts, $ a week of the bot alone, and the worst losing stretch.
Adoption bar, fixed before running: a split replaces S0 only if its payouts per evaluation are higher than S0's in all
three periods and its evaluation pass rate is no lower than S0's in any of them; among those, the highest payouts per
evaluation on 2019-25.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
CAP = 25.0
SPLITS = {"S0 4/4": (4, 4), "S1 6/2": (6, 2), "S2 8/2": (8, 2), "S3 6/0": (6, 0), "S4 8/0": (8, 0),
          "S5 10/0": (10, 0), "S6 10/2": (10, 2)}


def wick_trades(path: str, losers: int):
    """The bot at 1 contract on 1-minute bars (as apex25k.trades_for), with each trade's wick flag from the 5-minute
    signal bar ending at the check: (session, pnl, running max of minute equity, minute equity, wick)."""
    bars = A.rth(path)
    cfg = NoiseConfig(qty=1, max_loss_per_trade=CAP * A.PV, max_losers=losers, fed_dates=A.FED, skip_dates="",
                      target_on_fill_bar=True)
    res = run(bars, cfg, minutes=1)
    idx = bars.index.tz_convert(A.NY)
    tmin = (idx.hour * 60 + idx.minute).to_numpy()
    h, lo, c = bars.high.to_numpy(float), bars.low.to_numpy(float), bars.close.to_numpy(float)
    out = []
    for t in res.trades:
        i = t.entry_bar - 1  # the 1-minute bar ending at the check
        end = tmin[i] + 1
        j = i
        while j > 0 and tmin[j - 1] >= end - 5 and idx[j - 1].date() == idx[i].date():  # the 5 minutes to the check
            j -= 1
        hh, ll, cc = h[j:i + 1].max(), lo[j:i + 1].min(), c[i]
        rng = hh - ll
        wick = rng > 0 and ((hh - cc) / rng if t.direction > 0 else (cc - ll) / rng) > 0.5
        a, b = t.entry_bar, t.exit_bar
        if t.direction > 0:
            hi_path, lo_path = h[a:b] - t.entry, lo[a:b] - t.entry
        else:
            hi_path, lo_path = t.entry - lo[a:b], t.entry - h[a:b]
        hi_path = np.append(hi_path * A.PV - A.FEE, t.pnl)
        lo_path = np.append(lo_path * A.PV - A.FEE, t.pnl)
        out.append((t.entry_time.tz_convert(A.NY).normalize().tz_localize(None), t.pnl,
                    np.maximum.accumulate(hi_path), lo_path, bool(wick)))
    return out


def sized(trades, split):
    """Per-trade dollars at the split's size (0 = no order); the evaluation and PA functions then run with q = 1."""
    w, o = split
    out = []
    for day, pnl, hi_run, lo_path, wick in trades:
        q = w if wick else o
        if q:
            out.append((day, q * pnl, q * hi_run, q * lo_path))
    return out


def evaluate(args):
    path, first, last_start, label = args
    ev_tr, pa_tr = wick_trades(path, 3), wick_trades(path, 2)
    bars = A.rth(path)
    m = bars.index.tz_convert(A.NY)
    sess = [x for x in sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
            if x >= pd.Timestamp(first)]
    last = pd.Timestamp(last_start)
    rows = []
    share = np.mean([x[4] for x in ev_tr if pd.Timestamp(first) <= x[0] <= last])
    for name, split in SPLITS.items():
        ev_days, pa_days = P.by_day(sized(ev_tr, split), sess), P.by_day(sized(pa_tr, split), sess)
        starts = passes = busts = six = 0
        paid = []
        memo = {}
        for s, day in enumerate(sess):
            if day > last:
                break
            starts += 1
            res, used = A.attempt(ev_days[s:], 1, "intraday", 30)
            busts += res == "failed"
            if res != "passed":
                paid.append(0.0)
                continue
            passes += 1
            first_pa = s + used
            if first_pa not in memo:
                pp, end, _ = P.pa_run(pa_days[first_pa:], 1, P.CAPS["base"])
                memo[first_pa] = (sum(a for _, a in pp), end == "closed")
            paid.append(memo[first_pa][0])
            six += memo[first_pa][1]
        daily = pd.Series(0.0, index=pd.DatetimeIndex([d for d in sess if d <= last]))
        for day, pnl, _, _ in sized(ev_tr, split):
            if day in daily.index:
                daily[day] += pnl
        eq = daily.cumsum()
        week = daily.groupby(daily.index.to_period("W")).sum()
        rows.append({"period": label, "split (wick/other)": name, "wick share %": 100 * share,
                     "eval pass %": 100 * passes / starts, "eval bust %": 100 * busts / starts,
                     "$ paid per eval": float(np.mean(paid)), "all 6 paid %": 100 * six / starts,
                     "$/week": week.mean(), "weeks >= $1.5k %": 100 * (week >= 1500).mean(),
                     "worst stretch": float((eq.cummax() - eq).max())})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 250)
    jobs = [(nsx, "2011-01-01", "2018-12-31", "2011-2018"), (nsx, "2019-01-01", "2025-06-30", "2019-2025"),
            (nq, "2015-03-01", "2024-12-31", "NQ 2015-2024")]
    with ProcessPoolExecutor(max_workers=3) as pool:
        df = pd.DataFrame([r for rows in pool.map(evaluate, jobs) for r in rows])
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    base = df[df["split (wick/other)"] == "S0 4/4"].set_index("period")
    ok = []
    for name in SPLITS:
        if name == "S0 4/4":
            continue
        d = df[df["split (wick/other)"] == name].set_index("period")
        good = all(d.loc[p, "$ paid per eval"] > base.loc[p, "$ paid per eval"] and
                   d.loc[p, "eval pass %"] >= base.loc[p, "eval pass %"] for p in base.index)
        print(f"{name}: {'beats' if good else 'does not beat'} S0 in all three periods")
        if good:
            ok.append((d.loc["2019-2025", "$ paid per eval"], name))
    print(f"\nadopted: {max(ok)[1] if ok else 'none (S0 stays)'}")


if __name__ == "__main__":
    main()
