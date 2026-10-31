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
