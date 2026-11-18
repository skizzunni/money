# v4: the 2026-11-17 search (Pine v4.0 and NinjaTrader's "Funded growth v4")

After the first live days (Nov 13: +$332 a account; Nov 17: −$389 / −$399), the user asked for a version that makes
more on the chart window they look at (Aug 21 – Nov 17, 2026), with winning trades, and a NinjaTrader fix.

## Data

- **W, the user's window:** MNQ 5-minute RTH bars, Aug 21 – Nov 17 2026: the repository's series
  (`tests/data/mnq_traded_eth_*`, to Oct 16) and Yahoo's MNQ=F after (Yahoo matches it bar for bar from Sep 16; one bad
  tick removed, Oct 30 15:00 opened at 29,562 between bars near 28,300). A 16:00 bar is added as the research does.
- **Unseen:** MNQ Jul 16 – Aug 20 2026 (never used to choose).
- **History:** NQ futures 2015–2025 (Hugging Face, the original file: exact) and the Nasdaq-100 index 2011 – Mar 2025
  (Hugging Face's HistData mirror: close to the original files, not identical; docs/DATA_REBUILD.md).
- Each run is one account with no trailing floor (the raw strategy), at 1 MNQ unless stated.

## Searches (all in `verification/v4_search/`, scripts in `research/v4_search/`)

1. 2,000 random variants of today's Funded growth (`s1_random_2000.jsonl`).
2. A grid of the 7 settings that helped on all three sets (`s2_grid_1080.jsonl`).
3. The best 290 of both, period by period (`s3_periods_290.jsonl`): NQ 2015-19 / 2020-23 / 2024-25, the index
   2011-18 / 2019-25, the unseen Jul-Aug, and W.
4. A grid around the one change that held up in every period, the later lock (`s4_lock_grid_161.jsonl`).

**What did not hold up:** the window's best variants (up to $4,826 at 1 MNQ) relax the trend filter, which suits
this autumn's downtrend; they made 13-45% less on history. Search 2's best (a 30-session noise average and a
90-session trend, $4,558 on W) made less than today in 2024-25 and lost on the unseen Jul-Aug.

**What held up: the lock later.** Today the stop moves to the entry + 2.5 points once a trade is up 0.35 max
losses: 1,236 of NQ's 3,868 trades end there at about +$3 each (+$4,029 in all), while the profit comes from the
trades that reach the take-profit or the 16:00 close. Locking at 1.25 max losses lets those run.

| 1 MNQ | W (Aug 21-Nov 17) | W drawdown | NQ 15-19 | NQ 20-23 | NQ 24-25 | IX 11-18 | IX 19-25 | Jul-Aug (unseen) |
|---|---|---|---|---|---|---|---|---|
| Funded growth today | $1,300 | $1,567 | $29,129 | $35,597 | $10,691 | $42,984 | $50,295 | $970 |
| **v4 (#29)** | **$2,684** | **$1,300** | $29,792 | **$52,043** | **$11,150** | $41,408 | **$57,776** | $735 |

v4 = Funded growth with the lock at 1.25 max losses, the stop 0.5 noise units past the line (0.24), entry lines at
0.9 noise (1.0) and $250 a trade (187.50); the rest unchanged. Its neighbours (lock 1.25-1.5, entry 0.8-0.9) score
about the same. Trades that win: 32% (50% today); green days the same (32%). It is worse on the unseen five weeks
($735 against $970, 12 against 28 trades): small, but not better there.

## Pine v4.0 (`pine/mnq_noise_v4.pine`): the chart version, trading indefinitely

The Pine script has no gap trade, fill-ins or giveback brake (NinjaTrader's Funded growth has), so v4.0 is v3.8's
engine with v4's exits: the lock at 1.25, the stop 0.5 out, a 45-minute time stop, the trend over 45 sessions, **5 MNQ
at $250 each, no daily cap, no trailing drawdown, no evaluation stop.** The script itself, run by the repository's Pine
interpreter on W: **+$11,369, 46 trades, 39% winners, 42% green days, worst day −$1,259, worst drawdown −$2,512**
(v3.8's Pine on the same bars: +$2,181). Per contract on history it made $65,651 (NQ, 11/11 years up) and $76,278
(index, 14/15). `tests/test_pine_v4.py`: the script's defaults match the Python model trade for trade on the user's
MNQ bars.

**Its size is not for the Take Profit Trader 50K:** at 5 MNQ the window fell $2,512 from a high, past the $2,000
trailing drawdown. At 1 MNQ the same rules made $2,274 (drawdown $502).

## NinjaTrader: Mode "Funded growth v4" (opt-in)

`Funded growth v4` runs Funded growth (U58, G511's fill-ins, 1 MNQ growing with profit, the $2,000 floor) with v4's
four settings. NinjaTrader's code and the model agree trade for trade (`test_v38_opt_in_modes`). On W with the account
rules on: +$2,209 (today's Funded growth +$495), lowest point $467 under the start, drawdown $1,799 (close to the
floor). Not yet measured on G495's +$25,000 starts (needs the index's 2025-26 data). Funded growth stays the default.
