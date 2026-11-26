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
   (09:35 to 09:55, stop at the 09:30 open, at most 50 points; 30 now, section 29) switched on only once the account is $4,500 up (the floor
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

10. **The MambaFx "2 minute strategy"** (the user's video, 2026-11-24; `research/zoo/sr_break.py`, `twomin.py`,
   `run_sr.py`, `verification/zoo/mambafx_2min_grid.csv`). His rules from the transcript: the 2-minute chart, NASDAQ /
   US30, support and resistance from levels touched several times, enter when a 2-minute candle breaks one, the stop
   just past it, 1:4 (or break-even at 1:2 and trail from 1:4), stop after 2-3 losses a day, risking 2-5% a trade. Made
   mechanical (levels: swing highs / lows of the prior session and today with 2-3 touches within 0.03-0.06%), 320
   variants on 2-minute NQ 2015-25, ES and the live MNQ: it trades 80-100% of days but **no variant makes money on both
   dev and unseen NQ** (best dev PF 1.04, its unseen 0.85, ES 0.73, live 0.75), 41-100% of 50K starts lost; with the
   20-session trend filter 0 of 32 either. His risk (2-5% of the account a trade) would end a 50K with a $2,000 floor in
   one or two losers. Not used.

11. **"The old one made $20K, this one $2K"** (2026-11-24, the user's TradingView Strategy Tester: +$2,212, 25 trades,
   PF 3.61). Both Pine scripts on the same MNQ bars (Jun 29 - Nov 23 2026, the Pine interpreter): the old v4.3 at its
   default **8 MNQ** $22,445 (max drawdown $3,859, worst day -$3,630); at 3 MNQ $8,417. The new one: fixed 3 MNQ
   $16,622 (drawdown $1,522, worst day -$868), fixed 8 $22,298, its default steps (1 MNQ until +$2,000) $8,765. The gap
   is the contract count, not the rules. From a fresh 50K (the bench, 104 starts): the steps lose none (median $9,913);
   2 then 3 from +$2,000 lose 28.8%; a fixed 3 39-41% (median $11-13K); a fixed 8 63.5%. New setting "Fixed
   contracts" (NinjaTrader `FixedContracts`, Pine input; 0 = the steps). An account already up trades 3 by the steps
   once it is +$4,500 (sized from its balance live).

12. **More trades from the same signal: checks every 15 / 10 / 5 minutes** (`verification/zoo/stage6_check_every.txt`,
   `noise(step=...)`). More trades a traded day (2.4 to 3.0 / 3.4 / 4.1 on unseen NQ) but a lower profit factor
   (1.48 to 1.33 / 1.26 / 1.18; ES 1.17 to 1.04 / 0.99 / 0.82) and lost starts (0% to 13.5% / 15.4% / 26.9%). The
   half-hour checks stay. Trades a day (shipped): NQ 2015-25 about 1.0-1.1 a session, on 45% of sessions, 2.3-2.4 a
   traded day; live Jun 29 - Nov 23 2026 0.82 a session: none on 73 of 104 days, 1 on 12, 2 on 3, 3 on 7, 4 on 5,
   5-8 on 4.

13. **A trade for the no-signal days: fading stretches inside the noise area** (2026-11-24, the user: "majority days no
   trade is unacceptable"; `band_fade`, `verification/zoo/stage7_inside_band_fade.txt`). Inside the band (the market's
   own noise), a close k standard deviations from VWAP fades back to VWAP, the stop at the band edge: 48 variants (k 1.5 /
   2 / 2.5, to 12:00 or 15:00, 1 or 3 trades, VWAP or half way, with or without stopping after a breakout). It trades
   10-62% of days, but **0 of 48 make money on both dev and unseen NQ**; the dev-best lose $3,654-21,238 on unseen NQ
   and lose on ES (PF 0.29-0.73); the live months are positive for some (PF up to 1.68, 35-42 days), too few to trust
   against 10 years. Not used. The no-trade days are the strategy declining trades with no edge.

14. **News: fading the 08:30 move at the cash open** (2026-11-24, the user: "it's all about signals and news";
   `research/zoo/news.py`, `news_mom`, `verification/zoo/stage8_news_fade_*`). News days are read from the market (the
   08:30-08:34 volume against 08:20-08:29: first Fridays 8x, Mondays 1.2x), not a calendar. On those days, entering at
   09:30 against the move from 08:29 to 09:29 (a hard stop, out by 09:55-12:00) is **the first new edge that survives a
   dev-only pick**: of the 124 settings robust on 2015-19 (worst one-step neighbour PF > 1.1), 82% also make money on
   2020-25 NQ and on ES; momentum (with the move) does not; the same fade on every day does not. It is small: about
   20-40 trades a year, +$400-2,800 a contract in most years (2019, 2020 slightly down), and the live months are slightly
   negative (5-17 trades, from 5-minute Yahoo pre-open bars). Added to the shipped strategy in place of the gap trade on
   news days (out at 09:55, before the 10:00 entries): from +$4,500 it trades 8% more days with the same median ($9,942
   against $9,913) and no lost start; from the start the 25th percentile rises ($3,638 to $5,280) but 2.9% of starts are
   lost. Recorded, not shipped: it does not move the account.

15. **News days size the band's trades** (2026-11-24; `verification/zoo/stage9_news_size*.txt`). The shipped band's
   trades by the day's 08:30 volume spike: big news (> 6x) PF 3.35 dev / 1.94 unseen NQ ($71 / $34 a trade), quiet days
   1.44 / 1.52, mild news (2-3x) 0.72 / 0.94 (ES weaker: 1.09 / 1.16 / 1.02). Visible in dev alone, held on unseen.
   Rule: a mild-news day has no trades; a big-news day trades a contract more (never past 3). 104 starts: **none
   lost, median $9,913 to $12,418, 25th percentile $3,638 to $6,878**; all 36 neighbours (big at 5-8x, skip from 1.8-2.2x
   to 2.8-3.5x) lose 0-1%, median $9,644-12,962, 25th percentile $4,880-7,133. Against it: the live months (only 52 days
   with pre-open bars, no big-news band trade among them, 9 mild-news trades that made +$617) give $3,961 at 1 MNQ
   against $4,577 without the rule. Shipped on (NinjaTrader `NewsDays`, Pine "News days"; it needs an ETH / extended
   hours chart for the 08:30 bar, else it stays off), with the live caveat stated. Tests: trade for trade with pre-open
   bars in NinjaTrader and Pine.

16. **TJR's New York-morning liquidity sweep** (2026-11-24; the user's video "How To Start Day Trading In 2026 [Full
   Tutorial] | TJR", which YouTube does not serve to this machine, so his widely taught model rather than the video's
   words; `research/zoo/overnight.py`, `tjr_sweep`, `verification/zoo/stage10_tjr_sweep_grid.csv`). Liquidity: the prior
   session's and the overnight high / low; 09:30-11:00 a sweep past one, a break of structure back through the last 3-6
   bars within 6-12 bars, entry at market or at the fair value gap the break left, the stop past the sweep, 2-3R or the
   opposite level. Sweeps happen on 96% of days by 11:00. At market (trades on about 38% of days) PF about 1.0; 192
   variants with stop caps of 80 / 150 points: 35 above 1 on dev and unseen NQ, **none on ES as well**, and those 35
   are the gap entries that trade on 1-2% of days (10-30 trades). No edge as rules; not used. (G14 had rejected the
   evening-session sweep with an inversion gap the same way.)

17. **TJR's strategy as his 2026 tutorial states it** (the user's transcript of the 6.7-hour video; `tjr` in
   `research/zoo/strats.py`, session levels in `overnight.py`, `verification/zoo/stage11_tjr_as_taught.csv`). His
   steps: draws on liquidity (Asia 18:00-03:00 and London 03:00-08:30 session highs / lows, the prior day's), a sweep,
   a 5-minute candle CLOSE through the most recent swing (his "up candle then down candle" high), a retrace to
   equilibrium (50% of the most recent swing) or a fair value gap, a 5-minute candle closing back the trade's way
   (his simpler entry), the stop above the retrace, targets at the next draws on liquidity; manipulation 09:30-09:50,
   entry 09:50-10:10, done by 10:30, one trade. As stated: trades on 6% of days, PF 1.54 dev, 0.82 unseen NQ, 0.82 ES,
   0.57 live. 432 variants (levels, equilibrium or gap, stop at the retrace or the sweep, the first / second draw or
   2R / 3R, done by 10:30 / 11:00 / 12:00, 6-24 bars to break structure): 71 make money on dev and unseen NQ, 25 also
   on ES, **none also on the live MNQ months**; those 71 trade on 4-9% of days (about 20 trades a year) for +$250 to
   +$2,000 a contract over 5.5 years. His discretion (the 1-minute refinement, the daily bias read, SMT with ES) is
   not in rules here; as rules, no usable edge. Not used.

18. **How the shipped strategy's trades end** (2026-11-24, the user: "trade more but try not to make losing ones";
   `verification/zoo/stage12_how_trades_end.txt`). About 170-230 trades a year (0.8-1.1 a session, on 30-45% of days,
   2.4-2.7 a traded day). At 1 MNQ on unseen NQ: 29% scratches (within $10, the break-even stop), 30% small losses
   (under $100), 20% losses of $100 or more, 22% winners (13% over $250, the 2.5x targets and trend days). Red days
   average -$122, green days +$332 (live: 45% red, -$124 against +$485). An earlier break-even (0.3 / 0.2 / 0.15 of the
   hard stop) turns some full losses into scratches (full losses 19% to 16%) but lowers the median ($12,418 to
   $9,342-10,205), and entries to 14:30 lose 3.8-4.8% of starts: the shipped 0.4 and 14:00 stay.

19. **More trading days** (2026-11-24, the user: "I cannot do 73 days of no trade"; `verification/zoo/stage13_*`).
   Trading every day costs accounts: adding the 15-minute opening-range breakout (the best every-day family, PF
   1.13-1.17) to the band, gap and news fade trades 99-100% of days but 70-78% of them red and loses 35-46% of 50K
   starts. With the news-day rule on, the gap trade from day one does not: gap at least 0.5x the 14-session average,
   its stop at most 30 points (it was 1x and 50 points, from +$4,500): **0 of 104 starts lost, median $13,711 (from
   $12,418), 25th percentile $7,471 (from $6,878), days traded 45% on unseen NQ (from 35-40%), 36% live**; every gap
   size tried with the 30-point stop (0.3 / 0.5 / 1x) loses none, the 50-point stop with smaller gaps 1.9-2.9%.
   Shipped: `GapFrom` 0 (= always), `GapK` 0.5, `GapCap` 30; NinjaTrader and Pine trade for trade (20 tests).

20. **Why Nov 9-19 went down, and the day's-range rule** (2026-11-24, the user's TradingView chart;
   `verification/zoo/stage14_day_range_rule.txt`). Trade by trade: on Nov 13 the 10:00 short hit its target after a
   550-point fall, then the band re-shorted at every check while price was bouncing 100-250 points off the day's low (7
   shorts, -$383 at 1 MNQ); Nov 17 the same (the 11:00 short 266 points off the low, then 3 more losers); Nov 20's
   winners entered 38-126 points off the low, pressing it. Rule: an entry needs its close within the last 35% of the
   day's range so far toward its side (long: at least 65% up the range; `range_pos` 0.65). 104 starts: none lost,
   median $13,711 to $14,315, 25th percentile $7,471 to $8,244; band PF dev 1.41 to 1.47, unseen NQ 1.48 to 1.49, ES
   1.17 to 1.22, live 2.85 to 3.88; live Nov 9-19 +$164 to +$580 at 1 MNQ. Every setting from 50% to 20% loses none.
   Shipped (`RangePos` 0.65, NinjaTrader and Pine trade for trade).

21. **Letting winners run** (2026-11-24, the user: "profitable trades should go up higher";
   `noise(tp_frac, runner_lock)`, `verification/zoo/stage15_runners.txt`). Part off at the 2.5x target, the rest on the
   band / break-even stop (or a lock): the best trade doubles or triples ($499 to $1,125-1,794 at 1 MNQ) and the PF
   rises (dev 1.47 to 1.53-1.61), but the median does not (half off: $13,533; a third off: $13,584; no target: $10,744
   against $14,315), live per year falls ($12,913 to $10,462-12,708), and 1-3.8% of starts are lost: after the target
   the move more often turns back than runs. All off at the target stays. Growth comes from the contract steps (1 / 2 /
   3 as profit builds), capped at the user's 3.

22. **No chasing a day that has already run** (2026-11-24; `verification/zoo/stage16_day_move_cap.txt`). The band's
   trades by how far the day had already moved their way (from the open, in units of the last 14 sessions' average
   range): the weakest group on every set is beyond 1.1x (PF dev 1.11, unseen NQ 0.91, live 1.77, against 1.3-1.9 /
   1.4-1.9 / 4.2-5.0 below); trade number, time of day, the previous trade's result and the weekday flip between sets.
   Rule: no entry once the day has moved more than 1.1x its usual range the trade's way (`max_move` 1.1). 104 starts:
   none lost, median $14,288 (from $14,315), 25th percentile $9,373 (from $8,244); PF dev 1.54, unseen NQ 1.59, ES
   1.27, live 4.51 (from 1.47 / 1.49 / 1.22 / 3.88); about 8% fewer trades. 1.0x and 1.3x also lose none. Shipped
   (`MaxMove` 1.1; NinjaTrader and Pine trade for trade).

23. **Scratch exits as small wins** (2026-11-24, the user: "profitable trades is still bad", TradingView's 26%;
   `verification/zoo/stage17_break_even_lock.txt`). About 30% of trades left at the break-even stop, one tick past entry:
   after the stop's slippage and $1.24 of fees each closed at about -$1, counted a loss. The break-even stop at entry
   + 2 points instead (`be_plus` 2): winners 25% / 24% / 26% to **39% / 41% / 41%** (dev / unseen NQ / live), PF and net
   unchanged or better, 0 of 104 starts lost, median $14,288 to $15,275. +1, +3 and +5 points also lose none (at 0.5x
   2.9% are lost, so the trigger stays at 0.4x). Shipped (`BreakEvenPlus` 2).

24. **Counter-trend entries on strong breaks** (2026-11-24, the user's chart: no trades in the Nov 10-12 rally, price
   below its 20-session average; `counter_k`, `verification/zoo/stage18_counter_trend.txt`). Against the trend only
   past a band 1.0-2.5x as wide: days traded 51% to 53-64%, but 6.7-16.3% of starts lost at 1.0-2.0x and the live PF
   falls (3.07 to 1.96-2.48); the loosest, the only one trading Nov 10-12, lost there (4 trades, -$96). 2.5x loses none
   but its neighbour loses 6.7%. The trend filter stays.

25. **Done after a target?** (2026-11-24, Nov 13's re-entries after its 10:00 target: 6 more shorts, -$252;
   `after_target`, `verification/zoo/stage19_after_target.txt`). No more trades that day (or that direction) after a
   target: median $15,275 to $12,944, live per year $12,246 to $8,433 (Nov 20's second and third targets go). Not used.
   TradingView on the user's chart with the shipped rules (Aug 27 - Nov 23 2026): +$5,253, 46 trades, 39% winners,
   PF 3.48, max drawdown $1,084.

26. **The move cap not at 10:00** (2026-11-24, the user's chart: Nov 5 fell 1,500 points with one trade; 
   `move_free`, `verification/zoo/stage20_move_cap_at_ten.txt`). Nov 5 had fallen 1.47x its (quiet) usual range by the
   first check, so the cap blocked every short; the 10:00 short would have hit its target. A break at the first check
   is not a chase: without the cap there, dev, unseen NQ and ES are unchanged to the dollar (it hardly happens), live
   +$1,208 a year at 1 MNQ (Nov 5: 2 trades +$436 against 1, -$63), 0 of 104 starts lost. Shipped (NinjaTrader, Pine).

27. **More work on +$6,322 (TradingView, Aug 27 - Nov 23 2026: 47 trades, 40% winners, PF 3.98)** (2026-11-24).
   A breakdown of the band trades by how far past the band the entry closed, VWAP distance, the gap's and yesterday's
   direction, trend strength and volatility (dev / unseen NQ / live): only the stretch past the band was weak in the
   same place twice (0.1-0.25 sigma: PF 0.89 / 1.22 / 0.55; past 0.5 sigma 1.60-1.96 on all three), and trades with the
   gap beat those against it everywhere (1.62 / 1.63 / 6.37 against 1.33 / 1.56 / 1.79). Tested on the 104 starts, none
   used (`verification/zoo/stage21_*.txt`):
   - a minimum stretch past the band (0.10-0.35 sigma, or only against the gap): win rate up (live 42% to 46% at 0.25)
     but 15-20% fewer trades, the median $15,275 to $13,328-14,169, two settings lose 1.9-2.9% of starts;
   - the move cap measured from the band's reference (max/min of open and prior close: Nov 19's 14:00 short after a
     +472 gap that reversed) or the prior close: median $15,184 / $11,788, live +$4 / -$7,368 a year;
   - no move cap for a re-entry the way of a target already hit that day (Nov 5): 6 trades +$237 against 2, +$436,
     median $14,624;
   - the hard stop (and so break-even and target) 0.25-0.35x the 14-day average range: without bounds 6.7-8.7% of
     starts lost; bounded to 75-150 points the 25th percentile $9,478 to $11,265 but the median $14,417 and live wins
     42% to 36%;
   - limits for chop days like Nov 13 (a 10:00 target, then 3 scratches and 3 losers): no entry after 1 / 2 / 3 losing
     trades that day (median $8,364 / $12,989 / $15,246) or at most 4 / 5 / 6 trades a day (4: live +$623 a year but
     dev and unseen NQ lower, the 25th percentile $8,577; 5 and 6 within $200 a year of 9 everywhere). `max_losses`.

   One live fix from the walk through Nov 13 - 23: the history guard blocked the Mondays after Thanksgiving, Christmas
   and New Year. It counted calendar days (14 complete sessions within 23), but holidays and half days (out of the
   history: under 76 bars) push that to 24-26 on 8-10 days a year in 2015-2025 (Nov 30 2026 would have been one), days
   the backtest trades. It now counts weekdays without a complete session in the 14-session window and blocks only past
   5: holidays leave at most 4 (Jan 2025: Christmas Eve, Christmas, New Year, Jan 9), the Oct 19 - Nov 6 2026 hole 14.
   Tests: a holiday calendar trades exactly the guard-free reference (NinjaTrader, Pine), six missing sessions still
   block. Shipped (NinjaTrader, Pine).

28. **The gap trade's 09:30 bar** (2026-11-24; live since October the gap trade won 2 of 14; `min_body`,
   `verification/zoo/stage22_gap_first_bar.txt`). Its trades split by trend, gap size, opening outside yesterday's range,
   yesterday's direction, news and the 09:30 bar's size (dev / unseen NQ / ES / live): one bucket loses on all four, a
   09:30 bar moving the gap's way by under 3% of the 14-day average range (PF 0.76 / 0.64 / 0.00 / 0.00, 8% / 5% / 0% /
   0% winners). The stop is that bar's open, so a small bar leaves a stop a few points away, inside the noise. With
   the bar at least 3% of the average range: 0 of 104 starts lost, median $15,275 to $15,314, 25th percentile $9,478 to
   $9,620, win rate up 1-3 points on every set, per year at 1 MNQ dev +$31, unseen NQ +$59, ES +$98, live +$118, about 10
   fewer trades a year (0-8% of them winners). Neighbours 2% and 4%: 0 lost, the same way. Only gaps against
   yesterday's direction (live 52% winners, PF 4.46) cost dev and unseen NQ $500-700 a year: not used. Shipped
   (`GapMinBody` 0.03, NinjaTrader and Pine).

29. **The gap trade's size and stop, again** (2026-11-24, after 28; `verification/zoo/stage22_gap_grid*.txt`). With the
   small 09:30 bars out, the gap threshold 0.2-0.5 x the average gap and the stop cap 25-50 points: every 40-point cap
   beats 30, and 50 loses 2.9% of starts at 0.3 and 0.4 (the edge). Shipped: **0.3 and 40 points** (neighbours 0.2 / 0.4
   and 35 / 45: 0 lost, 25th percentile $9,666-10,465): 0 of 104 lost, median $15,314 to $15,719, 25th percentile $9,620
   to $10,873, per year at 1 MNQ dev $5,119 to $5,685, unseen NQ $6,971 to $7,157, ES $679 to $593, live $13,572 to
   $13,698; about 11 more trades a year. The 40-point stop at 3 MNQ risks $240. TradingView with 28 (Aug 27 - Nov 23
   2026): +$6,345, 44 trades, 43% winners, PF 4.02.
   **Taken back the same day.** On the user's TradingView window with 0.3 / 40: +$5,370, 48 trades, 42% winners, PF
   3.14. Gap trades Aug 27 - Nov 23: 19, +$244 at 1 MNQ against 14, +$618: the 5 smaller gaps all lost, and with the
   09:30 bars 60-170 points this autumn the cap is nearly always the stop, so each of 9 stops lost 10 points more. The
   adoption test was not met: live PF 3.34 to 2.94 and ES 1.17 to 1.14 (the per-year net over Jun 29 - Nov 23 hid it).
   A small gain on 2015-2025 does not outweigh a clear loss in the market traded now: back to 0.5 / 30 with 28's rule.

30. **One more contract on a strong break** (2026-11-24, the user: "improve it even more"; `harness.account`'s per-trade
   `add`, `strats.band_stretch`, `zoo/tv_window.py`, `verification/zoo/stage23_strong_break_size.txt`). Band entries
   whose signal close is 1.5 sigma or more past the band: 19 / 17 a year on dev / unseen NQ, 65% / 74% winners, PF
   2.11 / 2.84 (the rest 1.53 / 1.50); live 4 in the TradingView window, 3 targets and a scratch. One contract more on
   those (at most MaxContracts, not with FixedContracts): 0 of 104 starts lost (dev and unseen NQ each 0, the worst
   start up), median $15,314 to $16,030, 25th percentile $9,620 to $11,173; the TradingView window (`tv_window`) +$6,404
   to +$9,224, max drawdown $447 to $670. Neighbours 1.25 and 2.0 sigma: 0 lost; 1.0: 2.9% lost, 0.5: 3.8% (the edge).
   From 2 contracts only: no better. Against it: on ES those entries lose (PF 0.42, about 40 trades), as the gap trade
   does; the bot trades MNQ. Shipped (`StretchAddAt` 1.5, NinjaTrader and Pine; parity tests check every trade's size).

31. **The missed big days** (2026-11-24, the user: "too many missed signals"; `verification/zoo/stage24_trend_misses.txt`,
   `zoo/bench.py`: every gate in one call). TradingView with 30: +$9,186, 44 trades, 43% winners, PF 4.33, max drawdown
   $1,626 (the reference: +$9,224). In that window (62 sessions) 26 traded; of the 36 without a trade 13 moved (half the
   average range open to close or a full range): 6 never closed past the band at a check, 5 against the 20-day trend
   (Nov 2 -583, Oct 8 -260, Sep 3 +282), 1 mild news, 1 the range rule (Nov 17). Tried for the trend ones, none used:
   - the trend over 5 / 10 / 15 / 30 / 50 sessions: 5 loses 3.8% of starts; 10 and 15 the TradingView window
     +$6,314 / +$8,972 and a lower 25th percentile; 30 the window +$11,138 but the 25th percentile $11,173 to $7,778
     and dev $5,119 to $4,581 a year; 50 lower everywhere;
   - against the trend past a band 2 / 2.5 / 3 / 4x as wide: 2x loses 8.7%; 3x the 25th percentile $12,684 but the
     window +$6,761 and live PF 3.34 to 2.73; 2.5x and 4x the window flat and PF lower.

32. **Every setting again, and the size steps** (2026-11-24, the user: "every way and every angle";
   `verification/zoo/stage25_settings_sweep.txt`, `stage25_steps_day_stop.txt`). With 28 and 30 in, each setting one
   step either way (target 2.0-3.5R, break-even 0.3 / 0.5 and its lock 1-8 points, hard stop $175 / $225, last entry
   13:30 / 14:30, move cap 1.0 / 1.2, range rule 0.6 / 0.7, the band 0.9 / 1.1 sigma, a gap target 1-2R or exit at
   10:25): none beats the shipped settings on every gate (the 104 starts and the TradingView window); a wider stop, a
   later break-even and either band width lose 2.9-3.8% of starts. The rules are at their best point.
   The size steps were set before 20-30 made the trades safer. **3 contracts from +$3,500** (was +$4,500): 0 of 104
   lost, median $16,030 to $16,582, 25th percentile $11,173 to $11,321, the TradingView window +$9,224 to +$9,796 (PF
   4.06 to 4.25). Neighbours 3 from +$3,000 / +$4,000 and 2 from +$1,750 / +$2,250: 0 lost. Not used: 2 from +$1,000
   (window +$11,497, 25th percentile lower), 2 from day one (5.8% lost), the day stop $800 (+$400 median and 25th
   percentile, but $1,000 loses 1%: too near the edge).

33. **More angles with 32 in** (2026-11-24; `verification/zoo/stage26_more_angles.txt`; the bench's steps now +$3,500).
   None used: the strong-break contract at 1.25 / 2.0 sigma (both lower), a second contract at 2.5-4 sigma (no change:
   too rare); a bigger target on strong breaks (3R: median -$495; 4R: the TradingView window +$12,423 but median and
   25th percentile -$1,100 to -1,200, a November fit; none: lower); a time stop after 1-4 checks short of break-even
   (1-2: median down, ES negative; 3-4: no change); the VWAP stop off (3.8% lost), the VWAP entry filter on (lower);
   at most 6 trades a day (+$24 median, the window +$111: within noise, as in 27). The news-day rule is still worth
   $2,700 of median. The news fade at the open stays out (its live months were negative, section 14).
   The news thresholds again: skip 2-2.5x / 2-3.5x (median -$900 / -$2,800), no skip (2.9% lost; the window +$11,609),
   one more contract from 4x / 5x (median +$225-235, but the 25th percentile and the window's PF lower), from 8x
   (lower): 2-3x and 6x stay. A warning from it: skipping from 1.75x cuts the window to +$2,644, so live days sit
   near the 2x line; the rule's skip days in the window are the reason it stays at 2x.
   The band from the open alone (not max / min with the prior close: the "never past the band" misses of 31, e.g. Nov
   12's gap down and rally): the TradingView window +$14,807 (PF 5.17, 62 trades) but **17.3% of starts lost** and the
   25th percentile $2,282; half way: 3.8% lost. The prior close in the band is what keeps the account through 2015-25.

34. **More traded days** (2026-11-24, the user: "max 2-3 days no trading", then "not forced trades: more days traded and
   more profit"; `zoo/force.py`, `strats.backup_trade`, `verification/zoo/stage27_more_days.txt`). With the shipped
   rules 37% of the TradingView window's sessions trade (the longest run without a trade 6; 2015-25: 42%, up to 13).
   - A forced trade after 2 quiet sessions (the mild-news skip off that day; if nothing by 15:30 a 1-contract last
     half hour trade the day's way, a 40-70 point stop): 0 of 104 lost, the longest run 2 everywhere, 50% of sessions
     traded, but no more money (median $16,097-16,344, the window +$9,670-9,786; the backups PF 1.1-1.25 on NQ, 0.5
     on ES). Built and taken back: the user asked for real signals, not forced trades.
   - The best other setup of stage 1, the opening drive (the first 15 minutes closing in the top or bottom 30% of
     their range past the prior close, in at 09:45, the stop the range's middle; PF 1.43 / 1.23 / 1.33): with the
     band from day one 8.7-13.5% of starts lost; from a cushion (+$3,500 / 5,000 / 7,500 / 10,000) none lost and about
     20 more traded days a year, but median $14,115-15,261 and the window +$8,166-9,796 (its trades hold the account
     when the band's better ones come); out at 09:55 instead: 0-1% lost, median $14,322-15,555, the window lower. The
     5-minute opening range breakout: 41% lost. (Research fix: `drive` now returns its exit bar for `merge`.)
   None used: every way found to trade more days costs profit or accounts on this data.

35. **A second market for the days Nasdaq chops** (2026-11-24, the user: "if the market is chopped that day we look at
   another market"; `zoo/markets.py`, `verification/zoo/stage28_other_markets.txt`). 1-minute history from histdata
   (Hugging Face elthariel/histdata_fx_1m, UTC, no volume): spot gold (XAUUSD, for MGC) 2009 - Mar 2025, WTI (for MCL)
   2010-23, EUR/USD (for M6E) 2000 - Mar 2025; each market's main session (gold 08:30, crude 09:00, also 09:30) on the
   09:30-16:00 clock, prices rescaled month by month to today's level, the hard stop 0.15-0.25x the recent median day
   range (NQ's $200 is about 0.2x), everything else the shipped band; dev 2009-17, unseen 2018 on.
   - The band: gold PF 0.98-1.05 / 0.91-1.02 (8-10 of 17 years up), crude 0.66-0.74 / 0.90-1.03 (0-3 of 14), the euro
     0.39-0.50 / 0.30-0.35 (0 of 26). Before costs gold is PF 1.13 / 1.16 (13 of 17 years up): a small edge that the
     micro contract's fees and slippage take (MGC's 0.2x stop is about $80 against about $3 of costs; GC's $780 is too
     big for the $2,000 floor). Crude before costs 0.98 / 1.17, the euro 0.83 / 0.64.
   - The other families scaled to each market's range (opening range 5 / 15 / 30 minutes, the opening drive, gap and
     go, the last half hour, the prior day's high / low, VWAP reversion): crude none above PF 1.05 on both; gold only
     a full-day gap and go on 1x gaps (1.62 / 1.26, 20% of days, about $276 a contract a year).
   Not used: the band's edge is Nasdaq's (the intraday momentum the noise-band papers find in equity indices); the
   other index micros (MES, MYM, M2K) chop on the same days and ES is weaker (section 9). A file the user sent,
   "FUND US ARCX MGC", is the Vanguard Mega Cap Growth ETF (daily bars), not micro gold.

36. **The MNQ script as it is on Micro Gold** (2026-11-24; the user ran `pine/mnq_clean_band.pine` on MGC1! 5-minute,
   Aug 27 - Nov 23 2026: +$1,353, 45 trades, 42% winners, PF 2.08; the same run on MNQ1!: +$9,757, PF 4.53, the reference
   +$9,796). Gold 2009 - Mar 2025 with the script's own settings (a $200 stop = 20 MGC points, the gap trade, 09:30-16:00;
   `verification/zoo/stage30_gold_with_mnq_settings.txt`): PF 1.04 / 1.03 (2009-17 / 2018-25), 9 of 17 years up, 2024
   -$439, 2025 Q1 -$827; $150 / $300 stops and an 08:30 session the same (PF 1.01-1.07). Autumn 2026's +$1,353 is gold's
   fall from 4,200 to 3,500 (a trend the band rides), not an edge that lasts: not used.
   Also found by the gold / crude setup search (`verification/zoo/stage29_gold_crude_setups.csv`, 354 variants): gold's
   overnight move carried on from 08:20 (a 1-1.5x average overnight move, the first 15 minutes its way, the stop at the
   08:20 open, out 13:30 or 16:00): PF 1.31-1.46 / 1.23-1.32, 59-71% of years up, but 15% winners and $200-500 a contract
   a year. Crude: nothing above PF 1.15 on both halves with enough trades.

37. **MGC Overnight Carry: a second strategy for more trades** (2026-11-24, the user: "keep working, I need more
   trades"; `ninjatrader/Strategies/MgcOvernightCarry.cs`, `pine/mgc_overnight_carry.pine`, `mk_search.carry`,
   `tests/test_ninjatrader_gold.py`, `tests/test_pine_gold.py`, `verification/zoo/stage31_mnq_plus_gold.txt`). The one
   gold pattern of section 36's search, built for NinjaTrader: gold's move from the prior session's 13:25 close to the
   08:20 open at least 1.5x its 14-session average, the 08:20-08:35 bars closing its way: in at 08:35 its way, the stop a
   tick past the 08:20 open (60% of the way to the signal since section 39), out at 13:30 (14:15 since 41); sized like MNQ (1 / 2 / 3 from +$0 / 2,000 / 3,500); its own chart and
   strategy beside MnqCleanBand on the same account. Gold alone (5-minute bars, as NinjaTrader trades it): about 20
   trades a year, PF 1.29 (2009-17) / 1.54 (2018 - Mar 2025), 65% of years up, the worst trade -$348 a contract. With
   MNQ on one 50K (100 starts 2015 - Mar 2025, gold with no day stop of its own, MNQ's $600 as shipped): **0 lost,
   median $16,727 to $17,090, 25th percentile $11,524 to $11,584, trades a year 217 to 235**; every neighbour (1.25 /
   1.75x, 10 / 20 minutes, out 13:00 / 14:00) loses none. Stress (2009 - Mar 2025, about 4,000 sessions, 316 trades):
   NinjaTrader and the reference trade for trade, sizes too; Pine on the last 500 sessions. Two fixes it found: a
   holiday's early close (Feb 19 2018, Jan 12 2024) left no 13:25 bar, so the trade now goes out on the next trading
   day's first bar (live, NinjaTrader's exit on session close comes first); and a gap in the bars before 13:30 (Feb 21
   2011) exits on the first bar from 13:25 on. No live gold months here (the data ends Mar 2025): check it in
   TradingView on MGC1! before trusting it.

38. **The cushion guard** (2026-11-24; the user's accounts sat $800-1,000 above their floors; `verification/zoo/
   stage32_cushion_guard.txt`). Every test before started with the full $2,000 above the floor. From $1,000-1,200 above
   it the shipped rules lose far more (6-month runs on 2015-2025 NQ, a $48,000 floor): MNQ + gold from $48,806 16.1%,
   from $48,998 7.1%, from $49,500 1.8%. The guard, at each day's start: the floor trails the highest end-of-day balance
   by $2,000 (stopping at the start balance); under $1,500 above it, 1 contract (no strong-break or news contract), a
   day stop of a quarter of the cushion ($100 at least) and no gold trade; normal again once the cushion is back. With
   it: 4.5% / 0.9% / 0.0%; fresh 50K starts still 0 lost, median $17,062 to $16,078 (MNQ alone $16,582 to $14,835:
   the guard also acts after a fresh account's early losses). Tried: triggers $1,000 / $1,250 (fresh median $16,817 /
   $16,221, but $49,500 starts 1.8% / 0.0%), a guard held on until $2,000 (lower medians, no fewer lost), a fixed $150-250
   day stop (2.7% / 2.7% at $200, fresh median lower). Shipped at $1,500 (`CushionGuard`, `GuardDayStopShare`,
   `TrailingDrawdown`, `HighestBalance`; NinjaTrader and Pine, MNQ and gold). NinjaTrader cannot see the prop firm's
   floor: "Highest end-of-day balance so far" is copied from its dashboard, then the strategy raises it from each day's
   starting balance. It overrides FixedContracts near the floor (CushionGuard 0 turns it off). Tests: trade for trade
   with the reference from $800 above the floor and with a higher high-water mark, MNQ and gold, NinjaTrader and Pine.

39. **The gold trade's stop** (2026-11-24, a research round; `mk_search.carry` stop_at / be_r / tp_r,
   `verification/zoo/stage33_gold_stop.txt`). The stop sat a tick past the 08:20 open, as far as the first 15 minutes
   had run. Moved part of the way from the 08:20 open toward the signal close (the 08:30 bar's), gold alone (PF 2009-17 /
   2018 - Mar 2025, the worst trade a contract) and with MNQ on one 50K (100 starts, median / 25th percentile):
   0% (as shipped in 37) 1.24 / 1.54, -$347, $17,062 / $11,581; 40% 1.48 / 1.70, -$209, $16,787 / $11,782; 50% 1.50 /
   1.86, -$175, $17,076 / $11,824; **60% 1.80 / 1.88, -$141, $17,138 / $11,876**; 75% 1.65 / 2.55, -$89, $16,965 /
   $12,326; 0 lost in every case. Every stop from 40% to 75% beats the open; 60% is the middle. Not used: break-even at
   1-2x the risk (PF 1.31-1.34 / 1.66-1.82, the 25th percentile lower at 1.0 and 1.5), a target at 2-4x (PF 0.86-1.10
   on 2009-17). With the 60% stop the other settings again: the move 1.25 / 1.75x, 10 / 20 minutes, out 13:00 / 13:40
   (`StopAt` 0.6 with the shipped 1.5x / 15 / 13:30: all 0 lost). Shipped: `StopAt` 0.6 (NinjaTrader, Pine); tests
   trade for trade on 2009 - Mar 2025 gold.

40. **MNQ's exit details** (2026-11-24, a research round; `noise` be_on / exit_at,
   `verification/zoo/stage34_mnq_exit_details.txt`). Break-even on a bar's high / low instead of its close (still moved at
   the bar's close): 2.9-3.8% of starts lost at 0.4 / 0.5 / 0.6 (it scratches trades that would have run). Out at 15:30 /
   15:40 / 15:45 instead of 15:55: median $16,708 / $16,171 / $16,506 against $16,582, 25th percentile $11,576 / $10,388 /
   $10,987 against $11,321, ES lower in all three: up then down then down, no edge. None used.

41. **Gold's exit time, the gap trade's exit, gold's confirmation** (2026-11-24, a research round;
   `verification/zoo/stage35_gold_exit_gap_exit.txt`). With the 60% stop (39), gold out at (with MNQ, median / 25th
   percentile; gold alone PF 2009-17 / 2018 - Mar 2025): 13:30 $17,138 / $11,876, 1.80 / 1.88; 13:45 $17,213 / $11,942,
   1.86 / 1.85; 14:00 $17,405 / $12,038, 1.84 / 1.90; **14:15 $17,366 / $12,077, 2.02 / 1.84**; 14:30 $17,387 / $12,117,
   1.95 / 1.80; 15:00 $17,277 / $12,083, 1.88 / 1.73; all 0 lost: every exit from 13:45 to 15:00 beats 13:30, and 14:15
   is that plateau's middle. Shipped: `ExitAt` 855 (14:15); the move's reference stays the prior session's 13:25 bar
   (`SettleAt` 810, a separate setting now). Not used: gold confirmed over 10 / 20 minutes (median $16,866 / $16,815, PF
   1.24 / 1.32 on 2009-17); the MNQ gap trade out at 10:00 / 10:10 / 10:15 instead of 09:55 (the window +$289 at 10:00,
   but median -$1,002 and 25th percentile -$790; 10:10 / 10:15 lower everywhere). Re-entries after a target were
   section 25.

42. **Gold's size** (2026-11-24, a research round; `verification/zoo/stage36_gold_sizing.txt`; with the cushion guard).
   With the 60% stop a gold trade risks about $12 a contract (half between $7 and $23, at most $178). Sized to $100-250
   of risk a step but at most 3 MGC: no change (median $16,282 against $16,251, the 25th percentile lower); a contract
   more on big-news days: no change. Above the user's 3-contract rule (not used; the user's to decide): at most 5 MGC
   ($100 a step) median $16,510 / 25th percentile $12,240, at most 10 MGC median $18,132 / 25th percentile $11,421;
   accounts started near the floor unchanged (4.5% / 0.9% lost).

43. **An exponential trend, gold on news days** (2026-11-24, a research round; `noise` trend_ema,
   `verification/zoo/stage37_ema_trend.txt`). The trend filter as an exponential average of the prior closes: EMA 20 every
   set's 1-contract net up (dev $5,119 to $5,407, ES $679 to $974, live $13,572 to $14,162) and the window +$123, but the
   104 starts' median $16,582 to $16,059 and 25th percentile $11,321 to $10,785; EMA 15 median $16,129, the window lower;
   EMA 30 25th percentile $6,459. Not used. Gold by the day's 08:30 news spike (NQ's, 2015 - Mar 2025): mild days (2-3x)
   PF 3.30 on 2015-19 but 0.71 on 2020-25, so no skip; 3-6x days lost in both (PF 0.00 / 0.34) but on 23 trades, a
   bucket picked after the fact: noted, not used. The range rule with the overnight session: not testable here (the NQ
   history is regular hours only).

44. **A weekly loss limit** (2026-11-24, a research round; `verification/zoo/stage38_weekly_limit.txt`; on the shipped
   setup with the cushion guard and gold). No trades for the rest of the week once it is down $600 / $900 / $1,200 /
   $1,500: fresh 50K median $14,658 / $15,822 / $16,483 / $16,251 against $16,251, 25th percentile $10,207 / $11,804 /
   $11,765 / $11,745 against $11,745; accounts started near the floor lose the same (4.5% / 0.9%): the guard already
   covers it, and $1,200's +$232 sits between a lower $900 and no change. Not used. Also not repeated this round: a hard
   stop scaled to the band or the day's range (section 21: lost starts unbounded, mixed bounded) and a contract more on
   very large gaps (section 28's breakdown: gaps over 2.5x are the gap trade's weakest, PF 0.60 unseen NQ, 0.07 ES).

45. **The check times, the target's first bar, gold's window** (2026-11-24, a research round; `noise` check_off,
   `verification/zoo/stage39_check_times_gold_window.txt`). The band's checks moved off the half hour (:05 / :35, :10 /
   :40, :15 / :45): 8.7% / 14.4% / 21.2% of starts lost, the TradingView window +$1,647-3,108 against +$9,796, live PF
   1.54-1.79 against 3.34: the edge is at the half-hour closes (the noise-band papers' times). The take-profit working
   from the next bar (Pine's way) instead of the fill bar: identical results (a 2.5x target is not reached on the fill
   bar), so it is not the reason TradingView and NinjaTrader can differ. Gold's average move over 10 / 20 / 30 sessions
   instead of 14: median $17,295 / $17,454 / $16,694 against $17,366, PF 2.10 / 1.77 / 1.67 on 2009-17 against 2.02;
   no window better on every count. None used.

46. **Strong breaks late or without break-even, gold by weekday** (2026-11-24, a research round; `noise` strong_last /
   be_skip_strong, `verification/zoo/stage40_strong_late_be.txt`). Entries at 14:30 (or 15:00 too) for strong breaks
   (1.5 sigma) only: median $16,212 / $16,049 against $16,582, the window unchanged (they hardly happen that late). No
   break-even for breaks past 1.0 / 1.5 / 2.0 sigma: 3.8% of starts lost in each. Gold by weekday (PF 2009-17 / 2018 -
   Mar 2025): Mon 0.48 / 2.25, Tue 3.63 / 3.34, Wed 4.82 / 0.15, Thu 1.06 / 1.34, Fri 2.42 / 2.52: Monday and Wednesday
   flip, no day loses in both. None used.

47. **The VWAP stop after break-even, gold by limit** (2026-11-24, a research round; `noise` vwap_after_be,
   `carry` limit_entry, `verification/zoo/stage41_vwap_be_gold_limit.txt`). The VWAP tightening of MNQ's stop only after
   break-even: median $16,528 / 25th percentile $11,251 against $16,582 / $11,321, the window -$51. Gold in by a limit at
   the signal close (filled only through it): PF 1.52 / 1.00 against 2.02 / 1.84 (it fills the moves that come back,
   not the ones that run), median $16,482 against $17,366. MNQ's day stop with the open trade counted: no different (it
   enters only flat, so nothing is open when it decides). None used.

48. **Gold's stop idea on MNQ** (2026-11-24, a research round; `gap_go` stop_at, `noise` band_stop_at,
   `verification/zoo/stage42_mnq_stops_part_way.txt`). The gap trade's stop 25-75% of the way from the 09:30 open to the
   signal close: median $15,141-16,377 against $16,582 (the 30-point cap already sets most of those stops); the band
   trade's stop 25 / 40 / 60% of the way from the band (or hard) stop to the signal close: median $13,737 / $11,311 /
   $9,865, 5.8% lost at 60%. What helps gold (a wide first move, the stop at its start) does not carry over. Gold
   confirmed by the overnight VWAP: not testable (the gold history has no volume). None used.

49. **Live-readiness: slippage and shuffled years** (2026-11-24, a research round; `research/stress/montecarlo.py`,
   `verification/zoo/stage43_slippage_montecarlo.txt`; the shipped MNQ + gold with the cushion guard).
   - Slippage: 1 / 2 / 3 / 5 extra ticks a side on every trade: PF dev 1.56 / 1.53 / 1.49 / 1.42, unseen NQ 1.56 /
     1.53 / 1.50 / 1.45, live 3.27 / 3.20 / 3.12 / 2.98 (ES under 1 from 2 ticks); fresh 50K starts still 0 lost, median
     $15,506 / $14,882 / $14,211 / $12,445; from $48,806 / $48,998: 3.6-4.5% / 1.8-2.7% lost up to 3 ticks, 8.9% / 4.5%
     at 5. The edge holds through realistic fills.
   - **Shuffled years** (2,000 runs of 252 days drawn at random from 2020 - Mar 2025, MNQ + gold, the guard): a fresh 50K
     is lost in **6.3%** of years (median +$16,632, the worst 10% +$1,868); from $48,806 **18.9%**, from $48,998
     **14.5%**. The 0 of 104 calendar starts is the history as it happened; drawn in any order, losing days can come
     before the cushion does. That is the realistic risk (the walk-forward of section 7 said 5.7%).
   - Against it, in the same 2,000 runs: the guard from $2,000 / $2,500 / $3,000 (and a 15% day stop) 5.7% / 4.7% / 4.1%
     fresh, 17.8% / 17.1% / 16.8% from $48,806, at $1,500-4,000 of median; only gold (no MNQ) while guarded: 1 MGC
     0.0-0.1% lost but the account barely moves (median +$165), 3 MGC 19-30% lost. Nothing removes the risk without
     removing the profit: none used.

50. **The guard's last tier: strong breaks only** (2026-11-24, a research round; `verification/zoo/stage44_strong_only_tier.txt`).
   Against section 49's risk, while guarded (2,000 shuffled 2020 - Mar 2025 years; blown / median from $50,000,
   $48,806, $48,998): shipped 6.3% / $16,632, 19.7% / $12,581, 14.7% / $13,616; a $150 / $100 MNQ stop 5.5-5.9%,
   16.3-18.1%, 12.8-14.0% (median lower at $100); at most 1 MNQ trade a day 4.9%, 17.0%, 12.6% (median $6,369 from
   $48,806); **only strong breaks (1.5 sigma) and the gap trade** 1.5%, 6.2%, 3.8% but median $13,881 / $6,791 / $8,373.
   As a tier under the guard, with the strategy run again with `min_stretch` 1.5 on those days (exact), strong breaks
   only under $750 / **$1,000** / $1,250 above the floor: 3.6% / **2.7%** / 2.5%, 12.2% / **10.2%** / 8.8%, 8.6% / **6.5%** /
   5.1%, median $16,597 / **$16,017** / $15,218 fresh. In calendar order (104 + 111 + 111 starts): $750 no better near the
   floor (4.5% / 0.9%, $49,500 0.9%); **$1,000: fresh 0 lost, median $16,251 to $15,213, 25th percentile $11,745 to
   $10,135; from $48,806 4.5% to 1.8%, from $48,998 0.9% to 0.0%**; $1,250 the 25th percentile $6,324. Shipped at $1,000
   (`GuardStrongOnlyBelow`, `GuardStrongOnlyStretch` 1.5; NinjaTrader and Pine): a risk cut at a profit cost, the user's
   rule first ("never lose the account"); `CushionGuard` 0 turns the whole guard off. Two catches by the tests: the
   guard's high-water mark came from the replay of the loaded history, so live the floor could sit at the start
   balance (a $49,600 account read as $400 below it: 1 contract, a $100 day stop); at the switch to real time it now
   starts again from "Highest end-of-day balance" (MNQ and gold; a test reads the live dashboard at $49,600 and
   $48,800 and fails without the fix). Rejected with it: gold-only or gold-added modes while guarded (49).

51. **The tier on 2015-19, a careful first month, the floor rule** (2026-11-24, a research round;
   `verification/zoo/stage45_tier_2015_first_month.txt`). Shuffled 2015-19 years (2,000 runs; blown / median from $50,000,
   $48,806, $48,998): without the tier 2.7% / $11,641, 10.8% / $8,714, 7.2% / $9,350; with it 0.8% / $11,386, 6.3% /
   $7,033, 3.8% / $8,136: the same cut as on 2020-25. Strong breaks only from a fresh start until the first +$500 /
   +$1,000: 2020-25 fresh 2.5% / 2.1% lost against 2.7%, but 2015-19 1.1% against 0.8% and medians $1,700-2,800 lower:
   not used. The floor: the prop firm trails it from end-of-day balances, and the guard's high-water mark is each day's
   starting balance (the last end of day), so it matches.

52. **Half days: never held over the weekend** (2026-11-24; `verification/zoo/stage46_half_days.txt`). The torture
   script cut sessions at 13:15 (the Friday after Thanksgiving, Christmas Eve) with a trade open: it was held into the
   next session, which on a real half day is Sunday evening, with only NinjaTrader's session-close exit in the way.
   Now, MNQ and gold: out 5 minutes before the session's end from the trading-hours template (13:15: the 13:10 open;
   COMEX's 13:45: the 13:40 open), by 13:10 on those two dates whatever the template says, and a trade still open after
   any other early close goes out on the next bar (Pine: the calendar and the next bar). Each case has a test that
   fails without it. Half days were never in the research (complete sessions only); from the raw 2015-2025 NQ: 16
   trades, +$353 at 1 contract, PF 1.48: they trade as any day.

53. **One contract off early** (2026-11-24, a research round; `research/zoo/scale_out.py`,
   `verification/zoo/stage47_scale_out.txt`). With 2-3 contracts, one off at 0.5-2x the $200 stop, the rest as shipped:
   median $16,582 to $13,426-15,744, 25th percentile $11,321 to $8,527-11,558, the TradingView window $9,796 to
   $6,948-8,524; none lost either way. Rejected: the early contract is cut from the trades that reach 2.5x.

54. **The day stop's level again** (2026-11-24, a research round; `verification/zoo/stage48_day_stop_level.txt`). With
   the add and the +$3,500 step in: $400 / $500 cut the median to $15,256 / $15,419 and the 25th percentile to $8,987 /
   $9,365 (shipped $600: $16,582 / $11,321); $700 no different; $800 +$157 median but more fresh shuffled years blown
   (6.6% against 6.3%). $600 stays.

55. **A second gap check at 09:35** (2026-11-24, a research round; `research/zoo/gap_second_check.py`,
   `verification/zoo/stage49_gap_second_check.txt`). When the 09:30 bar does not qualify, the 09:35 close the gap's
   way by 3-10% of the average range -> in at 09:40: 2-19 more trades a year, but median $15,870-16,430 against
   $16,582, the 25th percentile and the TradingView window lower at every setting. Rejected.

56. **A second extra contract on very strong breaks** (2026-11-24, a research round; `bench.run(add2_at)`,
   `verification/zoo/stage50_second_add.txt`). Another contract at 1.75-4 sigma past the band (it only matters while
   trading 1): at 1.75 the median $16,994 and the window +$10,746, but 2.25-3.0 lower the 25th percentile or the
   median, and shuffled years blow more accounts from $48,998 (14.8-14.9% against 14.5%) for $35-195 of median. Not
   shipped: the extra size lands where an account is most fragile.

57. **A bar-quality filter** (2026-11-24, a research round; `noise` bar_pos / bar_n,
   `verification/zoo/stage51_bar_quality.txt`). A band entry only when the signal bar (or the half hour) closed in the
   top half / third / fifth of its own range (a short mirrored): 2.9-7.7% of starts lost, median $4,724-11,237 against
   $16,582, the window +$2,949-8,634. Rejected: the weak-closing breaks still pay. The most trades a day (27, 33) and a
   break-even for the gap trade (it has none: its stop stays at the 09:30 open) need nothing new.

58. **A second stop step** (2026-11-24, a research round; `noise` lad_r / lad_lock,
   `verification/zoo/stage52_stop_ladder.txt`). Once a band trade closes 1.25-1.75R up, the stop to entry + 0.3-0.6R:
   the pooled starts better (1.5R / +0.5R: median $16,939, 25th percentile $11,898; none lost; the window unchanged)
   and 2020-25 shuffled years blown 5.6% against 6.3% fresh, but 2015-19 flat to worse ($48,998 7.5% against 7.2%),
   4 of 12 years down $400-480, about +$125 a year a contract. Not shipped: too small and uneven for a new live order
   rule; re-check with live data.

59. **Another target for later entries** (2026-11-24, a research round; `noise` late_at / late_tp,
   `verification/zoo/stage53_late_target.txt`). 1.5 / 2.0 / 3.0R for band entries after 11:00-13:00: median
   $15,411-16,484 against $16,582 and the TradingView window $7,824-9,496 against $9,796. Rejected: afternoon breaks
   reach 2.5R often enough before 15:55.

60. **The gap trade's stop at the prior close; no gap trade on a wild open** (2026-11-24, a research round; `gap_go`
   stop_pc / max_bar, `verification/zoo/stage54_gap_stop_wild_open.txt`). The prior-close stop: lower median, window
   and dev. Skipping the gap trade when the 09:30 bar's range is over 1.5-1.75x its 14-day average: the trades' PF up
   on every set and the window +$125-151, but the account median never above $16,582 ($15,364-16,555) and the 25th
   percentile up and down between neighbours. A near miss, not shipped.

61. **The two near misses together: shipped** (2026-11-24, a research round; `verification/zoo/stage55_ladder_wild_open.txt`).
   The second stop step (58: a close 1.5R up moves the stop to entry + 0.5R) with the wild-open gap skip (60: no gap
   trade when the 09:30 bar's range is over 1.75x its 14-session average). Combining two near misses risks fitting
   noise, so the bar was every gate on both periods. 104 starts: none lost, median $16,582 to $16,931, 25th percentile
   $11,321 to $12,040, the window +$9,796 to +$9,921 (PF 4.25 to 4.43), PF up on dev, unseen NQ and live (ES flat).
   Shuffled years, blown from $50,000 / $48,806 / $48,998: 2020-25 6.3 / 18.9 / 14.5% to 5.0 / 17.2 / 12.7%, 2015-19
   2.7 / 11.5 / 7.2% to 2.3 / 10.8 / 6.5%, medians higher in all six. By year at 1 MNQ: 8 of 12 up, +$2,553 in all
   (about $220 a year; 2015, 2017, 2022 down $217-354). Neighbours (ladder 1.25-1.75R / +0.4-0.6R, skip 1.5-2.0x):
   none lost, the 25th percentile and the window up in all six, the median $16,019-16,937 (three below $16,582). Small
   and not certain: by period (section 68) the 2015-19 starts' 25th percentile is $546 lower ($5,256 against $5,802),
   the 2020-25 one $870 higher; fewer accounts blown in the shuffled years of both. Shipped:
   `LadderAt` 1.5, `LadderLock` 0.5, `GapMaxBar` 1.75 (NinjaTrader and Pine, trade for trade; 0 switches each off).

62. **The target again, with 61 in** (2026-11-24, a research round; `verification/zoo/stage56_target_with_ladder.txt`).
   2.0 / 3.0 / 3.5R against 2.5R: 3.0R the same median ($16,929) and a higher 25th percentile ($12,680) but the window
   +$7,590 against +$9,921; 2.0 and 3.5 lower. 2.5R stays.

63. **Break-even again, with 61 in** (2026-11-24, a research round; `verification/zoo/stage57_break_even_with_ladder.txt`).
   0.3R: median $14,917, 25th percentile $8,803; 0.5R: 3.8% of starts lost. 0.4R stays.

64. **The hard stop again, with 61 in** (2026-11-24, a research round; `verification/zoo/stage58_hard_stop_with_ladder.txt`).
   $175: median $15,624, the window +$8,294; $225: 3.8% of starts lost. $200 stays.

65. **The move cap and the range rule again, with 61 in** (2026-11-24, a research round;
   `verification/zoo/stage59_move_cap_range_with_ladder.txt`). Cap 1.0 / 1.2 and range 0.6 / 0.7: every one lower on
   the median and the 25th percentile (range 0.7: the window +$179, the rest lower). 1.1 and 0.65 stay.

66. **A second stop step for gold** (2026-11-24, a research round; `mk_search.carry` be_lock,
   `verification/zoo/stage60_gold_stop_step.txt`). Once up 1-2x the risk, the stop to entry + 0.3-1.0x: 2009-17 up to
   +$20 a year at 1 MGC, but 2018 - Mar 2025 $164-209 a year against $284 at every setting. Not shipped.

67. **The extra contracts again, with 61 in** (2026-11-24, a research round;
   `verification/zoo/stage61_add_news_with_ladder.txt`). The strong-break add at 1.25 sigma and the big-news add from 5x
   lift the median ($17,529 / $17,745) but lower the 25th percentile ($11,742 / $11,863 against $12,040): more size for a
   weaker tail. 1.75 sigma and 8x no better. 1.5 sigma and 6x stay.

68. **A walk-forward of 61** (2026-11-24, a research round; `research/zoo/walkforward_61.py`,
   `verification/zoo/stage62_walkforward_61.txt`). By period, fresh starts: 2015-19 median $13,058 to $13,639 but the
   25th percentile $5,802 to $5,256 (every setting with the rules lowers it there); 2020-25 median $17,530 to $18,453,
   25th percentile $14,215 to $15,085. Settings picked on 2015-19's median (ladder 1.25 / 0.4, skip 1.75) beat no rules
   on 2020-25; picked on its 25th percentile, no rules. Kept, as a judgment call; `LadderAt` 0 and `GapMaxBar` 0 go
   back to the earlier rules.

69. **61's two halves by period** (2026-11-24, a research round; `verification/zoo/stage63_61_halves.txt`). The skip
   alone: 2015-19 $14,007 / $5,407, 2020-25 $17,224 / $14,111 (median / 25th percentile); the step alone: $13,269 /
   $4,994, $18,476 / $14,987; the pair: $13,639 / $5,256, $18,453 / $15,085; neither: $13,058 / $5,802, $17,530 /
   $14,215. Neither half alone beats the pair; the pair stays. A fixed-point wild-open threshold is not stationary
   (NQ 4,000 to 21,000): the ratio stays.

70. **Extra checks in the first hour** (2026-11-24, a research round; `noise` extra_checks,
   `verification/zoo/stage64_extra_first_hour_checks.txt`). 10:15 (with or without 10:45): 7.3-10.9% of 2020-25
   starts lost. 10:45 alone: none lost, 2015-19 and the window up, but 2020-25 median $17,304 / 25th percentile $13,288
   against $18,453 / $15,085. The half-hour checks stay.

71. **Counter-trend breaks on gap days** (2026-11-24, a research round; `noise` trend_gap_k,
   `verification/zoo/stage65_counter_trend_on_gap_days.txt`). Breaks against the trend on days that opened 1.0-2.0x the
   average gap the break's way: 1.5x better in both periods but the window -$413 (PF 3.88), and 1.0x / 2.0x lower in one
   period each. A lone peak: not shipped.

72. **The noise area's lookback** (2026-11-24, a research round; `noise` sig_n,
   `verification/zoo/stage66_band_lookback.txt`). 10 / 20 / 30 sessions instead of 14: each better on 2015-19 and lower
   on 2020-25 (10: median $17,627 against $18,453; 20 and 30 lose 1.8% / 5.5% of 2020-25 starts). 14 stays.

73. **Holding the gap trade into a same-way band entry** (2026-11-24, a research round;
   `verification/zoo/stage67_hold_gap_into_band.txt`). Joined only when the 10:00 check agrees: +$223 / +$249 a year,
   but that decision would need the 10:00 close at 09:50 (hindsight). The tradeable version (hold every gap trade to
   the 10:00 check): 2015-19 -$137 a year, 2020-25 +$81. The 09:55 exit stays.

74. **The VWAP stop only until 11:00** (2026-11-24, a research round; `noise` vwap_until,
   `verification/zoo/stage68_vwap_stop_until.txt`). Better on both periods' medians and 25th percentiles at 10:30 /
   11:00 and fewer shuffled-year accounts blown in 5 of 6 cases, but only 6 of 12 years up and about $50 a year a
   contract; the window unchanged. Too small for a live change; not shipped. (A small-gap band reference: section 33's
   open-alone band lost accounts, and on small gaps the open and the prior close nearly coincide: not run.)

75. **Calendar effects** (2026-11-24, a research round; `verification/zoo/stage69_calendar_effects.txt`). Turn of the
   month, month ends and starts, options expiry, quarterly expiry, the days around holidays and the weekdays: every
   bucket weak in one period is fine in the other (last day of the month PF 0.46 on 2015-19, 1.40 on 2020-25; quarterly
   expiry 0.51 / 1.95), so nothing to skip. Fridays are above the average in all three sets, but one more contract on
   them loses 1.9% of starts. Nothing used.

76. **Yesterday's trend day and the opening half hour** (2026-11-24, a research round;
   `verification/zoo/stage70_trend_day_and_opening_range.txt`). No bucket weak in both periods (every PF 1.31+). Band
   trades after a wild first half hour (over 1.4x its average range) are strong in all three sets (PF 1.96 / 2.00 /
   8.49), but one more contract on them helps only 2015-19 (median +$1,186) and is flat on 2020-25. Not shipped.

77. **Live drift and gold beside MNQ** (2026-11-24, a research round; `verification/zoo/stage71_live_drift_gold_pairing.txt`).
   Since July 2026 the rules have run better than their history (PF 3.57 against 1.62-1.63; 0.70 trades a day against
   0.94-1.04), so no degradation, but a full year should look like the history (PF about 1.6, losing months like July).
   Gold and MNQ days correlate +0.04 / +0.11: gold diversifies; nothing to change.

78. **Slippage and fees with 61 in** (2026-11-24, a research round; `verification/zoo/stage72_slippage_fees_with_61.txt`).
   Up to 3 more ticks on every entry and stop, and $1.00 a side: no start lost in either period; the 2020-25 median
   $17,136 at +3 ticks. Section 61 leads more as fills worsen (2015-19 25th percentile $4,661 against $3,901 at +3 ticks).

79. **The band entry as a limit** (2026-11-24, a research round; `noise` limit_in,
   `verification/zoo/stage73_band_limit_entry.txt`). A limit at the signal close instead of a market order: 2020-25
   25th percentile $12,838 against $15,085 (the missed breaks are the runners), 2015-19 and the window a little higher.
   Market entries stay.

80. **Gold by the news spike** (2026-11-24, a research round; `verification/zoo/stage74_gold_by_news_spike.txt`). Big-news
   days (6x+): 2 trades on 2015-19 and 9 on 2020-25 with opposite results: no size rule. 3-6x loses in both but on 23
   trades in all (section 43's after-the-fact bucket). Nothing to change.

81. **The trend's slope** (2026-11-24, a research round; `noise` slope_n / slope_mode,
   `verification/zoo/stage75_trend_slope.txt`). The 20-session average rising / falling over 3-10 sessions, with or
   instead of the close past it: median $8,075-15,314 against $13,639 / $18,453 and the window about +$2,700 against
   +$9,921; alone, 5.5% of 2020-25 starts lost. The slope lags the first breaks of a move. Rejected.

82. **A two-check confirmation** (2026-11-24, a research round; `noise` confirm2,
   `verification/zoo/stage76_two_check_confirmation.txt`). Entries only when the close was past the band at the check
   before too: 1.8% of 2020-25 starts lost, medians $10,394 / $12,976 against $13,639 / $18,453, the window +$7,312.
   Rejected.

83. **The guard's level with 61 in** (2026-11-24, a research round; `verification/zoo/stage77_guard_level_with_61.txt`).
   Shuffled years: a $2,000 guard blows 0.4-1.0 points fewer accounts in 5 of 6 cases for about 8% less median; $1,250
   blows more everywhere. $1,500 stays; $2,000 is the user's risk choice (`CushionGuard`), not an improvement.

84. **A hysteresis band on the size steps** (2026-11-24, a research round; `verification/zoo/stage78_step_hysteresis.txt`).
   Stepping down only below +$1,500 / +$3,000 (up at +$2,000 / +$3,500): medians $48-292 higher but more accounts
   blown in all six shuffled-year cases (fresh 2020-25: 5.7% against 5.0%). Rejected: the steps stay symmetric.

85. **A contract fewer after two losing days** (2026-11-24, a research round; `verification/zoo/stage79_streak_step_down.txt`;
   on the real sequence, since shuffled days have no streaks). Medians $12,126 / $15,471 against $13,639 / $18,453 and
   the 25th percentiles $1,221 / $3,060 lower: the strategy recovers right after its losing runs. Rejected.

86. **A contract more after two losing days** (2026-11-24, a research round; `verification/zoo/stage80_streak_step_up.txt`).
   2015-19 median $15,869 against $13,639, but 1.8% of 2020-25 starts lost. Rejected: size after losses is how an
   account near its floor goes under.

87. **The gap trade's minimum gap again, with 61 in: 0.6x** (2026-11-24, a research round;
   `verification/zoo/stage81_gap_min_size.txt`). 0.6x the 14-session average gap instead of 0.5x: better on every gate
   in both periods (medians $14,028 / $18,980 against $13,639 / $18,453, 25th percentiles $5,324 / $15,811 against
   $5,256 / $15,085) and the window +$10,063; 0.55x agrees; fewer shuffled-year accounts blown in all six cases; 9 of
   12 years up, about $54 a year a contract. One setting's default, no new code: shipped (`GapK` 0.6, Pine "Gap at
   least").

88. **The gap stop cap again** (2026-11-24, a research round; `verification/zoo/stage82_gap_stop_cap.txt`). 25 points:
   medians and the window up, both 25th percentiles down; 35: mixed. 30 points stays.

89. **The gap trade's opening body again** (2026-11-24, a research round; `verification/zoo/stage83_gap_min_body.txt`).
   2% / 4% of the average range instead of 3%: both medians lower in both periods. 3% stays.

90. **61's settings again after 87** (2026-11-24, a research round; `verification/zoo/stage84_61_recheck_after_87.txt`).
   The wild-open skip at 1.5 / 2.0x and the stop step at 1.25 / 1.75R: each lowers at least one period's median. 1.75x
   and 1.5R / 0.5R stay.

91. **A walk-forward of 87** (2026-11-24, a research round; `verification/zoo/stage85_walkforward_87.txt`). Picked on
   2015-19 alone (median, or median + 25th percentile), the minimum gap is 0.6x, the shipped value, and it beats 0.5x on
   2020-25 ($18,980 / $15,811 against $18,453 / $15,085). Section 87 holds out of sample.

92. **The first half of 2025** (2026-11-24, a research round; `verification/zoo/stage86_2025_h1.txt`). +$682 at 1 MNQ
   (an average half-year: $3,940): March -$808 and June -$544 on wider, choppier days; every setup weaker, none failed
   alone; the strong-break contracts 9 of 9 won. No rule known in advance avoids it (the weekly loss limit, 44, was
   rejected). Nothing to change: a weak half-year is part of the history's PF of about 1.6.

93. **A monthly loss limit** (2026-11-24, a research round; `verification/zoo/stage87_monthly_loss_limit.txt`). No new
   entries for the month once it is down $1,000 / $1,500 / $2,000: 2020-25 medians $15,740-17,836 against $18,980, and
   $1,500 loses 1.8% of starts. The recovery days come right after the bad ones. Rejected.

94. **Protecting gains with a tighter day stop** (2026-11-24, a research round; `verification/zoo/stage88_profit_protection.txt`).
   $400 from +$5,000 / +$7,500: medians lower and no fewer fall-backs. Rejected. Starts that reached +$5,000 fell back
   under +$3,500 in 4 of 37 / 6 of 55 cases and none was lost.

95. **Gold around holidays** (2026-11-25, a research round; `verification/zoo/stage90_gold_holidays.txt`). No gold trade on
   a half day in 16 years; the days before / after holidays are 16 trades with opposite results by period. Nothing to
   change.

96. **MNQ after holidays and the history guard** (2026-11-25, a research round;
   `verification/zoo/stage91_after_holiday_guard.txt`). The day after a holiday is above average in both periods (PF
   3.17 / 1.84); the guard's worst real window misses 4 weekdays (limit 5), so it blocks no real day, after a holiday or
   not.

97. **Contract roll weeks** (2026-11-25, a research round; `verification/zoo/stage92_roll_weeks.txt`). The 8 days before a
   quarterly expiry are weaker in both periods (PF 1.04 / 1.37 against 1.74 / 1.68) but profitable; skipping them helps
   2015-19 and costs 2020-25 $1,792-2,020 of median. Rejected.

98. **The most trades a day again, with 61 and 87 in** (2026-11-25, a research round;
   `verification/zoo/stage97_gold_pine_and_max_trades.txt`). 5 a day: mixed (2020-25 median -$331, 25th percentile
   +$333); 3: lower everywhere. 9 stays. Gold's Pine inputs match MgcOvernightCarry.cs one for one.

99. **The last entry check again, with 61 and 87 in** (2026-11-25, a research round;
   `verification/zoo/stage98_last_entry.txt`). 13:30: lower everywhere; 14:30: 2020-25 median +$117 but its 25th
   percentile -$1,451 and 2015-19's median -$1,171. 14:00 stays.

100. **The trend length again, with 61 and 87 in** (2026-11-25, a research round; `verification/zoo/stage99_trend_length.txt`).
   15 sessions: both medians and the window lower; 25: 2020-25 25th percentile -$4,429. 20 stays.

101. **The band width again, with 61 and 87 in** (2026-11-25, a research round; `verification/zoo/stage100_band_width.txt`).
   0.95 / 1.05 sigma: lower on every number in both periods and the window. 1.0 stays.

102. **The break-even lock again, with 61 and 87 in** (2026-11-25, a research round;
   `verification/zoo/stage101_break_even_lock.txt`). +1 / +4 / +6 points: +4 helps 2015-19 but costs 2020-25 $2,057 of
   median; the others lower. +2 points stays.

103. **The size steps again, with 61 and 87 in** (2026-11-25, a research round; `verification/zoo/stage102_size_steps.txt`).
   2 from +$1,750 / +$2,250 and 3 from +$3,000 / +$4,000: every one lowers 2020-25's median. +$2,000 / +$3,500 stay.

104. **The mild-news skip again, with 61 and 87 in** (2026-11-25, a research round; `verification/zoo/stage103_news_skip.txt`).
   2-2.5x / 2.5-3.5x / 2-3.5x: every one lowers both periods' medians (2.5-3.5x lifts the window +$2,488, a gain the
   history does not hold). 2-3x stays.

105. **The target's half-steps, with 61 and 87 in** (2026-11-25, a research round;
   `verification/zoo/stage104_target_half_steps.txt`). 2.25R: lower everywhere; 2.75R: 2015-19 up, 2020-25 and the
   window down. 2.5R stays.

106. **Strong breaks only after a stop-out** (2026-11-25, a research round; `noise` reentry_min,
   `verification/zoo/stage105_reentry_after_stop.txt`). After a stop the same day, re-entries only 1.0-2.0 sigma past the
   band: medians $7,194-14,260 against $14,028 / $18,980. The re-entries pay. Rejected.
107. **Contracts by the day's range** (2026-11-25, a research round; `research/zoo/range_sizing.py`,
   `verification/zoo/stage106_range_sizing.txt`). The 14-session average range against its median over the year before.
   One contract fewer over 1.4-2.0x: 2015-19 medians -$1,294 to -$3,148. One more under 0.9x: +$1,458 / +$681, but
   one more on random days at the same rate gives +$734 / +$561, and both are inside that range: it is size, not the
   range. From 0.95x, 5.5% of 2020-25 accounts lost. Rejected. (A band exit at the checks is already in: every check
   to 15:00 moves the stop to the band, and a close back inside exits; after 15:00 the stop holds until 15:55, see 116.)
108. **Gold's settings by period** (2026-11-25, a research round; `research/zoo/gold_recheck.py`,
   `verification/zoo/stage107_gold_recheck.txt`). Gold alone, $ a year a contract, 2009-17 / 2018 - Mar 2025: shipped
   $361 / $286 (PF 2.02 / 1.84). The move at 1.25 / 1.35x: $327 / $445, $318 / $478 (better on one period, worse on the
   other); 1.65-2.0x lower on at least one. Confirmed over 10 / 20 minutes: lower on both. Out 13:45-14:45: 14:15 best
   on 2009-17, 14:00 +$21 on 2018-25. The settings were chosen on these years, so this checks they hold in each half:
   they do. No change.
109. **Gold's stop and its move's reference by period** (2026-11-25, a research round; `gold_recheck.py --stop`,
   `verification/zoo/stage108_gold_stop_reference.txt`). With the 14:15 exit, $ a year a contract, 2009-17 / 2018 -
   Mar 2025: the 60% stop $361 / $286; 70-80% $215-252 / $333-368; 40-50% $290-320 / $312-322: mixed, 60% stays. The
   move from the 13:30 bar's close: $374 / $351, but 13:20 and 13:40 are lower on 2009-17: a spike, under the bar for a
   change. No change.
110. **Gold and MNQ on the same day** (2026-11-25, a research round; `research/zoo/gold_mnq_same_day.py`,
   `verification/zoo/stage109_gold_mnq_same_day.txt`). Gold enters at 08:35, before MNQ, so no gold rule can use
   MNQ's day; the other way, MNQ's day (1 contract) after gold is stopped by 09:30 / still open: 2015-19 $30.6 / $22.8,
   2020-25 $14.6 / $59.3 (13 / 19 days open): opposite by period, too few days. The two days' $ barely move together
   (correlation 0.04 / 0.11); both lose on 22% / 26% of gold days, the worst such day -$582 a contract, inside the
   $600 day stop plus a gold loss. Nothing to use. Found on the way: gold wins only 9% of its trades (316 in 2009 -
   Mar 2025): losers $19.5 a contract on average (83% stopped by 09:30), winners $405. Now in "Running it" step 9.
111. **Gold in again after an early stop** (2026-11-25, a research round; `research/zoo/gold_reentry.py`,
   `verification/zoo/stage110_gold_reentry.txt`). Once, on the first close past the signal close by 09:00 / 09:30 /
   10:00, out at 14:15. With a stop past the extreme since the stop-out the re-entries make $131-277 a year a contract on
   2009-17 but -$33 to +$21 on 2018-25; with the first trade's stop the reverse (-$43 to -$67 / +$44 to +$105). Each
   version fails one period, and the worst gold day deepens (to -$156 to -$268). Rejected.
112. **The gold signal's shape** (2026-11-25, a research round; `research/zoo/gold_signal_shape.py`,
   `verification/zoo/stage111_gold_signal_shape.txt`). Known at the 08:30 close (the 08:35 open is the fill, so not a
   filter): the first 15 minutes' run against the overnight move, and the signal close in the 08:20-08:35 range. By
   terciles both flip between periods (the weakest run tercile PF 0.57 on 2009-17 is the best on 2018-25 at 5.59; the
   low close tercile 0.17 / 2.51), and each holds 1-7 winners. Nothing used.
113. **The band trades after the morning gap trade** (2026-11-25, a research round; `research/zoo/gap_won_add.py`,
   `verification/zoo/stage112_gap_won_add.txt`). Band trades the same way as a gap trade that won: PF 2.43 / 2.49
   (2015-19 / 2020-25) against 1.54 / 1.59 with no gap trade, but ES 1.09. One contract more on them: medians -$925 /
   +$96, inside a placebo's range. After a gap loss PF 1.03 / 1.36 (live 15.5 on 13 trades): no skip. Nothing used.
   The overnight range: section 177 (the NQ 1-minute data does hold the overnight hours).
114. **The opening volume** (2026-11-25, a research round; `research/zoo/open_volume.py`,
   `verification/zoo/stage113_open_volume.txt`). The 09:30-10:00 volume against its 14-session average for the band
   trades: no order that holds (the low tercile best on 2015-19 at PF 1.73, worst on 2020-25 at 1.39). The gap trade
   looks far better on high 09:30-10:00 volume (PF 3.97 / 2.27), but that is hindsight (the trade's own bars); with only
   the 09:30 bar's volume, known at entry, it is gone (over 1.2x 2.04 / 1.68 against 2.15 / 1.69). Nothing used.
115. **Out on a stretched day** (2026-11-25, a research round; `noise` exh_k, `research/zoo/exhaustion_exit.py`,
   `verification/zoo/stage114_exhaustion_exit.txt`). A band trade in profit closed once the day's range reaches 1.5 /
   1.75 / 2.0x its 14-session average: medians -$1,841 / -$1,365 / -$1,036 (2015-19) and -$551 / -$522 / -$225
   (2020-25); 2.5x and up never changes a trade. Stretched days keep running. Rejected.
116. **Checks that only manage the trade** (2026-11-25, a research round; `noise` exit_checks,
   `research/zoo/exit_checks.py`, `verification/zoo/stage115_exit_checks.txt`). The shipped checks run 10:00-15:00 every
   30 minutes; after 15:00 the stop holds to 15:55. Extra checks that move the stop and exit but never enter: after
   15:00 (15:15-15:45) almost no change; every 15 minutes from 12:00 / 10:00 medians -$302 / -$1,209 (2015-19) and -$319
   / -$889 (2020-25). Rejected (section 12 was entries and exits together).
117. **Out late without follow-through** (2026-11-25, a research round; `noise` late_flat / late_mode,
   `exit_checks.py --late`, `verification/zoo/stage116_late_flat.txt`). At 14:30 / 15:00 / 15:30, out if the trade is a
   small winner under the break-even distance, under it at all, or every trade. 15:00 small winners: 2015-19 +$158,
   2020-25 +$14 (p25 -$145), the window -$129; 15:30 every trade: 2020-25 +$924 but 2015-19 -$1,432; the rest lower on
   both. Rejected; 15:55 stays.
118. **The band on gap-trade days** (2026-11-25, a research round; `research/zoo/gap_day_band.py`,
   `verification/zoo/stage117_gap_day_band.txt`). The 10:00 entries on days the gap trade traded are the band's best
   (PF 2.34 / 3.00, ES 1.89), so no later first check. The later entries on those days are weaker in all three history
   sets (1.27 / 1.45 / ES 0.86 against 1.59 / 1.64 / 1.41) but pay on NQ and were live 2026's best (PF 18.3, 13 trades);
   dropping them: medians -$1,219 / -$4,101. Nothing used.
119. **An anchored VWAP for the stop** (2026-11-25, a research round; `noise` vwap_anchor, `exit_checks.py --anchor`,
   `verification/zoo/stage118_anchored_vwap.txt`). The VWAP from the entry / signal bar in place of the session's from
   09:30: medians -$5,932 / -$5,054 (2015-19), -$4,495 / -$3,946 (2020-25), the window $5,218 / $6,981 against $10,063:
   it starts at the entry price and stops the trades out early. Without the VWAP in the stop 7.3% of 2020-25 starts are
   lost. Rejected; the session VWAP stays.
120. **The band's losses by stretch** (2026-11-25, a research round; `research/zoo/stretch_losses.py`,
   `verification/zoo/stage119_stretch_losses.txt`). Analysis only. The deeper past the band, the bigger a loser (-$28 /
   -$41 under 0.25 sigma to -$141 / -$185 at 1.5-2.5, 14-17% at the full hard stop) but the more winners (70% / 78%)
   and $ a trade ($81 / $90): the extra contract's case (30). The shallow third ($2 / $8 a trade) is section 27's
   finding again (a minimum stretch cost the median). Past 2.5 sigma: opposite by period, 15 / 16 trades. Nothing new.
121. **What a normal bad run looks like** (2026-11-25, a research round; `research/zoo/bad_runs.py`,
   `verification/zoo/stage120_bad_runs.txt`). harness.account's loop with the path kept (checked to match it start by
   start), fresh 50K starts, 2015-19 / 2020-25 medians (worst): fall from the high $2,051 / $2,771 ($3,250 / $4,790),
   cushion low $1,175 / $1,245 ($804 / $500), losing days in a row 6 / 8 (8 / 10), trading days without a new high 21 /
   19 (62 / 32), worst day -$772 / -$912 (-$1,085 / -$1,107), worst 5 days -$1,882 / -$2,252 (-$2,597 / -$3,179). MNQ
   alone, no cushion guard (as every account figure here). Now "Running it" step 12.
122. **The bad run with gold** (2026-11-25, a research round; `bad_runs.py --gold`, `verification/zoo/stage120_bad_runs.txt`).
   MNQ + gold (gold as harness.account's extra leg, checked start by start): losing days in a row 7 / 9 (worst 7 / 12),
   days without a new high 24 / 20 (66 / 36), the deepest fall $2,051 / $2,875 ($3,289 / $4,832); the worst days as MNQ
   alone. Gold's frequent small losses lengthen the losing runs. Step 12 now covers both.
123. **The bad run with the cushion guard** (2026-11-25, a research round; `bad_runs.py --guard`,
   `verification/zoo/stage120_bad_runs.txt`). The shipped guard modelled ($1,500: 1 contract, a quarter-cushion day
   stop, no gold; $1,000: strong breaks and the gap trade only, section 50's exact method). It barely changes the bad
   runs: the closest approach to the floor $804 -> $648 (2015-19: one contract recovers more slowly, days without a new
   high median 21 -> 27) and $500 -> $672 (2020-25); falls, losing runs and worst days about the same. Step 12 corrected
   (it said live lows "a little shallower").
124. **How long the size steps take** (2026-11-25, a research round; `bad_runs.py`, `verification/zoo/stage120_bad_runs.txt`).
   Fresh 50K, the guard on, trading days to the first close at +$2,000 / +$3,500: 2015-19 median 93 / 150 (20% never
   reach +$3,500 in 12 months), 2020-25 48 / 82 (all reach both). With gold: 79 / 141 (4% never reach +$2,000, 16%
   never +$3,500) and 41 / 77. Without the guard: 70 / 107 and 42 / 75. A live expectation, now in step 12.
125. **Accounts starting near the floor** (2026-11-25, a research round; `bad_runs.py --guard --start`,
   `verification/zoo/stage120_bad_runs.txt`). From $48,806 / $48,998 against a $48,000 floor, the guard on, 2015-19 /
   2020-25: lost 0.0% / 1.8% and 0.0% / 0.0% (as section 50's calendar check); the guard off again after a median 50 /
   31 and 38 / 21 trading days; +$2,000 after 164 / 105 and 150 / 85 (2015-19: 22% / 18% never in 12 months); the
   closest calls $36-113 above the floor. Now in step 12.
126. **A stricter last tier under $1,000** (2026-11-25, a research round; `research/zoo/near_floor_tiers.py`,
   `verification/zoo/stage121_near_floor_tiers.txt`). MNQ alone, calendar and 2,000 shuffled years per period, from
   $50,000 / $48,806 / $48,998. No gap trade under $1,000: 2020-25 safer (from $48,806 shuffled 6.5% -> 3.1%) but
   2015-19 riskier (4.7% -> 5.5%), medians lower in both. The first trade a day only: the reverse (3.9% / 9.0%).
   Opposite by period: rejected; the shipped tier (strong breaks and the gap trade) stays.
127. **The guard's day stop share** (2026-11-25, a research round; `near_floor_tiers.py --share`,
   `verification/zoo/stage122_guard_day_stop_share.txt`). The first check of the share itself, with the strong-only tier
   in: 0.15-0.35 of the cushion move shuffled-year losses by 0.3 points at most; 0.3 / 0.35 lose 1 of 49 2015-19 calendar
   starts from $48,806 (none at 0.25); 0.15 / 0.2 cut the near-floor medians ($4,669 against $6,230 on 2015-19). 0.25
   stays (`GuardDayStopShare`).
128. **The guard's strong-break stretch** (2026-11-25, a research round; `near_floor_tiers.py --stretch`,
   `verification/zoo/stage123_guard_stretch.txt`). Under $1,000, strong breaks from 1.0-2.0 sigma (section 50 varied
   only the $ level): 1.0 / 1.25 riskier in both periods; 1.75 safer on 2015-19 (shuffled from $48,806 2.9% against
   4.7%) but riskier on 2020-25 (7.8% against 6.5%, calendar 5 of 55 lost); 2.0 the same 2020-25 risk at lower
   medians. 1.5 stays (`GuardStrongOnlyStretch`).
129. **The guard's levels by period** (2026-11-25, a research round; `near_floor_tiers.py --levels`,
   `verification/zoo/stage124_guard_levels.txt`). The guard from $1,250: more profit in both periods for up to 0.3
   points more shuffled risk (not taken: risk first); from $1,750 / $2,000: a little less risk for $370-1,130 less
   median. Strong only from $1,250: 2020-25 safer (6.5% -> 5.1%) but 1 of 49 2015-19 calendar starts lost from $48,806;
   from $750 riskier in both. $1,500 / $1,000 stay (`CushionGuard`, `GuardStrongOnlyBelow`).
130. **The extra contract and the news rule with the guard in** (2026-11-25, a research round; `near_floor_tiers.py
   --extras`, `verification/zoo/stage125_extras_with_guard.txt`). The extra contract from 1.25-2.0 sigma or off: shuffled
   risk flat, 1.5 at or near the best median in both periods. Without the mild-news skip 2015-19 calendar starts are
   lost 4.1% fresh and 14-16% near the floor: essential. No 6x contract: a little safer on 2020-25 only, lower medians
   in both. Skip 1.75-3x / 2-4x: opposite by period or lower medians. No change.
131. **The size steps with the guard in** (2026-11-25, a research round; `near_floor_tiers.py --steps`,
   `verification/zoo/stage126_steps_with_guard.txt`). Earlier steps (+$1,500 / +$3,000): more profit for a little more
   risk; later (+$2,500 / +$4,000): the reverse. 3 from +$3,000: the same shuffled risk, +$70-194 shuffled median, but
   lower calendar medians (as 103); 3 from +$4,500: lower medians. +$2,000 / +$3,500 stay.
132. **The day stop with the guard in** (2026-11-25, a research round; `near_floor_tiers.py --day-stop`,
   `verification/zoo/stage127_day_stop_with_guard.txt`). $400 / $500: lower medians in both periods at the same risk.
   $700 / $800: 2020-25 calendar higher (+$980 / +$1,455 fresh), 2015-19 lower (-$443 / -$274), a little more 2020-25
   shuffled risk (1.5% -> 1.7%), as section 54 found. $600 stays.
133. **Gold's effect on the risk, by period** (2026-11-25, a research round; `near_floor_tiers.py --gold`,
   `verification/zoo/stage128_gold_shuffled.txt`). Shuffled years with the guard, gold as it trades live (no news
   rule, none while guarded): lost 0.4% / 4.6% / 2.5% against 0.4% / 4.7% / 2.6% (2015-19, fresh / $48,806 / $48,998)
   and 1.4% / 6.3% / 3.6% against 1.5% / 6.5% / 3.7% (2020-25); medians +$246-356 and +$620-716. Gold lowers the risk a
   little and adds profit on both periods. (bad_runs.py --gold uses harness.account's convention, which applies the
   news rule to gold; noted.)
134. **Gold's size, by period** (2026-11-25, a research round; `near_floor_tiers.py --gold PATH --gold-size`,
   `verification/zoo/stage129_gold_size.txt`). Gold always 1 MGC: the same risk as the steps for less profit; always 2
   / 3: +$12-283 of median for up to 0.3 points more risk in most cells. Gold stays on the steps (1 / 2 / 3).
135. **Gold while guarded** (2026-11-25, a research round; `near_floor_tiers.py --gold PATH --gold-guarded`,
   `verification/zoo/stage130_gold_guarded.txt`). 1 MGC while guarded but not under $1,000: +0.1 points of risk on
   every 2015-19 cell, mixed on 2020-25, about the same median. 1 MGC at any cushion: riskier on both (from $48,806
   5.1% / 6.8% against 4.6% / 6.3%). Gold's frequent small losses hurt a cushion being rebuilt. No gold while guarded
   stays.
136. **"The result" verified on the final code** (2026-11-25, a research round; `research/zoo/verify_result.py`,
   `verification/zoo/stage131_verify_result.txt`). Every figure in "The result" (the pooled starts, both periods, the
   table, the years, the TradingView window +$10,063 / 50 trades / PF 4.66) reproduces exactly after sections 107-135's
   default-off research parameters.
137. **The gap trade's exit by period** (2026-11-25, a research round; `research/zoo/gap_exit_by_period.py`,
   `verification/zoo/stage132_gap_exit_by_period.txt`). Out at 09:45 / 09:50: lower everywhere. 10:00: 2020-25 up
   (+$137, the window +$289), 2015-19 down (-$1,294). 10:05: the gap trade alone better on both (PF 2.04 / 1.90) but the
   accounts worse (-$1,846 / -$2,962): it blocks the band's best entries, the 10:00 ones on gap days (118). 09:55 stays.
138. **One more contract on the gap trade** (2026-11-25, a research round; `near_floor_tiers.py --gap-add`,
   `verification/zoo/stage133_gap_add.txt`). Medians up in both periods (+$533 to +$1,263) for the same or slightly
   more risk (2015-19 fresh shuffled 0.4% -> 0.7%). Against 5 placebos (one more on random trades at the same rate): it
   beats every one on 2015-19 but sits inside their range on 2020-25. One period only; otherwise just more size.
   Not shipped. (Sections 87 / 88 / 98 already cover the gap minimum, the stop cap and the trades a day by period.)
139. **Break-even, the hard stop, the move cap and the range rule by period** (2026-11-25, a research round;
   `research/zoo/risk_settings_by_period.py`, `verification/zoo/stage134_risk_settings_by_period.txt`). Sections 63-65
   were pooled. By period: break-even 0.3R lower on both, 0.5R loses 7.3% of 2020-25 starts; $175 lower on both, $225
   loses 7.3%; cap 1.0 up on 2020-25's median only (the window -$3,071), 1.2 lower on both; range 0.6 / 0.7 lower medians
   on both. All stay. Every shipped setting now has a by-period check (the index under "The result").
140. **Two settings at once** (2026-11-25, a research round; `research/zoo/pair_grids.py`,
   `verification/zoo/stage135_pair_grids.txt`). 3 x 3 grids by period, the shipped cell in the middle: break-even
   0.35-0.45R x the hard stop $190-210 (the 0.45R row loses 7.3% of 2020-25 starts; 0.35R cuts 2015-19; no cell better on
   both); the target 2.25-2.75R x the second stop step 1.25-1.75R (the shipped cell the best on 2020-25; 2.75R better
   on 2015-19 only). No interaction the one-at-a-time checks missed. Both stay.
141. **Two more pairs** (2026-11-25, a research round; `pair_grids.py k_move / range_trend`,
   `verification/zoo/stage136_pair_grids_2.txt`). The band width 0.95-1.05 sigma x the move cap 1.0-1.2: the shipped
   cell has the best 2015-19 median and window (cap 1.0 better on 2020-25 only). The range rule 0.6-0.7 x the trend
   15-25 sessions: the shipped cell has the best median in both periods. Four pairs now checked; both stay.
142. **The gap trade's pairs** (2026-11-25, a research round; `pair_grids.py gap_cap / body_bar`,
   `verification/zoo/stage137_gap_pairs.txt`). The gap 0.55-0.65x x the stop cap 25-35: 0.65x lifts both medians
   (+$222 / +$281 at cap 30) but 2015-19's 25th percentile and the window slip and 0.7x is lower (87): a near-miss, not
   shipped. The body 2-4% x the wild open 1.5-2.0x: the shipped cell the best on 2015-19's median and 2020-25's 25th
   percentile. Six pairs checked; all stay.
143. **The 0.65x near-miss with the guard** (2026-11-25, a research round; `near_floor_tiers.py --gapk`,
   `verification/zoo/stage138_gapk_guarded.txt`). Shuffled years by period: 0.65x lowers 2020-25's risk (fresh 1.5% ->
   0.8%, from $48,806 6.5% -> 5.5%) and lifts its medians, but on 2015-19 the risk is the same and the medians lower
   (-$32 to -$451). One period only: closed, 0.6x stays.
144. **Gold's pairs** (2026-11-25, a research round; `gold_recheck.py --pairs`, `verification/zoo/stage139_gold_pairs.txt`).
   The move 1.35-1.65x x the stop 50-70%: 1.5x / 60% the best on 2009-17 ($361 a year a contract); 1.35x better on
   2018-25 only ($478-503 against $286; more in total over 2009-2025, almost all after 2018). The confirmation 10-20
   minutes x the exit 14:00-14:30: 15 / 14:15 the best on 2009-17, 14:00 +$21 on 2018-25. Both stay.
145. **Gold at 1.35x on the account** (2026-11-25, a research round; `near_floor_tiers.py --gold PATH --gold-k`,
   `verification/zoo/stage140_gold_k_account.txt`). With MNQ and the guard, shuffled years: both MNQ periods' medians up
   (+$149 to +$772) at about the same risk. By year, though, 1.35x beats 1.5x in only 5 of 17 years and is lower in 12
   (all of 2009-14); 2024 alone is +$927 of 2020-25's +$965. A gain carried by a year or two: not shipped, 1.5x stays.
146. **The near-misses by year** (2026-11-25, a research round; `research/zoo/near_miss_years.py`,
   `verification/zoo/stage141_near_miss_years.txt`). 1 contract, 2015-2026, against the shipped: the move cap 1.0 up in
   5 of 12 years (-$1,667 in all), the stop step from 1.75R 3 of 12 (-$590), the gap 0.65x 7 of 12 but by little (-$206),
   the trend 15 2 of 12 (-$1,887). Every one loses money in total: the rejections stand.
147. **The strategy year by year** (2026-11-25, a research round; `research/zoo/year_profile.py`,
   `verification/zoo/stage142_year_profile.txt`). At 1 contract the band made money every year 2015-2026; its weakest
   were 2017 (PF 1.20, the calmest year, day range 0.78%) and 2025 H1 (PF 1.16, the worst month on record, March 2025
   -$1,104). The gap trade lost only in 2025 H1 (PF 0.96, -$42). A usual worst month: -$300 to -$620 a contract (band).
   Now in step 12.
148. **March 2025, the worst month** (2026-11-25, a research round; `research/zoo/march_2025.py`,
   `verification/zoo/stage143_march_2025.txt`). 35 trades, -$808 at 1 contract: nearly all short with the falling
   market, stopped again and again (6 full $200 stops, up to 7 trades a day), 8 of 12 days lost, none past -$412. Strong
   breaks only after a stop fixes the month (+$7) but costs $16,750 over 2015-2026 (up in 1 of 12 years); at most 2
   losers a day makes it worse; 3 is noise (+$65 in 12 years). Nothing to change: this is the cost of the strategy.
149. **The band in calm and wild markets** (2026-11-25, a research round; `research/zoo/calm_band.py`,
   `verification/zoo/stage144_calm_band.txt`). By the band's width at 12:00 (terciles per period): calm PF 1.59 / 1.97,
   at the hard stop 1% / 3%; wild PF 1.47 / 1.26 with the most hard stops (9% / 12%) but still $22 / $14 a trade. Calm
   markets are not the weak spot (2017's weakness is that year's); wild ones pay least, and sizing down there was
   section 107's loss. Nothing to use.
150. **A wider hard stop on wild days only** (2026-11-25, a research round; `risk_settings_by_period.py --widen`,
   `verification/zoo/stage145_hard_widen.txt`). The hard stop at 0.25 / 0.3x the 14-day range, never under 100 points,
   at most 125 / 150: 2015-19's median up (+$905 to +$1,548) but every version loses 7.3% of 2020-25 starts (as $225 in
   139). Rejected; $200 stays.
151. **A tighter hard stop on calm days only** (2026-11-25, a research round; `risk_settings_by_period.py --tighten`,
   `verification/zoo/stage146_hard_tighten.txt`). 0.2 / 0.25x the 14-day range, at most 100 points, at least 75 / 85:
   both medians lower in every version (-$289 to -$2,020), the window lower; break-even and the target shrink with the
   stop and cut the winners. With 150: the flat $200 beats a scaled stop either way.
152. **A scaled stop alone** (2026-11-25, a research round; `noise` hard_stop_only, `risk_settings_by_period.py
   --stop-only`, `verification/zoo/stage147_stop_only_scaled.txt`). The hard stop at 0.2-0.3x the 14-day range within
   75-150 points, break-even / the target / the stop step kept on $200: no version loses a start in either period. The
   best, 0.25x within 75-150: medians +$1,109 / +$851, 25th percentiles -$30 / +$65, the window -$63; its neighbours
   mixed. A candidate: a grid around it, the years, shuffled years with the guard and the walk-forward come next.
153. **The scaled stop's grid and years** (2026-11-25, a research round; `research/zoo/stop_only_grid.py`,
   `verification/zoo/stage148_stop_only_grid.txt`, `stage148_stop_only_years.txt`, `stage149_stop_only_best_years.txt`).
   27 cells (0.2-0.3x, 70-80 / 140-160 points): none loses a start, 2015-19's median up in all, 2020-25's in 24; 0.3x
   within 70-150 raises all four numbers (medians +$747 / +$1,238). But by year it is up in only 5 of 12 (2022 alone
   +$1,795 of +$2,616; about +$75 a year otherwise), the window -$63. A one-year gain needing new order code: not
   shipped; the flat $200 stays, `hard_stop_only` documented (default off).
154. **The scaled stop with the guard** (2026-11-25, a research round; `near_floor_tiers.py --stopcell`,
   `verification/zoo/stage150_stopcell_guarded.txt`). Shuffled years by period: higher medians but more risk (2015-19
   fresh 0.4% -> 0.7%, from $48,806 4.7% -> 5.3%; 2020-25 fresh 1.5% -> 1.8%). With 153's years: closed, $200 stays.
155. **Long against short** (2026-11-25, a research round; `research/zoo/long_short.py`,
   `verification/zoo/stage151_long_short.txt`). The band's longs and shorts: PF 1.53 / 1.55 (2015-19), 1.77 / 1.54
   (2020-25), each up in 11 of 12 years; the trend filter puts it on the year's side (2022 the shorts' +$6,106, 2023 the
   longs' +$5,871). The gap trade pays both ways on NQ. Nothing to use.
156. **Ready for Monday Nov 30** (2026-11-25, a research round; `verification/zoo/stage152_nov30_readiness.txt`). The
   files sent on Nov 24 differ from the repo only in two header comments; every MNQ and gold default, the half-day
   13:10 and the history guard match step 11 and the Pine inputs. One stale text fixed: gold's description said
   "held to 13:30" (it exits at 14:15, as coded). No reinstall needed.
157. **The gap trade's sides by year** (2026-11-25, a research round; `research/zoo/gap_sides.py`,
   `verification/zoo/stage153_gap_sides.txt`). With / against the 20-session trend: opposite by period (PF 1.77 / 2.27
   on 2015-19, 1.81 / 1.59 on 2020-25), each up in 10 of 12 years at nearly equal totals; long / short up in 10 / 11 of
   12. Nothing to filter.
158. **The band by entry check, by year** (2026-11-25, a research round; `research/zoo/check_times.py`,
   `verification/zoo/stage154_check_times.txt`). Every check from 10:00 to 14:00 pays in both periods; the strongest
   10:00 and 13:30 (up in 11 of 12 years), the weakest 14:00 (PF 1.29 / 1.18, 6 of 12), still positive (and section 99
   found dropping it costs). Nothing to change.
159. **Missing bars in the data** (2026-11-25, a research round; `research/zoo/data_gaps.py`,
   `verification/zoo/stage155_data_gaps.txt`). 2015-19 and ES: none. 2020-25: 4 days, each a real exchange halt (the
   market-wide circuit breakers of March 9, 12, 16 and 18 2020, 15 minutes each); live 2026: 2026-10-30 lacks the
   14:55 bar. The strategy keys on bar times, and no trade on those days was mis-timed. The data is clean.
160. **Halts and missing bars live** (2026-11-25, a research round; `verification/zoo/stage156_live_halts.txt`, by
   reading MnqCleanBand.cs). Resting stops fill at the reopen (possible slippage); the 09:55 and 15:55 exits are "at or
   after", so a missing bar only delays them; a missing check bar skips that check, and because each check's sigma
   needs all 14 prior sessions, it stays off for 14 sessions (the research model does the same). Advice: reload the
   chart's history after a day with a feed drop or a halt (step 11). A code fix (10 of 14 sessions) noted, not made.
161. **Sigma from 10 of 14 sessions** (2026-11-25, a research round; `noise` sig_min,
   `verification/zoo/stage157_sigma_min_sessions.txt`). The fix for 160 measured: every set's trades identical (no day
   differs), so neutral on the backtests; live it keeps a check working after a missing bar. Gold has the same rule but
   reports it in its status. To be built into MnqCleanBand.cs and Pine with a missing-bar parity test.
162. **The missing-bar fix shipped** (2026-11-25, a research round; `verification/zoo/stage158_sigma_fix_shipped.txt`).
   `SigmaMinSessions` 10 (NinjaTrader; Pine "Sigma needs at least"): each check's sigma from the sessions that have
   that bar, at least 10 of the 14, so one missing bar (a halt, a feed drop) no longer turns a check off for 14
   sessions; an Output line names any check still off. Neutral on every backtest ("The result" exact); parity tests
   with a missing 10:00 bar for NinjaTrader and Pine.
163. **The other bars it needs, live** (2026-11-26, a research round; `verification/zoo/stage159_other_missing_bars.txt`,
   by reading MnqCleanBand.cs). A missing 09:30 bar makes the 09:35 open the day's open (the bands, the moves and the
   gap all measured wrong, silently; the gap trade itself skips): to fix (no trades that day). Missing news bars make
   the news rule "n/a" (trades normally): to add a warning. The trend and the average range use complete sessions
   only: safe. Monday Nov 30's prior close is Wednesday's, as in every backtest.
164. **A missing 09:30 bar: no trades that day** (2026-11-26, a research round;
   `verification/zoo/stage160_missing_open_bar.txt`). NinjaTrader and Pine: a session whose first bar is not 09:30
   places no trade and stays out of the history ("NO TRADING TODAY" on the dashboard, an Output line); an Output line
   also warns when an ETH chart's news bars are incomplete. No backtest can change (every day starts at 09:30); parity
   tests with the 09:30 bar removed.
165. **A normal week** (2026-11-26, a research round; `research/zoo/weekly_activity.py`,
   `verification/zoo/stage161_weekly_activity.txt`). About 4 trades on 2 of 5 days a week; only about half the weeks
   end up (52%; 45% live), the typical week small, the profit from fewer big weeks; live 2026 had 32% of weeks without
   a trade (7-8% in the history). Now in step 12.
166. **Gold after holidays** (2026-11-26, a research round; `mk_search.carry` ref_min,
   `verification/zoo/stage162_gold_holiday_windows.txt`). Gold's 14-session average needs every session's move, and 133
   holiday sessions lack the 08:20 or 13:25 bar, so gold sits out the 14 sessions after each (15% of sessions; live and
   the backtests agree, and the status line says so). Averaging over 10-12 of 14: 4-5 more trades a year that break
   even (2018-25 worse, 11 of 17 years down). Not shipped.
167. **The live order path** (2026-11-26, a research round; `verification/zoo/stage163_order_path.txt`). A cancelled or
   rejected stop and the target's OCO are covered by tests. Probed: a rejected entry is safe; a rejected 15:55 exit left
   the position open overnight (the "exiting" flag silences every later guard), and a partial entry whose rest never
   fills stopped the bot from trading again. Both to fix in the order handling, with tests.
168. **The order-path fixes** (2026-11-26, a research round; `verification/zoo/stage164_order_path_fixed.txt`).
   MnqCleanBand.cs: a refused exit is sent again at the next bar ("Exit retry"), so a refused 15:55 exit can no longer
   hold a position overnight; a part-filled entry's unfilled rest is cancelled, so the bot keeps trading. Tests for both
   on the NinjaTrader stand-in; no backtest trade changes.
169. **Gold's order path** (2026-11-26, a research round; `verification/zoo/stage165_gold_order_path.txt`). The same two
   gaps in MgcOvernightCarry.cs: a refused 14:15 exit held the position overnight (closed next day by its stop), and a
   part-filled entry's unfilled rest stopped all later gold trades. A refused entry is safe. To fix as in 168.
170. **Gold's order-path fixes** (2026-11-26, a research round; `verification/zoo/stage166_gold_order_fixes.txt`). As 168
   in MgcOvernightCarry.cs: a refused exit is sent again, a part-filled entry's rest is cancelled, now in both
   strategies even when the filled part is already out (most gold trades stop on their entry bar). Tests for both; no
   backtest trade changes.
171. **Restarts and reconnects with a trade open** (2026-11-26, a research round; `verification/zoo/stage167_reconnects.txt`,
   by reading the code). Both strategies start "wait until flat" and do not adopt the account's position, so after a
   restart or a long disconnect mid-trade the real position keeps its broker-side stop and target but gets no time
   exit from the strategy. Not testable here; a manual check added ("Running it" step 13).
172. **Pine's status table** (2026-11-26, a research round). Pine had no on-chart status; on a TradingView chart without
   extended hours its news rule is silently off (it trades the mild-news days NinjaTrader skips). Now a top-right table:
   Setup (OK / NOT READY / NO TRADING TODAY: no 09:30 bar), the news rule ("n/a - turn on extended hours"), any check
   that is off. No trade changes; a test reads the table. The TradingView section now says to turn on extended hours.
173. **TradingView against NinjaTrader: a checklist** (2026-11-26, a research round). Pine's costs checked ($0.62 a
   side, 1 tick of slippage on every fill: the research's figures). The six differences by design (extended hours, the
   target's first bar, size from the account vs the Strategy Tester, costs set in the Properties tab, the data at the
   roll, broker events) are now listed under "TradingView", so a mismatch can be told apart from a bug.
174. **The user's TradingView charts, trade by trade; the bands as level lines** (2026-11-26, a research round;
   `verification/zoo/stage168_tv_window_trades.txt`). The Pine script run on the live set (regular hours, as the user's
   chart) gives the same days, sides and exits as the user's TradingView charts for Oct 5 - Nov 20 (Oct 5's four longs,
   Oct 14's target, Oct 15-16, Oct 20, Oct 22, Oct 30, Nov 5, Nov 9's gap long, Nov 13, Nov 16, Nov 19-20); only the
   sizes differ, by the Strategy Tester's start (checklist item 3). The user's chart is regular hours ("news n/a"), so
   it trades two news days NinjaTrader skips: Oct 22 (+$1,001 at 3 contracts) and Nov 5 (+$1,496 at 3); Sep 16 (-$40)
   too. In this window the news rule would have given up about $2,450 at these sizes; it was chosen on 2015-2025 and
   kept (one window is not a test), but the TradingView number for this window is that much above what the live bot
   would have made. The plotted bands drew a diagonal from each day's 15:00 check to the next day's 10:00 check; now
   each check's level is held until the next check and the line breaks between sessions (display only, no trade
   changes; a test checks the held levels and the break).
175. **A live-against-backtest checker** (2026-11-26, a research round; `research/live_check.py`,
   `tests/test_live_check.py`, `verification/zoo/stage169_live_check.txt`). After a session, NinjaTrader's trade export
   is checked against the rules the strategies keep (entry names and times, at most 3 contracts, no loss past the hard
   stop + 4 points of slippage, out by 15:55 / 14:15 and never overnight, at most 9 trades, the $600 day stop, the exit
   names, the safety-net exits flagged), and with a 1-minute bars export each day is matched to the reference trade by
   trade, in points (side, entry bar, entry and exit prices, the exit; a mild-news day says so; each band trade's
   stretch shows whether the cushion guard would take it). The reference reproduces the Pine run's trades on the live
   set (Oct 16, Nov 13, Nov 20; Nov 5 a news day). A synthetic export tests it: a clean day matches at +0.00 points
   and is not flagged; a manual trade, a 120-point loss, a 15:58 exit and a news-day trade are flagged.
176. **The pre-open move and the band trades** (2026-11-26, a research round; `research/zoo/preopen_align.py`,
   `preopen_add.py`, `verification/zoo/stage170_preopen_move.txt`). The move from 08:29 to 09:29 (known before the
   open, every day, not only news days; section 14 traded it on news days). Band trades the move's way are better than
   those against it in both periods (PF 1.79 / 1.79 against 1.28 / 1.44; 9 of 11 years, not 2024 or 2025), but the
   trades against it still make money (+$4,382 / +$10,383 a contract), and in the live 2026 months the trades against
   it did better (14 trades). On the account with the guard: one more contract on the trades the move's way is no
   better than one more on random band trades at the same rate (shuffled-years medians $11,941 / $16,581 against
   placebos $11,648-12,258 / $16,010-16,575 from $50,000), with more accounts lost (0.4% to 0.8%, 1.5% to 2.4%): it
   is only more size. No band trade against the move lowers the median in both periods ($11,322 to $8,538, $15,582 to
   $11,622) and loses more of the near-floor calendar starts in 2020-25 (1.8% to 14.5%, 0% to 7.3%). Both rejected;
   nothing changes.
177. **The overnight range** (2026-11-26, a research round; `research/zoo/overnight_range.py`,
   `verification/zoo/stage171_overnight_range.txt`). Section 113 said the overnight range could not be tested; it can
   (the NQ 1-minute data holds 18:00-09:29, `zoo/overnight.py`). Band trades entering beyond the overnight high (a
   long) / low (a short) against inside it: PF 1.52 / 1.77 (2015-19), 1.64 / 1.55 (2020-25), ES 1.25 / 1.49; 90% of
   band trades are beyond, and the inside ones (83 / 109) are better in 5 of 11 years. The gap trade: 2.04 / 1.99,
   1.62 / 1.79. No side holds across the periods: nothing to filter or size on. Nothing changes.
178. **The wrong chart trades nothing** (2026-11-26, from the user's setup screenshots: MgcOvernightCarry added from
   Control Center > Strategies with Instrument MNQ DEC26, 1-minute bars, 5 days to load, Sim101, Highest end-of-day
   balance 0). Both strategies already did nothing on a non-5-minute chart, silently (the chart's "WRONG CHART" text
   was never drawn); neither checked the instrument, so the gold strategy on 5-minute MNQ would have traded MNQ (with
   gold's rules, beside MnqCleanBand on the same account). Now MnqCleanBand trades only MNQ and MgcOvernightCarry only
   MGC (not NQ / GC: 10x the risk a contract), on 5-minute bars; anything else trades nothing, prints "WRONG
   INSTRUMENT" / "WRONG CHART" once in the Output window and shows it on the chart. Tests: both strategies on the
   other's instrument, on the full-size contract and on 1-minute bars (no trades, one message), and on the right
   chart (trades). "Running it" step 4 and 9 now say to add each from its own chart and check the Data Series.
179. **A third guard tier deep near the floor** (2026-11-26, a research round; `research/zoo/deep_tier.py`,
   `verification/zoo/stage172_deep_tier.txt`). Under $500 above the floor one hard stop is 40% of what is left. Under
   $300 / $500 / $700: the gap trade only (a 30-point stop), or no trade at all; shuffled years from $50,000 /
   $48,500 / $48,806 / $48,998. The gap trade only under $500: lost 4.7% to 2.1% / 6.5% to 5.0% from $48,806
   (2015-19 / 2020-25) and 2.6% to 1.2% / 3.7% to 3.4% from $48,998, medians $487 / $598 and $293 / $91 lower; from
   $48,500 no better in 2020-25 (14.2% to 14.3%). No trade under the line loses nothing by construction, but only by
   parking the account: under $300 14% / 17% of the runs from $48,806 are parked within the year (against 4.7% /
   6.5% lost without the line), so most parked accounts would have climbed back; trading one again brings the risk
   back. Neither is a clear gain over the shipped two tiers (a smaller loss share for a lower median, mostly in
   2015-19); not shipped. A pause line stays the user's own decision (stop the strategy by hand under a level).

## The result (the shipped defaults, 2026-11-24, sections 1-90; research numbers, $0.62 a side)

| set | sessions | band trades (win, PF, net 1 MNQ) | gap trades (PF, net 1 MNQ) | days traded | 50K starts lost | median 12 months |
|---|---|---|---|---|---|---|
| dev NQ 2015-19 | 1,247 | 873 (42%, 1.54, $17,395) | 272 (2.01, $8,522) | 46% | 0 of 49 | $14,028 |
| unseen NQ 2020 - Jun 2025 | 1,367 | 1,091 (48%, 1.63, $31,425) | 306 (1.70, $8,675) | 46% | 0 of 55 | $18,980 |
| unseen ES 2020-24 (a cross-check) | 458 | 305 (24%, 1.27, $1,489) | 89 (0.71, -$462) | 46% | | |
| live MNQ Jun 29 - Nov 23 2026 | 104 | 53 (57%, 5.02, $5,555) | 18 (1.44, $353) | 30% | | |

The accounts: the news rule, the $600 day stop, 1 / 2 / 3 contracts from +$0 / +$2,000 / +$3,500 and one more on a
break 1.5 sigma past the band; the second stop step and the wild-open gap skip (61); the gap at least 0.6x (87). Pooled
104 fresh 50K starts, 12 months each: **none lost**, median **+$17,032**, 25th percentile +$12,433, 10th +$3,526, worst
+$1,404, best +$28,053; 79% reach +$10,000, 64% +$15,000, 30% +$20,000, 5% +$25,000; 41% of traded days green. A "win"
includes the break-even exits at +2 points. By period (68, 87): 2015-19 median $14,028, 25th percentile $5,324;
2020-25 median $18,980, 25th percentile $15,811.

By year, 1 contract, all trades (shipped now, section 87's table): 2015 $3,574, 2016 $6,361, 2017 $1,788, 2018 $7,762,
2019 $6,432, 2020 $6,498, 2021 $8,983, 2022 $10,585, 2023 $6,811, 2024 $6,540, 2025 H1 $682, 2026 $5,908. Before
sections 61 and 87 (the figures below were for those rules): 2015 $3,543, 2016 $6,251, 2017 $2,038, 2018 $7,140, 2019
$6,360, 2020 $5,398, 2021 $8,777, 2022 $11,240, 2023 $6,074, 2024 $5,933, 2025 H1 $395; live 2026 by month Jul -$257, Aug +$511, Sep +$885, Oct
+$1,997, Nov (to the 23rd) +$2,465. (No data here for Jul 2025 - Jun 2026.)

The user's TradingView window (Aug 27 - Nov 23 2026, a fresh 50K, `zoo/tv_window.py`): the reference +$9,796, 53
trades, PF 4.25, max drawdown $670 before section 61; now (61 and 87): +$10,063, 50 trades, PF 4.66, max drawdown $670. TradingView itself on the versions before: +$6,322 (section 27), +$6,345 (28),
+$9,186 (30); the reference's direction matched every time, its trade count runs higher.

**How sure is "none lost"?** (`verification/zoo/walkforward_dev_only.txt`) The protections were picked on dev and
unseen NQ together, so the 0 of 104 is partly in-sample. A walk-forward that picks on 2015-19 only loses on average
5.7% of the 2020-25 starts: the 2015-19 data cannot see the 2020 regime coming. The losses come from the $250 hard
stop, a late break-even and entries to 14:30, and every one-step change in sections 32-33 that loosens risk (a $225
stop, break-even 0.5, a band 0.9 or 1.1 sigma, the band from the open alone) loses 2.9-17% of starts. Expect a small
chance of losing a fresh account in a year like 2020, mostly in its first months; never loosen the risk settings.

**What was checked, and where (by period: 2015-19 and 2020-25 on their own; 2026-11-25).** Every shipped setting,
one step each way at least, the latest check first:

| setting (shipped) | by-period checks (earlier, pooled) |
|---|---|
| band width 1.0 sigma; noise lookback 14 sessions (sigma from at least 10 of them) | 101; 72 (162: neutral) |
| trend filter: close past the 20-session average | 100 (EMA 43, slope 81) |
| range rule 0.65; move cap 1.1 | 139 (65) |
| hard stop $200; break-even 0.4R to entry + 2 points | 139, 102 (63, 64) |
| second stop step 1.5R to entry + 0.5R | 90, 69 |
| target 2.5R | 105 (62) |
| last entry 14:00; at most 9 trades a day | 99; 98 |
| the stop moved to the band / session VWAP at the checks | 119, 74 (47) |
| checks every 30 minutes 10:00-15:00; out at 15:55 | 116, 117 (12, 40) |
| gap trade: gap 0.6x, body 3%, no wild open over 1.75x | 87, 89, 90 |
| gap trade: stop cap 30 points; out at 09:55 | 88; 137 (41) |
| size steps 1 / 2 / 3 from +$0 / +$2,000 / +$3,500 | 131, 103 |
| extra contract from 1.5 sigma; news 2-3x skip, 6x +1 | 130, 104 (67) |
| day stop $600 | 132 (54) |
| cushion guard $1,500, day stop share 0.25, strong only under $1,000 at 1.5 sigma | 129, 127, 128 (38, 50) |
| gold: move 1.5x, confirm 15 minutes, out 14:15 | 108 (39, 41) |
| gold: stop 60%, move from the 13:25 close | 109 (39) |
| gold: size on the steps; none while guarded; with MNQ | 134; 135; 133 |

**What it is not:** a trade-every-day strategy. It trades on about half of the sessions (a third live); the days it
skips are inside the noise band, against the 20-day trend or mild-news days, and every rule tried that trades them
loses accounts (sections 9, 19, 31, 33). ES is weaker than NQ (the gap trade and the strong-break contract lose there);
the bot trades MNQ.

## TradingView

`pine/mnq_clean_band.pine` is the same strategy for a TradingView MNQ 5-minute chart (add it, Strategy Tester for the
results). `tests/test_pine_clean.py` holds it to the same Python reference trade for trade on the Pine interpreter, with
one difference by design: Pine sets the take-profit from the fill price after the fill bar, so it works from the next
bar (NinjaTrader's bracket works from the fill bar). **Turn on extended hours** on the TradingView chart (the chart's settings > Symbol >
Session: Extended / ETH): the news rule reads the 08:20-08:30 bars, and without them it is off, so TradingView then
trades the mild-news days that NinjaTrader (on its ETH chart) skips, and the two disagree. The chart's top-right table
says "news n/a - turn on extended hours" when that is the case (section 172), and also shows "NOT READY" / "NO
TRADING TODAY: no 09:30 bar" and any check that is off, as NinjaTrader's dashboard does. The teal / maroon lines are
the bands: each check's level (10:00, 10:30, ... 15:00), held until the next check, with no line before 10:00.

**TradingView against NinjaTrader: what differs by design (section 173).** Check these before calling a mismatch a bug:
1. **Extended hours.** The TradingView chart needs extended hours (ETH) for the news rule, as NinjaTrader's chart does;
   without them TradingView trades the mild-news days NinjaTrader skips (its table says "news n/a"). In Aug 27 - Nov 23
   2026 that is Oct 22 and Nov 5, both winners (section 174): a regular-hours chart shows more than the live bot made.
2. **The take-profit's first bar.** Pine sets the target from the fill price after the fill bar, so it can only fill
   from the next bar; NinjaTrader's bracket works from the fill bar. A trade that hit +2.5R on its entry bar is a
   target in NinjaTrader and runs on in TradingView.
3. **Size.** TradingView sizes from its own Strategy Tester profit on a fresh $50,000 (inputs "Profit already made at
   the start $" and "Highest end-of-day balance"); NinjaTrader sizes from the live account. The same trade can be 1
   contract in one and 2-3 in the other, so compare points, not dollars, unless the inputs are set to the account.
4. **Costs.** Pine's defaults are $0.62 a contract a side and 1 tick of slippage on every fill (the research's
   figures). If the Strategy Tester's Properties tab shows other values, they were changed there.
5. **Data at the roll.** TradingView's continuous MNQ1! and NinjaTrader's dated contract (MNQ 12-26, then 03-27) differ
   by the roll gap around each roll (step 10); the bands (14 sessions back) can differ for up to 3 weeks after it.
6. **Fills NinjaTrader can see and TradingView cannot.** A refused or part-filled order (sections 168 / 170), a feed
   drop or a missing bar (160-164), a restart mid-trade (171): TradingView simulates clean fills on clean data.
Anything else (a trade on one side only on the same data, a different stop price) is worth sending me.

## Running it

NinjaTrader 8, on each funded account (both the same way):

1. **Turn off every other strategy on the account** (Control Center > Strategies tab: untick Enabled on MnqNoiseV38
   or anything else on that account). Two strategies on one account fight over the position.
2. **Install the file.** Copy `ninjatrader/Strategies/MnqCleanBand.cs` to
   `Documents\NinjaTrader 8\bin\Custom\Strategies\` (replace the old one). Open New > NinjaScript Editor, then press
   **F5** to compile; the bottom of the editor must show no errors. Close the editor.
3. **Open the chart.** New > Chart; instrument **MNQ** front month (MNQ 12-26 until the December roll); type
   **Minute**, value **5**; Trading hours **CME US Index Futures ETH** (the news rule reads the 08:30 bar); Load data
   based on **Days**, Days to load **40** or more. OK.
4. **Add the strategy.** Right-click the chart > Strategies > **MnqCleanBand** > Add. Set **Account** to the funded
   account. Leave every other setting at its default. Tick **Enabled**, then OK. Add it from the chart, not from Control Center >
   Strategies > New (there the Data Series must be set by hand: MNQ, Minute, 5, Days to load 40, and the chart's
   status box is not shown). On any other instrument or bar size it trades nothing and says WRONG INSTRUMENT / WRONG
   CHART (section 178).
5. **Check it.** The chart's top-right corner must say **Setup: OK**, the size (1 MNQ on a fresh account) and the
   news status. New > NinjaScript Output shows the settings line and every order. NOT READY: raise Days to load. NO
   TRADING: right-click the chart > Reload All Historical Data.
6. Leave NinjaTrader running through the session (09:30-16:00 New York); the strategy is flat by 15:55 every day.
7. **The cushion guard (section 38):** in group "7. Cushion guard" set "Highest end-of-day balance so far" to the
   highest end-of-day balance the prop firm's dashboard shows (0 if the account never closed a day above its start
   balance) and the trailing drawdown ($2,000 for the 50K); the same two numbers in MgcOvernightCarry (its group is "4.
   Cushion guard"). The chart then
   says CUSHION GUARD whenever the account is within $1,500 of its floor.
8. **Before Monday Nov 30** install this version: the older one would block that day (the holiday guard, section 27).
9. **Gold (optional, section 37):** copy `ninjatrader/Strategies/MgcOvernightCarry.cs` to the same folder, F5. Open an
   **MGC** 5-minute chart (front month, e.g. MGC 02-27; trading hours **CME/COMEX metals ETH**, the overnight session
   is needed), Days to load **30**. Right-click > Strategies > **MgcOvernightCarry** > the same funded account,
   defaults, Enabled. Check the Data Series is **MGC**, not MNQ (on MNQ it trades nothing and says WRONG
   INSTRUMENT, section 178), and set "Highest end-of-day balance so far" as step 7. The top-right corner says "waiting for history" until the first 08:30 check after loading, then
   OK once 14 complete sessions are loaded (NOT READY with fewer). It trades at most once a day
   (08:35 to 14:15) and sizes from the same account balance as MNQ. Expect most gold trades to lose: about 9 in 10 are
   stopped out within minutes of 08:35 for about $20 a contract (at most $141 in 2009 - Mar 2025), and the 1 in 10 that
   runs to 14:15 makes about $400 a contract (section 110). A run of 10-20 small gold losses is normal, not a fault.

10. **The contract roll (MNQ: Thursday Dec 10 2026, 8 days before the Dec 18 expiry; then every March, June, September
   and December the same way).** The strategy needs 21 or more complete sessions (every 5-minute bar 09:30-16:00) on
   the chart it trades, so on the new contract:
   - **Before the roll day:** Tools > Options > Market data > Merge policy **Merge back adjusted** (the research data is
     back-adjusted the same way), so the MNQ 03-27 chart carries the 12-26 history. With "Do not merge" the 03-27 chart
     holds only 03-27's own pre-roll bars, which can be thin; if a session misses any 5-minute bar it does not count,
     and the dashboard may say NOT READY or NO TRADING (this could not be checked here: no 03-27 pre-roll bars).
     Not **Merge not back adjusted**: it leaves the calendar spread (about 1%) as a price jump on the roll day, which
     the strategy reads as a real gap (a gap trade can fire, at most its 30-point stop) and which tilts the 20-session
     trend for weeks; safe (research/stress/torture.py's +8% / -7% gaps pass), but not the trades the research measured.
   - **After the close on Dec 9 (the strategy is flat by 15:55):** turn the strategy off, change the chart's instrument
     to **MNQ 03-27**, right-click > Reload All Historical Data, add the strategy again with the same settings (start
     balance, Highest end-of-day balance, Place orders), Enabled.
   - **Check:** the top-right corner must say OK, not NOT READY / NO TRADING, before 09:30 on Dec 10.
   - **Gold (MGC 02-27):** the same steps on its own rollover date, which NinjaTrader lists under Tools > Instruments >
     MGC > Rollovers (gold's active months are Feb / Apr / Jun / Aug / Oct / Dec).

11. **Before each week (Sunday evening; first: before Monday Nov 30 2026) and after any restart of NinjaTrader.**
   - NinjaTrader connected; Control Center > Strategies: MnqCleanBand (and MgcOvernightCarry, if used) **Enabled** on
     each funded account, nothing else enabled on those accounts.
   - **Highest end-of-day balance so far**: the prop firm dashboard's figure after Friday's close, entered in both
     strategies (MNQ group "7. Cushion guard", gold group "4. Cushion guard"); disable, change it, enable.
   - MNQ chart top-right: **Setup: OK** and the size you expect (CUSHION GUARD if within $1,500 of the floor).
     NOT READY: raise Days to load to 40+; NO TRADING: Reload All Historical Data.
   - The settings you rely on: Gap at least 0.6; Second stop step 1.5 / 0.5; Gap: no trade over 1.75; Place orders on.
   - Gold chart: "waiting for history" until Monday's 08:30 check is normal; it must then say OK (or NOT READY: raise
     Days to load to 30+).
   - Monday 09:35 / 10:00: the Output window shows the settings line and, if a trade fires, its order and stop.
   - After a day the data feed dropped or the market halted during the session (sections 160-162): after the close,
     right-click the MNQ chart > Reload All Historical Data, so the missing 5-minute bars are refilled. Since 162 one
     missing bar no longer turns a check off ("Sigma needs at least" 10 of 14), and the Output window says "check(s)
     ... off today" if several are missing.

12. **What a normal bad run looks like (sections 121-123).** In the history (fresh 50K accounts, 12 months each,
   2015-19 / 2020-25, MNQ alone and with gold, with and without the cushion guard, which changes these little):
   - a fall of about $2,000-2,900 from the highest balance at some point in a typical year, up to $3,250-4,830 in the
     worst start (the floor stops trailing at $50,000 once the account is $2,000 up, so these do not end it);
   - 6-8 losing trading days in a row in a typical year, up to 8-10 (with gold, whose small losses are frequent: 7-9,
     up to 12);
   - about 20-27 trading days without a new high in a typical year, up to 32-62 (with gold up to 69);
   - a worst day of about -$800 to -$900 (the $600 day stop is checked between trades, so a day can end past it), up to
     about -$1,100; the worst 5 trading days about -$1,900 to -$2,250, up to -$3,180;
   - in a typical year the balance came within about $1,200 of the floor at some point (as close as $500 without the
     guard, $648-672 with it).
   - the size steps take time (with the guard, about 21 trading days a month): +$2,000 (2 contracts, and the floor stops
     trailing at $50,000) after a median 48-93 trading days (2020-25 / 2015-19; 75% of starts within 86-145, the
     slowest 160-231); +$3,500 (3 contracts) after a median 82-150, and in 2015-19 20% of fresh years never got there
     in 12 months (16% with gold; with gold 4% of 2015-19 years also never reached +$2,000).
   - an account starting $800-1,000 above its floor (the user's two in November 2026; section 125), the guard on: the
     guard stays on for a median 21-50 trading days (2020-25 / 2015-19; the slowest 109-192, and 2% of 2020-25 starts
     from $800 above never got the cushion back to $1,500 in 12 months); +$2,000 after a median 85-164 trading days
     (18-22% of 2015-19 starts never got there in 12 months); in the history 1 of 55 starts from $800 above was lost
     (2020-25), none from $1,000 above, and the closest calls came within $36-113 of the floor and recovered.
   - the weakest years at 1 contract (section 147): a very quiet market (2017: the band PF 1.20) or a sharp choppy
     correction (March 2025: the band's worst month on record, -$1,104 a contract); a usual worst month -$300 to -$620
     a contract. Every year 2015-2026 still ended up at 1 contract.
   - a normal week (section 165): about 4 trades on 2 of the 5 days; only about half the weeks end up, and the year's
     profit comes from fewer, bigger weeks; a week without a trade happens (7-8% of weeks, 32% in the 2026 live months).
   None of those lost an account in the history. A run like this is not a fault; a run well past these is a reason to
   stop and check the setup (step 11) and the trades against TradingView.

13. **After a disconnect, a restart, or a disable / enable while a trade is open (section 171).** The strategies replay
   history and wait until flat (they do not take over a position already in the account). Compare Control Center >
   Positions (the account) with the Strategies tab (the strategy). If the account holds a position the strategy does not
   show, check its stop is working in Orders and close the position by hand before the session ends (MNQ by 15:55,
   gold by 14:15); the strategy will not send its time exit for it.

14. **After a session: check live against the backtest (section 175).** Control Center > New > Account Performance (the
   account, today, Generate) > Trades tab > right-click > Export, as a .csv. Then, from the repository folder:
   `python research/live_check.py trades.csv`. Each trade is listed with "CHECK:" under anything the strategy should
   not do (a manual trade, a loss past the stop, an exit after 15:55, a trade past the day stop, a safety-net exit).
   For the trade-by-trade match, also export the bars (Tools > Historical Data > Export: MNQ 12-26, 1 Minute, Last,
   the last 3 months) and add `--bars MNQ_12-26.Last.txt`. If NinjaTrader's time zone is not New York, add
   `--tz` and the zone (e.g. `--tz Europe/London`). Or send me the trades export (it holds the account number: send it
   in the chat, not to the repository).

Defaults: trend 20 sessions; hard stop $200 a contract; take profit 2.5 hard stops; break-even at 0.4 to entry + 2
points, and at 1.5 to entry + 0.5 hard stops (section 61); last entry 14:00 (840); at most 9 trades a day; day stop
$600; range rule 0.65; move cap 1.1; the gap trade every day (gap 0.6x, section 87; 09:30 bar 3% of the range and not over 1.75x
its usual size, stop at most 30 points); news days on (2-3x no trades, 6x a contract
more); 1 contract, 2 from +$2,000, 3 from +$3,500 over the $50,000 start balance, one more on a break 1.5 sigma past
the band, never more than 3 ("Most contracts"; "Fixed contracts" overrides all of it). Live it sizes from the
account's net liquidation; an account below $50,000 trades 1 contract until it is back above.

Live safety (tests/test_ninjatrader_clean.py): a stop the broker cancels or rejects while the position is open closes it
at market ("No stop"); no entries while the chart's last 14 sessions leave out more than 5 weekdays (a hole in the
history, as NinjaTrader's Oct 19 - Nov 6 2026 gap; holidays and half days leave at most 4; the Output window says to
reload the data); NinjaTrader's exit on session close as a backstop (half days, e.g. Nov 27 2026, close at 13:15
before the 15:55 exit). The no-stop exit waits out the race where a target's OCO cancel of the stop arrives before the
position shows flat (closes at the bar's close, or live 2 s later, only if still open and no stop is back), so a
target never closes twice. The chart shows Setup: OK / NOT READY (too few sessions loaded) / NO TRADING (a hole), the
size, the gap trade, the news status and today's P/L.
