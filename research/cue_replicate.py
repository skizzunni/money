"""Round seventy-four: a pre-registered replication of round seventy's three near-misses.

    python research/cue_replicate.py nsx1m_scaled.pkl nq1m_scaled.pkl "histdata_raw/*/DAT_ASCII_NSXUSD_M1_*.csv" \
        "nq1m/*.parquet"

Round seventy (research/cues.py) scanned 34 cues at the bot's signal on index 2011-2018. Only B2 passed its false
discovery bar, and it failed on 2019-2026. Three more were close but missed the bar, and were never looked at on later
data:
  B8  the 5-minute signal bar's wick against the trade is more than half its range (better: t +2.97 on 2011-18)
  B3  the 5-minute signal bar's range is more than 1.5x the average 5-minute range so far today (worse: t -2.60)
  C3  the last trading day of the month (worse: t -2.55)
Definitions, the bot and the data are exactly research/cues.py's (its build() is reused unchanged): v1.6 rules on
1-minute bars, 4 MNQ, $200 max loss, 3 losers a day, take-profit from the fill, Fed days, no skip dates; trades on the
first session of each month dropped.

Rules, fixed before running (one each):
  B8: keep every trade, 2x size on the trades with the rejection wick.
  B3: skip the trades with an oversized signal bar.
  C3: skip the trades on the last trading day of the month.
Skipping or doubling a trade leaves the bot's other trades as they were (as round seventy; an approximation for the
loser limit).
Test: the daily P/L difference against the bot alone (every session counted, zero where the rule changes nothing),
t = mean / sd x sqrt(sessions).
Pass bar, fixed before running (Bonferroni for 3 rules): the predicted sign (B8 positive; B3 and C3 positive, i.e.
skipping helps) with t >= 2.4 on index 2019 - Sep 2026, AND the predicted sign with t >= 1.5 on NQ futures 2019-2025
(NQ 2015-2018 overlaps the discovery years; the full 2015-2025 is also shown).
For a rule that passes: $ a week, win %, worst losing stretch, the 50K intraday-trail evaluation pass / bust % in 30
days (research/apex25k.py attempt, $3,000 target, $2,000 drawdown trailing open profit) and payouts per evaluation
(research/apex_payouts.py rules, base caps; the rule applies in the funded account too) against the bot alone, on
index 2011-18, 2019-26 and NQ futures.
"""
from __future__ import annotations

import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402
import cues as C  # noqa: E402

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
RULES = {"B8": ("2x on the rejection-wick trades", "double"), "B3": ("skip the oversized signal bars", "skip"),
         "C3": ("skip the last trading day of the month", "skip")}


def mult_for(df: pd.DataFrame, cue: str) -> np.ndarray:
    x = df[cue].to_numpy()
    if RULES[cue][1] == "double":
        return np.where(x == 1, 2.0, 1.0)
    return np.where(x == 1, 0.0, 1.0)


def diff_t(df: pd.DataFrame, sessions, mult: np.ndarray) -> tuple[float, float, int]:
    d = pd.Series(df.pnl.to_numpy() * (mult - 1.0), index=df.day).groupby(level=0).sum()
    d = d.reindex(sessions, fill_value=0.0)
    sd = d.std(ddof=1)
    return (float(d.mean() / sd * math.sqrt(len(d))) if sd > 0 else 0.0), float(d.mean()), len(d)


def payouts_per_eval(df, sessions, mult) -> float:
    by_day = {}
    for day, hi, lo, p, k in zip(df.day, df.hi, df.lo, df.pnl, mult, strict=True):
        if k > 0:
            by_day.setdefault(day, []).append((p * k, hi * k, lo * k))
    days = [(s, by_day.get(s, [])) for s in sessions]
    last = sessions[-1]
    out, memo = [], {}
    for s in range(len(days)):
        r, used = A.attempt(days[s:], 1, "intraday", 30)
        if r == "timeout" and (last - sessions[s]).days < 30:
            continue
        if r != "passed":
            out.append(0.0)
            continue
        first = s + used
        if first not in memo:
            paid, _, _ = P.pa_run(days[first:], 1, P.CAPS["base"])
            memo[first] = sum(a for _, a in paid)
        out.append(memo[first])
    return float(np.mean(out))


def main() -> None:
    nsx, nq, nsx_raw, nq_raw = sys.argv[1:5]
    pd.set_option("display.width", 250)
    with ProcessPoolExecutor(max_workers=2) as pool:
        built = {k: (df, ss) for k, df, ss, _ in pool.map(C.build, [(nsx, nsx_raw, "index"), (nq, nq_raw, "nq")])}
    idx_df, idx_ss = built["index"]
    nq_df, nq_ss = built["nq"]
    sets = {"index 2011-18": C.period(idx_df, idx_ss, 2011, 2018),
            "index 2019-26": C.period(idx_df, idx_ss, 2019, 2026)}
    nq_df = nq_df[nq_df.day >= pd.Timestamp("2015-03-01")]
    nq_ss = [s for s in nq_ss if s >= pd.Timestamp("2015-03-01")]
    sets["NQ 2015-25"] = C.period(nq_df, nq_ss, 2015, 2025)
    sets["NQ 2019-25"] = C.period(nq_df, nq_ss, 2019, 2025)
    rows, passed = [], []
    for cue, (name, _) in RULES.items():
        row = {"rule": f"{cue}: {name}"}
        for label, (d, ss) in sets.items():
            t, m, _ = diff_t(d, ss, mult_for(d, cue))
            row[f"t {label}"] = t
            row[f"$/day {label}"] = m
        ok = row["t index 2019-26"] >= 2.4 and row["t NQ 2019-25"] >= 1.5
        row["verdict"] = "PASS" if ok else "FAIL"
        rows.append(row)
        if ok:
            passed.append(cue)
    print("Daily P/L difference against the bot alone (positive = the rule helps)")
    print(pd.DataFrame(rows).round(2).to_string(index=False))
    print(f"\nRules that pass: {passed or 'none'}")
    for cue in passed:
        for label in ("index 2011-18", "index 2019-26", "NQ 2015-25"):
            d, ss = sets[label]
            base = C.rule_effect(d, ss, np.ones(len(d)))
            base["$ paid per eval"] = payouts_per_eval(d, ss, np.ones(len(d)))
            r = C.rule_effect(d, ss, mult_for(d, cue))
            r["$ paid per eval"] = payouts_per_eval(d, ss, mult_for(d, cue))
            print(f"\n{cue}, {label}")
            print(pd.DataFrame([base, r], index=["bot", RULES[cue][0]]).round(1).to_string())


if __name__ == "__main__":
    main()
