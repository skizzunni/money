"""Research (2026-11-26, docs section 180): the shipped MNQ trades on FOMC days (the scheduled 14:00 statement;
research/fomc_dates.csv, known in advance). Trades on FOMC days against the rest, by period and by year; then on the
account with the guard (near_floor_tiers.shuffled, 2,000 shuffled years per period, and the calendar starts):
  - no trading on FOMC days;
  - on FOMC days the last band entry at 13:00 and out by 13:55 (flat before the statement);
  - on FOMC days the last band entry at 13:00 only (trades already open keep their stop and target).
Run from research/: python zoo/fomc_days.py
"""
import os
import pickle
import sys
import warnings

import pandas as pd

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bad_runs as BR  # noqa: E402
import bench as B  # noqa: E402
import harness as H  # noqa: E402
import near_floor_tiers as NF  # noqa: E402
import strats as S  # noqa: E402

FOMC = set(pd.to_datetime(pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "fomc_dates.csv")).date).dt.date)


def pf(u):
    return u[u > 0].sum() / max(1e-9, -u[u < 0].sum())


def legs_for(band_fomc):
    def strat(days, i, tick, **_):
        b = {**B.BAND, **band_fomc} if days[i]["d"] in FOMC else B.BAND
        return S.merge(S.gap_go(days, i, tick, **B.GAP) + S.noise(days, i, tick, **b))
    return strat


def tables(d, s, band_fomc=None, skip=False):
    if band_fomc is None:
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        st = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, "min_stretch": 1.5})))
    else:
        t = H.trades_of(legs_for(band_fomc), d, s)
        st = H.trades_of(legs_for({**band_fomc, "min_stretch": 1.5}), d, s)
        # the strong-only table: min_stretch on every day, the FOMC change on FOMC days only
        st = st[st.d.isin(FOMC)]
        base_st = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, "min_stretch": 1.5})))
        st = pd.concat([base_st[~base_st.d.isin(FOMC)], st]).sort_values(["d", "bar"], kind="stable")
    if skip:
        t, st = t[~t.d.isin(FOMC)], st[~st.d.isin(FOMC)]
    t = t.reset_index(drop=True)
    t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
    return t, st.reset_index(drop=True)


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("unseen_es", "ES 2020-24"), ("live", "live 2026")):
        d, s = sets[n]
        t, st = tables(d, s)
        f = t.d.isin(FOMC)
        nf = sum(x["d"] in FOMC for x in d)
        late = t.bar >= (840 - 570) // 5  # entries from 14:00
        print(f"{lab}: {nf} FOMC days of {len(d)}")
        for nm, m in (("FOMC days", f), ("other days", ~f), ("FOMC days, entries before 14:00", f & ~late),
                      ("FOMC days, the 14:00 entry", f & late), ("other days, the 14:00 entry", ~f & late)):
            u = t[m].usd
            if len(u):
                print(f"  {nm}: {len(u)} trades, PF {pf(u):.2f}, ${u.mean():+.1f} a trade, ${u.sum():+,.0f}, "
                      f"worst ${u.min():,.0f}")
        if n in ("dev", "unseen_nq"):
            yr = pd.to_datetime(t.d).dt.year
            print("  FOMC days by year, $ (trades): " + ", ".join(
                f"{y} {t[f & (yr == y)].usd.sum():+,.0f} ({int((f & (yr == y)).sum())})" for y in sorted(set(yr))))
            rows = (("shipped", {}), ("no trading on FOMC days", dict(skip=True)),
                    ("FOMC days: last entry 13:00, out by 13:55", dict(band_fomc=dict(last=780, exit_at=835))),
                    ("FOMC days: last entry 13:00", dict(band_fomc=dict(last=780))))
            for nm, kw in rows:
                tt, ss = tables(d, s, **kw)
                cal = []
                for start in NF.STARTS:
                    r = BR.runs(tt, d, B.STEPS, 600.0, B._news(d), strong=ss, guard=1500.0, strong_below=1000.0,
                                start=start)
                    cal.append(f"${start:,.0f} {r.lost.mean():.1%} / ${r.profit.median():,.0f}")
                sh = NF.shuffled(tt, ss, d)
                shs = " ".join(f"${k:,.0f} {v[0]:.1%} / ${v[1]:,.0f}" for k, v in sh.items())
                print(f"  {nm}: {len(tt)} trades, ${tt.usd.sum():+,.0f} a contract\n     calendar: {' | '.join(cal)}"
                      f"\n     shuffled years: {shs}", flush=True)
        print(flush=True)


if __name__ == "__main__":
    main()
