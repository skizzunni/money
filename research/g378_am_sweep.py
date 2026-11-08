"""G378 (docs/NINJATRADER_V38.md): the user's video (TikTok, MNQ 1-minute, Oct 28): the morning range swept, then
reclaimed. research/patterns.py `amsweep` / `amsweep_cisd`: the 09:30-10:00 range; after 10:00, once price trades below
its low (above its high), the first 5-minute close back inside (with `_cisd` also past the previous bar's high / low)
buys (sells) at the next open; stop a tick past the sweep's extreme; target the range's other side or an R multiple.
patterns.py's execution: $500 risk (1-10 MNQ), a tick of slippage, $0.62 a side, one trade at a time, flat at 16:00.

    python research/g378_am_sweep.py <data dir> <MNQ_09-26> <MNQ_12-26>
"""
import itertools
import sys

import pandas as pd
import patterns as P


def main() -> None:
    P.init(*sys.argv[1:4])
    rows = []
    for setup in ("amsweep", "amsweep_cisd"):
        prepared = {name: (P.prepare(bars, setup), first) for name, (bars, first) in P.D.items()}
        for morning, (r, pat) in itertools.product((True, False), ((1.0, True), (1.0, False), (2.0, False))):
            for name, (days, first) in prepared.items():
                f = P.execute(days, False, False, morning, r, pat)
                rows.append({"setup": setup, "morning": morning, "target": "range" if pat else f"{r}R", "set": name,
                             **P.stats(f, first)})
    d = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(d.to_string(index=False))


if __name__ == "__main__":
    main()
