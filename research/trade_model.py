"""Round seventy-nine: a combined, walk-forward trade-quality model on the bot's trades, sized on a 50K Apex account.

    python research/trade_model.py nsx1m_scaled.pkl nq1m_scaled.pkl "histdata_raw/*/DAT_ASCII_NSXUSD_M1_*.csv" \
        "nq1m/*.parquet"

Single cues at the signal mostly fail (rounds eighteen and seventy); one (B8, the rejection wick) replicated (round
seventy-five) but sizing on it alone didn't fit a $2,000 drawdown (rounds seventy-six and seventy-seven). Here all 34 of
round seventy's cues go into one model, fitted only on past trades, to rank each new trade at its signal.

Trades and cues: research/cues.py's build(), unchanged (v1.6 rules on 1-minute bars, 4 MNQ, $200 max loss, take-profit
from the fill, Fed days, no skip dates; trades on the first session of each month dropped). Round eighteen's ten facts
are not added (research/meta_label.py computes them on a different engine run; several overlap the 34 cues).
Evaluation trades: 3 losers a day; funded-account trades: a second build with 2 losers a day (cues.LOSERS = 2), as
research/apex_payouts.py trades the funded account.

Model, fixed before running:
  features: the 34 cues (0/1), missing values (a cue not defined for that trade) filled with the training mean, then
    standardised with the training mean and sd;
  primary: L2-regularised logistic regression, C = 0.1, target = the trade won (P/L > 0), score = predicted
    probability; secondary (reported, not used for the decision): ridge regression, alpha = 10, target = P/L.
  Walk-forward, no peeking: index, for each year Y = 2015..2026, train on index trades of 2011..Y-1, score year Y.
    NQ futures, for each year Y = 2015..2025, train on index trades of 2011..Y-1 plus NQ trades of 2015..Y-1 (for
    Y = 2015: index 2011-2014 only), score NQ year Y.
  Terciles: thresholds = the 1/3 and 2/3 quantiles of the model's scores on its own training trades.
  Sizing rule: top tercile 6 MNQ, middle 4, bottom 2 (the same 25-point cap, so $300 / $200 / $100 max loss); the
    funded account's trades are scored by the same year's model and sized the same way.
Measures, out of sample only (index 2015 - Sep 2026; NQ futures March 2015 - 2025): AUC; win % and $ a trade (at
4 MNQ) by tercile; the 50K intraday-trail evaluation pass / bust % in 30 days (research/apex25k.py attempt, $3,000
target, $2,000 drawdown trailing open profit) and payouts per evaluation (research/apex_payouts.py rules, base caps)
for the sizing rule against flat 4 MNQ on the same sessions.
Adoption bar, fixed before running: top-tercile $ a trade above bottom-tercile $ a trade with Welch t >= 2 on both the
index 2015-26 and NQ 2015-25 (primary model), AND payouts per evaluation higher than flat 4 MNQ on both, with an
evaluation pass rate no lower on either.
"""
from __future__ import annotations

import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402
import cues as C  # noqa: E402

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
SIZE = {0: 0.5, 1: 1.0, 2: 1.5}  # bottom / middle / top tercile, as a multiple of 4 MNQ


def features(train: pd.DataFrame, test: pd.DataFrame):
    xtr = train[C.CUES].astype(float)
    mu = xtr.mean()
    xtr = xtr.fillna(mu)
    sd = xtr.std(ddof=0).replace(0, 1.0)
    xte = test[C.CUES].astype(float).fillna(mu)
    return ((xtr - mu) / sd).to_numpy(), ((xte - mu) / sd).to_numpy()


def score_year(train: pd.DataFrame, tests: list[pd.DataFrame]):
    """Fit on train; return, for each test frame, (logistic score, ridge score, logistic tercile, ridge tercile)."""
    out = []
    xtr, _ = features(train, train)
    lr = LogisticRegression(C=0.1, max_iter=2000).fit(xtr, train.win.astype(int))
    rg = Ridge(alpha=10.0).fit(xtr, train.pnl)
    q_l = np.quantile(lr.predict_proba(xtr)[:, 1], [1 / 3, 2 / 3])
    q_r = np.quantile(rg.predict(xtr), [1 / 3, 2 / 3])
    for te in tests:
        if te.empty:
            out.append((np.array([]),) * 4)
            continue
        _, xte = features(train, te)
        sl, sr = lr.predict_proba(xte)[:, 1], rg.predict(xte)
        out.append((sl, sr, np.searchsorted(q_l, sl, side="right"), np.searchsorted(q_r, sr, side="right")))
    return out


def walk(kind: str, idx3: pd.DataFrame, idx2: pd.DataFrame, nq3: pd.DataFrame, nq2: pd.DataFrame):
    """Out-of-sample scores and terciles for the evaluation (3-loser) and funded (2-loser) trades of one data set."""
    ev = (idx3 if kind == "index" else nq3).copy()
    pa = (idx2 if kind == "index" else nq2).copy()
    for col in ("s_l", "s_r", "t_l", "t_r"):
        ev[col] = np.nan
        pa[col] = np.nan
    years = range(2015, 2027) if kind == "index" else range(2015, 2026)
    for y in years:
        train = idx3[idx3.day.dt.year < y]
        if kind == "nq":
            train = pd.concat([train, nq3[nq3.day.dt.year < y]])
        me, mp = ev.day.dt.year == y, pa.day.dt.year == y
        (a, b, c, d), (e, f, g, h) = score_year(train, [ev[me], pa[mp]])
        if me.any():
            ev.loc[me, ["s_l", "s_r", "t_l", "t_r"]] = np.c_[a, b, c, d]
        if mp.any():
            pa.loc[mp, ["s_l", "s_r", "t_l", "t_r"]] = np.c_[e, f, g, h]
    y0 = 2015
    return ev[ev.day.dt.year >= y0], pa[pa.day.dt.year >= y0]


def welch(a, b):
    return (a.mean() - b.mean()) / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def payouts(ev: pd.DataFrame, pa: pd.DataFrame, sessions, m_ev, m_pa) -> float:
    def days_of(df, m):
        by = {}
        for day, hi, lo, p, k in zip(df.day, df.hi, df.lo, df.pnl, m, strict=True):
            if k > 0:
                by.setdefault(day, []).append((p * k, hi * k, lo * k))
        return [(s, by.get(s, [])) for s in sessions]
    ev_days, pa_days = days_of(ev, m_ev), days_of(pa, m_pa)
    last = sessions[-1]
    out, memo = [], {}
    for s in range(len(ev_days)):
        r, used = A.attempt(ev_days[s:], 1, "intraday", 30)
        if r == "timeout" and (last - sessions[s]).days < 30:
            continue
        if r != "passed":
            out.append(0.0)
            continue
        first = s + used
        if first not in memo:
            paid, _, _ = P.pa_run(pa_days[first:], 1, P.CAPS["base"])
            memo[first] = sum(a for _, a in paid)
        out.append(memo[first])
    return float(np.mean(out))


def main() -> None:
    nsx, nq, nsx_raw, nq_raw = sys.argv[1:5]
    pd.set_option("display.width", 250)
    built = {}
    for losers in (3, 2):
        C.LOSERS = losers  # read by build(); set before the workers fork
        with ProcessPoolExecutor(max_workers=2) as pool:
            for k, df, ss, _ in pool.map(C.build, [(nsx, nsx_raw, "index"), (nq, nq_raw, "nq")]):
                built[(k, losers)] = (df, ss)
    idx3, idx_ss = built[("index", 3)]
    idx2, _ = built[("index", 2)]
    nq3, nq_ss = built[("nq", 3)]
    nq2, _ = built[("nq", 2)]
    nq3 = nq3[nq3.day >= pd.Timestamp("2015-03-01")]
    nq2 = nq2[nq2.day >= pd.Timestamp("2015-03-01")]
    print(f"trades (3 / 2 losers): index {len(idx3)} / {len(idx2)}, NQ {len(nq3)} / {len(nq2)}")

    verdict = True
    for kind, ss_all, label in (("index", idx_ss, "index 2015-2026"), ("nq", nq_ss, "NQ 2015-2025")):
        ev, pa = walk(kind, idx3, idx2, nq3, nq2)
        y1 = 2026 if kind == "index" else 2025
        ss = [s for s in ss_all if s >= pd.Timestamp("2015-03-01" if kind == "nq" else "2015-01-01") and s.year <= y1]
        print(f"\n{label}: {len(ev)} out-of-sample trades")
        for model, s_col, t_col in (("logistic (primary)", "s_l", "t_l"), ("ridge (secondary)", "s_r", "t_r")):
            auc = roc_auc_score(ev.win.astype(int), ev[s_col])
            rows = []
            for t in (2, 1, 0):
                g = ev[ev[t_col] == t]
                rows.append({"tercile": {2: "top", 1: "middle", 0: "bottom"}[t], "trades": len(g),
                             "win %": 100 * g.win.mean(), "$/trade at 4 MNQ": g.pnl.mean()})
            top, bot = ev[ev[t_col] == 2].pnl, ev[ev[t_col] == 0].pnl
            t_tb = welch(top, bot)
            print(f"  {model}: AUC {auc:.3f}; top vs bottom $ a trade t {t_tb:.2f}")
            print("   " + pd.DataFrame(rows).round(2).to_string(index=False).replace("\n", "\n   "))
            if s_col == "s_l":
                verdict &= t_tb >= 2.0
        m_ev = ev.t_l.map(SIZE).to_numpy()
        m_pa = pa.t_l.map(SIZE).to_numpy()
        base = C.rule_effect(ev, ss, np.ones(len(ev)))
        base["$ paid per eval"] = payouts(ev, pa, ss, np.ones(len(ev)), np.ones(len(pa)))
        rule = C.rule_effect(ev, ss, m_ev)
        rule["$ paid per eval"] = payouts(ev, pa, ss, m_ev, m_pa)
        print(f"  Apex 50K intraday trail, {label}")
        print("   " + pd.DataFrame([base, rule], index=["flat 4 MNQ", "6 / 4 / 2 by tercile"]).round(1)
              .to_string().replace("\n", "\n   "))
        verdict &= rule["$ paid per eval"] > base["$ paid per eval"] and rule["eval pass %"] >= base["eval pass %"]
    print(f"\nAdoption bar: {'PASS' if verdict else 'FAIL'}")


if __name__ == "__main__":
    main()
