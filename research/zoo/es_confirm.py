"""Research (2026-11-26, docs section 187): NQ band entries confirmed by ES. At each NQ band entry (2020-24, where
NQ and ES overlap), where was ES at the same signal bar against its own band (S.band_stretch on the ES day, the same
side and bar; > 0: past its band the same way, as NQ is)? NQ trades with ES past its band / inside it, by half
(2020-22, 2023-24) and by year; then no NQ band entry without ES past its band, on the account with the guard
(shuffled years) against a placebo of as many random band trades removed. Live it would need an ES data series.
Run from research/: python zoo/es_confirm.py [--size]   (--size: one more contract on the NQ-alone entries)
"""
import pickle
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import fomc_days as F  # noqa: E402
import near_floor_tiers as NF  # noqa: E402
import strats as S  # noqa: E402


def main():
    sets = pickle.load(open(B.PK, "rb"))
    d, s = sets["unseen_nq"]
    es = sets["unseen_es"][0]
    ei = {x["d"]: i for i, x in enumerate(es)}
    ni = {x["d"]: i for i, x in enumerate(d)}
    d = [x for x in d if x["d"] <= es[-1]["d"]]
    t, st = F.tables(d, s, skip=True)  # FOMC days skipped, as shipped (docs 180)
    st_es = []
    for r in t.itertuples():
        j = ei.get(r.d)
        if r.bar <= 1 or j is None or j < 21 or len(es[j]["mm"]) != len(d[ni[r.d]]["mm"]):
            st_es.append(np.nan)
        else:
            st_es.append(S.band_stretch(es, j, r.side, r.bar, B.BAND["k"], B.BAND.get("sig_min", 0)))
    t["es"] = st_es
    band = t.bar > 1
    t["y"] = pd.to_datetime(t.d).dt.year
    for lab, ys in (("2020-22", (2020, 2021, 2022)), ("2023-24", (2023, 2024)), ("2020-24", tuple(range(2020, 2025)))):
        p = t[band & t.y.isin(ys)]
        for nm, m in (("ES past its band too", p.es > 0), ("ES inside its band", p.es <= 0), ("ES n/a", p.es.isna())):
            u = p[m].usd
            if len(u):
                print(f"{lab} NQ band, {nm}: {len(u)} trades, PF {F.pf(u):.2f}, ${u.mean():+.1f} a trade, "
                      f"${u.sum():+,.0f}")
    print("by year, $ a trade ES past / inside (n): " + ", ".join(
        f"{y} {g[g.es > 0].usd.mean():+.1f} ({(g.es > 0).sum()}) / {g[g.es <= 0].usd.mean():+.1f} ({(g.es <= 0).sum()})"
        for y, g in t[band].groupby("y")))
    cut = band & (t.es <= 0)
    print(f"no NQ band entry with ES inside its band: {int(cut.sum())} of {int(band.sum())} band trades removed")
    keep = ~cut.to_numpy()
    st_keep = st.merge(t[cut][["d", "bar"]].assign(x=1), on=["d", "bar"], how="left").x.isna().to_numpy()
    d_all = d
    sh = NF.shuffled(t[keep].reset_index(drop=True), st[st_keep].reset_index(drop=True), d_all)
    base = NF.shuffled(t, st, d_all)
    print("  shuffled shipped (FOMC skip): "
          + " ".join(f"${k:,.0f} {v[0]:.1%} / ${v[1]:,.0f}" for k, v in base.items()))
    print("  shuffled ES-confirmed only:   " + " ".join(f"${k:,.0f} {v[0]:.1%} / ${v[1]:,.0f}" for k, v in sh.items()))
    rng = np.random.default_rng(3)
    bi = np.flatnonzero(band.to_numpy())
    for k in range(3):
        drop = np.zeros(len(t), bool)
        drop[rng.choice(bi, int(cut.sum()), replace=False)] = True
        sdrop = st.merge(t[drop][["d", "bar"]].assign(x=1), on=["d", "bar"], how="left").x.isna().to_numpy()
        r = NF.shuffled(t[~drop].reset_index(drop=True), st[sdrop].reset_index(drop=True), d_all)
        print(f"  placebo {k + 1} (as many random band trades removed): "
              + " ".join(f"${a:,.0f} {v[0]:.1%} / ${v[1]:,.0f}" for a, v in r.items()), flush=True)


if __name__ == "__main__" and "--size" not in sys.argv:
    main()


def size_up():
    """docs 187: one more contract (the extra slot, at most 3) on NQ band entries with ES inside its band (NQ alone)."""
    sets = pickle.load(open(B.PK, "rb"))
    d, s = sets["unseen_nq"]
    es = sets["unseen_es"][0]
    ei = {x["d"]: i for i, x in enumerate(es)}
    ni = {x["d"]: i for i, x in enumerate(d)}
    d = [x for x in d if es[0]["d"] <= x["d"] <= es[-1]["d"]]
    t, st = F.tables(d, s, skip=True)
    ev = []
    for r in t.itertuples():
        j = ei.get(r.d)
        di = [x["d"] for x in d].index(r.d)
        ok = r.bar > 1 and j is not None and j >= 21 and len(es[j]["mm"]) == len(d[di]["mm"])
        ev.append(S.band_stretch(es, j, r.side, r.bar, B.BAND["k"], B.BAND.get("sig_min", 0)) if ok else np.nan)
    t["es"] = ev
    del ni
    base = t["add"].to_numpy().copy()
    alone = (t.bar > 1).to_numpy() & (t.es <= 0).to_numpy()
    print(f"{d[0]['d']} - {d[-1]['d']}: {len(d)} sessions, {int(alone.sum())} NQ-alone band entries of "
          f"{int((t.bar > 1).sum())}")
    for nm, sel in (("shipped", None), ("one more on NQ-alone entries", alone)):
        t["add"] = np.where(sel, 1, base) if sel is not None else base
        r = NF.shuffled(t, st, d)
        print(f"  {nm}: " + " ".join(f"${k:,.0f} {v[0]:.1%} / ${v[1]:,.0f}" for k, v in r.items()), flush=True)
    rng = np.random.default_rng(9)
    band = (t.bar > 1).to_numpy()
    rate = alone.sum() / band.sum()
    for k in range(5):
        m = band & (rng.random(len(t)) < rate)
        t["add"] = np.where(m, 1, base)
        r = NF.shuffled(t, st, d)
        print(f"  placebo {k + 1}: " + " ".join(f"${a:,.0f} {v[0]:.1%} / ${v[1]:,.0f}" for a, v in r.items()),
              flush=True)


if __name__ == "__main__" and "--size" in sys.argv:
    size_up()
