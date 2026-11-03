# MnqNoiseV38 — v3.8 for NinjaTrader 8

`ninjatrader/Strategies/MnqNoiseV38.cs` is one self-contained file: the rules and the orders together, with no
add-on to install. It trades `pine/mnq_noise_momentum.pine` v3.8 (docs/CANDIDATE_E50.md):
- 1 MNQ, $260 max loss per trade, take-profit 2 noise units;
- the stop moves with the line and never back toward the price; the lock at 0.35 max losses, to the entry + 2.5;
- $900 a day, with the stop cut to the room left rather than stopping;
- the filters: last entry 15:00, big day, calm stretch, range position, no shorts in the uptrend, Fed days and
  holidays;
- flat at 16:00.

## Verified

**The strategy's own code on the NinjaTrader simulator** (`ninjatrader/tests/Sim`) against the Python reference
(`mnqbot.noise` with v3.8's settings and NinjaTrader's execution):
- **The fixed MNQ sample** (`tests/test_ninjatrader_v38.py`): every trade identical on 5- and 30-minute bars.
- **The Jan 2025 – Oct 2026 stand-in** (`research/v38_ninjatrader_run.py`):
  - 30-minute bars: all 231 trades identical;
  - 5-minute bars: 257 of 258 identical. The other is March 9, 2026, where the data has missing bars and the session
    "ends early": Python closes at that bar's close, NinjaTrader at the next bar's open, $3.78 apart.
- **Existing tests:** the 135 earlier NinjaTrader tests still pass. It compiles as C# 5 with warnings as errors, as
  NinjaTrader 8 needs.

**The data used for the stand-in run:** where the data had no 16:00 bar (410 of 486 sessions), one was added at the
last price. On an ETH chart MNQ trades until 17:00, so NinjaTrader's 16:00 market exit fills there. Without it, those
trades were held to the next morning in the test, and one lost $897 on the overnight gap. On a real ETH chart this
cannot happen; on an RTH chart, "Exit on session close" (on) closes the position at the session's end.

## Results on the stand-in (`verification/noise_v2/v38_ninjatrader_*.csv`)

1 MNQ, $0.62 a side, 1 tick of slippage.

| Jan 2, 2025 – Oct 2026 | 30-minute bars | 5-minute bars |
|---|---|---|
| Trades | 231 | 258 |
| Net | **$9,242.74** | $7,895.02 |
| Winners | 56.7% | 64.7% |
| Profit factor | 1.877 | 1.837 |
| Closed drawdown | $1,323.20 | $1,232.98 |
| Largest loss | −$261.74 | −$261.74 |
| Worst day | −$414.98 | −$414.15 |
| Longest losing run | 5 | 5 |
| 50K evaluations ($3,000 target, $2,000 EOD trail) from every 5th session | 83.9% passed, **0 failed**, median 150 days | 82.8% passed, 0 failed |

The stand-in is NQ futures to Jul 2025, the Nasdaq-100 to Jun 2026, then the user's MNQ. A native NinjaTrader run on
real MNQ data will differ somewhat. The stand-in has flattered this strategy before.

## Install and run in NinjaTrader 8

1. Copy `MnqNoiseV38.cs` into `Documents\NinjaTrader 8\bin\Custom\Strategies\`.
2. Open **New → NinjaScript Editor** and press **F5** to compile. It should report no errors.
3. **Backtest:** **New → Strategy Analyzer**, Strategy **MnqNoiseV38**, with:
   - Instrument: **MNQ 12-26**. For history past the current contract, set Tools → Options → Data → Merge policy to
     "Merge back adjusted".
   - Data series: **Minute, 30**.
   - Trading hours: **CME US Index Futures ETH**.
   - Start date: **2024-09-01**. The filters need about 50 sessions of history before trading as tested; judge the
     results from 2025-01-02. End: today.
   - Slippage: **1**. Commission: a template of **$0.62 per side**.
   - Exit on session close: on.
4. **Live or sim account:** add it to a 30-minute MNQ chart (ETH), with Days to load 120 or more and Calculate On bar
   close. Then enable it. The dashboard is at the top right; the Output window logs each run's totals.

**Limits**
- **The daily $900 budget counts the strategy's own modelled P/L.** A live fill worse than the model can make a real
  day a little worse. The $100 below the $1,000 limit is that buffer.
- **The model and the account can disagree** after a rejected order or a broker-side fill that differs. If the account
  is in a position the model has closed, the strategy closes it at market ("Model flat"); it never holds a position the
  model doesn't manage.

## Funded growth mode (2026-10-31)

**The user's rule, clarified:** a trade may risk more than $300, as long as the day never reaches the $1,000 loss
limit and the account is never lost.

**Mode** (the first property): "Funded growth" (the default since 2026-10-31) applies the column below, "Evaluation" the
other; "Custom" uses the properties as set. The dashboard and the Output window show the first date of the data loaded:
results need about 50 sessions before the period judged.

The growth settings, as "Funded growth" sets them:

| Property | Evaluation (default) | Funded growth |
|---|---|---|
| Max loss per trade, $ | 260 | **187.5** (per contract; the position's grows with the contracts) |
| After a losing trade: max loss per trade, $ | 0 (the same) | **250** |
| Max loss a day, $ | 900 | **900** |
| Trailing drawdown (end of day, stops at the start), $ | 0 | **2000** |
| Trailing drawdown and contract steps from date | blank | **the funded account's first day** |
| Add a contract per $ of profit | 0 | **1500** |
| Most contracts | 15 | **15** |
| Size by the trade's own stop | off | **on** |

Each trade is sized to fit both today's room (the $900 less today's net loss) and the room above the trailing floor.
- **A single trade can lose more than $300.** That happens only on a day already up, so the day's net stays above
  −$900.
- **On the trailing floor:** the same settings never touched it on any data set or bar length (docs/V37_MAX.md).

**Verified:** the simulator against the Python reference, all 243 trades of the 30-minute stand-in window identical.
On 5-minute bars 275 of 276; the other is the same March 9 data gap. `tests/test_ninjatrader_v38.py` covers both
modes on the fixed MNQ sample.

**Results on the stand-in, Jan 2 2025 – Oct 2026, NinjaTrader execution, 1 tick, $0.62 a side:**

| | 30-minute bars | 5-minute bars |
|---|---|---|
| Net | **$26,672** | $18,275 |
| Trades / winners | 243 / 56.8% | 276 / 66.3% |
| Profit factor | 1.79 | 1.81 |
| Closed drawdown | $3,916 | $1,841 |
| Worst day | −$899 | −$899 |
| Largest single loss | −$1,634 | −$852 |
| Most contracts | 15 | 12 |
| Trailing floor touched | never | never |

**Over 10-16 years**, the worst day was −$899 to −$988 everywhere but one: −$1,023 on Dec 27, 2018 (30-minute NQ),
where price gapped past the stop. An $800 internal limit cut that, but on NQ the account then stalled near the floor.

**Expect from one account:**
- The fresh 21-month account replays (docs/V37_MAX.md) put a typical result at $20-27k.
- About 1 start in 4 reached $50k on NQ, and about 1 in 5 made almost nothing.

## How long one account takes to make $50,000 in funded growth mode (`research/growth_time_to_50k.py`)

Each run is a fresh account in funded growth mode ($900 a day, $2,000 trailing):
- it starts at 1 MNQ at a quarter start on NQ 2015-2025 and the Nasdaq-100 2011-2026;
- it runs to the end of the data, at least 3 years.

| | Starts | Reached $50k | Months to $50k: 25th / median / 75th | Within 21 months | Within 36 months |
|---|---|---|---|---|---|
| NQ, 5-min | 29 | 24 | 26.0 / 29.5 / 33.2 | 1 | 20 |
| Index, 5-min | 50 | 42 | 26.1 / 30.0 / 34.2 | 1 | 35 |
| NQ, 30-min | 29 | 22 | 17.0 / 22.0 / 25.5 | 10 | 22 |
| Index, 30-min | 50 | 41 | 22.9 / 27.9 / 36.5 | 6 | 29 |

**On one account, $50,000 typically takes about 2 to 2.5 years.** About 1 start in 5 never got there in the data.

## G2: growth mode with no take-profit (registered 2026-10-31, before its run)

**The variant:** funded growth mode exactly as above, except the take-profit is off. Winners exit only at the line
stop, the lock or 16:00.

**Adopt it only if all four hold:**
- 5-minute bars (the user's chart): net higher on NQ 2015-2025, on the index 2011-2026 and in the Jan 2025 – Oct 2026
  stand-in window;
- the trailing floor is never touched on any of them;
- no day reaches −$1,000 more often than with the take-profit;
- the same on 30-minute bars, reported.

**G2 result: rejected, the take-profit stays.** On 5-minute bars, without the take-profit:

| | With take-profit | Without |
|---|---|---|
| NQ | $269,579 | $225,665 |
| Index | $406,336 | $329,907 |
| Stand-in window | $18,473 | $14,384 |

It lost on all three. On 30-minute bars it was higher only on NQ ($238,996 against $207,740) and lower on the index
and in the window. The floor was never touched either way. The take-profit lets a trade's full size be re-used the same
day, which is worth more than the occasional bigger winner.

## G3: a per-trade risk cap in growth mode (registered 2026-10-31, before its run)

**The user wants the big wins without the big losses** (from v3.6's TradingView log at 15 MNQ: wins of
$2,296-3,116, losses of $1,117-1,818).

**The variant:** growth mode with a new research option, `trade_risk_cap`: no trade may risk more than this many
dollars. It is a third limit on the money budget, beside today's room and the trailing floor's, so it means fewer
contracts at the same stop distance.
- Caps tested: $400 and $600, against none (today's $900 at most).
- Reported on 5- and 30-minute bars, for NQ, the index and the window: net, PF, largest win, largest loss, worst day,
  closed drawdown and floor touches.

**Adopt a cap only if**, on 5-minute bars:
- its net is at least 90% of no cap's on all three sets; and
- its largest loss and closed drawdown are lower on all three.

**G3 result: not adopted as the default.** On 5-minute bars:

| | No cap | $600 cap | $400 cap |
|---|---|---|---|
| Window net / largest win / largest loss | $18,473 / $3,699 / −$853 | $13,844 / $2,774 / −$569 | $11,098 / $1,849 / −$399 |
| NQ net / largest loss / closed DD | $269,579 / −$3,776 / $17,027 | $164,295 / −$716 / $10,191 | $113,163 / −$412 / $5,911 |
| Index net / largest loss / closed DD | $406,336 / −$3,754 / $17,148 | $236,552 / −$701 / $9,139 | $161,914 / −$561 / $6,422 |

- **A cap cuts the big losses**, by 70-90% on the histories, and roughly halves the drawdown.
- **It cuts the big wins and the net just as hard.** The same contracts make both. A $600 cap keeps 58-75% of the net
  and $400 keeps 40-60%, against the 90% the rule required.
- **The winners are unchanged:** 64-66% at every cap. Profit factor falls slightly as the cap tightens.

It remains a choice for the user: the research option `trade_risk_cap` exists in the Python model. The NinjaTrader
strategy does not have it yet.

## Tracking (2026-10-31)

**The journal.** Every closed trade of the account, from NinjaTrader's own fills, goes into a CSV in
`Documents\NinjaTrader 8`. Each line has:
- the entry and exit time (New York), the side and the contracts;
- the trade number that day, the entry and exit price, how it ended, and the P/L;
- the day's P/L, the total, today's room left, the room above the trailing floor, and the next trade's contracts.

A DAY line closes each day with its trades and P/L.
- `MnqNoiseV38_backtest.csv`: written anew at each run, backtest or live.
- `MnqNoiseV38_live_<account>.csv`: live trades only, kept across restarts.
- A trade closed at a 09:30 open (a 16:00 exit on a chart without a 16:00 bar) is counted in the day before.

Tested (`tests/test_ninjatrader_v38.py`):
- one line per trade of the account, with the same P/L to the cent;
- every trade in exactly one day;
- the days adding up to the total;
- the dashboard drawn.

On the stand-in window this was checked for 326 trades (5-minute) and 289 trades (30-minute).

**The loss report.** `python research/journal_report.py <journal.csv>` prints:
- the results;
- every loss broken down by how it ended, side, entry hour and size;
- the 10 largest losses, with the day's P/L at the time;
- the streaks, the days and the months;
- three checks: the trades add up to the total, the days add up to the trades, and no day reached the $1,000 limit.

**Risk limits on the account's own numbers.** The $900 daily budget and the trailing floor use the worse of the
model's P/L and the account's real fills. A live fill worse than the model's can only make the next trade smaller.
With equal fills, as in the simulator, every trade is unchanged: all 243 and 231 30-minute window trades are identical
again.

**The dashboard** redraws at every bar close. It shows:
- the progress to the goal ($50,000 by default);
- the account's real P/L, total and today;
- the next trade's contracts and today's room;
- the mode, the first date of the data, the room above the trailing floor, the lines and the model's own totals.

## G4: partial profits in growth mode (registered 2026-10-31, before its run)

**The idea, from the user's Winter Trades screenshots:** "partial at the end of the move", "trading is all about
securing profits".

**The variant:** growth mode, plus a limit that closes part of the position at +X R. R is the trade's initial risk,
the bracket's stop distance (the model's `partial_at` with `partial_r` "initial", as the NinjaTrader strategy
measures it). The rest keeps every rule.

**Variants:**
- X = 1.0, half off;
- X = 1.5, half off;
- X = 1.0, a third off.

**Adopt a variant only if all hold:**
- on 5-minute bars it has a higher net than growth mode on NQ, the index and the window;
- it never touches the trailing floor;
- no day reaches −$1,000 more often.

**G4 result (run once, 2026-10-31): rejected.** Every partial variant made less on every data set, at both bar lengths.
The floor was never touched and the worst day did not change (−$1,023 on NQ, a gap, in every variant). Partials
trimmed the largest losses a little (the 30-minute window's −$853 became −$755) but cut the net by 22% to 58%:
the big winners pay for the strategy, and a partial takes half of each of them off at 1 R.

| Net | growth mode | half at 1 R | half at 1.5 R | a third at 1 R |
|---|---|---|---|---|
| 5 min, window | $18,473 | $10,154 | $13,188 | $14,394 |
| 5 min, NQ | $269,579 | $169,396 | $197,761 | $199,486 |
| 5 min, index | $406,336 | $272,120 | $300,844 | $314,658 |
| 30 min, window | $23,082 | $11,685 | $16,710 | $15,191 |
| 30 min, NQ | $207,740 | $86,724 | $142,853 | $147,438 |
| 30 min, index | $313,654 | $174,080 | $215,419 | $223,337 |

Growth mode stays as it is.

## G5: faster contract steps in growth mode (registered 2026-10-31, before its run)

**The idea:** growth mode adds a contract per $1,500 of profit, up to 15. The account grows faster if it adds them
sooner, as long as the $900 daily budget and the $2,000 trailing floor still size every trade (they do: a trade never
risks more than today's room or the room above the floor).

**Variants:** profit step $1,000 up to 15; $750 up to 15; $1,000 up to 20. Everything else is growth mode.

**Adopt a variant only if all hold:**
- on 5-minute bars it has a higher net than growth mode on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse than growth mode on any set.

If more than one passes, take the one with the highest 5-minute window net.

**G5 result (run once, 2026-10-31): rejected; faster steps lose the account.** With a $1,000 or $750 step the account
grows faster at first, then a run of losses at the larger size takes it all the way back to the floor (which stops at
the starting balance). There it can't size a trade, so it stops: net ≈ $0 after about 110 to 140 trades on NQ, at
both bar lengths, and on the index on 30-minute bars. In a prop account that is a lost account. The $1,500 step is
the fastest one that survives every history (`verification/noise_v2/g5_steps_growth.csv`).

| Net | $1,500 to 15 (growth mode) | $1,000 to 15 | $750 to 15 | $1,000 to 20 |
|---|---|---|---|---|
| 5 min, window | $18,473 | $20,202 | $17,525 | $20,215 |
| 5 min, NQ | $269,579 | **$0, back at the floor after 141 trades** | $286,839 | **$0, floor, 141 trades** |
| 5 min, index | $406,336 | $409,212 | $409,843 | $396,966 |
| 30 min, window | $23,082 | $27,397 | $29,066 | $27,966 |
| 30 min, NQ | $207,740 | **$4, floor, 114 trades** | **−$3, floor, 112 trades** | **$4, floor, 114 trades** |
| 30 min, index | $313,654 | **$7, floor, 63 trades** | **$1, floor, 60 trades** | **$7, floor, 63 trades** |

Growth mode stays at $1,500 a contract, up to 15.

## G6: a time stop in growth mode (registered 2026-10-31, before its run)

**The idea:** breakouts that work tend to work fast. The nineteenth round (docs/RESULTS.md) found that a 30-minute
time stop made the losses about 14% smaller at about the same profit, but that was on the old bot, at 1 contract,
with no lock and no take-profit. In growth mode, smaller losses could compound into more contracts sooner.

**The variant:** growth mode, plus a time stop (`time_stop` in mnqbot/noise.py). A trade that is not yet locked and
is losing at a bar close T minutes or more after its fill is closed at the next bar's open, as a market order sent at
that close would be. Everything else is unchanged.

**Variants:** T = 30 minutes and T = 60 minutes.

**Adopt a variant only if all hold:**
- on 5-minute bars it has a higher net than growth mode on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse than growth mode on any set.

If both pass, take the one with the higher 5-minute window net.

**G6 result (run once, 2026-10-31): the 60-minute time stop passes, and is now on in Funded growth mode.** On 5-minute
bars it made more on all three sets, the floor was never touched, and no day reached −$1,000 any more often. The
30-minute time stop failed (much less on the window). The gain is small, a few thousand dollars over ten years, and
the winners drop by about 4 points: some slow starters are cut before they work. In return, losers that drift
against you get cut instead of sitting there.

| Net | growth mode | time stop 30 min | time stop 60 min |
|---|---|---|---|
| 5 min, window | $18,473 | $13,161 | **$18,516** |
| 5 min, NQ | $269,579 | $256,086 | **$277,322** |
| 5 min, index | $406,336 | $378,497 | **$407,796** |
| 30 min, window | $23,082 | $22,966 | $25,834 |
| 30 min, NQ | $207,740 | $220,557 | $210,145 |
| 30 min, index | $313,654 | $314,582 | $301,828 |

**Checked again with NinjaTrader's own execution.** That means market exits at the next open and a bracket from the
fill. 16:00 bars were added where the history has none, so the 16:00 exit fills that day, as on an ETH chart:

| Net, NinjaTrader's execution | growth mode | time stop 60 min |
|---|---|---|
| 5 min, window | $18,283 | $18,549 |
| 5 min, NQ | $266,098 | $267,571 |
| 5 min, index | $398,911 | $404,250 |
| 30 min, window | $26,672 | $28,620 |
| 30 min, NQ | $252,213 | $257,756 |
| 30 min, index | $316,876 | $310,560 |

On those runs:
- the floor was never touched;
- the worst day was −$900 or better on every set;
- no day reached −$1,000.

All results are in `verification/noise_v2/g6_time_stop_growth.csv`.

**Implemented:**
- `time_stop` in mnqbot/noise.py.
- `TimeStop` in MnqNoiseV38.cs: 60 in Funded growth mode, 0 in Evaluation. NinjaTrader sends a market exit at the bar
  close ("Time stop"), so it fills at the next open.
- "Time stop" in the Pine script: 0 by default, because the evaluation hasn't been tested with it; set 60 for funded
  growth.

**Tests:**
- NinjaTrader's code matches the Python model trade for trade, with the time stop on, on 5 and 30 minutes.
- The Pine script matches the Python model trade for trade, alerts included.

**MnqNoiseV38.cs in Funded growth mode on the simulator, with the time stop, Jan 2025 to Oct 2026:**

| Bars | Before | Now | Trades | Winners | PF | Worst day | Matches the Python model |
|---|---|---|---|---|---|---|---|
| 30 min | $26,672 | **$28,620** | 252 | 53.6% | 1.88 | −$899 | every trade |
| 5 min | $18,275 | **$18,542** | 291 | 61.5% | 1.82 | −$899 | every trade but the Mar 9, 2026 data gap (above) |

The updated results are in `verification/noise_v2/v38_growth_ninjatrader_*.csv`.

## G7: the trend filter on both sides (registered 2026-10-31, before its run)

**The idea:** "trade with the bias" (the user's Winter Trades screenshots). Since v3.1 the bot takes no shorts while
yesterday's close is above its 50-session average. G7 adds the mirror: no new longs while yesterday's close is below
it (`trend_side` 0 in mnqbot/noise.py).

**Baseline:** growth mode as it now runs, with G6's 60-minute time stop.

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse than the baseline on any set.

**G7 result (run once, 2026-10-31): rejected.** Blocking longs below the 50-session average cut the net by about
half on every set, in both executions. The longs taken below the average make money on their own, so blocking them
only removes profit. The shorts-only filter stays.

| Net | baseline (no shorts in an uptrend) | both sides |
|---|---|---|
| 5 min, window (NinjaTrader) | $18,549 | $8,744 |
| 5 min, NQ (NinjaTrader) | $267,571 | $145,586 |
| 5 min, index (NinjaTrader) | $404,250 | $176,562 |
| 30 min, window (NinjaTrader) | $28,620 | $14,911 |
| 30 min, NQ (NinjaTrader) | $257,756 | $134,910 |
| 30 min, index (NinjaTrader) | $310,560 | $135,936 |

The chart's execution shows the same: on 30-minute bars the index even ran down to the floor and stopped
(`verification/noise_v2/g7_trend_both_growth.csv`).

## G8: entries at the 15:30 check too (registered 2026-10-31, before its run)

**The idea:** growth mode takes no new entries after the 15:00 check (`last_entry_end` 900, from v2.3). The
thirty-fourth round (docs/RESULTS.md) found the 15:30 entries paid about $23 a trade per contract on the old bot.
That was never checked with growth mode's sizing, lock, take-profit and time stop.

**The variant:** the last entry check is 15:30 (`last_entry_end` 930; "Last entry" 15:30 in MnqNoiseV38.cs).
Everything else is the baseline: growth mode with G6's time stop.

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse than the baseline on any set.

**G8 result (run once, 2026-10-31): rejected.** On the long histories the 15:30 entries change little: on 5-minute bars,
−$4k to +$2k on NQ and +$9k to +$10k on the index, over ten years. On the window, the period the account trades now, they lose:
−$5.2k on the chart's execution, −$6.3k on NinjaTrader's. Entries stay through 15:00.

| Net, 5 min | through 15:00 (now) | through 15:30 |
|---|---|---|
| window, chart / NinjaTrader | $18,516 / $18,549 | $13,319 / $12,280 |
| NQ, chart / NinjaTrader | $277,322 / $267,571 | $273,185 / $269,602 |
| index, chart / NinjaTrader | $407,796 / $404,250 | $417,836 / $412,826 |

On 30-minute bars it is mixed in the same way (`verification/noise_v2/g8_last_entry_growth.csv`). The floor was
never touched in any run.

## G9: a longer time stop (registered 2026-10-31, before its run)

**The idea:** G6 tried only 30 and 60 minutes. A longer limit cuts fewer slow starters and still closes the losers
that drift.

**Variants:** time stop 90 and 120 minutes, against the baseline's 60. Everything else is the baseline.

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the 60-minute time stop on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

This is a second look at a setting already chosen, so a variant must beat 60 on all six 5-minute runs. If both do,
take the one with the higher NinjaTrader window net.

**G9 result (run once, 2026-10-31): rejected; the time stop stays at 60 minutes.** A longer limit raises the winners
(about 61% to 63-65% on 5-minute bars) but makes less on NQ, by $6k to $15k over ten years. No variant beat 60 on all
six 5-minute runs.

| Net, 5 min (chart / NinjaTrader) | 60 min (now) | 90 min | 120 min |
|---|---|---|---|
| window | $18,516 / $18,549 | $18,113 / $16,325 | $18,463 / $18,578 |
| NQ | $277,322 / $267,571 | $261,951 / $259,244 | $261,149 / $260,613 |
| index | $407,796 / $404,250 | $397,711 / $392,367 | $412,677 / $403,429 |
| winners (NinjaTrader window) | 61.5% | 63.6% | 65.4% |

The floor was never touched in any run (`verification/noise_v2/g9_time_stop_long_growth.csv`).

## G10: more contracts once the day is green (registered 2026-11-01, before its run)

**The idea:** press when the day is working. Once today's closed P/L is above $0, the next entries take
`day_up_mult` times the contracts (the same stop distance), still no more than 15, and still sized down to today's
$900 room and the room above the floor. Tested on v2.8 (docs/RESULTS.md), where it made 2-17% more on the histories
at a deeper drawdown, but never in growth mode, where the room limits every trade.

**Variants:** `day_up_mult` 1.5 and 2.0, `day_up_from` $0. Everything else is the baseline (growth mode with G6's
60-minute time stop).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse than the baseline on any set.

If both pass, take the one with the higher NinjaTrader window net.

**G10 result (run once, 2026-11-01): rejected; it can lose the account early.** On 5-minute bars the window, which
starts the account at $0, went wrong at both sizes. The bigger trades after a green start lost back the early profit
before the floor had stopped at the starting balance. The account then sat at −$1,636, too close to the floor to size
a trade, after 49 trades. On a real account that is the end of it. On the ten-year histories, where the account is
already well above the floor when most of the pressing happens, it made more: +$15k to +$28k. On 30-minute bars,
2.0x ran NQ (chart execution) to the floor and stopped.

| Net, 5 min (chart / NinjaTrader) | baseline | 1.5x on a green day | 2x on a green day |
|---|---|---|---|
| window | $18,516 / $18,549 | **−$1,636 / −$1,636, stuck after 49 trades** | **−$1,636 / −$1,636, stuck** |
| NQ | $277,322 / $267,571 | $285,451 / $282,810 | $289,035 / $286,735 |
| index | $407,796 / $404,250 | $426,162 / $421,805 | $434,248 / $429,324 |

(`verification/noise_v2/g10_day_up_growth.csv`)

**What this says about bigger size in general.** G5 and G10 failed the same way. More size early, before the cushion
is built, can run a new account down to a floor that hasn't stopped yet. Any later idea that adds size has to be
safe from the first trade on.

## G11: more contracts on a green day, only once the floor has stopped (registered 2026-11-01, before its run)

**The idea:** G10's gain on the histories came once the account had a cushion. Its failure came on a new account,
before the floor had stopped at the starting balance. So press only after that: once the highest end-of-day equity
is $2,000 above the start, the floor is fixed at the starting balance for good (`day_up_locked` in
mnqbot/noise.py). Until then, growth mode as it is.

**Variants:** `day_up_mult` 1.5 and 2.0 once the day's closed P/L is above $0 and the floor has stopped. Still at
most 15 contracts, still sized down to today's $900 room and the room above the floor.

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse than the baseline on any set.

If both pass, take the one with the higher NinjaTrader window net.

**G11 result (run once, 2026-11-01): rejected.** Waiting for the floor to stop fixed the window: +$1.5k at 1.5x on
NinjaTrader's execution. It didn't save NQ on 5-minute bars. There the account reached $2,000 early, the floor
stopped at the starting balance, and the bigger trades gave everything back, down to the start (net $0 to $4 after
about 140 trades, both executions, both sizes). The room above a floor at the start is all of the account's profit,
and two or three bad weeks at double size used it up. On 30-minute bars and on the index it made a little more.

| Net, 5 min (chart / NinjaTrader) | baseline | 1.5x, floor stopped | 2x, floor stopped |
|---|---|---|---|
| window | $18,516 / $18,549 | $20,307 / $20,029 | $17,249 / $19,752 |
| NQ | $277,322 / $267,571 | **$0 / $4, back at the start after 140 trades** | **$1 / $1, back at the start** |
| index | $407,796 / $404,250 | $413,197 / $408,381 | $417,281 / $416,197 |

(`verification/noise_v2/g11_day_up_locked_growth.csv`)

**Sizing, so far:** G5, G10 and G11 all failed the same way. Growth mode's sizing is already about as large as one
account's $2,000 floor survives through a bad stretch.

## G12: the overnight "inflection", a sweep of the Asian range, then a reversal (registered 2026-11-02, before its run)

**The idea, from the user's two TikTok clips (an NQ trader).** About 02:30-03:00 New York time, price runs past the
overnight extreme and snaps back. They enter against the run with a stop a few points past the new extreme (4.25
points in one clip, 15 in the other), hold for hours, and make 135 times the risk on the day shown. It is a
reversal, the opposite of the bot's breakout, so it would be a second, separate setup. Close relatives tested before
(docs/RESULTS.md):
- flipping a failed breakout, rounds 19 and 94;
- the previous-day sweep, the pattern study;
- the bot's breakout logic overnight, round 23.

This exact version hasn't been tested: an overnight sweep of the Asian range with a tight stop at the sweep's
extreme and an all-day hold.

**Rules (1-minute bars, New York time):**
- **The Asian range:** the high and low from 18:00 the evening before to 02:59.
- **A long:** from 03:00 to 09:25, a 1-minute bar whose low goes below the Asian low, followed within 5 bars (that
  bar included) by a 1-minute close back above the Asian low. The first such sweep and close of the day counts.
  Enter at the next bar's open.
- **Its stop:** one tick below the lowest low from the sweeping bar to the close back above.
- **A short:** the mirror, at the Asian high.
- **Skips:** a trade whose stop is under 2 points or over 30 points from the entry.
- **One a day:** the first trigger, either side.
- **The exit:** the stop, or the 15:59 bar's close (flat by 16:00). No target, as in the clips.
- **Costs per MNQ:** $1.24 in fees, and 2 ticks of slippage on every fill (the overnight market is thinner); a stop
  that gaps fills at the bar's open.

**Pass (stage 1, the edge per contract):** daily P/L t-stat ≥ 2.24 on the index 2011-2018, then ≥ 1.65 on 2019-2022,
on 2023-Sep 2026, and on NQ futures 2015-2025. All four, run once. Only if it passes does stage 2 test it on the
account alongside the bot.

**G12 result (run once, 2026-11-02): rejected at stage 1; no edge.** The clips' days are real: the best trades made
123, 92, 69 and 64 times their risk. But about 95 trades in 100 are stopped out, often within minutes, and over the
years the big winners only about pay for them:

| Per MNQ | Trades | Winners | Stopped out | $ / trade | Average R | Best R | Daily t |
|---|---|---|---|---|---|---|---|
| index 2011-2018 | 1,478 | 4.3% | 95.7% | −$3.92 | −0.12 | 122.9 | −1.05 |
| index 2019-2022 | 574 | 5.9% | 93.9% | +$14.73 | +0.30 | 68.6 | 1.60 |
| index 2023-Sep 2026 | 593 | 3.9% | 96.1% | −$2.32 | +0.01 | 92.5 | −0.40 |
| NQ 2015-2025 | 1,820 | 5.5% | 94.5% | +$2.54 | +0.03 | 63.8 | 0.65 |

The pass bar was a t of 2.24, then 1.65 on each later set. It missed on all four: two sets lost money, and the two
that made money were not reliably different from zero. On the account it would also mean long losing streaks. At 95%
losers, 30 or more stop-outs in a row are routine, and a 1-in-20 winner can't be counted on before the floor.
(`verification/noise_v2/g12_overnight_inflection.csv`, `research/g12_overnight_inflection.py`)

## G13: a time lock (registered 2026-11-02, before its run)

**The idea:** the other half of G6's time stop. At 60 minutes a losing trade is closed. A trade that is up but hasn't
reached the lock's trigger keeps its full stop and can still turn into a full loss. The time lock locks it instead:
at a bar close T minutes or more after the fill, a trade not yet locked and in profit at that close gets the lock's
stop (the entry plus 2.5 points) from the next bar (`time_lock` in mnqbot/noise.py). If the price is already within
2.5 points of the entry, that stop is above it, so the trade closes at the next open ("Stop passed").

**Variants:** T = 60 (with the time stop, every trade still open at 60 minutes is then either closed or locked) and
T = 30. Baseline: growth mode with G6's 60-minute time stop.

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

If both pass, take the one with the higher NinjaTrader window net.

**G13 result (run once, 2026-11-02): rejected.** The time lock turns slow trades into small winners: up to 70.7% winners
at 30 minutes, against 61.5%. It cost money on the window at both times: −$2.0k at 60 minutes and −$3.5k at 30, on
NinjaTrader's execution. Some of the trades it locks would have gone on to the take-profit. At 60 minutes NQ and the
index were mixed (+$11k chart, −$0.3k NinjaTrader on NQ).

| Net, 5 min (chart / NinjaTrader) | baseline | time lock 30 min | time lock 60 min |
|---|---|---|---|
| window | $18,516 / $18,549 | $15,167 / $15,026 | $16,570 / $16,560 |
| NQ | $277,322 / $267,571 | $261,306 / $254,693 | $288,182 / $277,259 |
| index | $407,796 / $404,250 | $376,913 / $371,418 | $413,322 / $408,398 |
| winners (NinjaTrader window) | 61.5% | 70.7% | 65.7% |

(`verification/noise_v2/g13_time_lock_growth.csv`) A higher win rate is available this way, but it costs profit.

## G14: a liquidity sweep and an inversion fair value gap (registered 2026-11-02, before its run)

**The idea, from the user's six @jacotradez clips (transcribed).** Price takes out a "liquidity pool", a prior
high or low. They enter when a 1-minute fair value gap left by the sweep is "inverted": price closes back through it.
The target is the opposite liquidity. They trade mostly the evening (Asian) session. Their big days are one trade
copied to 20-28 prop accounts, about $250-$2,000 a day per account. G12 tested a sweep with a plain reversal and no
target; G14 adds their confirmation and a target.

**Rules (1-minute bars, New York time):**
- **The liquidity:** the previous regular session's (09:30-16:00) high and low.
- **The window:** from 19:00 to 02:00 the next morning, one trade a night, the first trigger.
- **A long:**
  - the sweep: a bar whose low is below the session low;
  - a bearish fair value gap (three bars k-2, k-1, k with high[k] < low[k-2]; its top is low[k-2]), formed from 30
    bars before the sweep up to the bar before the trigger;
  - the trigger: a close above the top of the most recent such gap, while the price is still within 30 bars of
    the sweep;
  - entry at the next bar's open, stop one tick below the lowest low from the sweep to the trigger.
- **A short:** the mirror, at the session high, with a bullish gap (low[k] > high[k-2]; its bottom is high[k-2]).
- **Skips:** a trade whose stop is under 3 points or over 40 points from the entry.
- **The exit:** a target at 2 times the risk, the stop (a bar that reaches both counts as the stop), or the close
  of the 09:25 bar, before the bot's session.
- **Costs per MNQ:** $1.24 in fees and 2 ticks of slippage on the entry and on stop and time exits; the target is a
  limit with no slippage.

**Pass (stage 1, the edge per contract):** daily P/L t-stat ≥ 2.24 on the index 2011-2018, then ≥ 1.65 on 2019-2022,
on 2023-Sep 2026, and on NQ futures 2015-2025. All four, run once. Only if it passes does stage 2 test it on the
account.

**G14 result (run once, 2026-11-02): rejected at stage 1; no edge.** The sweep and inversion gap hit its 2R target on
30-38% of trades and was stopped on the rest. That is the coin-flip rate for a 2R target (a third). Costs take what
is left:

| Per MNQ | Trades | Target hit | $ / trade | Average R | Daily t |
|---|---|---|---|---|---|
| index 2011-2018 | 679 | 37.6% | +$0.76 | +0.02 | 0.40 |
| index 2019-2022 | 374 | 33.4% | −$2.03 | −0.06 | −0.65 |
| index 2023-Sep 2026 | 336 | 30.1% | −$5.42 | −0.16 | −1.82 |
| NQ 2015-2025 | 955 | 33.8% | −$1.13 | −0.06 | −0.60 |

The bar was a t of 2.24, then 1.65 on each later set; none came close, and the recent years are the worst. As coded,
the confirmation the clips rely on doesn't predict the next 2R. The clips' results come from discretion that rules
can't capture, or from the 20-28 accounts each trade is copied to, not from this pattern
(`verification/noise_v2/g14_sweep_ifvg.csv`, `research/g14_sweep_ifvg.py`).

## G15: enter only on a strong break, "displacement" (registered 2026-11-02, before its run)

**The idea, from the @jacotradez clips:** they want "displacement", a move that leaves the level decisively, not a
close that just pokes past it. The bot enters on any close past the noise line. G15 enters only when the check's close
is past a wider line, `entry_k` times the noise from the reference price (`entry_k` in mnqbot/noise.py). The stop
stays at the normal line, so a strong break also starts further from its stop.

**Variants:** `entry_k` 1.25 and 1.5. Baseline: growth mode with G6's 60-minute time stop (`entry_k` 1).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

If both pass, take the one with the higher NinjaTrader window net.

**G15 result (run once, 2026-11-02): rejected.** Waiting for a stronger break gives up the trades that pay. Net fell
by half or more on the window, and several histories ran down to the floor and stopped. Waiting puts the entry
further from the stop, so each contract risks more and fewer fit the room. A few early losers at that risk drained a
new account. (Net $0-$7 after 66-102 trades: index 1.25x, NQ 1.5x.)

| Net, 5 min (chart / NinjaTrader) | baseline (any close past the line) | 1.25x the noise | 1.5x the noise |
|---|---|---|---|
| window | $18,516 / $18,549 | $8,744 / $8,694 | $2,353 / $2,384 |
| NQ | $277,322 / $267,571 | $204,769 / $202,230 | **$1 / $1, stuck** |
| index | $407,796 / $404,250 | **$7 / $0, stuck** | $256,117 / $250,089 |

(`verification/noise_v2/g15_entry_k_growth.csv`)

## G16: no wider stop after a loser (registered 2026-11-02, before its run)

**The idea:** since v2.2 the trade after a losing trade may risk $250 a contract instead of $187.50 (a wider max
loss, so a re-entry isn't stopped out by the same noise). That was chosen long before the 60-minute time stop. With
the time stop now cutting slow losers, the wider stop may only make the second loss bigger. G16 turns it off: every
trade risks at most $187.50 a contract (`after_loss_ml_mult` 1).

**Variant:** `after_loss_ml_mult` 1.0 (and "Max loss after a loser" = $187.50 in MnqNoiseV38.cs). Baseline: growth
mode with G6's time stop ($250 after a loser).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

**G16 result (run once, 2026-11-02): rejected by the rule, but the closest call so far.** Without the wider stop after
a loser:
- the histories made much more: NQ +$25-28k, the index +$8-13k on 5-minute bars;
- the largest single loss shrank from about −$3,776 to −$2,839;
- there were more winners: 64.0% against 61.5% on the window.

The window, the period the account trades now, made a little less (−$839 chart, −$1,112 NinjaTrader on 5-minute bars),
so it fails the pre-registered rule and isn't adopted. On 30-minute bars the window fell further (−$4.6k NinjaTrader).

| Net, 5 min (chart / NinjaTrader) | $250 after a loser (now) | $187.50 always |
|---|---|---|
| window | $18,516 / $18,549 | $17,677 / $17,437 |
| NQ | $277,322 / $267,571 | $302,035 / $295,625 |
| index | $407,796 / $404,250 | $420,552 / $412,643 |
| winners (NinjaTrader window) | 61.5% | 64.0% |
| largest loss (NinjaTrader NQ) | −$3,776 | −$2,839 |

The floor was never touched. One NinjaTrader index day reached −$942, still under −$1,000
(`verification/noise_v2/g16_after_loss_growth.csv`).

## G17: keep part of today's profit (registered 2026-11-02, before its run)

**The idea, from the user:** "these kinds of wins but not these kinds of losses". The worst day in growth mode is
never below −$900, yet single trades lose up to −$3,776. The daily room is $900 plus all of today's closed profit,
so after a +$3,000 morning one trade may risk most of it (up to 15 contracts at $250). G17 keeps part of the day's
profit off-limits: the day's room is $900 + today's P/L − `day_keep` × today's profit, when it is positive
(`day_keep` in mnqbot/noise.py).

**Variants:** `day_keep` 0.5 (half of today's profit is kept) and 1.0 (a trade never risks more than the $900 limit,
whatever the day has made). Baseline: growth mode with G6's time stop (`day_keep` 0).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

If both pass, take the one with the higher NinjaTrader window net. The largest single loss is reported too.

**G17 result (run once, 2026-11-02): rejected; it does what it says, at a price.** Keeping all of the day's profit
caps every trade's loss near the $900 limit:
- the largest single loss falls from −$3,776 to −$894 (NinjaTrader, NQ, 5-minute bars);
- the closed drawdown falls from $16.6k to $13.2k.

The re-risked profit is where much of the money comes from, though. The big winners often come after a green start,
at full size. Net fell everywhere:

| Net, 5 min (chart / NinjaTrader) | baseline (risk today's profit) | keep half | keep all |
|---|---|---|---|
| window | $18,516 / $18,549 | $18,267 / $18,316 | $16,850 / $16,895 |
| NQ | $277,322 / $267,571 | $258,625 / $249,991 | $234,677 / $228,367 |
| index | $407,796 / $404,250 | $360,723 / $355,830 | $311,967 / $309,457 |
| largest loss (NinjaTrader NQ) | −$3,776 | −$3,776 | −$894 |
| closed drawdown (NinjaTrader NQ) | $16,633 | $15,076 | $13,231 |

(`verification/noise_v2/g17_day_keep_growth.csv`) The "no big single losses" version is available: −$1.7k on the
window, −$39k on NQ over ten years.

## G18: no entries in a stormy stretch (registered 2026-11-02, before its run)

**The idea:** the mirror of the calm-stretch filter. The bot already sits out calm stretches (the last 10 sessions'
average range under 0.7x the last 40's). It has never sat out storms. The biggest single losses (−$3,000 and more)
come at full size in violent markets, where the noise line and the stop are far apart. G18 takes no new entries on a
day whose last 10 sessions' average range is above `storm_k` times the last 100 sessions' (`storm_k` /
`storm_long` in mnqbot/noise.py).

**Variants:** `storm_k` 1.5 and 2.0, `storm_long` 100. Baseline: growth mode with G6's time stop.

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

If both pass, take the one with the higher NinjaTrader window net.

**G18 result (run once, 2026-11-02): rejected; the storms pay.** Sitting out stormy stretches cut the net everywhere.
The window fell from $18.5k to $12.1k on 5-minute bars; it was itself a volatile stretch (April 2025). The profit
factor on the window rose (1.82 to 2.07 at 1.5x) and the window's drawdown halved, but the trades given up made more
than they lost. The largest single losses (−$3,776) were not in the skipped days: they stayed.

| Net, 5 min (chart / NinjaTrader) | baseline | storm 1.5x | storm 2x |
|---|---|---|---|
| window | $18,516 / $18,549 | $12,148 / $12,175 | $12,099 / $12,097 |
| NQ | $277,322 / $267,571 | $209,649 / $207,530 | $252,296 / $249,051 |
| index | $407,796 / $404,250 | $336,450 / $332,781 | $376,563 / $372,433 |

(`verification/noise_v2/g18_storm_growth.csv`) Together with the calm filter's history, it fits a pattern. The bot is
a volatility trader: it needs movement, and it earns most when the market is wild.

## G19: a late-day lock (registered 2026-11-02, before its run)

**The idea:** a trade still open late in the day has little time left to reach the take-profit, but plenty to give
back a gain before the 16:00 exit. From the bar closing at T, a trade not yet locked and in profit at that close is
locked: the stop goes to the entry plus 2.5 points, from the next bar (`late_lock_from` in mnqbot/noise.py). G13 locked
by the time since the fill; G19 locks by the clock.

**Variants:** T = 15:00 and 15:30. Baseline: growth mode with G6's time stop.

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

If both pass, take the one with the higher NinjaTrader window net.

**G19 result (run once, 2026-11-02): rejected.** Locking late winners raises the winners by 1-2 points but cuts the
afternoon runners that close at 16:00 well in profit. The window lost money at both times, most of all on
NinjaTrader's execution (−$3.8k from 15:00, −$2.2k from 15:30). The histories were mixed, within ±$17k.

| Net, 5 min (chart / NinjaTrader) | baseline | lock from 15:00 | lock from 15:30 |
|---|---|---|---|
| window | $18,516 / $18,549 | $16,549 / $14,741 | $18,502 / $16,338 |
| NQ | $277,322 / $267,571 | $272,934 / $270,160 | $274,464 / $265,035 |
| index | $407,796 / $404,250 | $393,496 / $387,208 | $404,699 / $399,450 |

(`verification/noise_v2/g19_late_lock_growth.csv`) G13, G17 and G19 now agree: every rule that takes profit off the
table early (by time in the trade, by the day's gains, or by the clock) costs more than it saves. The bot's money is
in the runners.

## G20: a farther take-profit for trades with the trend (registered 2026-11-02, before its run)

**The idea:** G13, G17 and G19 showed the bot's money is in the runners. G2 (no take-profit at all) lost net. A
middle way: let only the trades with the 50-session trend run further, a long while yesterday's close is above its
50-session average or a short while it is below. Those are the ones most likely to keep going. Every other trade keeps
the 2-noise-unit take-profit (`trend_with_tp` in mnqbot/noise.py).

**Variants:** with-trend take-profit 3 and 4 noise units. Baseline: growth mode with G6's time stop (2 for all).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

If both pass, take the one with the higher NinjaTrader window net.

**G20 result (run once, 2026-11-02): rejected.** A farther take-profit for trades with the trend raised the profit
factor on the histories (1.53 to 1.61 on NQ, NinjaTrader) but made less on the window and on the index. Net fell
overall. A likely reason, not measured: with fewer targets filled, the profit comes later, and so do the contract
steps.

| Net, 5 min (chart / NinjaTrader) | baseline (2 noise units) | 3 with the trend | 4 with the trend |
|---|---|---|---|
| window | $18,516 / $18,549 | $16,144 / $16,120 | $15,163 / $12,398 |
| NQ | $277,322 / $267,571 | $260,844 / $250,046 | $270,152 / $271,806 |
| index | $407,796 / $404,250 | $373,111 / $371,019 | $375,611 / $373,223 |

(`verification/noise_v2/g20_trend_tp_growth.csv`) The 2-unit take-profit (chosen walk-forward in round twenty-six)
stays.

## G21: the lock trigger, re-checked with the time stop (registered 2026-11-02, before its run)

**The idea:** the time stop (G6) only closes trades that are not locked, so the lock trigger now decides which slow
trades the time stop can cut. With a lower trigger, more trades lock early (a small win, never a time-stop loss);
with a higher one, more of them stay open to the time stop. The trigger, 0.35 times the max loss, was chosen before
the time stop existed.

**Variants:** `lock_at` 0.25 and 0.5. Baseline: growth mode with G6's time stop (0.35).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

This is a second look at a setting already chosen, so the bar is all six 5-minute runs, as for G9.

**G21 result (run once, 2026-11-02): rejected; 0.35 stays.**
- **A later lock (0.5)** made more on the window: +$3.2k chart, +$5.3k NinjaTrader on 5-minute bars. It made much
  less on the histories: NQ −$30-37k, the index −$65-90k. One 30-minute NQ run (chart execution) went to the floor
  and stopped.
- **An earlier lock (0.25)** raised the winners to 64-66% and cut the net on every 5-minute set.

0.35 is the only trigger that holds up on all of them.

| Net, 5 min (chart / NinjaTrader) | 0.35 (now) | 0.25 | 0.5 |
|---|---|---|---|
| window | $18,516 / $18,549 | $16,069 / $15,603 | $21,740 / $23,891 |
| NQ | $277,322 / $267,571 | $224,794 / $224,508 | $240,071 / $237,561 |
| index | $407,796 / $404,250 | $336,802 / $333,091 | $342,639 / $314,725 |
| winners (NinjaTrader window) | 61.5% | 65.7% | 56.9% |

(`verification/noise_v2/g21_lock_at_growth.csv`) A setting that wins only on the recent window, by $5k, and loses
$30-90k over ten years is the classic sign of fitting the recent past. That is what the all-sets rule is there to
catch.

## G22: the stop distance past the line, re-checked with the time stop (registered 2026-11-02, before its run)

**The idea:** the line stop sits 0.24 noise units past the noise line (`stop_buffer`, chosen on 2011-2018 long before
the time stop). With the time stop cutting slow losers at 60 minutes, a wider stop now costs less: fewer whipsaw
stop-outs, and the trades that drift get cut by the clock. A tighter stop gets out of failed breakouts sooner.

**Variants:** `stop_buffer` 0.15 and 0.35. Baseline: growth mode with G6's time stop (0.24).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

This is a second look at a setting already chosen, so the bar is all six 5-minute runs.

**G22 result (run once, 2026-11-02): rejected; 0.24 stays.** Both stop distances made less on the window: −$4.4k
(0.15) and −$8.3k (0.35) on NinjaTrader's execution, 5-minute bars. The tighter stop also added days past −$1,000 on
the chart's execution (the index: 2 against 0). The histories were mixed, within a few thousand dollars, except the
wider stop on the index (−$40k).

| Net, 5 min (chart / NinjaTrader) | 0.24 (now) | 0.15 | 0.35 |
|---|---|---|---|
| window | $18,516 / $18,549 | $16,222 / $14,170 | $10,340 / $10,259 |
| NQ | $277,322 / $267,571 | $266,371 / $269,050 | $259,776 / $257,301 |
| index | $407,796 / $404,250 | $421,711 / $406,230 | $366,538 / $364,414 |

(`verification/noise_v2/g22_stop_buffer_growth.csv`) With G9 (time stop) and G21 (lock trigger), the three main
exit settings have now each been re-checked with the time stop in place, and each current value held.

## G23: the range-position filter, re-checked with the time stop (registered 2026-11-02, before its run)

**The idea:** the bot's "don't trade the middle of the chop" filter needs a long's check close in the top 35% of the
day's range so far (`range_pos_min` 0.65; the mirror for a short). It was chosen in v2.9, before the time stop. With
the time stop cutting failed breakouts at 60 minutes, a looser filter may now pay (more trades, the bad ones cut
early). A tighter one may pay more (only clean breakouts).

**Variants:** `range_pos_min` 0.55 and 0.75. Baseline: growth mode with G6's time stop (0.65).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

This is a second look at a setting already chosen, so the bar is all six 5-minute runs.

**G23 result (run once, 2026-11-02): rejected; 0.65 stays.** Both made less on the window: −$4.2k (0.55) and −$6.8k
(0.75) on NinjaTrader's execution, 5-minute bars. Both made less on NQ, and on 30-minute bars both ran NQ to the floor
and stopped (net $0-$8, both executions). The looser 0.55 made more on the index (+$20k), the only set it won.

| Net, 5 min (chart / NinjaTrader) | 0.65 (now) | 0.55 | 0.75 |
|---|---|---|---|
| window | $18,516 / $18,549 | $14,244 / $14,301 | $11,801 / $11,774 |
| NQ | $277,322 / $267,571 | $259,650 / $257,075 | $232,764 / $231,349 |
| index | $407,796 / $404,250 | $426,364 / $424,110 | $359,338 / $358,735 |

(`verification/noise_v2/g23_range_pos_growth.csv`)

## G24: the noise lookback (registered 2026-11-02, before its run)

**The idea:** the noise area is the average of the last 14 sessions' moves at each check (`lookback` 14, from the
source paper). A shorter lookback adapts faster to a changing market; a longer one is steadier. It has not been
checked in growth mode.

**Variants:** `lookback` 10 and 20. Baseline: growth mode with G6's time stop (14).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

This is a second look at a setting already chosen, so the bar is all six 5-minute runs.

**G24 result (run once, 2026-11-02): rejected; 14 stays.** Both lookbacks made far less on the window: $9.7k (10)
and $13.3k (20) against $18.5k, NinjaTrader's execution, 5-minute bars. On NQ, 6 of the 8 runs at 10 or 20 ran down
to the floor and stopped. The 14-session noise area, the source paper's, is the one that survives every history.

| Net, 5 min (chart / NinjaTrader) | 14 (now) | 10 | 20 |
|---|---|---|---|
| window | $18,516 / $18,549 | $9,714 / $9,707 | $13,234 / $13,250 |
| NQ | $277,322 / $267,571 | $253,479 / **$2, stuck** | **$0 / $7, stuck** |
| index | $407,796 / $404,250 | $341,724 / $337,638 | $379,574 / $390,723 |

(`verification/noise_v2/g24_lookback_growth.csv`)

## G25: the trend filter's length (registered 2026-11-02, before its run)

**The idea:** no shorts while yesterday's close is above its 50-session average (`trend_n` 50, from v3.1; 20 and 100
were "close" then, before growth mode and the time stop). A shorter average turns faster after a top; a longer one
blocks shorts through more of a bull market.

**Variants:** `trend_n` 30 and 100. Baseline: growth mode with G6's time stop (50).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

This is a second look at a setting already chosen, so the bar is all six 5-minute runs.

**G25 result (run once, 2026-11-02): rejected by the rule, a near miss like G16; 50 stays.** A 30-session trend made
more on the histories, on both bar lengths and in both executions: NQ +$5k to +$15k, the index +$12k to +$23k. On the
window it made a few hundred dollars less on 5-minute bars (−$423 chart, −$296 NinjaTrader) and −$2.3k on 30-minute
bars, so it fails the all-sets rule. A 100-session trend made much less on the window (−$5.7k).

| Net, 5 min (chart / NinjaTrader) | 50 (now) | 30 | 100 |
|---|---|---|---|
| window | $18,516 / $18,549 | $18,093 / $18,253 | $12,832 / $12,888 |
| NQ | $277,322 / $267,571 | $282,231 / $280,910 | $264,398 / $256,527 |
| index | $407,796 / $404,250 | $419,596 / $427,694 | $425,317 / $431,180 |

(`verification/noise_v2/g25_trend_n_growth.csv`) Like G16, a choice the user can make. Over the long run the evidence
leans to 30, but it isn't better on the window, so the rule keeps 50.

## G26: G16 and G25 together (registered 2026-11-02, before its run)

**The idea:** the two near misses, G16 (no wider stop after a loser, `after_loss_ml_mult` 1) and G25 (a 30-session
trend, `trend_n` 30), each made more on the ten-year histories and a little less on the window. Their gains may
add up and cover the window.

**A caution, stated before the run:** both parts were picked after their results were seen. This is a combination of
near misses, which is where overfitting hides, so it gets no allowance. It is held to the same all-sets rule, in both
executions, and a pass would still be reported with this caution.

**The variant:** `after_loss_ml_mult` 1.0 and `trend_n` 30 together. Baseline: growth mode with G6's time stop.

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

**G26 result (run once, 2026-11-02): rejected by the rule; the strongest result on the histories so far.** Together,
G16 and G25 made far more on the ten-year histories, with smaller losses (NinjaTrader's execution, 5-minute bars):
- NQ +$44k, with the largest loss −$2,839 instead of −$3,776 and the drawdown $14.3k instead of $16.6k;
- the index +$52k;
- winners up to 63-65%.

On the window, the period the account trades now, it made $2.2k less on 5-minute bars and $7.6k less on 30-minute
bars, and its drawdown there was $3.4k against $1.9k. It fails the all-sets rule and is not adopted.

| Net, 5 min (chart / NinjaTrader) | baseline | G16 + G25 |
|---|---|---|
| window | $18,516 / $18,549 | $16,435 / $16,347 |
| NQ | $277,322 / $267,571 | $313,860 / $311,931 |
| index | $407,796 / $404,250 | $451,683 / $456,550 |
| largest loss (NinjaTrader NQ) | −$3,776 | −$2,839 |
| drawdown (NinjaTrader window / NQ) | $1,852 / $16,633 | $3,350 / $14,267 |

(`verification/noise_v2/g26_g16_g25_growth.csv`) **For the user to decide.** Over ten-plus years the evidence favors
G16 + G25 clearly. On the 21 months the account trades now, the current settings did better. The window is one
stretch of the market. The histories hold many such stretches, but they are older. As the caution above says, both
parts were picked after seeing results, so the histories' margin may be smaller going forward than it looks here.

## G27: the big-day rule's threshold (registered 2026-11-02, before its run)

**The idea:** after a session whose range was over 1.5 times its 10-session average, the bot takes no entries the next
day in the direction the big day closed (`big_day_k` 1.5, from v2.3, before growth mode and the time stop). A lower
threshold blocks more chasing after big days; a higher one blocks only the extreme ones.

**Variants:** `big_day_k` 1.25 and 2.0. Baseline: growth mode with G6's time stop (1.5).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

This is a second look at a setting already chosen, so the bar is all six 5-minute runs.

**G27 result (run once, 2026-11-02): rejected; 1.5 stays.** Both thresholds made less on every 5-minute set in both
executions:
- **1.25** blocks too much: the window fell from $18.5k to $8.5k.
- **2.0** blocks too little: the window fell to $9.1k on the chart and $16.0k on NinjaTrader, and the index added a
  day past −$1,000 (chart).

| Net, 5 min (chart / NinjaTrader) | 1.5 (now) | 1.25 | 2.0 |
|---|---|---|---|
| window | $18,516 / $18,549 | $8,514 / $8,516 | $9,057 / $16,038 |
| NQ | $277,322 / $267,571 | $245,105 / $242,967 | $261,009 / $258,697 |
| index | $407,796 / $404,250 | $369,101 / $367,269 | $389,743 / $382,807 |

(`verification/noise_v2/g27_big_day_growth.csv`)

## G28: the calm-stretch threshold (registered 2026-11-02, before its run)

**The idea:** no new entries while the last 10 sessions' average range is under 0.7 times the last 40 sessions'
(`calm_k` 0.7, from v2.5). It is the last of the bot's filters not yet re-checked with growth mode and the time stop.
G18 found that sitting out storms costs money, so the bot needs movement. Maybe sitting out calm stretches more
strictly (0.8) helps, or sitting out less of them (0.6) does.

**Variants:** `calm_k` 0.6 and 0.8. Baseline: growth mode with G6's time stop (0.7).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

This is a second look at a setting already chosen, so the bar is all six 5-minute runs.

**G28 result (run once, 2026-11-02): rejected; 0.7 stays.** Both thresholds made less on the window: −$3.7k (0.6) and
−$6.2k (0.8) on NinjaTrader's execution, 5-minute bars. They made a little less or about the same on the histories.

| Net, 5 min (chart / NinjaTrader) | 0.7 (now) | 0.6 | 0.8 |
|---|---|---|---|
| window | $18,516 / $18,549 | $12,647 / $14,811 | $12,309 / $12,322 |
| NQ | $277,322 / $267,571 | $272,492 / $270,352 | $254,168 / $251,469 |
| index | $407,796 / $404,250 | $403,729 / $397,603 | $392,342 / $388,384 |

(`verification/noise_v2/g28_calm_growth.csv`)

**The re-check is complete (G9, G16 and G21-G28).** Every setting growth mode uses has been tested against
its neighbours with the time stop in place. The results:
- held: time stop 60, lock 0.35, stop distance 0.24, range position 0.65, lookback 14, big day 1.5, calm 0.7;
- the after-loss stop and the trend length came out as near misses (G16, G25, together G26). They win on the
  ten-year histories and lose a little on the window.

The current settings are where the evidence points.

## G26 decision: year by year (registered 2026-11-02, before its run)

**The user's call, handed to me:** "I just want money to be made and not lost significantly." G26 (G16 + G25)
won on the ten-year histories and lost $2.2k on the 21-month window. A total over ten years can come from one or two
lucky years. The fair tiebreak is how often it wins.

**The rule, fixed before running:** on NinjaTrader's execution with 5-minute bars, compare G26 with the current
settings calendar year by calendar year, on NQ futures (2015-2025) and on the index (2011-2026).

Switch Funded growth mode to G26 only if all hold:
- it has a higher net in at least 70% of the years on each history;
- its worst calendar year is no worse than the current settings' worst year on each history;
- the floor is never touched.

Otherwise keep the current settings and close G26.

**G26 decision (run once, 2026-11-02): keep the current settings; G26 is closed.**

| NinjaTrader, 5 min | NQ 2015-2025 | index 2011-2026 |
|---|---|---|
| years G26 made more | **8 of 11 (73%)** | **10 of 16 (62.5%)**, short of 70% |
| worst year, now / G26 | +$2,367 / +$6,970 | −$2,918 / −$2,664 |
| total, now / G26 | $267,571 / $311,931 | $404,250 / $456,550 |

G26's ten-year lead is real, but on the index it comes from a handful of big years: 2017 +$16.5k, 2020 +$10.6k,
2022 +$11.9k, 2024 +$7.4k and 2025 +$13.3k. In the other years it trailed about as often as it led, including 2012
(−$13.3k) and the current 2026 (−$1.1k). The rule needs it to win year in, year out on both histories, and it
doesn't, so the current settings stay. Every year in both histories was profitable or close to flat under both
settings: the worst was −$2,918 (index, 2019) (`verification/noise_v2/g26_by_year.csv`).

## G29: stress test, worse fills (registered 2026-11-02, before its run)

**The question, from the user's goal ("money made and not lost significantly"):** the backtests assume 1 tick of
slippage on every market fill and stop. Live fills, on fast days and at 10-15 contracts, can be worse. G29 re-runs
the settings the account trades (growth mode with G6's time stop) at 2 and 3 ticks of slippage per fill. Nothing is
being chosen here; this checks how safe the current bot is.

**It holds up only if all hold, in both the chart's and NinjaTrader's execution, at 2 ticks:**
- net above $0 on every set and both bar lengths;
- the trailing floor never touched;
- no day at −$1,000 or worse beyond the baseline's.

3 ticks is reported for how much margin there is. If 2 ticks fails, the user is told plainly.

**G29 result (run once, 2026-11-02): the bot holds up at 2 ticks.** At 2 ticks of slippage on every fill (double the
backtests'), every set made money on both bar lengths and in both executions. The floor was never touched, and no
day reached −$1,000 beyond the baseline's one NQ gap day. 2 ticks costs about 10-20% of the net:

| Net, 5 min (chart / NinjaTrader) | 1 tick (backtests) | 2 ticks | 3 ticks |
|---|---|---|---|
| window | $18,516 / $18,549 | $15,892 / $14,571 | $11,197 / $13,096 |
| NQ | $277,322 / $267,571 | $244,361 / $246,956 | **$2 / $236,003** |
| index | $407,796 / $404,250 | $386,688 / $384,795 | $375,744 / $371,519 |

**The warning, at 3 ticks:** one run, NQ on 5-minute bars with the chart's execution, lost the early cushion and sat
at the floor after 144 trades. That is a new account, early on: the first few months, before the floor has stopped
at the starting balance, are the account's weakest point. NinjaTrader's execution at 3 ticks held there ($236k).
Every 30-minute run held at 3 ticks.

**For live trading:**
- Check the journal's fills against the model's after the first weeks.
- If slippage runs at 3 ticks or more, the first months are where the account is at risk. Growth mode already
  starts at 1 contract. A slower start (no contract steps until the floor has stopped) would be the next thing to
  test; it hasn't been tested yet.

(`verification/noise_v2/g29_slippage_growth.csv`)

## G30: a gentler start for a new account (registered 2026-11-02, before its run)

**The idea, from G29's warning:** a new account is weakest before its trailing floor has stopped at the starting
balance (the highest end-of-day equity $2,000 above the start). Growth mode adds a contract at +$1,500, so it is
already at 2 contracts while the floor still trails. With bad fills (3 ticks) one NQ run lost its cushion there. G30
keeps the starting 1 contract until the floor has stopped, then the usual steps apply (`steps_after_lock` in
mnqbot/noise.py).

**The variant:** `steps_after_lock` on, at 1, 2 and 3 ticks of slippage. Baseline: growth mode with G6's time stop,
at the same slippage.

**Adopt only if all hold:**
- at 1 tick, a net of at least 95% of the baseline's on all three 5-minute sets, in both executions (safety may cost
  a little, not much);
- the floor is never touched at 1, 2 or 3 ticks on any 5-minute set, in both executions;
- no more days at −$1,000 or worse.

**G30 result (run once, 2026-11-02): rejected by the rule; the safety it buys is real.**
- **What it fixes.** At 3 ticks the NQ run that sat at the floor now makes $241,762. No run at 1, 2 or 3 ticks
  touched the floor, on either bar length or execution.
- **What it costs.** At 1 tick it is within 1% of the baseline everywhere except NinjaTrader's window: $16,819
  against $18,549, or 90.7%. The window starts a new account, so that is where holding 1 contract costs most. The
  rule asked for 95%.
- **Why it isn't adopted.** The one floor hit it prevents came in the chart's execution at 3 ticks. NinjaTrader's
  execution, the one the account trades, held at 3 ticks without it.

| Net, 5 min, NinjaTrader | baseline 1 / 2 / 3 ticks | gentle start 1 / 2 / 3 ticks |
|---|---|---|
| window | $18,549 / $14,571 / $13,096 | $16,819 / $15,929 / $11,233 |
| NQ | $267,571 / $246,956 / $236,003 | $274,916 / $252,147 / $241,525 |
| index | $404,250 / $384,795 / $371,519 | $399,804 / $381,626 / $368,701 |
| **chart execution, NQ, 3 ticks** | **$2, stuck at the floor** | **$241,762** |

(`verification/noise_v2/g30_gentle_start_growth.csv`) If live fills turn out worse than 2 ticks, this is the setting
to turn on.

**Now in MnqNoiseV38.cs, off by default (2026-11-02).**
- **Where:** "Gentle start: no contract steps until the trailing floor has stopped", in group 1, "Size and risk".
- **Tested:** `test_v38_gentle_start_agrees` runs NinjaTrader's code against the Python model with it on, at 5 and 30
  minutes: the same trades to the cent, with the sizes changed.
- **When to switch it on:** if the journal shows fills 3 or more ticks worse than the model's on a new account.

## G31: the squeeze threshold (registered 2026-11-02, before its run)

**The idea:** when not one contract of the next trade fits today's room or the room above the floor, the bot still
takes 1 contract with its stop cut to the room left, if that leaves at least 20 points (`squeeze_min` 20, from v3.1).
It is the last setting not yet re-checked with growth mode and the time stop. A lower minimum takes more squeezed
trades (more chances late in a bad day); a higher one sits out more of them.

**Variants:** `squeeze_min` 10 and 30. Baseline: growth mode with G6's time stop (20).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

This is a second look at a setting already chosen, so the bar is all six 5-minute runs.

**G31 result (run once, 2026-11-02): rejected; 20 stays, and the setting barely matters.** Every run was within
about $2k (0.7%) of the baseline: the squeeze binds on few trades in growth mode. 10 points tied the window exactly
(no squeezed trade there). 30 points made $47-56 more on the window and $1.9k less on NQ (chart). Neither beat the
baseline on all six 5-minute runs.

| Net, 5 min (chart / NinjaTrader) | 20 (now) | 10 | 30 |
|---|---|---|---|
| window | $18,516 / $18,549 | $18,516 / $18,549 | $18,563 / $18,605 |
| NQ | $277,322 / $267,571 | $277,531 / $268,398 | $275,437 / $268,044 |
| index | $407,796 / $404,250 | $407,413 / $405,252 | $405,550 / $405,684 |

(`verification/noise_v2/g31_squeeze_growth.csv`) With G31, every setting growth mode uses has been re-checked with
the time stop in place.

## G32: the most contracts (registered 2026-11-02, before its run)

**The idea:** growth mode adds a contract per $1,500 of profit, up to 15 (`size_up_to` 15). G5 tried faster steps; the
cap itself was never re-checked. A lower cap means smaller losses once the account is large; a higher cap means
more profit on its best days. The $900 daily room and the floor still size every trade.

**Variants:** `size_up_to` 10 and 20, with the $1,500 step. Baseline: growth mode with G6's time stop (15).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

This is a second look at a setting already chosen, so the bar is all six 5-minute runs.

**G32 result (run once, 2026-11-02): rejected by the rule; a cap of 10 is the lower-risk option.**
- **Cap 10:**
  - made slightly more on the window (+$189 chart, +$205 NinjaTrader) and about the same on NQ (−$1.1k chart,
    +$1.0k NinjaTrader);
  - made less on the index (−$16-18k, about 4%), so it fails the all-sets rule;
  - cut the largest single loss by a third (−$3,776 to −$2,517);
  - cut the closed drawdown by 14-20% (NQ $16.6k to $14.3k, the index $19.3k to $15.3k, NinjaTrader).
- **Cap 20:** made less on the histories and its largest loss grew to −$5,035.

| 5 min, NinjaTrader | cap 15 (now) | cap 10 | cap 20 |
|---|---|---|---|
| net, window | $18,549 | $18,754 | $18,549 |
| net, NQ | $267,571 | $268,544 | $265,737 |
| net, index | $404,250 | $386,561 | $391,950 |
| largest loss, NQ | −$3,776 | −$2,517 | −$5,035 |
| drawdown, NQ / index | $16,633 / $19,255 | $14,298 / $15,326 | $17,107 / $18,680 |

(`verification/noise_v2/g32_max_qty_growth.csv`) "Most contracts" is already a setting in MnqNoiseV38.cs (Custom
mode). Funded growth keeps 15.

## G33: a "Funded safe" preset (registered 2026-11-02, before its run)

**The idea:** the user's goal is "money made and not lost significantly". Two tested settings cut risk at a small
cost: the 10-contract cap (G32: a third smaller largest loss, 14-20% smaller drawdowns, −4% net on the index) and the
gentle start (G30: no floor hit even at 3 ticks of slippage). G33 measures them together as a preset the user can
choose. It is not a change to Funded growth, so there is no adoption rule. The results are reported as they come:
- net at 1 and 3 ticks;
- the largest loss;
- the drawdown;
- floor touches.

**The preset:** growth mode with G6's time stop, `size_up_to` 10 and `steps_after_lock` on. Baseline: growth mode as
it trades.

**It becomes a Mode in MnqNoiseV38.cs only if:**
- the floor is never touched at 1 or 3 ticks, on any 5-minute set, in both executions;
- the largest loss and the drawdown are no larger than the baseline's on every 5-minute set.

**G33 result (run once, 2026-11-02): not made a Mode; it misses its own bar on the window by small amounts.**
- **On the histories it is what it promises.** The largest loss falls from about −$3,776 to −$2,517 everywhere. The
  drawdown falls 14-20%. The floor is never touched at 1 or 3 ticks (growth mode's 3-tick chart run on NQ sat at the
  floor).
- **What it costs.** About 4% of the net on the index and 9% on NinjaTrader's window at 1 tick. NQ is about even.
- **Where it misses.** On the window, a new account, where the 10-contract cap barely binds and the gentle start
  reshuffles the early trades, two numbers came out a little larger than growth mode's:
  - the drawdown on NinjaTrader's execution at 1 tick: $1,918 against $1,852;
  - the largest loss on the chart's execution at 3 ticks: −$759 against −$569.

  The bar was "no larger on every 5-minute set".

| 5 min, NinjaTrader, 1 tick | growth (now) | safe preset |
|---|---|---|
| net: window / NQ / index | $18,549 / $267,571 / $404,250 | $16,812 / $274,813 / $383,702 |
| largest loss: window / NQ / index | −$852 / −$3,776 / −$3,776 | −$792 / −$2,517 / −$2,517 |
| drawdown: window / NQ / index | $1,852 / $16,633 / $19,255 | $1,918 / $14,298 / $15,326 |

(`verification/noise_v2/g33_safe_growth.csv`) Both parts stay available as settings:
- "Most contracts" 10, in Custom mode;
- "Gentle start", the G30 switch.

## G34: a weekly loss brake (registered 2026-11-02, before its run)

**The idea, for "not lost significantly":** the $900 daily limit caps a bad day, but a bad week can string several
together. Once the closed P/L since the week's first session is `week_stop` or more in the red, the bot takes no new
entries until the next week (`week_stop` in mnqbot/noise.py). This has not been tested before.

**Variants:** `week_stop` $1,500 and $2,500. Baseline: growth mode with G6's time stop (no weekly brake).

**Adopt only if all hold, in both the chart's and NinjaTrader's execution:**
- on 5-minute bars it has a higher net than the baseline on NQ, the index and the window;
- it never touches the trailing floor;
- no more days at −$1,000 or worse.

The drawdown and the largest loss are reported too. If it cuts the drawdown but costs net, it goes on file as a
lower-risk option like G32.

**G34 result (run once, 2026-11-02): rejected; a weekly brake is not needed.** On the window neither brake ever
triggered: the 21 months had no week down $1,500 in closed P/L, so the results are identical.
- **$1,500 brake:** on the histories it trimmed the drawdown 7-11% but cost $5-13k on NQ and $1-5k on the index (5
  minutes).
- **$2,500 brake:** it barely triggered (within $1.4k everywhere).

Neither beat the baseline on all sets, and the window never needed it.

| Net, 5 min (chart / NinjaTrader) | no brake (now) | $1,500 a week | $2,500 a week |
|---|---|---|---|
| window | $18,516 / $18,549 | the same | the same |
| NQ | $277,322 / $267,571 | $264,098 / $261,796 | $277,050 / $267,303 |
| index | $407,796 / $404,250 | $402,573 / $399,166 | $409,160 / $405,462 |
| drawdown NQ / index (NinjaTrader) | $16,633 / $19,255 | $15,493 / $18,146 | $16,680 / $19,255 |

(`verification/noise_v2/g34_week_stop_growth.csv`) The daily $900 limit already keeps bad weeks small. The window's
worst stretch was $1,852.

## G35: a new account on any start date (registered 2026-11-02, before its run)

**The question, from the user's goal ("money made and not lost significantly"):** the window is one start date
(January 2025). G35 starts a fresh account every quarter and runs it for 21 months, the window's length. That covers
NQ futures 2015 to 2023 and the index 2011 to 2024. The settings are growth mode as it trades, with G6's time stop,
on NinjaTrader's execution and 5-minute bars, with 16:00 bars added. Nothing is chosen here. It measures what to
expect.

**Reported for each start:**
- the net after 21 months;
- whether the trailing floor (stopping at the starting balance) was ever touched;
- the lowest the account went below its start;
- whether it reached +$2,000 (the floor stops there).

**Read as:**
- the share of starts that touch the floor (a lost account);
- the share that end below the start;
- the median net and the worst net.

If more than 5% of starts touch the floor, the same starts are re-run with G30's gentle start and G32's 10-contract
cap, and the user is told which one to switch on.

**G35, first look, and a correction (2026-11-02).**

*What was wrong.* The first run counted a floor touch only when the closed equity went below the floor. Several starts
instead ended at the floor and stopped trading, with 41-127 trades in 21 months against about 280 normally:
- some had a trailing floor that rose with an early peak and was then reached;
- some reached +$2,000, which stops the floor at the start, and then fell back to the start.

At most firms an account at its floor has failed, so these count as lost.

*What it changes.* Earlier G rounds used the same "below the floor" check, and their "floor never touched" means
"never below it". The runs that stalled at the floor were caught by eye, as "net $0-$7, stuck".

*The fix.* The runner now reports the room above the floor at the end and counts a start as lost when under $100 is
left.

*The re-run.* By the pre-registered rule (more than 5% of starts lost), every start is re-run with G30's gentle start
and with G32's 10-contract cap.

**G35 result (re-run with the at-the-floor measure, 2026-11-02).**

| 21-month accounts, NinjaTrader, 5 min | growth mode (now) | gentle start | cap 10 |
|---|---|---|---|
| NQ starts lost (at the floor) | 7 of 35 (20%) | 7 of 35 | 7 of 35 |
| index starts lost | 6 of 54 (11%) | 8 of 54 | 6 of 54 |
| median net, NQ / index | $22,925 / $23,070 | $26,574 / $22,861 | $22,746 / $24,992 |
| 10th percentile net, NQ / index | −$460 / $444 | −$99 / $3 | −$460 / $444 |

**What the losses are:**
- the lost starts cluster in 2015, 2019-early 2020, 2011 and 2013, periods when the bot lost its first $2,000 before
  making it, or made $2,000 and gave it back;
- each ends with $1-$33 of room left. Every trade is sized to the room above the floor, and a squeezed 1-contract
  trade may risk all of it, so in a bad stretch the bot spends the cushion to the last dollar.

Neither G30 nor G32 changes that. The fix has to keep a reserve: never risk the last part of the room, or risk less
until the cushion is built.

**For the user:** a fresh 50K funded account on this bot made a median of about $23,000 in 21 months. About 1 in 9
(index) to 1 in 5 (NQ) such accounts would have been lost along the way. That is the honest risk, and it is higher than
the single January 2025 window suggested. G36 tests the reserve.

## G36: a reserve above the floor (registered 2026-11-02, before its run)

**The idea, from G35:** each lost account spent its cushion to the last dollar, because every trade is sized to the
room above the floor. A reserve keeps part of that room off-limits. Two existing options, in mnqbot/noise.py:
- `trail_buffer` $500: never risk the last $500 above the floor;
- `trail_frac` 0.5: never risk more than half of the room that is left.

**The test:** G35's 89 start dates (a new account every quarter, 21 months each, NinjaTrader's execution, 5-minute
bars), for each option and the baseline. An account that stops at its reserve doesn't fail, but it may stop trading.
So besides "lost" (under $100 above the floor) it counts "frozen" (no trade in the last 90 days), and "dead" (lost or
frozen).

**Adopt (as Funded growth's default) only if all hold:**
- fewer dead accounts than the baseline on both NQ and the index;
- a median net of at least 95% of the baseline's on both;
- and then the usual all-sets check on the window, NQ and the index (G-runner, both executions): no more than 5%
  less net on any 5-minute set, and the floor never touched.

**G36 result (run once, 2026-11-02): rejected; a reserve doesn't save the bad starts.**

| 89 start dates, 21 months each | growth mode (now) | $500 reserve | half the room |
|---|---|---|---|
| NQ: lost / frozen / dead of 35 | 7 / 7 / 7 | 0 / 15 / 15 | 7 / 6 / 7 |
| index: lost / frozen / dead of 54 | 6 / 7 / 7 | 0 / 20 / 20 | 6 / 7 / 7 |
| median net, NQ / index | $22,925 / $23,070 | $12,637 / $18,960 | $22,925 / $23,070 |

**What happened:**
- **The $500 reserve.** No account reached the floor, but more than twice as many froze about $500 above it. They
  could no longer size a trade and stopped for good, with a lower median.
- **Half the room.** It barely changes anything: a 1-contract trade already fits half of most rooms.

**What it says.** The lost starts are not a sizing accident at the end. In those periods (2011, 2013, 2015, 2019-early
2020) the bot lost money for months at 1 contract, its smallest size. The $2,000 trailing drawdown is about 10 of its
full $187.50 losses. On this edge, with this drawdown, about 1 in 9 (index) to 1 in 5 (NQ) fresh accounts fail inside
21 months, and the rest make a median of about $23,000.

The remaining lever is a smaller loss per trade from the start, so a bad stretch costs less of the $2,000: a
$100-125 max loss until the floor has stopped. That is G37.

## G37: a smaller loss per trade until the cushion is built (registered 2026-11-03, before its run)

**The idea, from G35 and G36:** the lost accounts had a bad stretch before the floor stopped at the starting balance.
At 1 contract, each full loss is $187.50 (or $250 after a loser), so about 10 of them use up the $2,000. Until the
floor has stopped, G37 caps every trade's max loss at `early_ml` a contract (`early_ml` in mnqbot/noise.py). The stop
is then at the max loss or the line, whichever is closer. After that, growth mode as now.

**Variants:** `early_ml` $125 and $100. Baseline: growth mode with G6's time stop.

**Adopt (as Funded growth's default) only if all hold:**
- on G35's 89 start dates: fewer dead accounts (lost or frozen) than the baseline on both NQ and the index, and a
  median net of at least 95% of the baseline's;
- the usual runner on the window, NQ and the index, both executions: at least 95% of the baseline's net on every
  5-minute set, and the floor never touched.

**G37 result (run once, 2026-11-03): rejected; the failure rate barely moves.**

| 89 start dates, 21 months each | growth mode (now) | $125 early | $100 early |
|---|---|---|---|
| NQ: dead of 35 | 7 | 5 | 6 |
| index: dead of 54 | 7 | 8 | 9 |
| median net, NQ / index | $22,925 / $23,070 | $27,145 / $26,074 | $23,019 / $24,048 |

$125 saved two NQ accounts and lost one more on the index. The rule needed fewer on both. A tighter stop gets hit
more often, so a bad stretch costs about as much in total. The medians rose, but the lost-account count is what this
test was about.

**After G35-G37.** Three kinds of fix were tried: sizing (gentle start, cap 10), a reserve ($500, half the room) and a
smaller early loss ($125, $100). None lowers the share of fresh accounts lost on both histories. On this edge, with a
$2,000 trailing drawdown, about 1 in 9 (index) to 1 in 5 (NQ) fresh accounts fail within 21 months. The bad starts
are bad stretches of the market for this strategy (2011, 2013, 2015, 2019-early 2020). No sizing rule turns a
losing stretch into a winning one. What it means for the user is a fact to plan with, not something to tune away:
- a lost account costs a new evaluation, not more than that;
- expect about one restart in five to nine accounts;
- weighed against a median of about $23,000 per 21-month account.

## Upgrades (shipped improvements to the bot the user runs)

**U1 (2026-11-03): the dashboard shows the open trade.** Two new dashboard lines in MnqNoiseV38.cs:
- **Trades today:** the account's closed trades this session.
- **Open trade:** side and contracts, the fill price, the stop and the target set for the next bar, the minutes in
  the trade, and whether the lock has armed ("locked (can't lose)" or "lock not reached"). While unlocked, it also
  shows the time-stop countdown ("time stop in 25 min if losing", or "out at the next bar if losing"). It says "none"
  when flat.

No trading logic changed: the trades are identical with and without it (`test_v38_dashboard_shows_the_open_trade`
checks every bar of the 5-minute sample). All 215 NinjaTrader and simulator tests pass. Re-import the file to see it.

**U2 (2026-11-03): a live loss guard for the $1,000 daily rule.** Every trade is sized to stay inside $900 a day, but a
gap or bad fills in a fast market can carry an open trade past its stop before the stop fills. The guard watches
every live tick (`OnMarketData`) and every bar close.
- **What it does.** Once today's closed P/L plus the open trade's P/L at the current price reaches −$950 ("Loss guard,
  live", group 1, default 950, 0 = off), it closes the position at market ("Loss guard"). It sends the exit again on
  each bar until it fills, and takes no new entry until the next session.
- **The dashboard** shows "Loss guard: flat at -$950 today, closed + open (live)", or "TRIPPED, flat and done for
  today".
- **The Output window** logs when it fires.

It works live only. Backtests and the trade-for-trade parity with the Python model are unchanged.
`test_v38_live_loss_guard` covers it:
- live with the guard off, the trades equal the backtest's;
- with a tight test guard ($150), it fires on the sample, the exit is named "Loss guard", and no entry follows that
  day.

The simulator now sends a live bar's ticks (open, low, high, close) before its close. All 216 NinjaTrader and simulator
tests pass. Re-import the file to get it; it is on by default at $950.

**U3 (2026-11-03): a startup check, and the mode read safely.**
- **The fix.** The Mode setting was matched exactly, so "funded growth" (lower case) or a stray space ran Custom's
  settings without a word. It is now read whatever its case and spaces. An unknown mode runs as Custom, with a warning.
- **The check.** At start the bot prints "MnqNoiseV38 WARNING: ..." to the Output window, and shows the first warning
  on the dashboard ("SETUP WARNING (n): ..."; "Setup: OK" when there is none), for:
  - a chart that isn't 5 or 30 minutes;
  - an instrument that isn't MNQ;
  - trading hours that aren't the ETH template (the 16:00 exit would fill late);
  - a loss guard below the daily budget (it would cut trades the budget allows);
  - a loss guard that is off or above $1,000 (no live backstop).

`test_v38_startup_checks` covers each warning, "Setup: OK", and that "  funded GROWTH " gives exactly Funded growth's
trades. All 217 NinjaTrader and simulator tests pass. Re-import the file to get it.

**U4 (2026-11-03): live alerts.** In NinjaTrader's Alerts window, with a sound ("5. Alerts": "Alerts (live)" and
"Alerts with a sound", both on by default), and in the Output window. Each alert fires live only:
- an entry: "BUY 3 MNQ at market (noise breakout), stop 21.50 points, target 54.00 points";
- every closed trade, with its exit and P/L: "Closed LONG 3 MNQ (Profit target): +$310.24, today 452.10";
- the time stop: "Time stop: the trade is still losing 60 min after its fill, closing at market";
- the loss guard: "LOSS GUARD: -955.00 today, flat and done for the day";
- each setup warning, once, as the strategy goes live.

`test_v38_alerts` checks:
- alerts only once live, one per closed trade;
- the sound setting;
- none with alerts off, and the same trades either way;
- the setup warning on going live.

All 218 NinjaTrader and simulator tests pass. Re-import the file to get it.
