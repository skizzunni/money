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
   and not certain, but on the user's first goal (not losing the account) better everywhere it was measured. Shipped:
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

## The result (the shipped defaults, 2026-11-24, sections 1-33; research numbers, $0.62 a side)

| set | sessions | band trades (win, PF, net 1 MNQ) | gap trades (PF, net 1 MNQ) | days traded | 50K starts lost | median 12 months |
|---|---|---|---|---|---|---|
| dev NQ 2015-19 | 1,247 | 868 (42%, 1.55, $17,512) | 318 (1.75, $7,819) | 48% | 0 of 49 | $13,058 |
| unseen NQ 2020 - Jun 2025 | 1,367 | 1,081 (48%, 1.61, $29,970) | 354 (1.54, $7,848) | 48% | 0 of 55 | $17,530 |
| unseen ES 2020-24 (a cross-check) | 458 | 305 (24%, 1.27, $1,489) | 102 (0.86, -$255) | 48% | | |
| live MNQ Jun 29 - Nov 23 2026 | 104 | 52 (56%, 4.95, $5,457) | 22 (1.14, $144) | 33% | | |

The accounts: the news rule, the $600 day stop, 1 / 2 / 3 contracts from +$0 / +$2,000 / +$3,500 and one more on a
break 1.5 sigma past the band. Pooled 104 fresh 50K starts, 12 months each: **none lost**, median **+$16,582**, 25th
percentile +$11,321, 10th +$4,672, worst +$1,789, best +$30,355; 79% reach +$10,000, 57% +$15,000, 29% +$20,000, 9%
+$25,000; 40% of traded days green. A "win" includes the break-even exits at +2 points.

By year, 1 contract, all trades: 2015 $3,543, 2016 $6,251, 2017 $2,038, 2018 $7,140, 2019 $6,360, 2020 $5,398, 2021
$8,777, 2022 $11,240, 2023 $6,074, 2024 $5,933, 2025 H1 $395; live 2026 by month Jul -$257, Aug +$511, Sep +$885, Oct
+$1,997, Nov (to the 23rd) +$2,465. (No data here for Jul 2025 - Jun 2026.)

The user's TradingView window (Aug 27 - Nov 23 2026, a fresh 50K, `zoo/tv_window.py`): the reference +$9,796, 53
trades, PF 4.25, max drawdown $670 (with section 61: +$9,921, 52 trades, PF 4.43; the 104 starts' median $16,931, 25th
percentile $12,040). TradingView itself on the versions before: +$6,322 (section 27), +$6,345 (28),
+$9,186 (30); the reference's direction matched every time, its trade count runs higher.

**How sure is "none lost"?** (`verification/zoo/walkforward_dev_only.txt`) The protections were picked on dev and
unseen NQ together, so the 0 of 104 is partly in-sample. A walk-forward that picks on 2015-19 only loses on average
5.7% of the 2020-25 starts: the 2015-19 data cannot see the 2020 regime coming. The losses come from the $250 hard
stop, a late break-even and entries to 14:30, and every one-step change in sections 32-33 that loosens risk (a $225
stop, break-even 0.5, a band 0.9 or 1.1 sigma, the band from the open alone) loses 2.9-17% of starts. Expect a small
chance of losing a fresh account in a year like 2020, mostly in its first months; never loosen the risk settings.

**What it is not:** a trade-every-day strategy. It trades on about half of the sessions (a third live); the days it
skips are inside the noise band, against the 20-day trend or mild-news days, and every rule tried that trades them
loses accounts (sections 9, 19, 31, 33). ES is weaker than NQ (the gap trade and the strong-break contract lose there);
the bot trades MNQ.

## TradingView

`pine/mnq_clean_band.pine` is the same strategy for a TradingView MNQ 5-minute chart (add it, Strategy Tester for the
results). `tests/test_pine_clean.py` holds it to the same Python reference trade for trade on the Pine interpreter, with
one difference by design: Pine sets the take-profit from the fill price after the fill bar, so it works from the next
bar (NinjaTrader's bracket works from the fill bar).

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
   account. Leave every other setting at its default. Tick **Enabled**, then OK.
5. **Check it.** The chart's top-right corner must say **Setup: OK**, the size (1 MNQ on a fresh account) and the
   news status. New > NinjaScript Output shows the settings line and every order. NOT READY: raise Days to load. NO
   TRADING: right-click the chart > Reload All Historical Data.
6. Leave NinjaTrader running through the session (09:30-16:00 New York); the strategy is flat by 15:55 every day.
7. **The cushion guard (section 38):** in group "7. Cushion guard" set "Highest end-of-day balance so far" to the
   highest end-of-day balance the prop firm's dashboard shows (0 if the account never closed a day above its start
   balance) and the trailing drawdown ($2,000 for the 50K); the same two numbers in MgcOvernightCarry. The chart then
   says CUSHION GUARD whenever the account is within $1,500 of its floor.
8. **Before Monday Nov 30** install this version: the older one would block that day (the holiday guard, section 27).
9. **Gold (optional, section 37):** copy `ninjatrader/Strategies/MgcOvernightCarry.cs` to the same folder, F5. Open an
   **MGC** 5-minute chart (front month, e.g. MGC 02-27; trading hours **CME/COMEX metals ETH**, the overnight session
   is needed), Days to load **30**. Right-click > Strategies > **MgcOvernightCarry** > the same funded account,
   defaults, Enabled. The top-right corner says OK once 14 complete sessions are loaded. It trades at most once a day
   (08:35 to 14:15) and sizes from the same account balance as MNQ.

Defaults: trend 20 sessions; hard stop $200 a contract; take profit 2.5 hard stops; break-even at 0.4 to entry + 2
points, and at 1.5 to entry + 0.5 hard stops (section 61); last entry 14:00 (840); at most 9 trades a day; day stop
$600; range rule 0.65; move cap 1.1; the gap trade every day (gap 0.5x, 09:30 bar 3% of the range and not over 1.75x
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
