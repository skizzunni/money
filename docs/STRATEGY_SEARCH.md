# The strategy search (2026-11-23) and MnqCleanBand

The user: "keep the strategy I gave you in mind ... not just that strategy but every single one ... find something that
works and commit it to an auto-trading NinjaTrader script". The step process, each step committed:

1. **One bench for everything** (`research/zoo/harness.py`). 5-minute regular-hours bars; sets: **dev** NQ 2015-2019,
   **unseen** NQ 2020 - mid 2025 and ES 2020-2024 (MES), **live** the user's MNQ Jun 29 - Nov 20 2026 (NinjaTrader export,
   the days it lacks from Yahoo with a bad-print filter). The account test: a fresh 50K started every month, 12 months,
   the $2,000 end-of-day trailing floor stopping at $50,000, lost when a trade or a day ends at or below it.
2. **Every intraday family** (`research/zoo/strats.py`, `run1.py`, `verification/zoo/stage1_all_families.csv`): the user's
   Clean Noise-Band spec, opening-range breakout (5-60 min), gap fade, gap and go, VWAP reversion, RSI(2) pullbacks,
   last-half-hour momentum (Gao et al.), prior-day high/low break and fade, EMA cross + VWAP, opening drive, Bollinger
   squeeze; 300+ variants at 1 contract. **Only the noise band (PF 1.45-1.61) and gap and go (1.7-2.1) hold on dev and
   unseen**; every other family is near PF 1.0-1.2 or fails unseen.
3. **What breaks the noise band**: at 1 MNQ every NQ start of Jan-Nov 2020 was lost (2020's chop, win rates 5-14% a
   month, a $3,920 drawdown into Feb 2021). Capping losers a day would not help (trades after 1-3 losers still pay).
4. **The fix** (`run2.py`, `verification/zoo/stage2_noise_gap_daystop.csv`, 972 combinations, picked on fewest lost
   then dev median): a $200 hard stop (not $250), the stop to break-even once up half of it, **no entries after the 14:00
   check**, a day stop. **0% of starts lost on dev and on unseen NQ**, PF 1.73 / 1.47, ES 1.18. The gap leg adds money but
   loses 1.8% of unseen starts: left out.
5. **Account protection and size** (`run3.py` and the sizing table below): an equity-curve filter and fewer trades
   while the cushion is small only cut profit. Sizing is what matters:

| contracts | day stop | 50K starts lost (104) | median 12 months |
|---|---|---|---|
| a fixed 3 from day one | none / $600 | 43-56% | -$165 to $7,445 |
| 2, then 3 from +$1,500 or +$3,000 | | 20-39% | |
| 1, 2 from +$1,000, 3 from +$2,500 | | 13-14% | $7,177-7,999 |
| **1, 2 from +$2,000, 3 from +$4,500** | **$600** | **0%** | **$6,426** |

6. **NinjaTrader-exact rules and parity**: the reference was switched to what NinjaTrader executes (the hard stop from
   the expected fill, set with the entry; a moved stop at or past the price exits at market; the 15:55 exit at the next
   open; stops on the tick grid, only ever tightened). `ninjatrader/Strategies/MnqCleanBand.cs`;
   `tests/test_ninjatrader_clean.py` holds it to the Python reference trade for trade (entry bar, entry and exit price,
   contracts) on seeded synthetic sessions and, with `ZOO_DATA`, on the user's live months.

## The result (the shipped defaults, research numbers, 2 ticks of stop slippage, $0.62 a side)

| set | trades | win | PF | net (1 MNQ) | 50K starts lost | median 12 months |
|---|---|---|---|---|---|---|
| dev NQ 2015-19 | 887 | 21% | 1.57 | $19,962 | 0 of 49 | $5,043 |
| unseen NQ 2020-25 | 1,023 | 23% | 1.52 | $25,297 | 0 of 55 | $7,659 |
| unseen ES 2020-24 | 325 | 22% | 1.17 | $994 | | |
| live MNQ Jun 29 - Nov 20 2026 | 49 | 27% | 4.29 | $4,873 | | |

Pooled 104 starts: none lost, median +$6,426, 25th percentile +$2,303, worst +-$400 (never near the floor), 31% reach
+$10,000 in 12 months, none +$25,000. Live by month (1 MNQ): Jul -$138, Aug +$747, Sep +$848, Oct +$1,374, Nov (to the
20th) +$2,043; Nov 13 +$243, Nov 16 -$102, Nov 17 -$297, Nov 19 -$2, Nov 20 +$1,835.

**What it is not:** a high win-rate strategy. About 1 trade in 4 wins and about 1 traded day in 3 is green; the
winners (held to 15:55 on trend days) are 4-6x the losers. It trades on about a third of the sessions. With the user's
3-contract cap the edge supports roughly $5-10K a year on a 50K, not $25K; starting at 3 contracts loses about half of
fresh accounts.

## Running it

NinjaTrader 8: copy `ninjatrader/Strategies/MnqCleanBand.cs` to Documents\NinjaTrader 8\bin\Custom\Strategies, compile
(F5 in the NinjaScript editor), add it to an **MNQ 5-minute** chart (CME US Index Futures ETH or RTH, at least 30 days
loaded), account = the funded account, Enabled. Defaults: trend 20 sessions, hard stop $200 a contract, break-even at
0.5, last entry 14:00 (840), up to 9 trades a day, day stop $600, at most 3 contracts (2 from +$2,000, 3 from +$4,500 over
the $50,000 start balance; live it sizes from the account's balance). The Output window prints the settings at start
and every entry.
