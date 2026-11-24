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
| **1, 2 from +$2,000, 3 from +$4,500** | **$600** | **0%** | **$6,426** (break-even 0.5), **$6,652** (0.4, shipped) |

6. **NinjaTrader-exact rules and parity**: the reference was switched to what NinjaTrader executes (the hard stop from
   the expected fill, set with the entry; a moved stop at or past the price exits at market; the 15:55 exit at the next
   open; stops on the tick grid, only ever tightened). `ninjatrader/Strategies/MnqCleanBand.cs`;
   `tests/test_ninjatrader_clean.py` holds it to the Python reference trade for trade (entry bar, entry and exit price,
   contracts) on seeded synthetic sessions and, with `ZOO_DATA`, on the user's live months.

7. **Is it a knife edge?** (`verification/zoo/robustness_neighbours.txt`, `robustness_safe_region.txt`) Every setting
   moved one step: the profit holds everywhere (ES PF 1.07-1.21, live 3.6-4.9), but survival does not on one side: a
   wider hard stop ($225-250), a later break-even (0.6-0.75) or entries to 14:30 bring back 5-11% lost starts. At the
   $200 hard stop every break-even 0.3-0.5 with the last entry at 13:30 or 14:00 loses none, so the shipped
   break-even is **0.4**, the middle of that safe region (its neighbours: 0-4.8% lost; around 0.5: up to 9.6%).
   Read: the survival comes from keeping each trade's risk small, not from a lucky fit, and the risk settings should
   not be loosened.

8. **More money without more risk** (`verification/zoo/stage4_target_and_gap_leg.txt`): a take-profit at 2.5 hard
   stops lifts the win rate (24% to 28%) and the weak starts (25th percentile $2,090 to $3,454); the gap-and-go leg
   (09:35 to 09:55, stop at the 09:30 open, at most 50 points) switched on only once the account is $4,500 up (the floor
   has stopped trailing by then) lifts the median to $8,772. **Every neighbour** (target 2.0-3.0, gap from $4,000-6,000,
   break-even 0.3-0.5, hard stop $175-225) also loses no start: the target makes the risk settings less fragile, not
   more. Caveat: gap and go loses on ES (PF 0.69, 70 trades) while it holds on NQ dev / unseen (1.95 / 1.76) and the live
   MNQ months (2.34); it is one switch ("Gap trade") and never runs before the cushion. The gap trade exits at 09:55
   (not 10:00) so it is never closing on the bar the band's 10:00 entry fills.

9. **More trading days, and the VWAP entry filter** (2026-11-24, the user: "trade every day";
   `verification/zoo/stage5_more_days.txt`, `stage5_no_vwap_entry.txt`). Trading more days costs accounts: without the
   trend filter (61% of days traded) 9.6% of starts are lost, with a lower entry line too (69%) 38%. Without the VWAP
   entry filter (the same days) none is lost and the median rises $8,769 to $9,913 (25th percentile $3,235 to $3,638),
   every neighbour safe but trend 15 (1%); live Jun 29 - Nov 23 at 1 MNQ $5,678 against $6,036. Shipped: the filter off
   (`VwapEntry` false). **A bug the parity test caught first:** without the filter a long can enter below VWAP and the
   VWAP-tightened stop then sat above the fill; the reference booked those as wins at the stop (an earlier run showed
   a $10,649 median, wrong). Now, when VWAP is on the wrong side of the expected fill, the stop at entry is the band
   alone, in all three (Python, NinjaTrader, Pine), and a stop the fill has already passed fills at the open.
   Trades: on about 30% of sessions (31 of 104 live), 2.7 a traded day on average, at most 8.

## The result (the shipped defaults, research numbers, 2 ticks of stop slippage, $0.62 a side)

| set | band trades | win | PF | band net (1 MNQ) | gap trades (PF, net) | 50K starts lost | median 12 months |
|---|---|---|---|---|---|---|---|
| dev NQ 2015-19 | 1,004 | 21% | 1.44 | $17,649 | 224 (1.95, $6,799) | 0 of 49 | $4,211 |
| unseen NQ 2020-25 | 1,216 | 22% | 1.45 | $26,340 | 270 (1.76, $8,713) | 0 of 55 | $10,838 |
| unseen ES 2020-24 | 325 | 22% | 1.17 | $994 | 70 (0.69, -$379) | | |
| live MNQ Jun 29 - Nov 20 2026 | 65 | 28% | 3.34 | $4,935 | 16 (2.34, $1,101) | | |

(The accounts' numbers use the gap leg only from +$4,500 and the contract steps; the trade columns are 1 contract, every
gap trade. ES's band uses the MNQ $ stop in points, a cross-check only.)

Pooled 104 starts: **none lost**, median **+$8,772**, 25th percentile +$3,235, 10th +$1,441, worst -$20 (never near
the floor), 43% reach +$10,000 and 12.5% +$15,000 in 12 months, none +$25,000; green on 38% of traded days. Live band by
month (1 MNQ): Jul -$138, Aug +$745, Sep +$824, Oct +$2,086, Nov (to the 20th) +$1,418; Nov 13 +$236, Nov 16 -$102,
Nov 17 -$297, Nov 19 -$2, Nov 20 +$1,295 (the 2.5x target took the trend day's first leg).

By year, 1 contract (band / gap leg): 2015 $2,869 / $1,158, 2016 $3,709 / $2,802, 2017 $1,098 / $895, 2018 $6,486 /
$64, 2019 $3,486 / $1,880, 2020 $3,352 / $1,505, 2021 $6,702 / $1,104, 2022 $6,670 / $3,844, 2023 $5,160 / $449, 2024
$4,370 / $1,521, 2025 H1 $85 / $290, 2026 Jun 29 - Nov 20 $4,935 / $1,101: every year up for both. (No data here for
Jul 2025 - Jun 2026.)

**How sure is "none lost"?** (`verification/zoo/walkforward_dev_only.txt`) The protections were picked on dev and
unseen NQ together, so the 0 of 104 is partly in-sample. A walk-forward that picks on 2015-19 only: of the 294 settings
in the stage-4 grid that lose no 2015-19 start, the average loses 5.7% of the 2020-25 starts and 47% lose none; picking
by the safest dev neighbourhood does no better (5.3%). The 2015-19 data cannot see the 2020 regime coming. What the
grid does show is where the losses come from: the $250 hard stop, the late break-even (0.75) and entries to 14:30;
every setting at $200 or less with break-even at 0.3-0.5 and a target of 2-3 hard stops loses none on either. Expect a
small chance (a few percent) of losing a fresh account in a year like 2020, almost all of it in its first months, before
the $2,000 cushion that brings the second contract; never loosen the risk settings.

**Fewer trades while the account is new does not help** (`verification/zoo/early_trade_limit.txt`): at most 1-3
trades a day until +$1,000 / +$2,000, on the shipped setting and on the walk-forward's riskier picks, loses as many or
more starts (the shipped one: up to 20%) and halves the median. The cushion comes from the trend-day winners; cutting
trades delays it. Not used.

**What it is not:** a high win-rate strategy. About 1 trade in 4 wins and about 3 traded days in 8 are green; the
winners (the 2.5x target or the 15:55 close on trend days) are 4-6x the losers, which the band and break-even keep small. It trades on about a third of the sessions. With the user's
3-contract cap the edge supports roughly $4-11K a year on a 50K (median $8.8K), not $25K; starting at 3 contracts
loses about half of fresh accounts.

## TradingView

`pine/mnq_clean_band.pine` is the same strategy for a TradingView MNQ 5-minute chart (add it, Strategy Tester for the
results). `tests/test_pine_clean.py` holds it to the same Python reference trade for trade on the Pine interpreter, with
one difference by design: Pine sets the take-profit from the fill price after the fill bar, so it works from the next
bar (NinjaTrader's bracket works from the fill bar).

## Running it

NinjaTrader 8, on each funded account:

1. **Disable MnqNoiseV38 (and any other strategy) on the account first.** Two strategies on one account fight over
   the position.
2. Copy `ninjatrader/Strategies/MnqCleanBand.cs` to Documents\NinjaTrader 8\bin\Custom\Strategies and compile (F5
   in the NinjaScript editor, or open and close the editor).
3. Open an **MNQ 5-minute** chart (the front month; CME US Index Futures ETH or RTH) with **Days to load: 40** or more
   (Data Series window). It needs 21 complete sessions to start.
4. Strategies tab, add **MnqCleanBand**, account = the funded account, keep the defaults, **Enabled**. The chart's
   top-right corner must say **Setup: OK**. The Output window prints the settings and every order.

Defaults: trend 20 sessions, hard stop $200 a contract, break-even at 0.4, take profit at 2.5 hard stops, last entry
14:00 (840), up to 9 trades a day, day stop $600, the gap trade from +$4,500, at most 3 contracts (2 from +$2,000, 3 from
+$4,500 over the $50,000 start balance; live it sizes from the account's net liquidation). An account below $50,000
trades 1 contract and no gap trade until it is back above.

Live safety (tests/test_ninjatrader_clean.py): a stop the broker cancels or rejects while the position is open closes it
at market ("No stop"); no entries while the chart's last 14 sessions span more than 23 days (a hole in the history, as
NinjaTrader's Oct 19 - Nov 6 2026 gap; the Output window says to reload the data); NinjaTrader's exit on session close
as a backstop (half days, e.g. Nov 27 2026, close at 13:15 before the 15:55 exit). The no-stop exit waits out the
race where a target's OCO cancel of the stop arrives before the position shows flat (closes at the bar's close, or live
2 s later, only if still open and no stop is back), so a target never closes twice. The chart shows Setup: OK / NOT READY
(too few sessions loaded) / NO TRADING (a hole), the size, the gap leg and today's P/L.
