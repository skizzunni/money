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
