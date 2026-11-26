"""Research (2026-11-26, docs section 188): a smaller hard stop for late band entries (less time left to work; the
break-even, the target and the stop step stay on the $200 unit). late_hard $100 / $150 for entries after 11:30 /
12:30, FOMC days skipped as shipped; by period (trades, PF, $ a contract) and on the account with the guard (shuffled
years and the calendar starts). Run from research/: python zoo/late_hard.py
"""
import pickle
import sys
import warnings

import pandas as pd

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import fomc_days as F  # noqa: E402
import harness as H  # noqa: E402
import ism_days as I  # noqa: E402
import strats as S  # noqa: E402


def tables(d, s, **kw):
    t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, **kw})))
    st = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", {**B.BAND, **kw, "min_stretch": 1.5})))
    t, st = t[~t.d.isin(F.FOMC)].reset_index(drop=True), st[~st.d.isin(F.FOMC)].reset_index(drop=True)
    t["add"] = (B._stretch(d, t, 1.0) >= 1.5).astype(int)
    return t, st


def main():
    sets = pickle.load(open(B.PK, "rb"))
    rows = [("shipped ($200 always)", {})]
    rows += [(f"${h} after {a // 60}:{a % 60:02d}", dict(late_hard_at=a, late_hard=float(h)))
             for a in (690, 750) for h in (100, 150)]
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("unseen_es", "ES 2020-24"), ("live", "live 2026")):
        d, s = sets[n]
        print(lab, flush=True)
        for nm, kw in rows:
            t, st = tables(d, s, **kw)
            b = t[t.bar > 1]
            yr = b.groupby(pd.to_datetime(b.d).dt.year).usd.sum()
            print(f"  {nm}: band {len(b)} trades, PF {F.pf(b.usd):.2f}, ${b.usd.sum():+,.0f}; by year "
                  + " ".join(f"{y}:{v:+,.0f}" for y, v in yr.items()), flush=True)
            if n in ("dev", "unseen_nq"):
                I.acct(nm, t, st, d)


if __name__ == "__main__":
    main()
