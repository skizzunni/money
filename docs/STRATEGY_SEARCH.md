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
3. Open an **MNQ 5-minute** chart (the front month; **CME US Index Futures ETH**, so the news rule sees the 08:30 bar)
   with **Days to load: 40** or more
   (Data Series window). It needs 21 complete sessions to start.
4. Strategies tab, add **MnqCleanBand**, account = the funded account, keep the defaults, **Enabled**. The chart's
   top-right corner must say **Setup: OK**. The Output window prints the settings and every order.

Defaults: trend 20 sessions, hard stop $200 a contract, break-even at 0.4, take profit at 2.5 hard stops, last entry
14:00 (840), up to 9 trades a day, day stop $600, the gap trade from the first day, at most 3 contracts (2 from +$2,000, 3 from
+$4,500 (+$3,500 since section 32) over the $50,000 start balance; live it sizes from the account's net liquidation). An account below $50,000
trades 1 contract until it is back above.

Live safety (tests/test_ninjatrader_clean.py): a stop the broker cancels or rejects while the position is open closes it
at market ("No stop"); no entries while the chart's last 14 sessions leave out more than 5 weekdays (a hole in the
history, as NinjaTrader's Oct 19 - Nov 6 2026 gap; holidays and half days leave at most 4; the Output window says to
reload the data); NinjaTrader's exit on session close
as a backstop (half days, e.g. Nov 27 2026, close at 13:15 before the 15:55 exit). The no-stop exit waits out the
race where a target's OCO cancel of the stop arrives before the position shows flat (closes at the bar's close, or live
2 s later, only if still open and no stop is back), so a target never closes twice. The chart shows Setup: OK / NOT READY
(too few sessions loaded) / NO TRADING (a hole), the size, the gap leg and today's P/L.
