"""Research (2026-11-25, docs section 120): the band trades' losses by the entry's stretch past the band, per period.

Analysis only. The stretch (strats.band_stretch, as MnqCleanBand sizes the extra contract: sigmas past the band at
the signal close) in buckets; per bucket the trades, win rate, $ a trade a contract, the losers' average and the share
of trades out at the full hard stop (a loss of at least $190 a contract with costs).
Run from research/: python zoo/stretch_losses.py
"""
import pickle
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import harness as H  # noqa: E402
import strats as S  # noqa: E402


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25"), ("unseen_es", "ES 2020-24")):
        d, s = sets[n]
        t = H.trades_of(S.everyday, d, s, legs=(("gap_go", B.GAP), ("noise", B.BAND)))
        t["st"] = B._stretch(d, t, 1.0)
        b = t[t.bar > 1].copy()
        b["bk"] = pd.cut(b.st, [-9, 0.25, 0.5, 1.0, 1.5, 2.5, 99])
        g = b.groupby("bk", observed=True)
        out = pd.DataFrame({"trades": g.size(), "win": g.usd.apply(lambda u: np.mean(u > 0)).round(2),
                            "$ a trade": g.usd.mean().round(1),
                            "losers' avg": g.usd.apply(lambda u: u[u < 0].mean()).round(1),
                            "at the hard stop": g.usd.apply(lambda u: np.mean(u <= -190)).round(3)})
        print(f"{lab} (band trades, sigmas past the band at the signal close):\n{out.to_string()}\n", flush=True)


if __name__ == "__main__":
    main()
