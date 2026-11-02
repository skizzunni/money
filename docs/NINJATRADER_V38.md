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
