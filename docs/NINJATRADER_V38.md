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

## Go live (2026-11-03)

**The backtest of the file you trade** (`research/v38_ninjatrader_run.py grow`, the strategy's own code on the NinjaTrader
simulator, Funded growth, from 2025-01-02, 1 tick of slippage, $0.62 a side;
`verification/noise_v2/v38g_nt_2026-11-03.csv` and the trade lists beside it):

| Jan 2, 2025 – Oct 2026 (updated 2026-11-04, U25) | 5-minute bars | 30-minute bars |
|---|---|---|
| Trades | 703 | 252 |
| Net | **$43,966.90** | $28,620.10 |
| Winners | 50.9% | 53.6% |
| Profit factor | 1.685 | 1.881 |
| Closed drawdown | $3,317.67 | $3,934.78 |
| Largest loss | −$1,762.10 | −$1,634.41 |
| Worst day | −$899.06 | −$899.20 |
| Most contracts | 15 | 15 |
| Days with a trade (the model) | about 72% | about 29% |

The 5-minute chart includes gap and go (U19, U20, U25: up to 10 MNQ once the floor has stopped), More trading days with the 2-point sizing allowance (U22) and the
data fix (G67). They need the 5-minute chart, so **trade the 5-minute chart**.

**It matches the Python model, trade for trade.**
- **30-minute bars:** all 303 trades are identical.
- **5-minute bars:** identical to 2026-03-09, where the stand-in data stops at 15:10: the model closes at that bar, the
  strategy at the next open, and the paths part from there. Live, MNQ trades to 16:00, so it can't happen.

**U16: a go-live check for the start date.** With the trailing drawdown on and "Trailing drawdown and contract steps
from date" blank, the floor and the contract steps count from the chart's first bar. Live, that counts the strategy's
backtest on the loaded history as the account's profit, so a new account could start at 4-5 contracts with a floor it
doesn't have. Going live with it blank now raises a setup warning, on the dashboard and as an alert, to set it to the
account's first trading day. `test_v38_alerts` checks the warning, and that it doesn't fire with the date set.

**The checklist:**
1. **The file.** Copy `MnqNoiseV38.cs` to `Documents\NinjaTrader 8\bin\Custom\Strategies\`. Open New → NinjaScript
   Editor and press F5: no errors.
2. **The chart.** MNQ (front month, 12-26 now), **5 minute**, Trading hours **CME US Index Futures ETH**, Days to load
   **120** (the filters need 50 sessions).
3. **The strategy** (right-click the chart → Strategies → MnqNoiseV38):
   - Mode **Funded growth** (or the 100K/150K/Apex mode of your account);
   - **Trailing drawdown and contract steps from date: your account's first trading day**, yyyy-MM-dd (today if it
     is new);
   - Account: your prop account; Calculate: On bar close; leave the rest as they are.
4. **Enable it** and read the dashboard (top right):
   - "Setup: OK";
   - "Next trade: 1 MNQ" on a new account;
   - "Room above the trailing floor: $2000";
   - the "Today:" line.

   Any SETUP WARNING: fix it before the open.
5. **Every day:** leave NinjaTrader running from before 09:30 to after 16:00 New York. Alerts tell you each entry,
   exit, the day's and the week's summary.
6. **Every week:** `python research/journal_report.py MnqNoiseV38_live_<account>.csv`, and check "Live vs tested".

**U17 (2026-11-03): the data check.** The user's Strategy Analyzer run on MNQ DEC26 alone gave 54 trades where the
model gives about 125. Moving the start date earlier changed nothing, which means NinjaTrader had no earlier bars for
that contract. The strategy now counts each session's 09:30-16:00 bars (the no-trade dates aside). It warns when more
than 1 session in 20 (and over 2) is missing over a tenth of its bars, and when fewer than 50 sessions come before the
start date. The warning shows on the dashboard ("DATA WARNING: …", or "Data check: n sessions, all complete"), goes to
the Output window at the end of every backtest, and, live, is a setup alert. It names the fix: the instrument MNQ ##-##
(or Merge back adjusted) and the history loaded in Tools > Historical Data.

**U18 (2026-11-03): the settings panel shows Funded growth's values.** The defaults were the Evaluation's ($260, no
trailing drawdown, no steps, no time stop), so the panel showed numbers Funded growth doesn't use. They are now Funded
growth's: $187.50 / $250, $900, $2,000, $1,500 steps to 15, sized by its own stop, the 60-minute time stop. The trades
are unchanged in every mode.

`test_v38_data_check` covers three cases:
- the full sample: no warning;
- every third bar removed: a warning on the dashboard and in the Output window, naming MNQ ##-##;
- a start date 30 days in: the 50-session warning.

All 29 NinjaTrader v3.8 tests and 162 NinjaTrader tests pass.

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

**U5 (2026-11-03): progress tracking.**
- **The dashboard** now shows, from the account's own fills:
  - "This week $X, this month $Y; real fills: N trades, W% winners";
  - once a month of trading has passed, "Pace: $P a month since <date>, about M more months to the goal".
- **`research/journal_report.py`** gains:
  - a weekly table (the last 12 weeks, with green and red weeks, the best and the worst);
  - the pace to the goal ($50,000 by default, or a third argument).

`test_v38_progress_matches_the_journal` checks the dashboard's week, month, trade count and win rate against the
journal's own trades to the cent, and the report's weeks and pace. All 15 NinjaTrader v3.8 tests pass. Re-import the
file to get it.

**U6 (2026-11-03): fill quality, tracked on every trade.** For each trade the bot records the ticks paid worse than
planned:
- **the entry:** against the close the market order was sent at;
- **a stop:** against the resting stop price;
- **a market exit:** against the price it was sent at (time stop, 16:00, stop passed, the loss guard's tick);
- **a target:** a limit, nothing to measure.

**Where it shows:**
- two new journal columns, "entry slip ticks" and "exit slip ticks";
- the dashboard's "Fills vs plan: entries +x ticks (n), stops and market exits +y ticks (m)";
- a "Fills vs plan" line in `research/journal_report.py`.

Once 20 trades average more than 2 ticks, the dashboard adds "consider Gentle start". G29-G30 found that 3 ticks is
where a new account's first months are at risk.

A live journal from before this version, with the old columns, is moved aside as `..._until_<time>.csv`, so no file
mixes the two layouts.

`test_v38_fill_quality` checks each trade's entry slip against the simulator's fill and the bar it was sent at,
exactly. It also checks every stop's slip at 1 and 3 ticks, no slip on targets, the dashboard average, the warning at 3
ticks and unchanged trades. All 16 NinjaTrader v3.8 tests pass. Re-import the file to get it.

**U7 (2026-11-03): the day's summary.**
- **The alert.** Live, once a session, on the first bar from 16:00 on (after the 16:00 exit has filled), an alert and
  an Output line: "Day done 2026-11-03: +$412.50 in 3 trades (2 winners), total $8214.00, room above the floor $6214,
  tomorrow up to 6 MNQ".
- **The journal.** The DAY lines now fill in the room above the trailing floor and the next day's contracts.

`test_v38_day_summary` checks one summary per live session, each with the day's P/L and trade count exactly as its
journal DAY line has them, and the DAY lines' new fields. All 17 NinjaTrader v3.8 tests pass. Re-import the file to
get it.

**U8 (2026-11-03): milestone and goal alerts.** Live, at the day's close (with the "Day done" summary):
- **Milestones.** Each time the profit since the start passes a new multiple of "Milestone alerts" (group 5, default
  $5,000, 0 = off), one alert: "Milestone: +$10000 since the start (20% of the $50000 goal); room above the floor
  $12000, next trade up to 7 MNQ". A day that passes several levels gives one alert, for the highest.
- **The goal.** The day the profit since the start reaches the Goal setting ($50,000), once: "GOAL REACHED: +$50210
  since the start (goal $50000); ... Check your firm's payout rules before withdrawing".

Levels already passed when the strategy goes live give no alert, so a restart doesn't repeat them. The trades are
unchanged. `test_v38_milestones` checks:
- one alert per level, rising, the last at the highest level reached;
- none for the levels before going live;
- one goal alert, even for a goal between two levels;
- the same trades with the alerts on or off.

All 26 NinjaTrader v3.8 tests pass. Re-import the file to get it.

**U9 (2026-11-03): one Preset setting on TradingView, as NinjaTrader's Mode.**
- **The problem.** To match NinjaTrader's Funded growth, `pine/mnq_noise_momentum.pine` needed seven sizing inputs set
  by hand ($187.50 max loss, $250 after a loser, the $2,000 trailing drawdown, a contract per $1,500 up to 15, the
  trade's own stop, the 60-minute time stop). A missed one tests a different bot.
- **The setting.** A new first input, "Preset (as NinjaTrader's Mode)", whose options are NinjaTrader's Modes:
  - Funded growth (the default, as in NinjaTrader);
  - Funded growth 100K and 150K (Topstep's rules);
  - Funded growth Apex 100K and Apex 150K;
  - Custom: the inputs as set, as before.

  Any Funded growth preset sets the sizing and the account's daily budget and trailing drawdown, whatever those inputs
  say.

`test_pine_presets` checks each preset against the Python model of that mode, trade for trade, with every overridden
input set to something else. It also checks that the time stop fires, that Custom keeps the inputs, and that the default
is Funded growth. The other Pine tests now name Custom. Re-paste the script on TradingView to get it.

**U10 (2026-11-03): the TradingView dashboard, closer to NinjaTrader's.**
- **The fix.** With a preset on (U9), the dashboard's title still read "Evaluation, 1 MNQ" from the old account tick
  box. It now names the preset and the contracts the account is at, e.g. "Funded growth 100K, 4 MNQ".
- **Room above the floor.** A new row shows the room left above the trailing floor and the next trade's size: "$3,412.50,
  next trade up to 4 MNQ". It turns orange under $500.
- **The goal.** A new row compares the profit since the start date against "Profit goal for the dashboard" (Display
  group, default $50,000, 0 = hide): "$12,345.00 since the start (24.7%)", then "goal reached".

`test_pine_dashboard_goal_and_room` checks the title, the room against the floor computed from the script's own trades
(its end-of-day peak), and the goal row's amount and share, to the cent. The trades are unchanged. Re-paste the script
on TradingView to get it.

**U11 (2026-11-03): live vs tested, in the journal report.** `research/journal_report.py` has a new section,
"Live vs tested". It sets the journal's numbers against the ranges Funded growth showed in testing (5-minute bars,
NinjaTrader's execution, on the window, NQ 2015-2025 and the index 2011-2026):

| measure | tested range |
|---|---|
| win % | 61.2 to 62.2 |
| profit factor | 1.53 to 1.82 |
| trades a month | 13.4 to 18.4 |
| time stops % | 6.0 to 11.7 |

From 30 trades on, it works out how likely so few winners would be if the bot still won 61.2% of its trades. Under 5%,
it warns: "WARNING: the win rate is below what was tested", and says to check the fills, the chart and the Mode before
trading on. That catches a live setup that isn't the tested bot (bad fills, a wrong chart or session, a wrong Mode)
within a few weeks, instead of months of losses.

`test_journal_report_flags_a_low_win_rate` checks the binomial tail exactly (45 winners in 100 flagged, 58 not).
`test_v38_progress_matches_the_journal` checks the section's win rate against the simulator's journal. Run it on the
live journal: `python research/journal_report.py MnqNoiseV38_live_<account>.csv`.

**U12 (2026-11-03): replay any day.** `research/replay_day.py` runs the bot on chosen days of a NinjaTrader MNQ
export and shows what it did:

    python research/replay_day.py MNQ_12-26.Last.txt 2026-10-29 2026-11-02 --out replays

- **For each day:** the trades (side, times, prices, why each closed, P/L), and `replay_<day>.html`. That page is a
  candle chart with the noise lines from each half-hour check, every entry and every exit.
- **The rules:** Funded growth's, at the starting size (1 MNQ, $187.50, $250 after a loser, $900 a day, the time stop),
  on 5-minute bars in NinjaTrader's execution. A larger account's contracts multiply each trade's P/L; the trades are the
  same.
- **Two contracts:** given an old and a new export, it joins them at the first session both cover to 15:59, the older
  back-adjusted by that close's difference, as `research/mnq_bars.py` does at the September roll. It warns when an
  export has under 60 sessions before a day, because the calm and trend rules read that far back.

On the user's data, 10/16/2026 replays as five shorts: −$60.74, −$251.74, +$476.76, +$572.26, +$3.26, so +$739.80 per
MNQ. That is the kind of trend day the bot is built for.

`tests/test_replay_day.py` checks that a replayed day equals the Python model's trades for it, exactly, and that the
page shows them. It also checks that two contracts 100 points apart join into the newer one's prices throughout. It is
for days like those in the user's Winter Trades clips (10/29, 11/2): export MNQ 12-26 1-minute bars through today and
replay them.

**U13 (2026-11-03): the win-rate check on NinjaTrader's dashboard.** U11's check, live, without running a script.
From 30 trades, the dashboard compares the real win rate with the tested one ("Win rate check", group 5, default 61.2%,
0 = off), using the same binomial tail as `research/journal_report.py`:
- "Win rate in line with the tests: 63.3% in 49 trades (tested 61.2%)"; or
- under a 5% chance, "WIN RATE WARNING: 48.0% in 50 trades, below the tested 61.2% (0.4% chance): check the fills, the
  chart and the Mode". Live, it also sends one alert.

Before 30 trades it shows "Win rate check: from 30 trades (n so far)". `test_v38_win_rate_check` checks that the line
is in line at 61.2% and that a tested rate of 90% gives the warning. It checks the warning's chance against the
report's to 0.05 points, one alert live, and the same trades. All 27 NinjaTrader v3.8 tests pass. Re-import the file to
get it.

**U14 (2026-11-03): the week's summary.** Live, on Fridays, after the day's summary (U7), one more alert and Output
line: "Week done (from 2026-11-02): +$1,234.50 in 9 trades (6 winners); this month +$2,345.00, total $8,214.00". The
week runs Monday to Friday by the 09:30 session. A Friday holiday sends none that week.

`test_v38_day_summary` now also checks one week summary per live Friday, its Monday, and its P/L and trade count
against the sum of that week's journal DAY lines. The trades are unchanged. Re-import the file to get it.

**U15 (2026-11-03): "Today" on the dashboard: what the bot may do, and when it next looks.** A new line under
"Trades today", for example:
- "Today: longs yes; shorts no (uptrend: above the 50-session average); next entry check 11:30 (in 12 min)";
- "Today: longs no (after a big up day); shorts yes; …";
- "Today: no entries (calm stretch: the last 10 sessions' ranges are small); …";
- "Today: no entries (today's loss budget is used up)", "… (holiday / half day)", and "shorts after 14:00 (Fed day)".

After the 15:00 check it says "no more entry checks today (the last is 15:00)". It answers "why isn't it trading?"
without reading the code.

`test_v38_today_line` reads the line at every bar of the 5-minute sample. It checks that no entry was taken against it:
a long only under "longs yes", a short only under "shorts yes" (or after 14:00 on a Fed day). It also checks the next
check's time and countdown at every bar from 10:00 to 15:00, and that the trades are unchanged. All 28 NinjaTrader
v3.8 tests pass. Re-import the file to get it.

## G38: trapped buyers at the high of the day, order flow from volume (registered 2026-11-03, before its run)

**The idea, from the user's @chicago_trades clip.** At the high of the day: retail stops are run, fresh sellers fill,
and the most aggressive buyers are trapped (the candle closes below where they bought, with a large upper wick). The
next candle closes below them. Then short, with the stop above the high and the target at the low of the day. The
mirror applies at the low. The clip uses bid/ask order flow. The closest test the data allows uses NQ futures' real
traded volume.

**Rules (NQ futures, 5-minute bars from 1-minute, New York time, regular session):**
- **The trap bar, at the high (a short):** from 10:00 to 15:00, a bar whose high is a new high of the day. Its volume
  is at least 1.5 times the average of the 20 bars before it, the stops being run. It closes in the lower half of
  its range, with an upper wick at least half the bar, so the buyers are trapped.
- **The confirmation:** the next bar closes below the trap bar's low.
- **Entry:** at the open of the bar after the confirmation. The stop is one tick above the trap bar's high. The
  target is the low of the day as it stands at the entry, but at least 1R away; if the low is nearer, the target is
  1R.
- **The exit:** the stop, the target, or the 15:55 bar's close. A bar that reaches both counts as the stop.
- **A long:** the mirror, at a new low of the day.
- **Limits:** one trade a day per side, and a stop distance of 4-40 points.
- **Costs per MNQ:** $1.24 in fees, 1 tick of slippage on the entry and on stop and time exits; the target is a limit.

**Pass (stage 1, the edge per contract):** daily t ≥ 1.65 and positive net on each of NQ 2015-2018, 2019-2021 and
2022-July 2025. If it passes, stage 2 adds it to the bot (in the trades the bot isn't in) on the account.

**G38 result (run once, 2026-11-03): rejected; rare, and it loses.** On ten years of NQ futures the full setup came up
52 times. All three of the clip's conditions together are rare on 5-minute bars: a new extreme on heavy volume, a
trapped close, and a confirming close beyond the bar. It lost money in two of the three periods and was flat in the
first. About 2 trades in 3 were stopped, and only 0-20% reached the low (high) of the day.

| Per MNQ | Trades | Winners | Reached the target | $ / trade | Daily t |
|---|---|---|---|---|---|
| NQ 2015-2018 | 39 | 28.2% | 15.4% | −$0.09 | −0.01 |
| NQ 2019-2021 | 8 | 12.5% | 0.0% | −$44.86 | −2.06 |
| NQ 2022-Jul 2025 | 5 | 20.0% | 20.0% | −$17.44 | −0.34 |

The clip's 241-point day is real, and the pattern did catch some big moves (a best trade of 6.4R). Read from price and
total volume, though, the "trapped buyers" are not a repeatable edge. Whether bid/ask order flow (who hit what,
at what size) adds one can only be tested with that data (`verification/noise_v2/g38_trapped.csv`).

## G39: the same bot on a 100K or 150K account (registered 2026-11-03, before its run)

**The idea:** one 50K account caps the bot at $900 a day and a $2,000 trailing floor. Every sizing fix since G5 has
run into those two numbers. A bigger account raises both, and the bot's sizing follows its limits automatically.
The rules used, typical for these sizes (Topstep-style):
- **100K:** a $3,000 end-of-day trailing drawdown and a $2,000 daily loss.
- **150K:** a $4,500 trailing drawdown and a $3,000 daily loss.

**The variants.** Growth mode with G6's time stop, its money limits scaled by the account (x2 or x3). Every trading
rule and the max loss per contract are unchanged.
- **100K:** daily budget $1,800, trailing drawdown $2,000 x 1.5 = $3,000, 2 starting contracts, up to 30.
- **150K:** daily budget $2,700, trailing drawdown $4,500, 3 starting contracts, up to 45.

Contracts are still added per $1,500 of profit.

**Measured:**
- G35's 89 start dates (a new account every quarter, 21 months each, NinjaTrader's execution, 5-minute bars): the
  median and mean net, the 10th percentile, and the share of accounts lost (under $100 above their own floor) or
  frozen;
- the window (Jan 2025-Oct 2026) with the usual runner.

**Adopt (as new Modes "Funded growth 100K" and "Funded growth 150K" in MnqNoiseV38.cs) only if:**
- the share of dead accounts is no higher than the 50K's on both NQ and the index;
- the median net is higher than the 50K's on both;
- the window's net is higher, the floor never touched, and no day reaches its account's daily limit.

**G39 result (run once, 2026-11-03): rejected; scaling the size up with the account loses more accounts.**

| 89 start dates, 21 months | 50K (now) | 100K, 2 to 30 contracts | 150K, 3 to 45 contracts |
|---|---|---|---|
| dead, NQ / index | 7 / 7 | 14 / 19 | 15 / 23 |
| median net, NQ / index | $22,925 / $23,070 | $13,329 / $23,241 | $10,614 / $10,242 |
| mean net, NQ / index | $21,333 / $22,498 | $30,192 / $33,696 | $60,480 / $40,263 |

The means rise: the accounts that survive make far more (NQ from 2015: $572k at 100K, $1.09M at 150K). But starting at
2-3 contracts risks the larger floor as fast as it grows. More than twice as many accounts die, and the window itself
sat at its floor from early on (5-minute bars: −$1,621 at 100K, −$1,939 at 150K)
(`verification/noise_v2/g39_account_size.csv`, `g35_start_dates_acct*.csv`).

## G40: a bigger account at the 50K's size (registered 2026-11-03, before its run)

**The idea, from G39:** keep the 50K's trading exactly (1 starting contract, +1 per $1,500, up to 15, $187.50 a
contract). Let the bigger account's limits act as cushion, not size:
- **100K:** daily budget $1,800, trailing drawdown $3,000;
- **150K:** daily budget $2,700, trailing drawdown $4,500.

A bad start then has $3,000-4,500 to burn through instead of $2,000.

**Adopt (as Modes "Funded growth 100K" and "Funded growth 150K") only if, on G35's 89 start dates:**
- fewer dead accounts than the 50K on both NQ and the index;
- a median net at least the 50K's on both;
- and on the window: at least the 50K's net, the floor never touched, and no day at its daily limit.

**G40 result (run once, 2026-11-03): adopted as two new modes.** The 50K's size on a bigger account's limits passes
every part of the rule.

| | 50K (Funded growth) | 100K at the 50K's size | 150K at the 50K's size |
|---|---|---|---|
| dead, of 35 NQ starts | 7 | 5 | 4 |
| dead, of 54 index starts | 7 | 3 | 1 |
| median net per 21-month account, NQ / index | $22,925 / $23,070 | $27,233 / $35,363 | $27,990 / $35,397 |
| mean net, NQ / index | $21,333 / $22,498 | $32,385 / $34,361 | $37,440 / $41,421 |
| 10th percentile, NQ / index | −$460 / $444 | $1 / $4,807 | $930 / $5,756 |
| window, 5 / 30 min (NinjaTrader) | $18,549 / $28,620 | $24,041 / $44,330 | $27,314 / $51,171 |
| worst day on the window, 5 min (daily loss rule) | −$899 ($1,000) | −$1,720 ($2,000) | −$1,962 ($3,000) |

The floor was never touched on the window, NQ or the index, at either bar length.

**Why it works:**
- the larger trailing drawdown absorbs the bad starts that end 50K accounts;
- the larger daily budget lets the bot keep trading on its strong days, where the 50K's $900 stopped it.

The size per trade and the steps are the 50K's, so the bigger account adds cushion, not risk
(`verification/noise_v2/g40_account_cushion.csv`, `g35_start_dates_cush*.csv`).

**In MnqNoiseV38.cs:**
- **Funded growth 100K:** budget $1,800 a day, a $3,000 trailing floor, loss guard $1,900.
- **Funded growth 150K:** budget $2,700, a $4,500 floor, loss guard $2,850.

Everything else is Funded growth's. The startup check's loss-guard warning now follows the account's daily rule.
`test_v38_bigger_accounts_agree` checks NinjaTrader against the Python model, trade for trade, for both modes at 5 and
30 minutes, with each mode's budget and guard applied. All 21 NinjaTrader v3.8 tests pass.

## G41: faster contract steps on the bigger accounts (registered 2026-11-03, before its run)

**The idea, from G5 and G40:** on a 50K, a contract per $1,000 of profit (instead of $1,500) ran accounts into the
$2,000 floor (G5). The 100K and 150K modes have $3,000-4,500 of floor and twice or three times the daily budget, so
the faster growth may now survive.

**Variants:** Funded growth 100K and 150K with `profit_step` $1,000; everything else as G40 adopted.

**Adopt (in that mode) only if, against the same mode with $1,500:**
- no more dead accounts on G35's 89 start dates, on NQ or the index;
- a higher median net on both;
- a higher window net at 5 and 30 minutes, the floor never touched, and no day at the daily limit.

**G41 result (run once, 2026-11-03): rejected; faster steps still lose accounts on a bigger account.**

| 89 start dates, 21 months | 100K, $1,500 | 100K, $1,000 | 150K, $1,500 | 150K, $1,000 |
|---|---|---|---|---|
| dead, NQ / index | 5 / 3 | 6 / 7 | 4 / 1 | 4 / 5 |
| median net, NQ / index | $27,233 / $35,363 | $37,871 / $39,020 | $27,990 / $35,397 | $47,432 / $43,235 |
| NQ from 2015, 30 min (NinjaTrader) | $485,904 | **$1, at the floor** | $655,739 | **$1, at the floor** |

The $1,000 step makes the typical account more, but it loses more of them. On NQ from 2015, both bigger accounts
went back to the floor early on 30-minute bars, as the 50K did in G5. The $1,500 step stays in all three Funded growth
modes (`verification/noise_v2/g41_steps_big.csv`, `g35_start_dates_cush*s1000.csv`).

## G42: the bigger-account modes on Apex's rules (registered 2026-11-03, before its run)

**The rules, as published for 2026 (third-party summaries; the user should confirm on the firm's site).**
- **Topstep:** a $3,000 / $4,500 maximum loss on the 100K / 150K, trailing the closing balance up to the start, with a
  $2,000 / $3,000 daily loss limit. That is what Funded growth 100K / 150K (G40) assume.
- **Apex, end-of-day accounts:** a $3,000 / $4,000 trailing drawdown with a $1,500 / $2,000 daily loss limit, so a
  tighter day.

**The variants:** G40's sizing (the 50K's), with the bot's daily budget at 90% of Apex's limit:
- **Apex 100K:** $1,350 a day, a $3,000 trailing floor.
- **Apex 150K:** $1,800 a day, a $4,000 floor.

**Adopt (as Modes "Funded growth Apex 100K" / "Apex 150K") on G40's rule against the 50K:**
- fewer dead accounts on both NQ and the index (G35's 89 start dates);
- a median net at least the 50K's on both;
- a window net at least the 50K's at 5 and 30 minutes, the floor never touched, and no day at the daily limit.

**G42 result (run once, 2026-11-03): adopted as two more modes.** On Apex's rules both pass G40's bar against the 50K.

| | 50K | Apex 100K | Apex 150K |
|---|---|---|---|
| dead, NQ / index | 7 / 7 | 5 / 2 | 4 / 2 |
| median net, NQ / index | $22,925 / $23,070 | $28,447 / $34,472 | $27,454 / $35,363 |
| 10th percentile, NQ / index | −$460 / $444 | $1 / $5,843 | $987 / $6,748 |
| window, 5 / 30 min | $18,549 / $28,620 | $20,512 / $37,838 | $24,041 / $44,330 |
| worst day, window to histories (daily loss rule) | −$899 ($1,000) | −$1,352 ($1,500) | −$1,805 ($2,000) |

The floor was never touched (`verification/noise_v2/g42_apex.csv`, `g35_start_dates_apex*.csv`).

**In MnqNoiseV38.cs:**
- **Funded growth Apex 100K:** $1,350 a day, a $3,000 floor, loss guard $1,425.
- **Funded growth Apex 150K:** $1,800, $4,000, $1,900.

The 100K / 150K modes are Topstep's ($2,000 / $3,000 daily, $3,000 / $4,500 trailing).

**Caveats:**
- **Where Apex's trail stops.** Published sources differ: at the start plus $100, or later. The bot assumes the start,
  as with the others, so an account whose trail stops higher has a little less cushion than modelled.
- **The source of the rules.** These come from third-party summaries of 2026's rules; check them on the firm's site.

`test_v38_bigger_accounts_agree` now covers all four modes at 5 and 30 minutes, trade for trade. All 25 NinjaTrader
v3.8 tests pass.

## G43: how long to +$50,000, by account (registered 2026-11-03, before its run)

**The question, the user's goal:** how long one account takes to reach +$50,000, and how often it is lost first.

**The test:**
- **Starts:** a new account every six months, run for up to 60 months: NQ from April 2015 to July 2020, the index
  from April 2011 to September 2021.
- **Accounts:** growth mode (50K), and the four bigger-account modes (G40, G42).
- **Execution:** NinjaTrader's, 5-minute bars.

**Reported for each mode:**
- the share that reach +$50,000 within 5 years;
- the median months to get there (among those that do);
- the share lost or frozen first.

Nothing is chosen here. It tells the user which account to trade for the goal.

**G43 result (run once, 2026-11-03): the 150K reaches +$50,000 fastest, and loses the fewest accounts first.**

| starts every 6 months, up to 5 years | 50K | Topstep 100K | Topstep 150K | Apex 100K | Apex 150K |
|---|---|---|---|---|---|
| reached +$50,000, NQ (11 starts) | 8 | 9 | 9 | 9 | 9 |
| reached +$50,000, index (21 starts) | 18 | 20 | **21** | 20 | **21** |
| median months to +$50,000, NQ | 28.0 | 26.8 | **25.5** | 27.1 | 26.8 |
| median months to +$50,000, index | 29.4 | 23.6 | **20.9** | 24.5 | 24.3 |
| quickest quarter of starts, index | 27.7 | 19.1 | **17.5** | 20.6 | 19.3 |
| slowest start that got there, index | 46.3 | 42.1 | **38.8** | 44.9 | 42.1 |
| lost or frozen before +$50,000, NQ / index | 3 / 3 | 2 / 1 | 2 / **0** | 2 / 1 | 2 / **0** |
| median net after 5 years, NQ / index | $95,972 / $108,909 | $184,866 / $193,629 | $243,845 / $246,712 | $156,133 / $163,989 | $184,866 / $193,629 |

**Every lost account died in its first few months.** It made under 200 trades, and none had reached +$50,000:
- On the 50K: NQ starting 2015-04, 2019-04 and 2019-10; the index starting 2011-04, 2013-04 and 2019-04.
- On the 150K: only NQ starting 2019-04 and 2019-10.

Two kinds of death:
- Some fell to the floor before the first +$2,000.
- Others got far enough up for the floor to lock at the start balance, then came back to it.

**Once an account is a few months in and well above its floor, none was lost before the goal.**

**Caveats:**
- **Overlap.** The starts overlap, so they are not independent tries.
- **No withdrawals.** The test takes no payouts. Withdrawing profit lowers the balance and slows the next contract
  steps.
- **Firm rules not modelled.** It ignores the firms' consistency and payout rules, and the bigger accounts' higher fees.
- **A backtest.** These are past markets, not a promise.

(`verification/noise_v2/g35_start_dates_{base,cush100,cush150,apex100,apex150}_60m.csv`.)

## G44: no second try after the time stop (registered 2026-11-03, before its run)

**The idea, from G6:** the time stop closes a trade that is still losing an hour after its fill. That signal often
comes back at a later half-hour check the same day, and the bot buys (or sells) the same stalled move again.

**The variants** (`ts_block` in `mnqbot/noise.py`, on Funded growth with its 60-minute time stop):
- **side:** after a time-stop exit, no new entry on that side for the rest of the session;
- **day:** after a time-stop exit, no new entry at all for the rest of the session.

**Adopt (the better of the two by window net) only if, against Funded growth as it is:**
- a higher net on all three 5-minute sets (the window, NQ from 2015, the index from 2011), in both the chart's
  execution and NinjaTrader's;
- the floor is never touched;
- there are no more days at −$1,000.

The 30-minute runs are reported, not judged.

**G44 result (run once, 2026-11-03): rejected; the second try after a time stop pays.**

| 5-minute net | as it is | side | day |
|---|---|---|---|
| window, chart / NinjaTrader | $18,516 / $18,549 | $17,246 / $17,354 | $17,246 / $17,354 |
| NQ from 2015, chart / NinjaTrader | $277,322 / $267,571 | $255,838 / $252,107 | $253,524 / $251,161 |
| index from 2011, chart / NinjaTrader | $407,796 / $404,250 | $395,045 / $389,234 | $392,643 / $386,830 |

- **Both variants made less on every set, in both executions.** The win rate rose a little (61.2% to 62.8% on the
  window), but the blocked re-entries were worth more than the losers they avoided.
- **30-minute bars (reported, not judged).** On the chart's execution, NQ from 2015 with either block went back to the
  floor after 118 trades and stopped there ($0 net). As it is, the same run made $210,145.

The time stop stays as G6 adopted it, with re-entries allowed (`verification/noise_v2/g44_ts_block.csv`;
`ts_block` stays in `mnqbot/noise.py`, off).

## G45: the take-profit distance, re-checked with the time stop (registered 2026-11-03, before its run)

**The idea:** the take-profit (2 noise units from the fill) was set before G6's time stop. Since then, slow trades
end at 60 minutes, so the trades still open later are the ones that are already working. A different target may now
pay more, in either direction:
- nearer, banking more of the winners that later fall back to the lock;
- farther, letting the working trades run.

**The variants:** Funded growth with `take_profit` 1.75 and 2.5; everything else as it is, with the 60-minute time
stop.

**Adopt (the better by window net) only if, against 2.0:**
- a higher net on all three 5-minute sets (the window, NQ from 2015, the index from 2011), in both the chart's
  execution and NinjaTrader's;
- the floor is never touched;
- there are no more days at −$1,000.

The 30-minute runs are reported, not judged.

**G45 result (run once, 2026-11-03): rejected; 2.0 stays.** Both distances made less on every 5-minute set, in both
executions.

| 5-minute net, chart / NinjaTrader | 1.75 | 2.0 (as it is) | 2.5 |
|---|---|---|---|
| window | $15,524 / $15,608 | **$18,516 / $18,549** | $16,438 / $16,068 |
| NQ from 2015 | $262,411 / $254,828 | **$277,322 / $267,571** | $268,409 / $266,595 |
| index from 2011 | $355,721 / $349,475 | **$407,796 / $404,250** | $373,933 / $371,535 |

- **The nearer target** won about as often (61.4% vs 61.2% on the window) and took more trades, but each winner was
  smaller.
- **The farther target** raised the profit factor on NQ (1.591 vs 1.541), but cost about $2,000 on the window and $34,000
  on the index.
- **30 minutes (reported, not judged).** 1.75 made more on the window in NinjaTrader's execution ($30,665 vs $28,620),
  and less on both histories.

The floor was never touched (`verification/noise_v2/g45_take_profit.csv`).

## G46: how much the lock keeps, re-checked with the time stop (registered 2026-11-03, before its run)

**The idea:** once a trade has been 0.35 max losses in profit, its stop moves to the entry plus 2.5 points ($5 a
contract), so it can't become a loser. That 2.5 was set before the time stop. Since then, a locked trade is exempt from
the time stop and runs to its target, its line stop or the lock. Moving the lock's stop changes what those trades keep:
- nearer the entry, fewer locked trades are shaken out by a pullback;
- farther, more is banked when they are.

**The variants:** Funded growth with `lock_plus` 1.0 and 5.0 points; everything else as it is.

**Adopt (the better by window net) only if, against 2.5:**
- a higher net on all three 5-minute sets (the window, NQ from 2015, the index from 2011), in both the chart's
  execution and NinjaTrader's;
- the floor is never touched;
- there are no more days at −$1,000.

The 30-minute runs are reported, not judged.

**G46 result (run once, 2026-11-03): rejected; 2.5 stays.**

| 5-minute net, chart / NinjaTrader | 1.0 | 2.5 (as it is) | 5.0 |
|---|---|---|---|
| window | $18,175 / $18,297 | **$18,516 / $18,549** | $12,296 / $14,395 |
| NQ from 2015 | $276,503 / $274,007 | $277,322 / $267,571 | $256,364 / $255,589 |
| index from 2011 | $410,206 / $406,767 | $407,796 / $404,250 | $425,144 / $420,220 |

- **1.0 is close to a tie.** It made more on the index in both executions and on NQ in NinjaTrader's (+$6,436), but
  less on the window (−$341 / −$252) and on NQ in the chart's (−$819). The window is the market the user trades, so
  the rule keeps 2.5.
- **5.0** made the most on the index, and far less on the window (−$6,220).
- **30 minutes (reported, not judged).** 1.0 made more on the window ($28,125 / $31,233 against $25,834 / $28,620)
  and the index, and less on NQ.

The floor was never touched (`verification/noise_v2/g46_lock_plus.csv`).

## G47: an earlier last entry (registered 2026-11-03, before its run)

**The idea, from G8:** entries at the 15:30 check changed little (G8). The other way has not been tried with the time
stop on. A trade entered at the 14:30 or 15:00 check has at most 60-90 minutes before the 16:00 exit, so it often
can't reach its take-profit (2 noise units), while it can still take its full stop.

**The variants:** Funded growth with the last entry check at 14:00 (`last_entry_end` 840) and at 14:30 (870), instead
of 15:00 (900); everything else as it is.

**Adopt (the better by window net) only if, against 15:00:**
- a higher net on all three 5-minute sets (the window, NQ from 2015, the index from 2011), in both the chart's
  execution and NinjaTrader's;
- the floor is never touched;
- there are no more days at −$1,000.

The 30-minute runs are reported, not judged.

**G47 result (run once, 2026-11-03): rejected; the 15:00 check stays.** An earlier last entry made far less
everywhere.

| 5-minute net, chart / NinjaTrader | 14:00 | 14:30 | 15:00 (as it is) |
|---|---|---|---|
| window | $8,626 / $10,781 | $12,056 / $12,069 | **$18,516 / $18,549** |
| NQ from 2015 | $198,550 / $195,919 | $229,325 / $226,166 | **$277,322 / $267,571** |
| index from 2011 | $323,144 / $326,147 | $355,633 / $355,300 | **$407,796 / $404,250** |

The afternoon entries are among the bot's best: dropping the 14:30 and 15:00 checks lost about $10,000 on the window
and $80,000 on NQ. The profit factor rose on 30-minute bars (2.17 against 1.89 on the window), but the net still fell.
Together with G8 (15:30 changed little), 15:00 is the right last check (`verification/noise_v2/g47_last_entry.csv`).

## G48: the big-day rule's lookback (registered 2026-11-03, before its run)

**The idea:** after a session whose range was over 1.5 times the average range, the bot takes no entries the next
day in that session's direction (v2.3). G27 re-checked the 1.5 with the time stop on; the average's length, 10
sessions, has not been re-checked since v2.3. The variants:
- **5 sessions:** a shorter average follows a change of pace faster;
- **20 sessions:** a longer one marks fewer days as big in a stretch of large ranges.

**The variants:** Funded growth with `big_day_n` 5 and 20; everything else as it is.

**Adopt (the better by window net) only if, against 10:**
- a higher net on all three 5-minute sets (the window, NQ from 2015, the index from 2011), in both the chart's
  execution and NinjaTrader's;
- the floor is never touched;
- there are no more days at −$1,000.

The 30-minute runs are reported, not judged.

**G48 result (run once, 2026-11-03): rejected; 10 stays.**

| 5-minute net, chart / NinjaTrader | 5 sessions | 10 (as it is) | 20 sessions |
|---|---|---|---|
| window | $8,919 / $14,971 | **$18,516 / $18,549** | $17,459 / $16,928 |
| NQ from 2015 | **$1 / $1, at the floor after 139 trades** | $277,322 / $267,571 | $282,013 / $269,195 |
| index from 2011 | $385,619 / $383,372 | $407,796 / $404,250 | $409,538 / $402,921 |

- **5 sessions lost the NQ account in its first months** and froze it at the floor, on both executions. A short average
  marks too many days as big, and the bot is then kept out of the next day's move.
- **20 sessions** made a little more on NQ and the index in the chart's execution, but less on the window in both
  executions (−$1,057 / −$1,621).

(`verification/noise_v2/g48_big_day_n.csv`.)

## G49: the calm-stretch rule's windows (registered 2026-11-03, before its run)

**The idea:** no new entries while the last 10 sessions' average range is under 0.7 times the last 40 sessions'
(v2.5). G28 re-checked the 0.7 with the time stop on; the two windows have not been re-checked since v2.5. The variants:
- **5 against 40:** reacts to a quiet spell, and its end, twice as fast;
- **10 against 60:** a longer baseline, so a long run of large ranges sets a higher bar for "calm".

**The variants:** Funded growth with (`calm_short`, `calm_long`) = (5, 40) and (10, 60); everything else as it is.

**Adopt (the better by window net) only if, against (10, 40):**
- a higher net on all three 5-minute sets (the window, NQ from 2015, the index from 2011), in both the chart's
  execution and NinjaTrader's;
- the floor is never touched;
- there are no more days at −$1,000.

The 30-minute runs are reported, not judged.

**G49 result (run once, 2026-11-03): rejected; (10, 40) stays.**

| 5-minute net, chart / NinjaTrader | 5 / 40 | 10 / 40 (as it is) | 10 / 60 |
|---|---|---|---|
| window | **$21,342 / $21,365** | $18,516 / $18,549 | $14,684 / $14,721 |
| NQ from 2015 | $259,072 / $251,381 | **$277,322 / $267,571** | $244,790 / $241,848 |
| index from 2011 | $396,542 / $390,894 | **$407,796 / $404,250** | $374,577 / $371,471 |

- **5 / 40 made $2,800 more on the window** (and on 30-minute bars in NinjaTrader's execution, $32,879 against $28,620).
  But it made $16,000-18,000 less on NQ and $11,000-13,000 less on the index. A gain on the recent window alone, with
  losses over the ten and fifteen years, is a fit to the window, not an edge, which is what the rule guards against.
- **10 / 60** made less everywhere.

(`verification/noise_v2/g49_calm_windows.csv`.)

## G50: the max loss per contract, re-checked with the time stop (registered 2026-11-03, before its run)

**The idea:** each trade's stop is the line (0.24 noise units past it) or $187.50 a contract from the fill, whichever
is nearer ($250 after a loser), from v3.6's sizing scan. The time stop now closes most slow losers before either is
reached, so the cap matters mostly for fast moves against the trade. The variants:
- **nearer, $150 / $200:** cuts those fast losses;
- **farther, $225 / $300:** lets the line stop do more of the work.

Sizing follows: the daily budget and the floor's room fit contracts at the new stop.

**The variants:** Funded growth with `max_loss_per_trade` 150 and 225; the after-loss stop keeps its 4:3 ratio
(`after_loss_ml_mult` 250 / 187.5); everything else as it is.

**Adopt (the better by window net) only if, against $187.50:**
- a higher net on all three 5-minute sets (the window, NQ from 2015, the index from 2011), in both the chart's
  execution and NinjaTrader's;
- the floor is never touched;
- there are no more days at −$1,000.

The 30-minute runs are reported, not judged.

**G50 result (run once, 2026-11-03): rejected; $187.50 stays. The window and the histories pull opposite ways.**

| 5-minute net, chart / NinjaTrader | $150 / $200 | $187.50 / $250 (as it is) | $225 / $300 |
|---|---|---|---|
| window | $11,051 / $9,083 | $18,516 / $18,549 | **$19,792 / $20,036** |
| NQ from 2015 | **$278,052 / $279,183** | $277,322 / $267,571 | $273,022 / $271,682 |
| index from 2011 | **$429,264 / $425,660** | $407,796 / $404,250 | $373,844 / $343,016 |

- **$150 made more on both histories,** up to $21,000 on the index, with more winners (62.6% against 61.7%). But it
  made $7,500-9,500 less on the window: in 2025-2026's larger swings a nearer stop is hit by normal moves (profit
  factor 1.42 against 1.82).
- **$225 made more on the window** (+$1,300-1,500), but less on both histories (−$34,000 to −$61,000 on the index).
- **$187.50 sits between them,** and is the only one that does well on all three. No variant passes the rule.

On 30-minute bars (reported, not judged), $150 also made more on both histories and less on the window
(`verification/noise_v2/g50_max_loss.csv`).

## G51: a max loss that follows the noise (registered 2026-11-03, before its run)

**The idea, from G50:** a fixed $150 stop did best on the histories, a fixed $225 on the window. If that is the market's
noise level speaking, a max loss set from the noise should do well everywhere. At each half-hour check, the max loss
per contract becomes k times the noise (sigma, the line's distance) times the price times $2. The after-loss stop keeps
its 4:3 ratio, and the contracts are sized from it as now.

**Calibration (before the run, from the noise only, no results):** the median noise at a check is $446 a contract on
the index (2011-2026), $458 on NQ and $402 on the window. So $187.50 is 0.42 of the index's median noise and 0.47 of the
window's.

**The variants:** Funded growth with `ml_sigma` 0.42 and 0.47 (`mnqbot/noise.py`, off by default); everything else as
it is. (The measurement found the window slightly calmer than the scaled histories, not wilder, which argues against
the idea; it is run as registered.)

**Adopt (the better by window net) only if, against the fixed $187.50:**
- a higher net on all three 5-minute sets (the window, NQ from 2015, the index from 2011), in both the chart's
  execution and NinjaTrader's;
- the floor is never touched;
- there are no more days at −$1,000.

The 30-minute runs are reported, not judged.

**G51 result (run once, 2026-11-03): rejected; the fixed $187.50 stays.**

| 5-minute net, chart / NinjaTrader | fixed $187.50 (as it is) | 0.42 × noise | 0.47 × noise |
|---|---|---|---|
| window | **$18,516 / $18,549** | $12,441 / $9,651 | $15,142 / $14,121 |
| NQ from 2015 | $277,322 / $267,571 | $283,587 / $293,949 | $287,327 / $285,063 |
| index from 2011 | **$407,796 / $404,250** | $389,200 / $371,638 | $376,278 / $365,062 |
| days past −$1,000, index (chart) | 0 | 4 | 3 |

- **More winners, less money.** The win rate rose to 65-66% on the window, but the net fell $3,400-8,900. Early
  checks have little noise, so their stops are tight and normal moves hit them; late checks have wide stops and lose
  more when they're wrong.
- **It broke the daily rule.** On the index, in the chart's execution, 3-4 days went past −$1,000 (worst −$1,351);
  the fixed stop has none.
- **30 minutes (reported, not judged).** On the chart's execution, both variants lost the NQ account in its first months.

Only NQ improved. `ml_sigma` stays in `mnqbot/noise.py`, off (`verification/noise_v2/g51_ml_sigma.csv`).

## G52: no entries on monthly options expiration days (registered 2026-11-03, before its run)

**The idea (not tested in any round before):** on the third Friday of each month, the monthly index options expire.
Dealers' hedging of large open positions near the strikes tends to pin the price there ("pinning"), damping trends.
This bot makes its money on trend days, so its breakouts may fail more on those days.

**The variant:** Funded growth, with every month's third Friday (2011-2026) added to the dates with no new trades
(`skip_dates`, as the holidays are); a trade already open runs as usual. Everything else as it is.

**Adopt only if, against Funded growth as it is:**
- a higher net on all three 5-minute sets (the window, NQ from 2015, the index from 2011), in both the chart's
  execution and NinjaTrader's;
- the floor is never touched;
- there are no more days at −$1,000.

The 30-minute runs are reported, not judged.

**G52 result (run once, 2026-11-03): rejected; the bot trades expiration Fridays.**

| 5-minute net, chart / NinjaTrader | as it is | no entries on the third Friday |
|---|---|---|
| window | $18,516 / $18,549 | $19,539 / $19,556 |
| NQ from 2015 | **$277,322 / $267,571** | $262,800 / $259,487 |
| index from 2011 | **$407,796 / $404,250** | $397,904 / $370,819 |

Skipping them helped a little on the window (+$1,000), but cost $8,000-15,000 on NQ and $10,000-33,000 on the index.
Over the long run, expiration Fridays are profitable days for the bot, not pinned ones. 30-minute bars agree (less
everywhere). (`verification/noise_v2/g52_opex.csv`.)

## G53: no entries against a big opening gap (registered 2026-11-03, before its run)

**The idea (not tested in any round before; the gap was only tested as a separate fade setup):** a day that opens far
from the prior close has its news already in the price. A breakout against the gap goes against the day's information
and may fail more often.

**The variant:** Funded growth, with `gap_block` 0.01. On a day whose 09:30 open is more than 1% from the prior 16:00
close, no entries against the gap's direction: no shorts after a gap up, no longs after a gap down. Everything else as
it is.

**Adopt only if, against Funded growth as it is:**
- a higher net on all three 5-minute sets (the window, NQ from 2015, the index from 2011), in both the chart's
  execution and NinjaTrader's;
- the floor is never touched;
- there are no more days at −$1,000.

The 30-minute runs are reported, not judged.

**G53 result (run once, 2026-11-03): rejected; trades against a big gap pay.**

| 5-minute net, chart / NinjaTrader | as it is | no entries against a gap over 1% |
|---|---|---|
| window | **$18,516 / $18,549** | $16,714 / $16,285 |
| NQ from 2015 | **$277,322 / $267,571** | $266,338 / $263,007 |
| index from 2011 | **$407,796 / $404,250** | $402,941 / $398,392 |

Blocking breakouts against the gap made less on every set, in both executions (−$1,800 to −$2,300 on the window). When
price breaks the noise line against a big gap, it is a reversal of the gap the bot does well to follow. 30-minute bars
were mixed (more on the index in the chart's execution, less on the window). `gap_block` stays in `mnqbot/noise.py`,
off (`verification/noise_v2/g53_gap.csv`).

**The user's Strategy Analyzer run, explained (2026-11-03).** The Output window said "data from 2026-05-03":
NinjaTrader's MNQ DEC26 history starts May 3, 2026, so no January-April bars existed and the start date changed
nothing. Given only data from May 3, the model makes 82 trades and $8,620.84 to Oct 16 on the stand-in data, against
NinjaTrader's 54 trades and $3,669.60 on DEC26. Before the September roll DEC26 was the back month, thinly traded, so
its prices aren't the front-month market the bot was tested on. The warning for this case now says so plainly:
"the data starts on 2026-05-03, after the start date 2026-01-02: this instrument has no earlier history here", and
names the fix (load MNQ 03-26, 06-26, 09-26 and merge them, or move the start date). `test_v38_data_check` covers it.

## G54: 30-minute bars for a new account (registered 2026-11-03, before its run)

**The question, from the user ("net profit back up to $25k"):** the same bot on 30-minute bars made $28,620 on the
window against $18,542 on 5-minute bars (NinjaTrader's execution; the user tests on 30-minute TradingView charts). Over
the histories, 5-minute bars made more (index $404,250 against $310,560). Is the 30-minute chart as safe for a new 50K
account?

**The test:** G35's 89 start dates (21 months each), Funded growth on 30-minute bars, NinjaTrader's execution, against
G35's 5-minute results (`research/g35_start_dates.py` with `SCAN_MINUTES=30`).

**Recommend the 30-minute chart only if:** it loses (room under $100) or freezes no more accounts than 5 minutes on
either NQ or the index, and its median net is at least 5 minutes' on both.

**G54 result (run once, 2026-11-03): not recommended by the rule; more profit, more lost accounts on NQ.**

| 89 start dates, 21 months | 5-minute | 30-minute |
|---|---|---|
| lost or frozen, NQ | 7 of 35 (20%) | **10 of 35 (29%)** |
| lost or frozen, index | 7 of 54 | 7 of 54 |
| median net, NQ / index | $22,925 / $23,070 | **$28,713 / $24,081** |
| best 10%, NQ / index | $39,277 / $39,303 | $62,903 / $44,049 |
| worst 10%, NQ / index | −$461 / $444 | $1 / $396 |

On 30-minute bars the typical account makes more ($24,000-29,000 against $23,000 in 21 months) and the best ones far
more, but on NQ 3 more accounts in 35 were lost. The rule asked for no more lost accounts, so 5 minutes stays the
recommendation. It is the user's choice: 30 minutes trades for more profit with a higher chance of losing the account
(`verification/noise_v2/g35_start_dates_base_30min.csv`; MnqNoiseV38.cs runs on either chart, trade for trade with the
model).

## G55: why most days have no trade (measured 2026-11-03, at the user's question)

The user asked why the bot doesn't trade on about 7 days in 10. Each day filter was turned off in turn (5-minute bars,
the chart's execution, Funded growth; `research/g55_filters_off.py`, `verification/noise_v2/g55_filters_off.txt`):

| | days with a trade: window / NQ / index | net: window / NQ / index |
|---|---|---|
| **as it is** | 29% / 37% / 36% | **$18,516 / $277,322 / $407,796** |
| no calm-stretch filter | 32% / 39% / 38% | $13,199 / $271,131 / $399,800 |
| no range-position filter | 29% / 37% / 36% | $17,824 / $259,075 / $410,742 |
| no big-day rule | 31% / 39% / 38% | $9,060 / $251,746 / $382,762 |
| shorts in uptrends too | 43% / 46% / 45% | $16,058 / $293,623 / $390,564 |
| all four off | 51% / account lost / 53% | $13,727 / $0 / $313,115 |

- **Most quiet days are quiet because price never leaves the noise area.** The filters block only 2-3 days in 100
  each. Even with all of them off, half the days have no breakout.
- **Every filter that adds days costs money.** The days they block are mostly failed breakouts. With all four off, the
  NQ account was lost in its first months, and the index had a −$1,207 day.
- **Shorts in uptrends** adds the most days (+14 in 100). It made more on NQ (+$16,000) but less on the window
  (−$2,500) and the index (−$17,000).

More trading days, with this bot, means more losing trades. The way to trade more days without that is a second,
separate market (the same bot on the S&P 500 or the Russell 2000), whose trend days are not always the Nasdaq's. That
needs S&P data, not yet in hand.

## G56: the same bot on the S&P 500, as a second market (registered 2026-11-03, before its run)

**The idea, from G55 and the user ("that many days without trading is horrible"):** with this bot, more trading days in
the Nasdaq means more losing trades (G55). A second market whose trend days are not always the Nasdaq's can add trading
days without that. Rounds forty-seven and forty-eight found no edge on the S&P, but with v2.x's fixed 10 contracts and
$350 stop; today's Funded growth (its own-stop sizing, lock, take-profit, time stop, filters) was never run there.

**The test:** Funded growth on MES (the S&P 500, $5 a point; HistData SPXUSD 1-minute bars scaled to the futures, as
round forty-seven), 5-minute bars, NinjaTrader's execution, its own $900 daily budget and $2,000 trailing floor. The max
loss per contract is the MNQ's in percent of price: $120 a contract ($160 after a loser), as $187.50 is about 0.31% of
MNQ at 30,000. Fees $0.62 a side, a tick of slippage.

**Passes only if:**
- it makes money in 2011-2018 and in 2019-Sep 2026, each on its own;
- its account never reaches the floor in either period;
- it has no day at −$1,000.

**Reported:** the days it trades, how many of them the Nasdaq bot (the index set) doesn't trade, and the correlation of
the two daily P/Ls.

**G56 result (run once, 2026-11-03): rejected; the bot has no edge on the S&P.**

| | 2011-2018 | 2019-Sep 2026 |
|---|---|---|
| MES trades / net | 1,819 / +$42,740 | 162 / **−$991, the account at the floor ($8 of room)** |
| MES winners / profit factor | 51.1% / 1.15 | 49.4% / 0.79 |
| MES worst day | **−$9,300** | −$599 |
| days MES traded and the Nasdaq bot didn't | 287 of 855 | 40 of 76 |
| correlation of the two daily P/Ls | 0.35 | 0.53 |

It would add trading days (about a third of its days are days the Nasdaq bot sits out). But from 2019 its account went
to the floor in its first months. 2011-2018 has a −$9,300 day, which only a data fault (a gap in the S&P bars held
across it) could make under a $900 budget; either way it fails. (The Nasdaq column for 2019 was the same single start
date, which G35 already counts among the lost starts.) This agrees with rounds forty-seven and forty-eight: the edge is
the Nasdaq's. `research/g56_mes.py`.

**How long to $53,000 on a new 50K (+$3,000), 2026-11-03.** G35's 89 start dates, 21 months each, Funded growth on
5-minute bars (`verification/noise_v2/g35_start_dates_base.csv`, column "days to 3k"; every other column unchanged):
78 of 89 got there. The median was 143 calendar days (about 4½ months): a quarter of starts within 97 days, a quarter
after 234 days. 9 got there within 2 months, 19 within 3 and 47 within 6. 11 (12%) were lost or frozen first. The
user's window, from 2025-01-02, took 13½ months (+$2,000 by late April 2025, then a flat stretch).

**+$3,000 in one week? (measured 2026-11-03, at the user's question).** The bot's trades at a fixed size, every calendar
week of the histories as a one-week try (NQ 2015-2025: 549 weeks; the index 2011-2026: 821 weeks), counting whether the
closed P/L reached +$3,000 before −$2,000 within the week. At 1 MNQ the bot averages about $100-108 a week.

| contracts on every trade | reached +$3,000 in the week, NQ / index | lost $2,000 first, NQ / index |
|---|---|---|
| 1 | 0% / 0% | 0% / 0% |
| 5 | 12.6% / 10.8% | 7.3% / 6.6% |
| 10 | 26.2% / 23.5% | 21.3% / 18.5% |
| 20 | 29.9% / 27.0% | 38.4% / 34.6% |
| 40 | 26.0% / 24.1% | 49.4% / 46.0% |

This is the best case: it ignores the $1,000 daily loss rule (at 10 MNQ one full stop is $1,875) and losses inside a
trade before it closes. No size makes +$3,000 in a week more likely than not. Past 10 contracts the account is lost more
often than the target is reached.

## G57: the bot's rules overnight (registered 2026-11-03, before its run)

**The idea, from the user's own trades (Oct 30 - Nov 3: 13 trades, +$3,804; all 3 trades opened between 18:00 and
03:00 New York won):** the bot trades only 09:30-16:00, and about 70% of days have no trade there (G55). The noise-area
breakout has never been run in the overnight sessions. (Round seven's half-hour "overnight drift" stream and G12's
Asian-range sweep were different setups.)

**The test:** Funded growth's rules, unchanged, run on two overnight sessions as if each were a day session of 6½
hours:
- **Asia:** 18:00-00:30 New York;
- **London:** 02:00-08:30.

Each session's own open, the close before it and its own 14-session noise make the lines. The entry checks run every
half hour from 30 minutes in until 1½ hours before its end, as by day, with every exit rule and the flat time at its
end. 5-minute bars, the chart's execution, NQ futures 2015-Jul 2025 and the index (CFD) 2011-Sep 2026, each split into
halves. Each session trades its own 50K, as a separate account.

**Passes (for a session) only if,** in all four halves (NQ 2015-2019, 2020-2025; the index 2011-2018, 2019-2026):
- the net is positive and the profit factor is at least 1.2;
- the account never reaches the floor.

A pass gets a second test beside the day bot (the shared daily budget) before any change to the file the user runs.

**G57 result (run once, 2026-11-03): rejected; the bot's breakout loses overnight in every period.**

| | Asia 18:00-00:30: net, profit factor | London 02:00-08:30: net, profit factor |
|---|---|---|
| NQ 2015-2019 | −$3,644, 0.72 (floor passed) | −$950, 0.88 (floor passed) |
| NQ 2020-2025 | −$1,383, 0.67 (at the floor) | −$1,902, 0.29 (at the floor) |
| index 2011-2018 | −$1,772, 0.83 (floor passed) | −$1,819, 0.85 (floor passed) |
| index 2019-2026 | −$3,092, 0.83 (floor passed) | +$4, 1.00 (at the floor) |

Overnight, a move past the noise area is not momentum: winners are 33-49%, and every account ends at or past the floor.
The bot's edge is the day session's. The user's overnight winners came from their own reading of the market, which no rule
here reproduces (`research/g57_overnight.py`).

## G58: the user's own style as rules (registered 2026-11-03, before its run)

**Where the rules come from:** the user's 13 trades of Oct 30 - Nov 3 (+$3,804), set against Yahoo's 1-minute MNQ bars
for those days. Every short went in near the top of the last 2 hours' range, after price had risen over the hour before.
Every long went in at the bottom after a drop. The 5 shorts at the very top after a rise of 36+ points all won; the
losers were shorts without that stretch. The stop averaged 43 points, and winners 107 points over about 2 hours. In
percent of price, that is a 0.16% stop and a 0.38% target.

**The rules (24 hours a day, 5-minute bars, one trade at a time):**
- **Short:** at a bar close in the top 5% of the last 2 hours' range (24 bars), after a rise of at least 0.13% of price
  over the last hour (12 bars). The mirror for longs: the bottom 5% after a fall of at least 0.13%.
- **The trade:** in at the next bar's open, a stop 0.16% away, a target 0.38% away, out at market after 4 hours.
- **Variant A (with the trend):** shorts only while the 5-minute 50-bar EMA is below the 200-bar EMA, longs only when
  above. That is the user's case on 12 of 13 trades.
- **Variant B:** both sides at all times.
- **Costs:** 1 MNQ, $1.24 a round trip, a tick of slippage on every market and stop fill; the stop first when a bar
  reaches both.

**Passes only if, for a variant:**
- NQ 2015-2019: net positive with t ≥ 2;
- NQ 2020-Jul 2025 and the index 2011-2018 and 2019-Sep 2026: net positive;
- the profit factor is at least 1.1 in all four.

A pass goes on to sizing and the shared daily budget beside the day bot before anything goes into the user's file.

**G58 result (run once, 2026-11-03): rejected; as rules, the style loses everywhere.**

| 1 MNQ | A, with the trend: trades a week, net, t, profit factor | B, both sides |
|---|---|---|
| NQ 2015-2019 | 14.0, −$8,260, t −1.01, 0.96 | 30.1, −$25,577, t −1.86, 0.95 |
| NQ 2020-Jul 2025 | 17.9, −$46,700, t −3.05, 0.87 | 41.2, −$78,203, t −3.95, 0.90 |
| index 2011-2018 | 15.9, −$33,754, t −2.54, 0.92 | 32.9, −$56,648, t −2.80, 0.94 |
| index 2019-Sep 2026 | 18.6, −$76,114, t −3.98, 0.86 | 41.6, −$128,832, t −5.03, 0.89 |

- **Trades every day, and loses.** 32-36% winners, about a fifth of trades reaching the 0.38% target, the rest stopped
  or timed out. Over thousands of trades the loss is far beyond luck.
- **The user's week, by these rules (Yahoo's MNQ bars):** Oct 30 - Nov 3 gives 9 trades and −$34 (A), or 28 trades and
  +$76 (B). Aug 25 - Oct 29 gives −$2,103 (A) or +$1,670 (B). So the rules don't reproduce the +$3,804: that week came
  from the user's own choices of which stretched moves to sell, in a one-way fall.

The day bot stays as it is (`research/g58_fade_extremes.py`).

## G59: a narrower entry band, for more trading days (registered 2026-11-03, before its run)

**The idea (the user: "it goes days without trading"):** a new entry needs a close past the noise line. Entering at 0.9
or 0.85 of the line's distance from the open (`entry_k`) takes the breakouts that stop short of it, so more days trade.
The stop stays 0.24 noise units past the full line, so 0.85 is the narrowest that keeps the stop on the far side of the
entry.

**Variants:** Funded growth with `entry_k` 0.9 and 0.85.

**Adopt (the better by window net) only if, against 1.0:**
- a higher net on all three 5-minute sets (the window, NQ from 2015, the index from 2011), in the chart's execution;
- the floor is never touched;
- there are no more days at −$1,000.

Days with a trade are reported for each.

**G59 result (run once, 2026-11-03): rejected; a few more days, less on the window, and the NQ account lost at 0.9.**

| 5-minute, the chart's execution | days with a trade: window / NQ / index | net: window / NQ / index |
|---|---|---|
| 1.0 (as it is) | 29% / 37% / 36% | **$18,516** / $277,322 / $407,796 |
| 0.9 | 31% / account lost / 38% | $13,652 / $1 / $449,022 |
| 0.85 | 33% / 42% / 40% | $10,640 / **$330,979** / **$478,238** |

0.85 made 17-19% more on the histories but 43% less on the window, with a −$1,085 day on the index. 0.9 lost the NQ
account in its first months. Either way only 2-5 more days in 100 trade (`verification/noise_v2/g59_band.txt`).

**Where this leaves "more trading days" (G55-G59, 2026-11-03).** With every filter off, a narrower band, a second market
(the S&P), overnight sessions, and the user's own style as rules, each either loses money over the histories or loses
accounts. Most days the Nasdaq does not trend inside the day session, and none of the setups tested trades those days
at a profit after costs.

## G60: "gap and go" before 10:00, beside the bot (registered 2026-11-03, before its run)

**The idea:** round seventy-one's best setup, gap and go, was positive in every Nasdaq data set (t 2.0 / 3.4 / 3.5) and
on the S&P, the DAX and the Nikkei (t 1.8 / 2.4 / 1.8). It failed the strict confirmation bar, but nothing else came
closer. It trades in 09:30-10:00, when the bot never does. Here it gets an exit before the bot's first entry can fill
(10:05), so the two never hold a position at once.

**The rules (1 MNQ, 5-minute bars):**
- **When:** the 09:30 open is at least 0.5 times the average of the last 14 sessions' gaps away from the prior 16:00
  close, and the 09:30 bar closes beyond its open in the gap's direction.
- **The trade:** in at the 09:35 open in the gap's direction, a stop at the 09:30 open, out at the 10:00 open.
- **Costs:** $1.24 a round trip and a tick of slippage on each market and stop fill.
- **Left out:** each month's first session (the scaled data's monthly rescale makes a false gap there), and the
  no-trade dates.

**Passes only if:** the net is positive in all four halves (NQ 2015-2019, NQ 2020-Jul 2025, the index 2011-2018, the
index 2019-Sep 2026), and is above 0 with t ≥ 2 on all four pooled.

It reports the trades a week, the days it trades when the bot (Funded growth, 5-minute) doesn't, and the bot's net
with and without it.

**G60 result (run once, 2026-11-03): passes. Gap and go before 10:00 makes money in all four halves.**

| 1 MNQ, 09:35-10:00 | trades a week | net | winners | profit factor | t |
|---|---|---|---|---|---|
| NQ 2015-2019 | 1.37 | +$5,751 | 37.0% | 1.41 | 2.34 |
| NQ 2020-Jul 2025 | 1.34 | +$9,047 | 35.7% | 1.42 | 2.54 |
| index 2011-2018 | 1.31 | +$4,731 | 31.7% | 1.21 | 1.59 |
| index 2019-Sep 2026 | 1.13 | +$11,795 | 37.5% | 1.49 | 3.15 |
| all 1,748 trades | | **+$31,324** | | | **4.85** |

- **Fresh data:** Yahoo's MNQ bars, Aug 25 - Nov 3, 2026, which no round has seen. 14 trades, −$183 (4 winners). That
  is within the spread expected of 14 trades (about +$20 a trade on average, with wide swings).
- **The setup was picked from 24 in round seventy-one.** The exit by 10:00 is new here and the pass rule was fixed
  before this run, but the data was not untouched. Live results are the real test.

**Beside the bot, on the same account (a simple sum, `research/g60_combined.py`):**

| | days with a trade | net | lowest room above the floor | worst day |
|---|---|---|---|---|
| NQ: bot / bot + gap | 36.6% / **51.4%** | $277,322 / **$291,958** | $459 / $238 | (bot ≤ $900) / −$1,112 |
| index: bot / bot + gap | 35.7% / **49.0%** | $407,796 / **$424,322** | $1,229 / $989 | (bot ≤ $900) / −$1,280 |

The simple sum ignores the shared $900 daily budget, which is why two days pass −$1,000. Next: gap and go inside the
model and MnqNoiseV38.cs, sized from the same daily budget and trailing floor as the bot, then the same tests again.

**G60 stage 2 (registered 2026-11-03, before its run): gap and go inside the bot.** `gap_go` in `mnqbot/noise.py` (off by
default) sizes each gap trade like the bot's own: its contract steps, and the trade's own stop against today's budget
and the trailing floor. While a gap trade is open, its risk to the stop is held back from the bot's budget. Its P/L
counts in the day and the equity like any trade. Funded growth, 5-minute bars (gap and go needs the 09:30 bar),
`research/g60_integrated.py`. **Adopt (on by default in Funded growth) only if, against Funded growth as it is,** on
all three 5-minute sets in both executions: a higher net, the floor never touched, and no more days at −$1,000. The
share of days with a trade is reported.

**G60 stage 2 result (run once, 2026-11-03): fails the rule. More days and more money, but the NQ account was lost
early.**

| 5-minute, chart / NinjaTrader | days with a trade | net |
|---|---|---|
| window: as it is / with gap and go | 28.9% / **44.0%** | $18,516 / $18,549 → **$22,539 / $23,935** |
| NQ: as it is / with gap and go | 36.6% / 3.8% | $277,322 / $267,571 → **$0 / $1, the account lost in 2015** |
| index: as it is / with gap and go | 35.7% / **49.4%** | $407,796 / $404,250 → **$486,458 / $476,571**, one −$1,347 day |

- **NQ:** the bot alone came within $459 of the floor in its first months from 2015. The early gap losses took it the
  rest of the way.
- **The −$1,347 day (Aug 26, 2015):** a 14-contract gap trade was sized from the 09:30 close, filled at a 09:35 open
  farther from its stop, and was stopped on the fill bar.

**G60 stage 3 (registered 2026-11-03, before its run).** Two changes, for the two faults:
- **`gap_go_after_lock`:** gap trades only once the trailing floor has stopped at the start (the account's first $2,000
  made), so the first months stay the bot's alone, as G43 found they are the dangerous ones;
- **`gap_go_cap`:** each gap trade's stop no farther than the bot's $187.50 a contract from the expected fill.

The rule is stage 2's (a higher net on all three 5-minute sets in both executions, the floor never touched, no more
days at −$1,000). G35's 89 start dates are also run, with no more lost accounts allowed than the bot's (7 on NQ, 7 on
the index).

**G60 stage 3 result (run once, 2026-11-03): rejected; worse than stage 2.**
- **The window:** $12,111 / $12,115 (against $18,516 / $18,549), with a −$1,661 day.
- **NQ:** the account was lost in 2015 again.
- **The index:** $474,679 / $468,546, with the same −$1,347 day.

Waiting for the floor to lock left the early months unchanged on NQ (the bot alone nearly died there), and the cap does
not reach the real fault: a gap trade stopped on its fill bar after the 09:35 open moved past the price it was sized
on.

**Stage 2 on G35's 89 start dates** (`g35_start_dates_gapgo.csv`):

| 89 start dates, 21 months | the bot | the bot + gap and go |
|---|---|---|
| lost or frozen: NQ / index | 7 of 35 / 7 of 54 | **10 of 35** / **4 of 54** |
| median net: NQ / index | $22,925 / $23,070 | **$32,644 / $30,596** |

The same number of accounts lost in all (14 of 89), more on NQ and fewer on the index, and the typical account makes
about 35-40% more. It fails the rule set before the run (more lost NQ accounts, days past −$1,000). It is not made the
default. As a switch, its trade-off is: half of all days with a trade instead of a third, about a third more profit in
the typical account, and a real chance that a 09:35 fill goes past its stop and a day goes past the $1,000 limit.

**G60 stage 4 (registered 2026-11-03, before its run): stage 2, out at 09:55.** In NinjaTrader an exit and the bot's
first entry in the same bar can collide (an exit and a reverse sent together). So the gap trade closes at the 09:55
open (`gap_go_exit` 595), a bar before the bot's first fill can come. Otherwise it is stage 2 (no wait for the floor,
no cap). Reported as stage 2, for the switch's description; it is not made the default whatever the result.

**G60 stage 4 result (run once, 2026-11-03): too dangerous.**
- **Chart's execution:** the window made $26,296 and the index $609,678, but the NQ account was lost and the index had
  a −$1,347 day.
- **NinjaTrader's execution:** the window's own account was lost early (a −$1,661 day) and NQ's too; the index made
  $600,244.

Sized like the bot's trades (up to 15 contracts, with stops only 20-50 points away), a fast open can carry a gap trade
far past its stop.

**G60 stage 5 (registered 2026-11-03, before its run): stage 4 with each gap trade at 1 contract
(`gap_go_max_qty` 1).** The point is the extra trading days at a risk too small to hurt the account. Adopt as the
default only on stage 2's rule (a higher net on all three 5-minute sets in both executions, the floor never touched,
no more days at −$1,000).

**G60 stage 5 result (run once, 2026-11-03): passes. Gap and go at 1 contract, out at 09:55, beside the bot.**

| 5-minute | days with a trade | net, chart / NinjaTrader | worst day, chart / NinjaTrader |
|---|---|---|---|
| window: as it is | 28.9% | $18,516 / $18,549 | −$900 / −$899 |
| window: with gap and go | **44.0%** | **$19,618 / $19,626** | −$892 / −$899 |
| NQ: as it is | 36.6% | $277,322 / $267,571 | −$1,023 / −$899 |
| NQ: with gap and go | **51.5%** | **$306,951 / $304,106** | −$1,038 / −$899 |
| index: as it is | 35.7% | $407,796 / $404,250 | −$988 / −$900 |
| index: with gap and go | **49.4%** | **$447,417 / $438,285** | −$996 / −$900 |

- **Higher net in all six runs**, the floor never touched, and no more days at −$1,000 (NQ's one day in the chart's
  execution was already there; NinjaTrader's execution has none).
- **About 1.3 gap trades a week**, and the days with a trade go from a third to a half.

Next, before it is made the default: G35's 89 start dates with it on (variant `gapgo1`), then MnqNoiseV38.cs and the
parity tests (`verification/noise_v2/g60_stage5.txt`).

**G60 stage 5 on G35's 89 start dates (21 months; `g35_start_dates_gapgo1.csv`): adopted.**

| | lost or frozen: NQ / index | median net: NQ / index | worst 10%: NQ / index | best 10%: NQ / index |
|---|---|---|---|---|
| the bot | 7 of 35 / 7 of 54 | $22,925 / $23,070 | −$461 / $444 | $39,277 / $39,303 |
| the bot + gap and go (1 contract) | **6 of 35 / 5 of 54** | **$32,382 / $30,180** | **$1 / $4,638** | **$49,328 / $48,485** |

Fewer lost accounts (11 of 89 against 14) and about 35% more in the typical account. The gap trades at 1 contract add a
little profit, and they make it early, which brings the contract steps sooner. **Gap and go goes on by default in
Funded growth**, at 1 contract, 09:35-09:55.

**U19 (2026-11-03): gap and go is in MnqNoiseV38.cs, on by default (G60).** A new switch in group 1, "Gap and go: 1 MNQ
with a big opening gap, 09:35-09:55 (5-minute chart)", on by default. It applies in the Funded growth modes and Custom,
never in Evaluation, and does nothing on a 30-minute chart.

At the 09:30 bar's close, when the open is at least half the last 14 sessions' average gap away from the prior close
and the bar closed beyond the open the gap's way:
- **The entry:** 1 MNQ at market ("GapLong"/"GapShort"), with a stop at the 09:30 open attached;
- **The exit:** a market exit at the 09:50 bar's close fills at the 09:55 open ("Gap exit"), so it never meets the
  bot's first fill at 10:00;
- **Sizing:** the trade must fit the day's budget and the room above the floor;
- **Bookkeeping:** its P/L counts like any trade's;
- **Live:** an alert ("SELL 1 MNQ at market (gap and go), stop …, out at 09:55") and the dashboard's open-trade line.

It is outside the bot's day filters (calm stretch, trend, big day) by design, as tested. The "Model flat" safety check
leaves it alone.

**Tests:**
- `test_v38_gap_go`: NinjaTrader's code and the model agree trade for trade with it on (gap trades included, each 1
  contract, in at 09:35, out by its stop or at 09:55) and off (no gap trades).
- Every Funded growth parity test now runs with it on. All 30 NinjaTrader v3.8 tests pass.

**The backtest of the file** (`research/v38_ninjatrader_run.py grow`, 5-minute, from 2025-01-02;
`verification/noise_v2/v38g_nt_gapgo_2026-11-03.csv`):
- **The result:** 404 trades in the window, **$19,618.65** (was $18,541.72), 53.7% winners, profit factor 1.69, closed
  drawdown $2,416, worst day −$899.09.
- **Against the model:** all 481 trades agree except the known 12/24/2024 warm-up trade ($0.50).
- **30-minute bars:** unchanged (gap and go needs the 09:30 bar).

## G61: gap and go at 2 contracts (registered 2026-11-03, before its run)

**The idea:** G60 adopted gap and go at 1 contract. Its stage 4, at the bot's full size, lost accounts. 2 contracts is
the step between.

**The variant:** Funded growth with gap and go at up to 2 contracts (`gap_go_max_qty` 2), against today's default (1).

**Adopt only if, against 1 contract:**
- a higher net on all three 5-minute sets in both executions;
- the floor never touched;
- no more days at −$1,000;
- on G35's 89 start dates, no more lost or frozen accounts than 1 contract's (11).

**G61 result (run once, 2026-11-03): rejected; 2 contracts loses accounts in NinjaTrader's execution.**

| 5-minute, chart / NinjaTrader | 1 contract (as it is) | 2 contracts |
|---|---|---|
| window | $19,618 / $19,626 | $21,681 / **$2, the account lost (a −$1,661 day)** |
| NQ | $306,951 / $304,106 | $335,880 / **$2, the account lost** |
| index | $447,417 / $438,285 | $478,825 / $468,724 (a −$1,009 day, chart) |

In the chart's execution 2 contracts make 7-11% more. In NinjaTrader's, the window's and NQ's accounts go to the floor
in their first months. A fast 09:35 open that gaps past the stop costs twice as much, and early on the account has no
room for that. 1 contract stays (`verification/noise_v2/g61_gap_qty.txt`).

**Not yet in the TradingView script:** gap and go (G60) is in the Python model and MnqNoiseV38.cs, not in
`pine/mnq_noise_momentum.pine`. On a 30-minute TradingView chart it could not trade anyway (it needs the 09:30-09:35
bar). On a 5-minute TradingView chart the script's results will be below NinjaTrader's by the gap trades, about 1.3 a
week.

## G62: double size on jobs-report days (registered 2026-11-03, before its run)

**The idea, from round seventy-three:** on the monthly jobs-report days (8:30 New York, about 12 a year) the bot made
2.5-3.4 times its usual dollars a day, in the same direction on 2011-18, 2019-26 and NQ futures. 2x size there was
positive everywhere (t 1.84 / 1.30 / 1.71) but under that round's bar. Here it is tried inside today's bot.

**The variant:** today's default (Funded growth with gap and go at 1 contract), with the bot's entries on jobs-report
days at 2x its contracts, after the contract steps. The daily budget and the trailing floor still cap each trade.
Dates: `research/nfp_dates.csv` (BLS's rule).

**Adopt only if, against today's default:**
- a higher net on all three 5-minute sets in both executions;
- the floor never touched;
- no more days at −$1,000;
- on G35's 89 start dates, no more lost or frozen accounts (11).

**G62 result (run once, 2026-11-03): rejected; 2x on jobs-report days helps the window only.**

| 5-minute, chart / NinjaTrader | as it is | 2x on jobs-report days |
|---|---|---|
| window | $19,618 / $19,626 | **$22,547 / $22,615** |
| NQ | **$306,951 / $304,106** | $305,889 / $298,474 |
| index | **$447,417 / $438,285** | $444,606 / $436,003 |

It made $2,900 more on the window but less on both histories, in both executions. Round seventy-three's effect was
measured on the bot's average day; with today's growth sizing and filters, the doubled jobs-report trades don't pay
over the long run. (`verification/noise_v2/g62_nfp.txt`; `news_mult` stays in the model, off.)

## G63: a contract per $1,000 again, now with gap and go (registered 2026-11-03, before its run)

**The idea:** G5 rejected $1,000 steps because new accounts went to the floor early. Gap and go (G60) has since made the
early months safer (11 lost or frozen of 89 against 14). Faster steps bring the larger size sooner, which is where the
profit grows.

**The variant:** today's default with `profit_step` 1000 (was 1500).

**Adopt only if, against today's default:**
- a higher net on all three 5-minute sets in both executions;
- the floor never touched;
- no more days at −$1,000;
- on G35's 89 start dates, no more lost or frozen accounts (11).

**G63 result (run once, 2026-11-03): rejected; $1,000 steps still lose the NQ account.**
- **The window:** $20,191 / $22,320 (against $19,618 / $19,626).
- **The index:** $450,619 / $445,250 (against $447,417 / $438,285).
- **NQ from 2015:** **$0 / $1, at the floor in its first months**, in both executions.

The NQ start of 2015 is the bot's narrowest escape (its lowest room is $238-459), and faster steps take it over the edge.
(`verification/noise_v2/g63_steps.txt`. G62's start-date run, for the record: 10 lost or frozen, median $38,045 NQ /
$31,129 index; it was already rejected.)

G63's start-date run, for the record: **18 lost or frozen of 89** (index 8, NQ 10) against today's 11, median
$33,430 index / $36,278 NQ. It confirms the rejection (`verification/noise_v2/g35_start_dates_gapgo1s1000.csv`).

## G64: the gap and go trigger (registered 2026-11-03, before its run)

**The idea:** gap and go fires when the gap is at least 0.5 times the last 14 sessions' average. At 0.25 it fires on
more days (more trading days, more early profit at 1 contract); at 0.75 on fewer, larger gaps.

**The variants:** today's default with `gap_go_k` 0.25 and 0.75.

**Adopt (the better by window net) only if, against 0.5:**
- a higher net on all three 5-minute sets in both executions;
- the floor never touched;
- no more days at −$1,000;
- on G35's 89 start dates, no more lost or frozen accounts (11).

**G64 result (run once, 2026-11-03): rejected; 0.5 stays.**
- **0.25** (more gap trades, 49.5-55.6% of days traded): less on the window in the chart's execution ($18,562) and a
  −$1,042 day on the index.
- **0.75:** more on the window ($20,533 / $21,088), but less on the index in both executions and on NQ in
  NinjaTrader's ($302,240 against $304,106).

(`verification/noise_v2/g64_gap_k.txt`.)

## G65: shorts in an uptrend at 1 contract (registered 2026-11-03, before its run)

**The idea, from G55:** the trend filter blocks every short while the last close is above its 50-session average. With
shorts allowed at full size, 14 more days in 100 traded, but the window and the index made less (G55). Here those shorts
trade at 1 contract, at the usual $187.50 max loss a contract (`trend_small`). They add the trading days with little
at risk.

**Adopt only if, against today's default:**
- a higher net on all three 5-minute sets in both executions;
- the floor never touched;
- no more days at −$1,000;
- on G35's 89 start dates, no more lost or frozen accounts (11).

**G65 result (run once, 2026-11-03): rejected by the rule; a near miss.**

| 5-minute, chart / NinjaTrader | days with a trade | net |
|---|---|---|
| window: as it is / uptrend shorts at 1 | 44.0% / **55.1%** | $19,618 / $19,626 → **$21,365 / $21,228** |
| NQ | 51.5% / **58.9%** | $306,951 / $304,106 → **$336,124 / $326,342** |
| index | 49.4% / **56.5%** | **$447,417 / $438,285** → $444,983 / $434,318 |

It trades 7-11 more days in 100 and makes more on the window and NQ, but 0.5-0.9% less on the index. The index's long
bull years punish shorts in an uptrend, even at 1 contract. The rule asks for more on all three, so it stays out.
`trend_small` stays in the model, off (`verification/noise_v2/g65_trend_small.txt`).

G65's start-date run, for the record: **17 lost or frozen of 89** (index 9, NQ 8) against today's 11, median
$30,413 index / $36,193 NQ. The extra shorts cost new accounts more often, which confirms the rejection
(`verification/noise_v2/g35_start_dates_gapgo1trend.csv`).

## G66: an "opening drive" for the gap and go slot (registered 2026-11-03, before its run)

**The idea:** gap and go (G60) trades 09:35-09:55 only when the open gaps. Many days without a gap still open with a
strong first 5 minutes, and the bot leaves 09:35-10:00 unused on those days. Here a strong 09:30 bar takes the same
trade with no gap needed: when the gap rule doesn't fire and the 09:30 bar's body |close − open| is at least
`gap_go_drive_k` × the average body of the last 14 sessions' 09:30 bars, go its way at the 09:35 open, stop at the
09:30 open, out at the 09:55 open, 1 contract (as gap and go). It adds trading days.

**The variants:** today's default with `gap_go_drive_k` 1.0 and 1.5.

**Adopt (the better by window net) only if, against today's default:**
- a higher net on all three 5-minute sets in both executions;
- the floor never touched;
- no more days at −$1,000;
- on G35's 89 start dates, no more lost or frozen accounts (11).

**G66 result (run once, 2026-11-03): rejected; the opening drive loses the account early.**

| 5-minute, chart / NinjaTrader | days with a trade | net |
|---|---|---|
| window: as it is / drive 1.0 / drive 1.5 | 44.0% / 7.8% / 6.9% | $19,618 / $19,626 → **−$1,215 / −$1,211** → **−$1,251 / −$1,249** |
| NQ | 51.5% / 4.9% / 4.3% | $306,951 / $304,106 → **$0 / $0** → **$0 / $1** |
| index | 49.4% / 65.5% / 58.4% | $447,417 / $438,285 → $467,840 / $466,322 → $477,146 / $467,169 |

On the window and NQ the drive trades lose at the start, the account reaches the floor in its first weeks and stops
(days traded falls to 4-8%). The index's long run makes more, but a new account doesn't survive to see it.
`gap_go_drive_k` stays in the model, off (`verification/noise_v2/g66_drive.txt`).

## G67: a bigger gap trade once the floor has stopped (registered 2026-11-03, before its run)

**The idea, from G61:** 2-contract gap trades made 7-11% more in the chart's execution but lost new accounts in
NinjaTrader's, in their first months, before any cushion. Here the gap trade stays at 1 contract until the trailing
floor has stopped at the starting balance (the account's first $2,000 made). After that it takes up to
`gap_go_locked_qty` contracts, still sized down to today's room and the room above the floor.

**The variants:** today's default with `gap_go_locked_qty` 2 and 3.

**Adopt (the better by window net) only if, against today's default:**
- a higher net on all three 5-minute sets in both executions;
- the floor never touched;
- no more days at −$1,000;
- on G35's 89 start dates, no more lost or frozen accounts (11).

**G67 result (run once, 2026-11-03): rejected as run, and it found a data error.**

| 5-minute, chart / NinjaTrader | as it is | up to 2 once stopped | up to 3 once stopped |
|---|---|---|---|
| window | $19,618 / $19,626 | **$1 / $1, the account lost** | **$1 / $1, the account lost** |
| NQ | $306,951 / $304,106 | $335,883 / **−$2, lost early** | $356,039 / $359,943 |
| index | $447,417 / $438,285 | $478,825 / $468,724 | $508,291 / $498,705 |

**Why the window failed: the data, not the market.** Its account lost all its profit in one trade, a 2-contract gap
trade on 2025-06-20 at −$1,661. That session's bars mix two contracts. It was June's expiration, after the
Juneteenth closure. The 09:30 and 09:35 bars are September's contract (about 22,100). From 09:40 on they are the
expired June contract, 445 points lower, at 78 contracts a bar against 9,300. The "fall" hit the gap trade's stop.
No live chart had it. The NQ history has the same session (the window's 2025 part is built from it). G61's
"window account lost (a −$1,661 day)" was this same bar.

A scan of every set for a regular-hours bar more than 1.2% from the last close (`research/data_errors.py`) finds only
this session, plus two real moves (2020-03-16 on NQ, 2023-03-10 on the index). From now on
`research/v24_scan.py` drops it (`BAD_SESSIONS`) from the window proxy and the NQ history, and so does
`research/v38_ninjatrader_run.py`. Today's default and G67 are re-run on the corrected data next (G67b), before any
decision (`verification/noise_v2/g67_locked_qty.txt`).

## G67b: G67 on the corrected data (registered 2026-11-03, before its run)

**Why:** G67's window result came from the data error above, so it decided nothing. Run once more, unchanged, on the
data without 2025-06-20, today's default with it. Known before this run: NQ and the index are hardly touched by the
fix (one session in 10-15 years), and there `gap_go_locked_qty` 2 lost NQ's account in NinjaTrader's execution while
3 didn't. What is new here is the window, and G35's start dates after it.

**Adopt (the better by window net) only on G67's rule:** against today's default on the same corrected data, a
higher net on all three 5-minute sets in both executions; the floor never touched; no more days at −$1,000; on G35's
89 start dates, no more lost or frozen accounts than the default's on the corrected data.

**G67b result (run once, 2026-11-03): passes. Gap trades take up to 3 contracts once the floor has stopped.**

On the corrected data (the window and NQ without 2025-06-20; the index as it was, clean there):

| 5-minute, chart / NinjaTrader | today's default | up to 2 once stopped | **up to 3 once stopped** |
|---|---|---|---|
| window | $23,081 / $22,731 | $27,976 / $27,683 | **$30,161 / $29,836** |
| NQ 2015-Jul 2025 | $306,951 / $304,106 | $335,883 / **−$2, lost early** | **$356,039 / $359,943** |
| index 2011-Sep 2026 | $447,417 / $438,285 | $478,825 / $468,724 | **$508,291 / $498,705** |
| days at −$1,000 or worse (chart NQ) | 1 | 1 | 1 |
| floor touched | never | NQ, NinjaTrader's | **never** |

**G35's 89 start dates (21 months each), corrected data:**

| | lost or frozen, NQ / index | median net, NQ / index |
|---|---|---|
| today's default (1 contract) | 6 of 35 / 5 of 54 = **11** | $32,382 / $30,180 |
| **up to 3 once stopped** | 5 of 35 / 6 of 54 = **11** | $34,564 / $27,703 |

Every part of the rule holds for 3 (2 fails: NQ's account in NinjaTrader's execution), so **3 is adopted**.

**The data fix alone** raised today's default on the window from $19,618 / $19,626 to $23,081 / $22,731 (chart /
NinjaTrader): the false 445-point fall on 2025-06-20 had cost the gap trade and every contract step after it.

**What to keep in mind:**
- **2 failing where 3 passes** shows NQ's 2015 start is still on the edge: a small change in the path decides that
  account. The 89 start dates are the better guide (11 either way).
- **The typical 21-month index account makes a little less** ($27,703 against $30,180). The long histories and NQ's
  typical account make more.
- **The window's closed drawdown is larger**, $3,706 against $2,600 (chart). The floor is never touched.

(`verification/noise_v2/g67b_locked_qty.txt`, `g35_start_dates_gapgo1.csv` and `g35_start_dates_gapgo1lq3.csv`.)

**U20 (2026-11-03): gap and go at up to 3 MNQ once the floor has stopped (G67b), and the data fix.**
- **The setting:** group 1, "Gap and go once the trailing floor has stopped at the start: up to this many MNQ (0 = 1
  MNQ always)", **3 by default**. Until the account's highest end-of-day balance is $2,000 above the start (the floor
  then stops at the start balance for good), each gap trade is 1 MNQ, as before. After that, up to 3, still sized
  down to the day's budget and the room above the floor.
- **The file you trade, on the NinjaTrader simulator** (`research/v38_ninjatrader_run.py grow`, 5-minute, from
  2025-01-02): **401 trades, $29,820.65, 53.6% winners, profit factor 1.709, closed drawdown $3,648, worst day
  −$899.11, largest loss −$1,006.91.** It matches the model trade for trade except one: 2026-03-09, where the window's
  data stops at 15:10 (the model closes at that bar, the strategy at the next open; live, MNQ trades to 16:00). The
  30-minute chart is unchanged (gap and go needs 5-minute bars): $28,620.10, all 303 trades identical
  (`verification/noise_v2/v38g_nt_lq3_2026-11-03.txt` and the trade list beside it).
- **Tests:** `test_v38_gap_go_locked`: with a $600 trailing drawdown (Custom mode), so the floor stops within the
  sample, NinjaTrader's code and the model agree trade for trade at 3 and at 0, gap trades grow only at 3, and never past
  3. The test's Funded growth config now stops its floor at the start (`trail_cap` 0), as NinjaTrader's always does.
- **The data:** `research/data_errors.py` scans every set; `research/v24_scan.py` drops `BAD_SESSIONS` (2025-06-20)
  from the window proxy and the NQ history.

## G68: up to 5 gap contracts once the floor has stopped (registered 2026-11-03, before its run)

**The idea:** G67b's 3 contracts made 14-30% more with no more lost accounts. Does the gap trade have room for more
once the account has its cushion? One variant: `gap_go_locked_qty` 5.

**Adopt only if, against today's default (3, U20), on the corrected data:**
- a higher net on all three 5-minute sets in both executions;
- the floor never touched;
- no more days at −$1,000;
- on G35's 89 start dates, no more lost or frozen accounts (11).

**G68 result (run once, 2026-11-03): rejected; 5 contracts lose NQ's account.**

| 5-minute, chart / NinjaTrader | up to 3 (as it is) | up to 5 |
|---|---|---|
| window | $30,161 / $29,836 | $34,828 / $34,689 |
| NQ 2015-Jul 2025 | $356,039 / $359,943 | **$3 / −$2, the account lost in its first months** |
| index | $508,291 / $498,705 | $546,846 / $539,061 (a −$1,054 day, chart) |

The window and the index make more, but NQ's 2015 account goes back to the start, in both executions. 3 stays. The
30-minute chart has no gap trades (they need the 09:30-09:35 bar), so G67b and G68 don't change it
(`verification/noise_v2/g68_locked5.txt`).

**Scorecard, G44-G68:** 25 rounds. Adopted: G60 (gap and go, U19), G67b (3 gap contracts once the floor has
stopped, U20), plus the data fix that G67 found. Rejected: 22 (G54 and G55 were measurements).

## G69: a trade on 70% of days, with the same account rules (registered 2026-11-03, before its run)

**The ask:** the user wants trades on about 70% of days (today about 44%), with the same limits ($900 daily budget
under the $1,000 loss limit, the $2,000 end-of-day trailing floor). G55 showed most quiet days are quiet because price
never leaves the noise area, so the bot's own filters can't add them. The added trades come in the free 09:35-09:55
slot and against the trend, **each at 1 MNQ always** (never the contract steps or G67b's 3), and their P/L counts in
the day's budget and the floor like any trade's:
- **small gaps** (`gap_go_small_k` 0): a gap below gap and go's 0.5 x the average gap, the 09:30 bar closing the gap's
  way: the same 09:35-09:55 trade, 1 MNQ;
- **uptrend shorts** (`trend_small`, G65): the shorts the trend filter blocks, 1 MNQ at the usual $187.50 max loss;
- **opening drive** (`gap_go_drive_k` 0.5, G66, now 1 MNQ always): no gap trade, and the 09:30 bar's body at least
  half the last 14 sessions' average body: its way, 09:35-09:55, 1 MNQ.

**Packages:** P1 = small gaps; P2 = P1 + uptrend shorts; P3 = P2 + opening drive.

**Stage 1 (days only, no profit looked at):** 5-minute bars, the chart's execution. The first of P1, P2, P3 with a
trade on at least 70% of sessions on the window, NQ and the index is the candidate. If none reaches 70%, P3 is, and the
shortfall is reported.

**Stage 2, the candidate against today's default (U20), both executions, all three sets:**
- **as the default** if it has a higher net on all three, the floor never touched, no more days at −$1,000, and on
  G35's 89 start dates no more lost or frozen accounts (11);
- **as a switch** ("More trading days", off by default) if only the account rules hold: the floor never touched, no
  more days at −$1,000 and no more lost or frozen accounts (11), with its cost in net reported;
- otherwise rejected.

**G69 result (run once, 2026-11-03): rejected; the fill-in trades lose new accounts.**

| 5-minute, chart's execution | days with a trade: window / NQ / index | net: window / NQ / index |
|---|---|---|
| today's default (U20) | 43.9% / 51.5% / 49.4% | $30,161 / $356,039 / $508,291 |
| P1 small gaps | 55.0% / **4.3%** / 57.9% | $29,578 / **$0, lost** / $501,196 |
| P2 + uptrend shorts | 62.6% / 65.9% / 63.4% | $32,315 / $390,236 / $502,197 |
| P3 + opening drive | **86.3% / 84.9%** / **1.6%** | $36,044 / $400,334 / **−$8, lost** |

Stage 1: none reaches 70% on all three (P3 does on the window and NQ but loses the index's account), so P3 was the
candidate, and stage 2 rejects it: its index account is lost in its first weeks. Where the accounts live, the fill-in
trades make more (P3: +$5,900 on the window, +$44,000 on NQ). What kills an account is when they come: in its first
weeks, with no cushion above the floor (`verification/noise_v2/g69_days.txt`).

## G70: the fill-in trades only once the floor has stopped (registered 2026-11-03, before its run)

**The idea, from G69:** G69's 1-MNQ fill-in trades add days and money where an account lives, and lose accounts at
their start. G67b's lesson again: wait for the cushion. Here they trade only once the trailing floor has stopped at
the starting balance (the account's first $2,000 made, `fill_after_lock`). Until then the bot is today's default.

**Packages:** P2L = G69's P2 and P3L = G69's P3, each with `fill_after_lock`.

**Stage 1 (days only):** 5-minute, the chart's execution. The first of P2L, P3L with a trade on at least 70% of the
window's, NQ's and the index's sessions is the candidate; if neither, P3L, with the shortfall reported.

**Stage 2:** G69's (as the default if a higher net on all three in both executions, the floor never touched, no more
days at −$1,000, and no more lost or frozen accounts on G35's 89 start dates (11); as a switch if only the account
rules hold; otherwise rejected).

**G70 result (run once, 2026-11-03): rejected; NQ's 2015 account is still lost.**

| 5-minute, chart's execution | days with a trade: window / NQ / index | net: window / NQ / index |
|---|---|---|
| today's default (U20) | 43.9% / 51.5% / 49.4% | $30,161 / $356,039 / $508,291 |
| P2L | 60.0% / **4.1%, lost** / 63.3% | $32,325 / $0 / $503,134 |
| P3L | **80.7%** / **4.8%, lost** / **81.0%** | $31,217 / −$3 / $522,078 (a −$1,042 day) |

NQ's account (from January 2015) reached +$6,387 by July 2015, then the August 2015 crash took it back to the floor:
mostly the bot's own 4-5 contract losses and 3-contract gap stops, with the fill-in losers on top. The default
escapes that stretch by a few hundred dollars; anything more on those days tips it over. The index's −$1,042 day
(2016-05-16): a +$115 gap trade raised that day's budget, and the bot's next trade, sized to it, exited past its stop at
−$1,156. NinjaTrader's execution was not run to the end: stage 2 was already decided
(`verification/noise_v2/g70_fill_after_lock.txt`).

## G71: fill-in trades only with a cushion, and today's gains don't raise today's risk (registered 2026-11-03, before its run)

**From G70, two changes:**
- **A cushion for the fill-ins** (`fill_min_room`): G69's P3 fill-in trades only while the account is at least
  $3,000 (variant A) or $4,000 (variant B) above the trailing floor. They stop in a drawdown like August 2015's and
  start again once it's made back. The floor must also have stopped (`fill_after_lock`).
- **Today's gains don't widen today's budget** (`day_keep` 1): the bot's room for the day is $900 plus today's losses,
  never plus today's profits, so a morning gap win can't size a bigger trade that day.

**Stage 1 (days only):** 5-minute, the chart's execution. A, then B: the first with trades on at least 70% of sessions
on all three sets is the candidate; if neither, B, with the shortfall reported.

**Stage 2:** G69's rule, against today's default (U20).

**G71 result (run once, 2026-11-03): rejected; 70% of days reached, but the money and an account lost.**

| 5-minute | days with a trade: window / NQ / index | net: window / NQ / index |
|---|---|---|
| today's default (U20), chart | 43.9% / 51.5% / 49.4% | $30,161 / $356,039 / $508,291 |
| **A** ($3,000 cushion), chart | **72.4% / 82.3% / 80.6%** | $26,220 / $266,571 / $341,283 |
| A, NinjaTrader's | 72.6% / **4.4%, lost** / 80.6% | $26,177 / $1 / $342,229 |
| B ($4,000 cushion), chart | 68.7% / 82.6% / 80.5% | $26,557 / $274,988 / $341,293 |

Stage 1 chose A, the first at 70% on all three. Stage 2 rejects it: less net everywhere, and NQ's account lost in
NinjaTrader's execution. Until the floor stops, A differs from the default only by `day_keep`, so that is what lost NQ
(a smaller trade after a green morning changes the early path) and most of the lost money: a green morning's bigger
afternoon trades are where the bot makes its profit. The cushion itself did its job: the fill-ins stopped in NQ's
August 2015 and the chart's NQ account lived (`verification/noise_v2/g71_cushion.txt`).

## G72: G71 without `day_keep` (registered 2026-11-03, before its run)

**From G71:** keep the fill-in trades with a cushion (after the floor stops, while $3,000 / $4,000 above it), drop the
`day_keep` change.

**Packages:** A2 (`fill_min_room` 3000), B2 (4000), both G69's P3 fill-ins with `fill_after_lock`.

**Stage 1 and stage 2:** G71's (days ≥ 70% on all three sets, A2 first; then G69's rule against today's default).

**G72 result (run once, 2026-11-03): rejected; more money, but NQ's account lost.**

| 5-minute, chart / NinjaTrader | days: window / NQ / index | window | NQ | index |
|---|---|---|---|---|
| today's default (U20) | 43.9% / 51.5% / 49.4% | $30,161 / $29,836 | $356,039 / $359,943 | $508,291 / $498,705 |
| A2 ($3,000 cushion) | 72.4% / **4.5%** / 80.6% | **$33,986 / $33,719** | **−$2 / −$6, lost** | $528,608 / $520,367 |
| B2 ($4,000 cushion) | 68.7% / 4.4% (chart) / 80.5% | $34,401 / $34,441 | $1 / $381,707 | $528,618 / $523,395 |

The fill-ins make more where the account lives (window +$3,800, index +$20,000), but NQ's 2015 account goes back to the
start in August 2015 in 3 of 4 runs. The cushion stops the fill-ins in the drawdown, yet their earlier profits had
already raised the contract steps, so the bot's own trades were bigger going into the crash. The index's chart run
also had the −$1,042 day (`verification/noise_v2/g72_cushion_no_keep.txt`).

## G73: fill-in trades that don't raise the contract steps (registered 2026-11-03, before its run)

**From G72:** the fill-in trades' P/L still counts in the account, the day's budget and the floor, but not toward the
bot's contract steps (`fill_no_steps`): the bot sizes as if the fill-ins hadn't traded. Then a fill-in winning streak
can't put bigger bot trades into a crash, and their profit is extra cushion above the floor.

**Packages:** A3 = A2 + `fill_no_steps`, B3 = B2 + `fill_no_steps`.

**Stage 1 and stage 2:** G71's (days ≥ 70% on all three, A3 first; then G69's rule against today's default).

**G73 result (run once, 2026-11-03): rejected; NQ's 2015 account still lost.** A3 ($3,000 cushion): 72.8% / 4.5% /
80.6% of days, window $33,523 / $33,393, index $525,666 / $521,756 (a −$1,042 day, chart), NQ $1 / −$2. B3 alike
(`verification/noise_v2/g73_no_steps.txt`).

**Why NQ from January 2015 decides every test (measured after G73, research only):** today's default itself ends
October 2015 **$41** above its floor on that path. A3's fill-in trades netted −$217 in June-August 2015, and that alone
took it to the floor. A test passes or fails there on whether a change is $41 better or worse in one summer, which says
little about the change. G35's 89 start dates (35 of them on NQ, from April 2015 on) measure a new account's survival
far better.

## G74: the fill-ins judged on the 89 start dates, and gap wins don't widen the day (registered 2026-11-03, before its run)

**The package (A4):** G72's A2 (G69's P3 fill-in trades at 1 MNQ, only once the floor has stopped and while $3,000
above it) plus `gap_no_budget`: a 09:35 trade's profit doesn't widen the rest of that day's budget (the cause of G70's
−$1,042 day; the bot's own profits still do, unlike G71's `day_keep`).

**Adopt as the default only if all hold, against today's default (U20), 5-minute bars:**
- trades on at least 70% of sessions on the window, NQ and the index (the chart's execution);
- a higher net on the window and the index, in both executions;
- the floor never touched, and no more days at −$1,000, on the window and the index, in both executions;
- **on G35's 89 start dates (21 months each), no more lost or frozen accounts than the default's 11.**
- **NQ from January 2015** is reported, not a gate (the default's own margin there is $41).

**As a switch** ("More trading days", off) if only the 70%, the floor, the −$1,000 days and the 89 start dates hold.
Otherwise rejected.

**G72's A2 on the 89 start dates (21 months each):**

| | lost or frozen, NQ / index | median net, NQ / index |
|---|---|---|
| today's default (U20) | 5 of 35 / 6 of 54 = **11** | $34,564 / $27,703 |
| **A2, "More trading days"** | 5 of 35 / 6 of 54 = **11** | **$40,639 / $35,370** |

A new account survives as often, and the typical one makes $6,000-7,700 more over 21 months
(`verification/noise_v2/g35_start_dates_a2.csv`).

**U21 (2026-11-03): "More trading days", a switch, off by default (G72's A2).** At the user's ask for trades on about
70% of days. Group 1:
- **"More trading days: 1-MNQ fill-in trades once the floor has stopped"** (off), and **"…only while the account is
  at least this far above the trailing floor, $"** (3,000).
- **What it adds**, each at 1 MNQ, never the contract steps, and only once the trailing floor has stopped at the start
  and while the account is $3,000 or more above it:
  - **small gaps:** any gap the 09:30 bar closes beyond the open its way, the 09:35-09:55 trade;
  - **opening drive:** no gap trade, and the 09:30 bar's body at least half the last 14 sessions' average: its way,
    09:35-09:55;
  - **uptrend shorts:** the shorts the trend filter blocks, at the usual $187.50 max loss.
- **The numbers (5-minute, chart / NinjaTrader's execution, the model):**

| | days with a trade | window | NQ 2015-25 | index 2011-26 |
|---|---|---|---|---|
| off (the default) | 44% / 52% / 49% | $30,161 / $29,836 | $356,039 / $359,943 | $508,291 / $498,705 |
| **on** | **72% / 82% / 81%** | **$33,986 / $33,719** | **lost** (Aug 2015) / lost | **$528,608 / $520,367** |

  NinjaTrader's own code on the window with it on: **706 trades, $33,022.03**, worst day −$899.06, largest loss
  −$1,006.91, closed drawdown $2,860. It matches the model trade for trade up to 2026-03-09, the data hole where the
  stand-in data stops at 15:10; after that the two paths part (`verification/noise_v2/v38g_nt_moredays_2026-11-03.txt`).
- **Why it is off by default (what it missed):**
  - one −$1,042 day on the index, 2016-05-16, in the chart's execution only (NinjaTrader's: worst −$906). A morning gap
    win widened that day's budget and the bot's next trade exited past its stop;
  - NQ from January 2015 lost in August 2015. The default itself is only $41 above its floor there, so this one path
    says little; on the 89 start dates it survives as often as the default.
- **Tests:** `test_v38_more_days`: with a $600 trailing drawdown and a $100 cushion (Custom mode), so the fill-ins fire
  within the sample, NinjaTrader's code and the model agree trade for trade, and the switch adds trading days; off, the
  trades are the default's.

## G75: the live loss guard in the backtest (registered 2026-11-03, before its run)

**The idea:** MnqNoiseV38.cs has a live-only loss guard (`LossGuard` $950 in Funded growth). On every tick, when the
day's closed P/L plus the open trade's reaches −$950, it closes the position at market and stops entries for the day.
The backtests (the model's and the strategy's) don't have it, so a bar-close exit past the stop can show a day below
−$1,000 that live trading would have cut near −$950: G70-G72's −$1,042 index day. Here the model gets it
(`loss_guard` 950). Within a bar, the bot's stop orders fill first (at their price). Then, if the bar's worst price
puts the day at −$950 or worse, the trade closes at the price where the day is −$950 (or the bar's open, if it opened
past it), less the usual slippage. No more entries that day.

**Variants:** today's default and U21's "More trading days" on, each with `loss_guard` 950.

**Pass, for each:** against itself without the guard, both executions, all three 5-minute sets: no day at −$1,000 or
worse, and a net no more than 1% lower (the guard only cuts a few days). If both pass, the guard goes into the
NinjaTrader backtest too (the live guard is already there), and U21 is judged again on G74's rule.

**G75 amended before any run (2026-11-03).** Reading the stop code first: on 2016-05-16 the bot's stop was passed by
the bar's open (a 5-point jump), and a live tick-level guard would fill at that same open, so modelling the guard
can't remove that day. The cause is the room: after the morning's +$115 gap win, the day's room was $1,015, so a few
points past the stop crossed −$1,000. **G75 instead tests a $950 cap on the room (`trade_risk_cap` 950, G3's option):** the room for a new trade is never more
than $950 (90% of the daily budget's $900 plus today's P/L as now, but at most $950), so after a green morning the bot
still sizes up, to $950 at most, and $50 of slippage past the stop stays above −$1,000. Variants and pass rule as
registered above (today's default and U21 on, each against itself without it: no −$1,000 day, net at most 1% lower).

**G75 result (run once, 2026-11-03): rejected; capping the room costs most of the profit.**

| 5-minute, chart / NinjaTrader | window | NQ | index | days at −$1,000 |
|---|---|---|---|---|
| today's default | $30,161 / $29,836 | $356,039 / $359,943 | $508,291 / $498,705 | 1 (NQ, chart) |
| default + $950 cap | $25,167 / $25,098 | **$1 / $1, lost** | $364,186 / $358,444 | 0 |
| U21 on | $33,986 / $33,719 | lost / lost | $528,608 / $520,367 | 1 (index, chart) |
| U21 on + $950 cap | $28,691-29,085 | lost | $365,216-365,462 | 0 |

The cap removes the −$1,000 days, but the room after a green morning is where the bot's biggest trades come from: a
trend day's afternoon at 10-15 contracts on the morning's profit. Capped, the index makes 28% less
(`verification/noise_v2/g75_room_cap.txt`).

**Scorecard, G44-G75:** 32 rounds. Adopted: G60 (gap and go, U19), G67b (3 gap contracts once the floor has stopped,
U20) and G67's data fix. Shipped as a switch, off: G72's A2 ("More trading days", U21). Rejected: 27 (G54 and G55
were measurements).

**U21 review fixes (2026-11-03):**
- "More trading days" now does nothing on any chart but 5-minute (it was tested there only; on 30-minute it would have
  traded untested uptrend shorts).
- The dashboard's "today" line: on a calm stretch it says the 09:35 gap trade can still come (it can, since U19), and
  with "More trading days" on and the cushion there, uptrend shorts read "1 MNQ only" instead of "no".

## G76: size for a stop that fills 2 points worse (registered 2026-11-03, before its run)

**The idea, from G75:** a −$1,000 day comes from a bot trade sized to all of the day's room whose stop is passed by
a bar's open (2016-05-16: 5 points past). Capping the room cost 17-28%. Here the room stays, and each contract's risk
in the sizing counts 2 points more slippage at the stop (`size_slip_pts` 2, $4 a contract): at 12 contracts, $48 of
the room is kept for a fill past the stop. It costs a contract only when the room is what limits the size.

**Variants:** today's default and U21's "More trading days" on, each with `size_slip_pts` 2.

**Pass, for each, against itself without it, both executions, all three 5-minute sets:** no day at −$1,000 or worse,
the floor never touched where it wasn't, and a net at most 1% lower. If the default passes, it becomes the default; if
U21-on passes, U21 is judged again on G74's rule.

**G76 result (run once, 2026-11-03): rejected; a near miss for U21.**

| 5-minute, chart / NinjaTrader | window | NQ | index | days at −$1,000 |
|---|---|---|---|---|
| default | $30,161 / $29,836 | $356,039 / $359,943 | $508,291 / $498,705 | 1 |
| default + 2 points | $29,812 / $29,552 | **lost** / $357,545 | $498,270 / $490,286 | 0 |
| U21 on | $33,986 / $33,719 | lost / lost | $528,608 / $520,367 | 1 |
| U21 on + 2 points | $33,962 / $33,773 | lost / lost | $521,452 / $515,363 | **0** |

For U21 it removes the −$1,042 day for 0.1% on the window but 1.0-1.4% on the index, past the 1% registered. For the
default it costs 1-2% and tips NQ's 2015 path in the chart's execution (`verification/noise_v2/g76_size_slip.txt`).

## G77: the gap trade's stop to breakeven at +1R (registered 2026-11-03, before its run)

**The idea:** the 09:35 gap trade's stop is the 09:30 open, and it is out at 09:55 either way. Once a bar closes with
the trade up by its initial risk (entry − stop), its stop moves to the entry plus 1 tick (`gap_go_be` 1.0), so a
gap trade that was up 1R can't become a full loser in the last minutes.

**The variant:** today's default with `gap_go_be` 1.0.

**Adopt only if, against today's default:** a higher net on all three 5-minute sets in both executions; the floor
never touched; no more days at −$1,000; on G35's 89 start dates, no more lost or frozen accounts (11).

**G77 result (run once, 2026-11-03): rejected; NQ's 2015 path again.** Window $30,568 / $30,165 (against $30,161 /
$29,836), index $511,074 / $498,921 (against $508,291 / $498,705), NQ $0 / $1: lost in its first months
(`verification/noise_v2/g77_gap_be.txt`).

## The rule from G78 on (set 2026-11-03, before G78's run)

NQ's single path from January 2015 has decided G61, G63, G68, G72, G73, G76 and G77. Today's default clears it by $41
(G73's note), so it measures one summer's luck, not the change. **From G78 on:** survival is judged on G35's 89 start
dates (35 on NQ from April 2015, 54 on the index), no more lost or frozen accounts than the default's 11. The full NQ
history's net is still a gate wherever the account lives in the default's run; if the change loses that account, it is
reported, and the change is judged on the 89 start dates. The other parts stay: a higher net on the window and the index
(both executions; NQ too where its account lives), the floor never touched on the window and the index, and no more
days at −$1,000 on any set.

## G78: up to 4 gap contracts once the floor has stopped (registered 2026-11-03, before its run)

**The idea:** G67b's 3 passed and G68's 5 failed only on NQ's 2015 path and one −$1,054 index day. 4 is the step
between. `gap_go_locked_qty` 4.

**Adopt on the rule above**, against today's default (3).

**G78 result (run once, 2026-11-03): rejected; the window makes a little less.** Window $30,053 / $29,798 (against
$30,161 / $29,836); index $533,907 / $525,209 (against $508,291 / $498,705); NQ from 2015 lost (reported). 89 start
dates: 11 lost or frozen (as the default), medians $36,647 NQ / $28,805 index (against $34,564 / $27,703)
(`verification/noise_v2/g78_locked4.txt`).

## G79: "More trading days" with the 2-point sizing allowance, as the default (registered 2026-11-03, before its run)

**The idea:** U21's switch (G72's A2) missed only on a −$1,042 index day and NQ's 2015 path. G76's 2-point sizing
allowance removed that day (A2s: no −$1,000 day on any set, either execution). Against today's default, A2s already
showed: window $33,962 / $33,773 (default $30,161 / $29,836), index $521,452 / $515,363 (default $508,291 / $498,705),
72-81% of days. What is missing for G78's rule is the 89 start dates.

**Adopt A2s as the default on G78's rule:** the numbers above stand (run once in G76; not re-run), and on G35's 89 start
dates no more lost or frozen accounts than 11.

**G79 result (2026-11-03): passes; adopted.** On G35's 89 start dates: **11 lost or frozen** (5 of 35 NQ, 6 of 54
index), as the default; medians **$40,443 NQ / $34,289 index** (default $34,564 / $27,703). With G76's numbers
(window $33,962 / $33,773, index $521,452 / $515,363, no −$1,000 day on any set, 72-81% of days), every part of G78's
rule holds. NQ from January 2015 is lost (reported, as the rule says) (`verification/noise_v2/g35_start_dates_a2s.csv`).

**U22 (2026-11-03): "More trading days" on by default, with the 2-point sizing allowance (G79).**
- **Defaults:** "More trading days" **on** (cushion $3,000), and "Sizing: count this many points more slippage at
  each stop" **2**. Both work on 5-minute charts only (where they were tested); on a 30-minute chart the strategy is
  exactly as before. Evaluation mode has neither.
- **The file you trade, on the NinjaTrader simulator** (`research/v38_ninjatrader_run.py grow`, from 2025-01-02):
  - **5-minute: 710 trades, $33,011.82, 51.2% winners, profit factor 1.585, closed drawdown $2,859.94, worst day
    −$899.06, largest loss −$1,006.91.** It matches the model trade for trade to 2026-03-09, the stand-in data's hole
    (the data stops at 15:10; live, MNQ trades to 16:00); the paths part there.
  - 30-minute: unchanged, all 303 trades identical, $28,620.10.
  (`verification/noise_v2/v38g_nt_g79_2026-11-03.txt` and the trade lists beside it.)
- **Tests:** the Funded growth test config now has the fill-ins and the 2-point allowance; `test_v38_gap_go` and
  `test_v38_more_days` switch the fill-ins off where they test without them.

**Scorecard, G44-G79:** 36 rounds. Adopted: G60 (U19), G67b (U20), G67's data fix, G79 (U22, from G72 and G76).
Rejected: 30 (G54 and G55 were measurements).

## G80: up to 5 gap contracts once the floor has stopped, on U22 (registered 2026-11-03, before its run)

**The idea:** G68's 5 gap contracts made $4,700 more on the window and $38,000 on the index, and failed on NQ's 2015
path (no longer a gate, G78's rule) and one −$1,054 index day, which U22's 2-point allowance may now prevent.

**The variant:** today's default (U22) with `gap_go_locked_qty` 5.

**Adopt on G78's rule**, against U22: a higher net on the window and the index in both executions (NQ too where its
account lives), the floor never touched on the window and the index, no more days at −$1,000 on any set, and on the 89
start dates no more lost or frozen accounts than U22's 11.

**G80 result (run once, 2026-11-03/04): passes; adopted.**

| 5-minute, chart / NinjaTrader | U22 (3 gap contracts once stopped) | **U22 + 5** |
|---|---|---|
| days with a trade (window / NQ / index) | 72% / lost / 81% | 72% / lost / 81% |
| window | $33,962 / $33,773 | **$37,861 / $38,189** |
| NQ 2015-25 | lost / lost (reported) | lost / lost (reported) |
| index | $521,452 / $515,363 | **$557,421 / $551,532** |
| days at −$1,000 | 0 | 0 |
| floor touched (window, index) | never | never |
| 89 start dates: lost or frozen | 11 | **11** |
| medians NQ / index | $40,443 / $34,289 | $40,251 / $35,065 |

(`verification/noise_v2/g80_u22_q5.txt`, `g35_start_dates_u22q5.csv`.)

**U23 (2026-11-04): gap and go up to 5 MNQ once the floor has stopped (G80).** "Gap and go once the trailing floor
has stopped at the start: up to this many MNQ" now defaults to **5** (was 3).
- **The file you trade, on the NinjaTrader simulator, 5-minute, from 2025-01-02: 710 trades, $38,090.29, 51.2%
  winners, profit factor 1.625, closed drawdown $3,363.85, worst day −$899.16, largest loss −$1,258.64** (a 5-contract
  gap stop on a day already green). Trade for trade with the model to 2026-03-09 (the stand-in data's hole). 30-minute
  unchanged: $28,620.10, all 303 identical (`verification/noise_v2/v38g_nt_g80_2026-11-04.txt`).

**Scorecard, G44-G80:** 37 rounds. Adopted: G60 (U19), G67b (U20), G67's data fix, G79 (U22), G80 (U23). Rejected: 30
(G54 and G55 were measurements).

## G81: More trading days from a $2,000 cushion (registered 2026-11-04, before its run)

**The idea:** the fill-ins wait for $3,000 above the stopped floor. At $2,000 they start the day the floor stops (the
floor stops when the account is $2,000 up), so the account's second stretch trades more days.

**The variant:** today's default (U23) with "More trading days" cushion $2,000 (`fill_min_room` 2000).

**Adopt on G78's rule**, against U23 (and its 89 start dates' 11).

**G81 result (run once, 2026-11-04): rejected; the window makes less in the chart's execution.** 73.3% / 80.7% of days
(window / index); window $37,569 / $38,250 (U23: $37,861 / $38,189); index $557,462 / $551,577 (U23: $557,421 /
$551,532). The $3,000 cushion stays (`verification/noise_v2/g81_cushion2000.txt`).

## G82: up to 7 gap contracts once the floor has stopped (registered 2026-11-04, before its run)

**The idea:** 3 (G67b) and then 5 (G80) passed. 7 tests whether the gap trade still has room.

**The variant:** U23 with `gap_go_locked_qty` 7. **Adopt on G78's rule**, against U23.

**G82 result (run once, 2026-11-04): passes; adopted.**

| 5-minute, chart / NinjaTrader | U23 (5) | **U23 + 7** |
|---|---|---|
| window | $37,861 / $38,189 | **$40,185 / $40,385** |
| NQ 2015-25 | lost (reported) | lost (reported) |
| index | $557,421 / $551,532 | **$577,985 / $571,453** |
| days at −$1,000, floor touched | 0, never | 0, never |
| 89 start dates: lost or frozen | 11 | **11** |
| medians NQ / index | $40,251 / $35,065 | $42,055 / $34,294 |

(`verification/noise_v2/g82_u23_q7.txt`, `g35_start_dates_u23q7.csv`.)

**U24 (2026-11-04): gap and go up to 7 MNQ once the floor has stopped (G82).** The setting now defaults to **7**.
- **The file you trade, on the NinjaTrader simulator, 5-minute, from 2025-01-02: 706 trades, $40,679.56, 50.9%
  winners, profit factor 1.646, closed drawdown $3,608.60, worst day −$899.06, largest loss −$1,510.37** (a bot trade on
  a day a gap trade had already made money). Trade for trade with the model to 2026-03-09. 30-minute unchanged
  ($28,620.10, all 303 identical) (`verification/noise_v2/v38g_nt_g82_2026-11-04.txt`).

**Scorecard, G44-G82:** 39 rounds. Adopted: G60 (U19), G67b (U20), G67's data fix, G79 (U22), G80 (U23), G82 (U24).
Rejected: 31 (G54 and G55 were measurements).

## G83: the gap trade at the bot's size once the floor has stopped (registered 2026-11-04, before its run)

**The idea:** 3, 5 and 7 each passed. With 15 (the most contracts), a gap trade after the floor stops takes the bot's
own size (its contract steps, sized down to the day's room and the floor's room).

**The variant:** U24 with `gap_go_locked_qty` 15. **Adopt on G78's rule**, against U24.

**G83 result (run once, 2026-11-04): rejected; a −$1,347 day.** Window $44,769 / $45,045, index $626,877 / $618,646,
but the index has a **−$1,347 day in both executions**: a gap trade at the bot's full size whose stop the market jumped
past. That is a broken daily loss limit; 7 stays (`verification/noise_v2/g83_u24_q15.txt`).

## G84: up to 10 gap contracts once the floor has stopped (registered 2026-11-04, before its run)

**The idea:** 7 passed, 15 broke the daily limit once. 10 is between. U24 with `gap_go_locked_qty` 10.
**Adopt on G78's rule**, against U24.

**G84 result (run once, 2026-11-04): passes; adopted.**

| 5-minute, chart / NinjaTrader | U24 (7) | **U24 + 10** |
|---|---|---|
| window | $40,185 / $40,385 | **$43,463 / $43,740** |
| NQ 2015-25 | lost (reported) | lost (reported) |
| index | $577,985 / $571,453 | **$607,307 / $600,553** |
| days at −$1,000, floor touched | 0, never | 0, never |
| 89 start dates: lost or frozen | 11 | **11** |
| medians NQ / index | $42,055 / $34,294 | **$44,185 / $36,305** |

(`verification/noise_v2/g84_u24_q10.txt`, `g35_start_dates_u24q10.csv`.)

**U25 (2026-11-04): gap and go up to 10 MNQ once the floor has stopped (G84).** The setting now defaults to **10**
(15 broke the daily limit once, G83).
- **The file you trade, NinjaTrader simulator, 5-minute, from 2025-01-02: 703 trades, $43,966.90, 50.9% winners,
  profit factor 1.685, closed drawdown $3,317.67, worst day −$899.06, largest loss −$1,762.10** (a trade on a day
  already green). Trade for trade with the model to 2026-03-09. 30-minute unchanged ($28,620.10, all 303 identical)
  (`verification/noise_v2/v38g_nt_g84_2026-11-04.txt`).

**Scorecard, G44-G84:** 41 rounds. Adopted: G60 (U19), G67b (U20), G67's data fix, G79 (U22), G80 (U23), G82 (U24),
G84 (U25). Rejected: 32 (G54 and G55 were measurements).

## G85: up to 12 gap contracts once the floor has stopped (registered 2026-11-04, before its run)

**The idea:** 10 passed, 15 broke the daily limit once (G83). 12 is between. U25 with `gap_go_locked_qty` 12.
**Adopt on G78's rule**, against U25.

**G85 result (run once, 2026-11-04): rejected; a −$1,155 day.** Window $44,397 / $44,670, index $621,412 / $613,266,
but a −$1,155 index day in both executions (a 12-contract gap stop jumped at the open). **10 is the ceiling**: past
it, one gap through the stop at the 09:35 open can break the daily limit (`verification/noise_v2/g85_u25_q12.txt`).

**Scorecard, G44-G85:** 42 rounds. Adopted: G60 (U19), G67b (U20), G67's data fix, G79 (U22), G80 (U23), G82 (U24),
G84 (U25). Rejected: 33 (G54 and G55 were measurements).

## G86: size the gap trade for a jumped stop, then let it grow (registered 2026-11-04, before its run)

**The idea, from G83 and G85:** past 10 contracts, one gap trade whose stop the market jumps at the open breaks the
daily limit. Here each gap contract's risk in the sizing counts 5 points more slippage at its stop (`gap_slip_pts` 5,
$10 a contract), so the trade is cut to what the day's room holds even with a jump; with that, it may take up to 15
(`gap_go_locked_qty` 15).

**The variant:** U25 with `gap_slip_pts` 5 and `gap_go_locked_qty` 15. **Adopt on G78's rule**, against U25.

**G86 result (run once, 2026-11-04): rejected.** Window $42,186 / $42,390 (U25: $43,463 / $43,740), index $612,347 /
$603,423, and the −$1,155 index day is still there in both executions: it isn't the gap stop alone (a big gap win
widens the day, and the bot's next trade, sized to it, takes the loss). U25 stays (`verification/noise_v2/g86_gap_slip.txt`).

**Scorecard, G44-G86:** 43 rounds. Adopted: G60 (U19), G67b (U20), G67's data fix, G79 (U22), G80 (U23), G82 (U24),
G84 (U25). Rejected: 34 (G54 and G55 were measurements).

## G87: a shadow gate near the floor, to save the lost accounts (registered 2026-11-04, before its run)

**The ask:** the user wants the 11 lost or frozen accounts of 89 down to about 1, with the results kept.

**What the 11 are (U25, `g35_start_dates_u24q10.csv`):** 7 made the first $2,000 (the floor stopped at the start)
and then gave it all back; 4 never got there. All 11 died in long losing stretches for this strategy (2011, 2014, 2015,
2019-20, 2021-22). G36-G37 showed that no size or stop change saves them: the bot loses for months even at 1 contract.
The one thing that does is not trading through the stretch. The old equity-curve filter (v3.2's study) did that all
the time and cut the profit by a quarter to most of it.

**The rule (`protect_room`, `protect_n` 20):** a shadow (paper) record of the bot's own signals at 1 contract (no
contract steps, no fill-ins, gap and go at 1, no floor) runs beside the account. While the account is more than
`protect_room` above its trailing floor, nothing changes. Within `protect_room` of it, the account takes a trade (bot,
gap and go, fill-ins) only on a day after the shadow's end-of-day equity closed at or above its average of the last 20
sessions. The shadow never stops, so the account starts again when the strategy does.

**Variants:** A: `protect_room` $1,000; B: $1,500.

**Adopt (the one with fewer lost or frozen; A if tied) only if, against U25, both executions:**
- on G35's 89 start dates, fewer lost or frozen accounts than 11;
- the window's and the index's net at least 95% of U25's (the ask is survival, with the results kept);
- no day at −$1,000 on any set, and the floor never touched on the window and the index.
