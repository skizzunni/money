"""Round seventy-nine: mega-cap earnings reaction sessions as a cue for the bot.

    python research/earnings_days.py dates <edgar_dir>                    # build research/megacap_earnings.csv
    python research/earnings_days.py test bars5_scaled.pkl nq5m_scaled.pkl [nsx1m_scaled.pkl nq1m_scaled.pkl]

Reasoning, written before running. The Nasdaq-100 is dominated by Apple, Microsoft, Nvidia, Amazon, Alphabet, Meta,
Tesla and Broadcom; most report after the close, and the next session often trends. The noise-momentum bot earns on
trend days, and round seventy-three found it earns 2.5-3.4x its usual $ a day on jobs-report days (under the bar).
Hypothesis, fixed now: the bot earns more on the session that reacts to a mega-cap earnings report than on others.

Dates: SEC EDGAR (data.sec.gov/submissions/CIK##########.json and its older 'files' pages, fetched with curl): every
form 8-K (not 8-K/A) whose items include 2.02 ('Results of Operations and Financial Condition'), for Apple (CIK
320193), Microsoft (789019), Nvidia (1045810), Amazon (1018724), Google Inc. (1288776, until the October 2015
reorganisation) and Alphabet (1652044), Meta (1326801), Tesla (1318605), Avago (1441634), Broadcom Pte. Ltd. (1649338)
and Broadcom Inc. (1730168); CIKs from sec.gov's company_tickers.json and the names in each submissions file. Item 2.02
is the earnings release; it also catches the odd other results release (Tesla files its quarterly delivery numbers
under it), kept as they come. The acceptance time (UTC) is converted to New York time; the reaction session is the
same day if accepted before 09:30, else the next session (the first trading session on or after that date).
Written to research/megacap_earnings.csv with the source.

Test: the bot (v1.6, 4 MNQ, $200 max loss, 3 losers a day, take-profit from the fill, FOMC dates from
research/fomc_dates.csv, no skip list; mnqbot.noise.run on the 5-minute bars), every session, $0 on days without a
trade; trades on the first session of each month dropped (the monthly rescaling makes a fake gap there, as in round
seventy-three). Jobs-report days (research/nfp_dates.csv) are left out of both groups. Periods: index 2011-2018
(discovery), index 2019 - Sep 2026 and NQ futures 2015 - July 2025 (checks).
Pass bar, fixed before running: the bot's mean $ a day is higher on reaction sessions than on other sessions in all
three periods, AND the one-sided Welch t (reaction minus other) >= 2.0 on index 2019-26.
Only if it passes, on one 50K intraday-trail Apex account (research/wick_size.py machinery: 1-minute bars, per-trade
paths scaled, apex25k.attempt with a $3,000 target and $2,000 drawdown, apex_payouts.pa_run base caps, evaluation 3
losers a day, funded 2), a rule fixed now: 6 MNQ on reaction sessions and jobs-report days, 4 otherwise (the same
25-point cap) against flat 4: evaluation pass/bust %, paid per evaluation, $ a week, per period.
"""
from __future__ import annotations

import glob
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mnqbot.data import NY  # noqa: E402
from mnqbot.noise import RTH_OPEN, NoiseConfig, run  # noqa: E402

HERE = Path(__file__).resolve().parent
CSV = HERE / "megacap_earnings.csv"
FED = ",".join(pd.read_csv(HERE / "fomc_dates.csv").date)
CFG = dict(qty=4, max_loss_per_trade=200.0, max_losers=3, target_on_fill_bar=True, fed_dates=FED, skip_dates="")
TICKER = {"0000320193": "AAPL", "0000789019": "MSFT", "0001045810": "NVDA", "0001018724": "AMZN",
          "0001288776": "GOOG (Google Inc.)", "0001652044": "GOOGL", "0001326801": "META", "0001318605": "TSLA",
          "0001441634": "AVGO (Avago)", "0001649338": "AVGO (Broadcom Pte.)", "0001730168": "AVGO"}


def build_dates(edgar_dir: str) -> pd.DataFrame:
    rows = []
    for f in glob.glob(str(Path(edgar_dir) / "*.json")):
        name = Path(f).name
        if "CIK" in name:
            cik = name.split("CIK")[1][:10]
        elif name.startswith("sub_"):
            cik = name[4:14]
        else:
            continue
        d = json.loads(Path(f).read_text())
        r = d["filings"]["recent"] if "filings" in d else d
        for form, items, acc, acn in zip(r["form"], r["items"], r["acceptanceDateTime"], r["accessionNumber"],
                                         strict=True):
            if form == "8-K" and "2.02" in items.split(","):
                rows.append((TICKER[cik], cik, acn, acc))
    df = pd.DataFrame(rows, columns=["ticker", "cik", "accession", "accepted_utc"]).drop_duplicates("accession")
    ny = pd.to_datetime(df.accepted_utc, utc=True).dt.tz_convert(NY)
    df["accepted_new_york"] = ny.dt.strftime("%Y-%m-%d %H:%M")
    before_open = ny.dt.hour * 60 + ny.dt.minute < RTH_OPEN
    day = ny.dt.tz_localize(None).dt.normalize()
    df["reaction_from"] = (day.where(before_open, day + pd.Timedelta(days=1))).dt.strftime("%Y-%m-%d")
    df["source"] = "SEC EDGAR submissions JSON, 8-K item 2.02; reaction = same day if accepted before 09:30 ET"
    return df.sort_values("accepted_utc").reset_index(drop=True)


def sessions_of(bars: pd.DataFrame) -> pd.DatetimeIndex:
    idx = bars.index.tz_convert(NY).tz_localize(None)
    return pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == RTH_OPEN].normalize())))


def reaction_sessions(sess: pd.DatetimeIndex) -> set:
    dates = pd.to_datetime(pd.read_csv(CSV).reaction_from)
    pos = np.searchsorted(sess.values, dates.values)  # the first session on or after
    return {sess[p] for p in pos if p < len(sess)}


def welch_one_sided(a: np.ndarray, b: np.ndarray) -> float:
    return (a.mean() - b.mean()) / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def daily_pnl(path: str):
    bars = pd.read_pickle(path)
    sess = sessions_of(bars)
    first = set(pd.Series(sess).groupby(sess.to_period("M")).min())
    res = run(bars, NoiseConfig(**CFG), minutes=5)
    tf = pd.DataFrame([t.__dict__ for t in res.trades])
    e = tf.entry_time.dt.tz_convert(NY).dt.tz_localize(None).dt.normalize()
    keep = ~e.isin(first)
    sessions = sess[~sess.isin(list(first))]
    return tf[keep].groupby(e[keep]).pnl.sum().reindex(sessions, fill_value=0.0)


def test(idx_path: str, nq_path: str):
    nfp = set(pd.to_datetime(pd.read_csv(HERE / "nfp_dates.csv").date))
    rows, verdict = [], {}
    for path, periods in ((idx_path, (("index 2011-18", 2011, 2018), ("index 2019-26", 2019, 2026))),
                          (nq_path, (("NQ 2015-25", 2015, 2025),))):
        d = daily_pnl(path)
        react = reaction_sessions(sessions_of(pd.read_pickle(path)))
        for label, y0, y1 in periods:
            x = d[(d.index.year >= y0) & (d.index.year <= y1) & ~d.index.isin(list(nfp))]
            isr = x.index.isin(list(react))
            a, b = x[isr].to_numpy(), x[~isr].to_numpy()
            t = welch_one_sided(a, b)
            rows.append({"period": label, "reaction sessions": len(a), "$/day reaction": a.mean(),
                         "other sessions": len(b), "$/day other": b.mean(), "ratio": a.mean() / b.mean(),
                         "one-sided Welch t": t})
            verdict[label] = (a.mean() > b.mean(), t)
    df = pd.DataFrame(rows)
    ok = all(v[0] for v in verdict.values()) and verdict["index 2019-26"][1] >= 2.0
    return df, ok


def apex(one_idx: str, one_nq: str):
    import apex25k as A
    import apex_payouts as P
    import wick_size as W

    nfp = set(pd.to_datetime(pd.read_csv(HERE / "nfp_dates.csv").date))
    out = []
    for path, first, last_start, label in ((one_idx, "2011-01-01", "2018-12-31", "2011-2018"),
                                           (one_idx, "2019-01-01", "2025-06-30", "2019-2025"),
                                           (one_nq, "2015-03-01", "2024-12-31", "NQ 2015-2024")):
        bars = A.rth(path)
        m = bars.index.tz_convert(A.NY)
        sess_all = pd.DatetimeIndex(sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None))))
        big = reaction_sessions(sess_all) | nfp
        sess = [x for x in sess_all if x >= pd.Timestamp(first)]
        trades = {lz: W.wick_trades(path, lz) for lz in (3, 2)}
        rules = (("flat 4", lambda day: 4), ("6 on news, else 4", lambda day, big=big: 6 if day in big else 4))
        for name, rule in rules:
            def scaled(tr, rule=rule):
                return [(day, rule(day) * p, rule(day) * hi, rule(day) * lo) for day, p, hi, lo, _ in tr]
            ev, pa = P.by_day(scaled(trades[3]), sess), P.by_day(scaled(trades[2]), sess)
            starts = passes = busts = 0
            paid, memo = [], {}
            for s, day in enumerate(sess):
                if day > pd.Timestamp(last_start):
                    break
                starts += 1
                res, used = A.attempt(ev[s:], 1, "intraday", 30)
                busts += res == "failed"
                if res != "passed":
                    paid.append(0.0)
                    continue
                passes += 1
                f = s + used
                if f not in memo:
                    pp, _, _ = P.pa_run(pa[f:], 1, P.CAPS["base"])
                    memo[f] = sum(a for _, a in pp)
                paid.append(memo[f])
            daily = pd.Series(0.0, index=pd.DatetimeIndex([d for d in sess if d <= pd.Timestamp(last_start)]))
            for day, p, _, _ in scaled(trades[3]):
                if day in daily.index:
                    daily[day] += p
            week = daily.groupby(daily.index.to_period("W")).sum()
            out.append({"period": label, "rule": name, "eval pass %": 100 * passes / starts,
                        "eval bust %": 100 * busts / starts, "$ paid per eval": float(np.mean(paid)),
                        "$/week": week.mean()})
    return pd.DataFrame(out)


def main() -> None:
    pd.set_option("display.width", 200)
    if sys.argv[1] == "dates":
        df = build_dates(sys.argv[2])
        df.to_csv(CSV, index=False)
        print(f"{len(df)} filings, {df.accepted_new_york.min()} to {df.accepted_new_york.max()}")
        print(df.groupby("ticker").size().to_string())
        return
    df, ok = test(sys.argv[2], sys.argv[3])
    print(df.round(2).to_string(index=False))
    print(f"\n{'PASS' if ok else 'FAIL'}")
    if ok and len(sys.argv) > 5:
        print(apex(sys.argv[4], sys.argv[5]).round(1).to_string(index=False))


if __name__ == "__main__":
    main()
