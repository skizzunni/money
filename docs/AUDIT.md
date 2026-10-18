# Audit of the NinjaTrader strategy (October 18, 2026)

The brief: better profit after costs, smaller drawdowns, less damage from losing trades; code repairs kept apart
from trading experiments; no claim without a test. This file records each stage, what was verified and how, and
what is still open. Results of the trading experiments are in [RESULTS.md](RESULTS.md) (round 137 on).

## Stage 1: the baseline

**Source of the run**: commit `d4cb597` (both files unchanged since then until the repairs below), kept as
[`baseline/MnqNoiseMomentum.d4cb597.cs.txt`](baseline/MnqNoiseMomentum.d4cb597.cs.txt) and
[`baseline/MnqNoiseEngine.d4cb597.cs.txt`](baseline/MnqNoiseEngine.d4cb597.cs.txt). The export:
[`data/nt_strategy_analyzer_2026-08-18_10-17.csv`](../data/nt_strategy_analyzer_2026-08-18_10-17.csv).

Every figure of the brief recomputed from the export (`research/nt_run_check.py` and the commands in this audit):

| Measurement | Brief | Recomputed |
|---|---:|---:|
| Period | Sep 8 - Oct 16, 2026 | first entry 9/8 09:32, last exit 10/16 13:34 |
| Trades | 70 | 70 |
| Net after commissions | $9,276.20 | $9,276.20 |
| Commissions | $497.80 | $497.80 |
| Momentum (bot) trades | 51, +$9,934.40 | 51, +$9,934.40 |
| Breakout ("W") trades | 19, -$658.20 | 19, -$658.20 (shorts 8, -$2,346.60, 7 losers; longs 11, +$1,688.40) |
| Max drawdown, closed trades | $3,750.50 | $3,750.50: $7,883.70 after #33 to $4,133.20 after #58 |
| Longest losing streak | 10 | 10 |
| Losing days | 13 of 23 | 13 of 23 (worst -$927.60, Oct 5) |
| Small bot winners | 16, +$180.40, MFE $6,296 | 16, +$180.40, MFE $6,296; #50: MFE $738, +$10.40 |
| 5 largest winners | $8,680 | $8,680 (93.6% of net) |

**Reproducing the run from market data: blocked.** It needs the same 1-minute MNQ DEC26 bars NinjaTrader used
(Tools -> Historical Data -> Export, Minute, 18 Aug - 17 Oct). Yahoo refused this environment (HTTP 429) and keeps
only ~30 days of 1-minute bars, which with the 14-session warm-up would not reach back to 8 Sep. With the export, the
strategy's own C# code runs on those bars in the stand-in (`ninjatrader/tests/Sim`) and each trade is compared.

## Stage 2: dependencies, settings, data

| Item | Value | Source |
|---|---|---|
| Strategy files | `Strategies/MnqNoiseMomentum.cs` + `AddOns/MnqNoiseEngine.cs` (`NoiseEngine`, `WilliamsBreakout`, `NoiseSettings`) | the repository; both sent to the user at 01:32 ET |
| NinjaTrader version | **unknown** | needed from the user (Help -> About) |
| Instrument | MNQ DEC26, one contract, not a continuous series | Strategy Analyzer screenshot |
| Bars | 1 minute, price based on Last, 08/18/2026 - 10/17/2026 | screenshot |
| Trading hours | `<Use instrument settings>` (normally CME US Index Futures ETH) | screenshot; exact template unknown |
| Platform time zone | Eastern, by inference (entries at 10:01, 10:31 after the 10:00, 10:30 checks) | export |
| Calculate | On bar close, by inference (the strategy refuses to trade otherwise and it traded) | code + export |
| Fill resolution / limit on touch | Standard (Fastest) / on | screenshot |
| Slippage / commission | 1 tick / "NinjaTrader Brokerage" template: $1.90 a contract a round trip | screenshot; $7.60 per 4 MNQ in the export |
| Roll / adjustment | none (a single contract) | screenshot |
| Account mode | evaluation: the account is "Backtest", not APEX-.../PA-APEX-..., so the FUNDED switch (off) decides | code + export (4 MNQ, 3-loser settings) |
| Evaluation target / payout stop | inactive: both work live only (`EvalTargetOn`, `PayoutStopOn` need State.Realtime) | code |
| Warm-up | 14 full sessions (Aug 18 - Sep 4; Labor Day Sep 7 is a skip date), first trade Sep 8 | code + export |
| Skip dates | `NoiseEngine.SkipDatesDefault`: exchange holidays and half days 2026-27 (Sep 7 in the window) | code |
| Fed dates | `FedDatesDefault`: scheduled FOMC days, no shorts before 14:00 (Sep 16 in the window) | code |
| Strategy parameters | the defaults shown: evaluation 4 MNQ, $200, 3 losers; breakout K 0.5, stop 0.25 x range, risk $400 (eval) / $200 (funded), max 10, take-profit 8 stops; place orders on | screenshot |

## Stage 3: execution correctness

| # | Concern | Finding | Class | Evidence / repair |
|---|---|---|---|---|
| 1 | Model vs actual trades | The engine's position, `DayPnl` and `LosersToday` come from its own model fills (bar close + 1 tick), not from NinjaTrader's executions. A rejected or blocked entry still counts as a trade in the model, and its loser count follows model P/L. | Confirmed from source | `MnqNoiseEngine.cs` `ClosePos` (`LosersToday++`); open: an execution ledger (stage 4) |
| 2 | Breakout loss limits | The breakout is not in the bot's loser limit (one a day of its own), so a day can lose 3 x ~$209 + ~$410 + fees. | Confirmed from source and the export | Oct 5: breakout -$298.80 + three bot stops = -$927.60 |
| 3 | Risk budgets | $200 a bot trade vs $400 a breakout trade in the evaluation (round 134); worst breakout loss -$409.50 vs bot -$209.60. | Confirmed from source and export | equal-risk comparison in stage 6 |
| 4 | Lock timing | The lock is detected at a bar's close (its high/low reached +25 points) and the new stop is sent then; it works from the next bar. A reversal inside the trigger minute is not protected by it. | Confirmed from source | `ManageOrders` (`realLocked` from High[0]/Low[0]) |
| 5 | Historical vs live | Evaluation target and payout stop are off in backtests; Strategy Analyzer results ignore them. | Confirmed from source | account rules replayed separately (`research/nt_run_check.py`, slot model) |
| 6 | Position mismatch | The guard blocked entries only from the second mismatched bar: an entry could go in on the first. | Confirmed from source; **repaired** (b222d44) | test: a foreign position on the very entry bar (bot and breakout) blocks it; mutation-checked |
| 7 | Rejected orders | A rejected stop sends the position to market once; if that exit was rejected too, only an alert, and the position could stay open without a stop. | Confirmed from source; **repaired** (6773767) | test: one and two rejected exits in a row, the exit is sent again each bar until flat; mutation-checked |
| 8 | Early closes | The strategy flattens at 16:00 or at the first bar outside 09:30-16:00; an early close with no bar after it left a position to the next bar. Known half days are skip dates (no entries). | Confirmed from source; **backstop added** (b222d44): NinjaTrader's exit 60 s before the session end | the backstop uses NinjaTrader's trading-hours template: **unverifiable here** (the stand-in has none); to check in Playback on a half day with the skip date removed |
| 9 | "Order placed" alerts | With orders on, every entry alert said "The strategy placed it", even when no order went out (guard, evaluation target reached, payout day). | Confirmed from source; **repaired** (b222d44) | alerts now say "sent" or "NOT sent" and why; test + mutation. Still model-based for fills: the fill is in NinjaTrader's Orders/Executions tabs |
| 10 | Stop loosening | The line stop is recomputed at each half hour from that check's 14-day average move, which can fall: the stop then moves back toward the price. Never past the $200 cap or the lock (both fixed from the fill). | Confirmed from source; measured: the line steps back in 28.8% of half-hour steps (median 6.9, 95th pct 26.7 points), 2011-26 | the tested model does the same, so the backtests include it; a tighten-only stop is an experiment, not a repair |
| 11 | Sizing vs base Qty | The bot's $ cap is computed from the base contracts (`MaxLoss / Qty`); with the bold finish (2.5x contracts, off by default) the stop stays in points, so the $ risk is 2.5x. | Confirmed from source; by design, off by default | keep off in research |

Not repaired, and why: 1 (needs an execution ledger, stage 4), 2 and 3 (trading-rule questions, stage 6), 4 and 10
(exit design, stages 7-8).

## Stage 4: execution ledger and a shared risk gate (not built yet)

What exists: the dashboard and alerts are driven by the strategy's model (concern 1); NinjaTrader's own Orders,
Executions and Strategy Performance tabs are the execution record. What a ledger would add, and why it is not built in
this pass: reconciling model vs fills needs NinjaTrader's execution events (`OnExecutionUpdate`, partial fills,
commissions), which the stand-in does not model, so it could not be tested here; an untested ledger is worse than
none. Specification for the next pass, from the brief: trades defined from flat to flat on executions; losers and
realized $ for the trading day (reset at 18:00 New York, kept in the payout-cycle file across restarts); one gate in
front of both entry paths (bot and breakout, reversals included) that checks actual losers today, realized loss +
open risk + risk reserved by working entries against a daily budget, the 10 MNQ limit and an unresolved
mismatch (repair 6 already blocks entries on a mismatch). Default off, then tested as a trading change (it changes
which trades happen).

## Stage 5: sizing

| Item | Finding | Class |
|---|---|---|
| MNQ point value / tick | read from the instrument (`Instrument.MasterInstrument.PointValue`, `TickSize`): $2 / 0.25 points ($0.50) | confirmed from source |
| Bot | fixed 4 MNQ; the $200 cap becomes 25 points (`MaxLoss / Qty / PointValue`), from the fill | confirmed |
| Breakout | contracts = floor(risk / (stop points x $2)), 1-10; **one contract is forced when it costs between 1x and 1.5x the budget** (only above 1.5x is the trade skipped) | confirmed from source (`MnqNoiseEngine.cs` 487-497 and `research/combo_more.py`); a trading-rule question, logged for a test |
| Costs in the budget | the budgets cover price risk only; fees ($1.90 a contract round trip here) and slippage come on top: worst bot loss in the export $209.60 on $200, worst breakout $409.50 on $400 | confirmed by the export |
| Adverse entry fill | the stop is placed in ticks from the actual fill, so the points at risk stay the same and the $ risk moves only with slippage on the stop | confirmed from source |
| Bold finish | contracts x2.5 with stops unchanged in points: $ risk x2.5; off by default and off in all research here | confirmed |

## Stage 9: intrabar behaviour and failure cases

| Case | Covered by | Mechanism |
|---|---|---|
| Lock trigger then reversal in the same minute | stand-in tests (the lock works from the next bar), research model the same | 1-minute bars, bar-close decisions |
| Stop and target in one bar | stand-in and research: the stop counts first (conservative) | 1-minute bars |
| Gap through a stop | stand-in: fills at the open less a tick | 1-minute bars |
| Partial entry fills / partial exits | **not tested** (the stand-in fills whole orders); NinjaTrader's `PerEntryExecution` attaches a stop and target to each part | needs Playback |
| Breakout-to-bot handoff, same and opposite direction | stand-in parity tests (`test_breakout_in_the_bots_gaps`) | 1-minute bars |
| Rejected protective order / rejected emergency exit | stand-in tests (repair 7) | injected rejections |
| Account / strategy disagreement | stand-in tests (repair 6) | injected foreign position |
| Connection loss / restart with a position | stand-in: restart mid-evaluation (target from the account), payout cycle across restarts; **not tested**: NinjaTrader's recalculation itself | needs Playback |
| Early close / daylight-saving change | early close: skip dates + backstop (repair 8, unverifiable here); DST: New York time from the platform's time zone, tested with bars stamped in London time | stand-in |
| Daily limits with orders pending | the loser limit is checked at the signal; entries are market orders (no resting entry orders) | confirmed from source |

The strategy needs `Calculate.OnBarClose`; it refuses to trade otherwise. NinjaTrader's Tick Replay and "High"
order-fill resolution change how historical fills are simulated inside a bar; neither was used in the user's run
(Standard fill resolution). None of the tests here establishes intrabar fill order: every result assumes the stop
first when a bar reaches both.

## Stage 11: validation, honestly

- No data before 16 October 2026 is untouched: 2011-18 was the development set; 2019-25, NQ 2015-24 and July 2025 -
  August 2026 have all been used by earlier rounds (135+ rounds in total; all are listed in RESULTS.md), and the
  user's September - October run has now been looked at. The only clean test is forward: weeks after 16 October 2026.
- The September - October run in numbers: 29 sessions, $320 a day ($1,599 a week). Resampling whole trading days
  (20,000 draws) gives a 90% range of **$93 to $3,250 a week**, and 3.7% of draws at or below zero. The 16-year
  average for the same settings is about $407 a week of trading P/L (before the account's rules): well inside that
  range. Six weeks cannot tell a better strategy from a good stretch.

## Stages 6-8: trading experiments (RESULTS.md rounds 137-138)

- **The breakout stays, with its shorts** (round 137): the account nets more with it in every period; dropping the
  shorts nets less in every period (the export's 8 shorts, 7 losers, were a small sample). Its $400 risk in the
  evaluation is mostly exposure: at the bot's $200 the return per unit of intraday drawdown is about the same.
- **The lock stays** (round 138): the export's giveback is the lock as designed. A 1R trail and half-at-1R both win
  slightly more often and both cut the big winners (net -29% to -50%); half at 1R lowers the intraday drawdown in every
  period for about a third less net.

## Stage 10: the account's rules, separately

The Strategy Analyzer does not apply the account's rules (target and payout stop act live only). They are replayed
on the trades in research: the export through the 50K intraday-trail evaluation (`research/nt_run_check.py`: passes 21
Sep from an 8 Sep start; 14 of 21 start days pass, 7 bust), and 16 years through evaluation and funded account
(`research/slot_size.py` and the rounds above: $2,000 drawdown trailing open-profit peaks, close at $3,000, 30 days;
funded: threshold stops at +$100, $1,000 daily loss tier, five $200 days, $52,600, 50% rule, caps; payout eligible,
asked for and left the account are separate events in the strategy since repair 128/132). The rules come from
third-party summaries of Apex's help center (its site is blocked here); the evaluation's lack of a daily loss limit
is quoted from Apex's own help center in search results.

## Stage 12: decisions

| Candidate | Decision | Why |
|---|---|---|
| Repairs 6, 7, 9 (guard from the first bar, exit retry, honest alerts) | **kept** | defects confirmed from source, each with a failing-then-passing test |
| Repair 8 (session-close backstop) | kept, **unverified** | NinjaTrader's trading-hours behaviour can't run here; check in Playback |
| Breakout (and its shorts) | **retain** | round 137 |
| Breakout at $400 vs $200 | retain $400 for the account; know it is exposure | rounds 134, 137 |
| Lock vs 1R trail | **reject** the trail | round 138 |
| Lock vs half at 1R | reject as the default; **an option** if lower drawdown matters more than profit | round 138 |
| Tighten-only stop (concern 10) | **adopted, built in** | round 139: more on the account in all four periods, drawdown slightly smaller in all four; parity-tested on and off |
| Breakout's forced 1-contract rule (stage 5) | **keep the rule** | round 139: skipping those trades nets less on the account in three periods |
| Execution ledger and shared gate (stage 4) | **build next**, test in Playback | needs NinjaTrader's execution events |
| 6 MNQ evaluation, funded breakout $300 | continue (round 133, 135 near-misses) | not the pre-registered picks |

**Forward test, defined before it starts**: the strategy on Sim101 with live data, orders on, from the first session
after it is installed, for 20 sessions or 60 trades, whichever is later. Each day: export the executions and the
1-minute bars; every trade re-run from those bars in the stand-in must match entry and exit within a tick and P/L
within fees, and every entry alert must match an order. **Stop at once** on: a position without a stop, an execution
the replay can't explain, a day losing more than $1,100, or a drawdown of $2,000 from the high (what would end an
evaluation). Judge the result against the bootstrap range above, not a single number.

## Still missing from the user (the minimum)

1. The 1-minute MNQ DEC26 bars of the run (Tools -> Historical Data -> Export) - to reproduce the run trade by trade.
2. NinjaTrader's version (Help -> About) and the chart's trading-hours template.
3. A Playback run with orders on - to check the backstop, partial fills and a restart on NinjaTrader itself.
