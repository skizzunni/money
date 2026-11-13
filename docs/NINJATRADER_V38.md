# MnqNoiseV38 — v3.8 for NinjaTrader 8

`ninjatrader/Strategies/MnqNoiseV38.cs` is one self-contained file: the rules and the orders together, with no
add-on to install. It trades `pine/mnq_noise_momentum.pine` v3.8 (docs/CANDIDATE_E50.md):
- 1 MNQ, $260 max loss per trade, take-profit 2 noise units;
- the stop moves with the line and never back toward the price; the lock at 0.35 max losses, to the entry + 2.5;
- $900 a day, with the stop cut to the room left rather than stopping;
- the filters: last entry 15:00, big day, calm stretch, range position, no shorts in the uptrend, Fed days and
  holidays;
- flat at 16:00.

## Quick start (current, 2026-11-11)

**The file:** `ninjatrader/Strategies/MnqNoiseV38.cs` (one file, nothing else to install).

1. Copy it into `Documents\NinjaTrader 8\bin\Custom\Strategies\` (replace the old one).
2. **New → NinjaScript Editor**, press **F5**. It must report no errors (the repository compiles it as C# 5 with warnings
   as errors, as NinjaTrader 8 does; 709 tests pass, 2026-11-12).
3. Open a **5-minute MNQ chart** (the front month, e.g. MNQ 12-26), trading hours **CME US Index Futures ETH**, **Days to
   load 120** or more (the filters need about 60 sessions before they trade as tested).
4. Add **MnqNoiseV38** to the chart with:
   - **Mode: Funded growth**, for the Test and the funded account alike (G429: with no deadline it passes about 86% of
     Tests against the sprint's 57%, in a median of about 6 months; it is U58, the tested funded mode, on 5-minute bars);
   - Calculate: **On bar close** (the default); leave the other settings as they are;
   - **Place orders:** on, the strategy sends the orders (automated trading); off, it only alerts and you place each
     order by hand. Take Profit Trader's rules do not allow automated trading.
5. Enable it. The dashboard (top right) is **live**: once the strategy is running on live data it redraws on the ticks
   (at most once a second, and at once when the position changes), not only at the 5-minute bar closes. Its first line
   reads "LIVE, updated hh:mm:ss New York, last <price>"; it shows the account's balance, net liquidation, realized and
   open P/L, the prop floor and the room above it, the strategy's P/L today, this week and this month, the next trade's
   size, today's rules and the next entry check, and the open trade (side, size, entry, stop, target, its open P/L at the
   last price and the points left to its stop, the lock and the time stop). A dashboard error never stops the trading
   (it is printed once and the next bar redraws it). The Output window logs every stop it sends ("MnqNoiseV38 stop
   placed") and alerts **STOP CHECK FAILED** if a position is ever without a live stop.

**Other modes (opt-in, 5-minute chart only):**
- **Funded green days** (50K): Funded growth that, from 11:00, stops for the day as soon as the day is green (G481).
  About 50% of traded days green instead of 42%, at half to two thirds of the money.
- **Funded growth plus** (50K): Funded growth with +1 MNQ per $1,250 of profit (G478). It made 11-16% more a session on
  every set; it lost 1 more account on two of the three sets (3.2% against 0% and 1.6%). The middle ground.
- **Funded aggressive** (50K): no giveback brake, +1 MNQ per $1,000 of profit, a $1,000 day budget until the floor
  stops (G475's A1). It made 13-26% more a session but lost about 1 account in 8 on the recent starts and 1 in 11 on
  unseen ones (Funded growth: 0 and 1 in 64). Only if a lost account is cheap to replace.
- **Funded growth 100K U58** (a 100K): U58 on a $3,000 end-of-day trailing floor and a $1,800 day budget ($1,500 until
  the floor stops), +1 MNQ per $2,000 of profit, no brake (G466 / G473). Those limits are assumed: check them against
  your firm's and change Daily loss / Trailing drawdown if they differ.

**Several accounts:** NinjaTrader runs a strategy per account. For each funded account, open its own 5-minute MNQ chart
(or one chart with the strategy added once per account), add MnqNoiseV38 with that account selected under Account and
its own Mode, and enable it. Each copy sizes and protects its own account; profits add up account by account. Check
your firm's limit on accounts per person and its rules on automated trading first.

**What it does:** U58. Entries at the half-hour checks (10:00-15:00 New York in Funded growth; the Test sprint to 15:30) when price closes outside the noise area
(narrower on calm stretches), a stop with every entry ($187.50 a contract at most), the size from the profit so far and
the room above the $2,000 floor, the 45-minute time stop, flat at 16:00. On the 2025-26 window, NinjaTrader's own
backtest of this file: $75,486 on 5-minute bars, 784 trades, profit factor 1.91, worst day −$899.

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

| Jan 2, 2025 – Oct 2026 (updated 2026-11-05, U47) | 5-minute bars | 30-minute bars |
|---|---|---|
| Trades | 760 | 254 |
| Net | **$61,096.19** | $28,191.46 |
| Winners | 49.3% | 53.5% |
| Profit factor | 1.665 | 1.933 |
| Closed drawdown | $6,106.23 | $3,633.60 |
| Largest loss | −$1,927.41 | −$1,634.41 |
| Worst day | −$899.24 | −$899.20 |
| Most contracts | 75 | 15 |
| Days with a trade (the model) | about 72% | about 29% |

The 5-minute chart includes gap and go (U19, U20, U25: up to 10 MNQ once the floor has stopped), More trading days with the sizing allowance (U22, U26: 2-MNQ fill-ins from $6,000, 3 points), the
data fix (G67), the after-loss max loss at $187.50 once the floor has stopped (U30), up to 50 MNQ (U32) and no entries
at 13:00 and 14:30 until the floor has stopped (U33), faster contract steps above $10,000 of profit (U34) and the after-loss max loss as every trade's, $187.50 (U35-U37), a 5-point sizing allowance (U38) the drive fill-in at 0.6x (U39) More trading days from a $2,500 cushion (U40) no gap trade while the giveback brake is on (U41) and G204's five survival settings (U42: three losers a day, a $750 day budget until the floor stops, a 45-minute time stop, the top 70% of the range, the gap trade from 0.6x; on the 50K's Funded growth, both charts) $700 steps above $8,000 with 3-MNQ fill-ins from $9,000 (U43), and $650 steps, fill-ins at 2 MNQ from $4,000 and 3 from $8,000, up to 75 MNQ (U44), and the fast steps from $9,000, a 4-point sizing allowance and the giveback brake at 0.45 (U47). They need the 5-minute chart, so **trade the 5-minute chart**.

**What to expect (measured 2026-11-04, G141/G144/G165 and the 263 fresh starts):**
- A fresh 50K account on U47: about **1 in 24 is lost or frozen** within 21 months (22 of 526 starts on the 1st and the
  15th of each month; U46: 23; U45: 25; U42-U44: 28; U41: 38; U40: 42; U34: 60, about 1 in 9); the median account makes **$46,561
  in 21 months** (about $510 a week; U46 $39,513); +$3,000 takes a median 144 days (within 30 days in 4.2%); +$50,000
  within 21 months in 51.9% (median 15.9 months). U42-U43 trade some of the median's profit for 10 fewer lost accounts in 526;
  U43's own gain is in the grown phase and on the long histories.
- Once the account is $10,000-30,000 up: the window averaged **$1,483 a week** on U44 (11% of weeks at +$3,000 or more;
  U43 $1,668, U42 $1,532; G213, `verification/noise_v2/g213_weekly_u44.txt`);
  past $30,000 the day's $900 budget caps every trade and the long histories average $600-1,200 a week.
- At 2 ticks of slippage instead of 1, the window still makes $52,137 (G156).

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

Once 20 trades average more than 2 ticks, the dashboard warns to check the connection and order route (until G222 it
said "consider Gentle start", which G222 found doesn't help on U44). G29-G30 and G215 found that worse fills put a new
account's first months at risk.

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
From 30 trades, the dashboard compares the real win rate with the tested one ("Win rate check", group 5, default 61.2% until U45, 49.7% in U45, now 49.3%,
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

## G88: today's default on the 100K and 150K accounts (a measurement, 2026-11-04)

**Why:** G87 shows the lost accounts move around under any rule but the count stays near 10-11 of 89 on a 50K. What
changed it before was the cushion (G40: the 50K's size on a 150K's limits, 14 → 5 dead). This measures today's
default (U25) on the 100K ($1,800 budget, $3,000 trailing) and 150K ($2,700, $4,500) limits, the existing Funded
growth 100K / 150K modes. No adoption: the modes are there; this says what they now give.

**G87 as run: not the rule as written.** Building the NinjaTrader side showed the model's shadow was not 1 contract:
with contract steps off, an old sizing branch (`size_up_to` with `profit_step` 0) let it trade up to 15 contracts
whenever the day's room allowed. NinjaTrader's shadow is 1 contract, as registered. As run, variant A gave 10 lost or
frozen of 89 (index 3, NQ 7), window $42,726 / $42,854, index $602,186 / $593,329, NQ $457,838 / $457,374 (the 2015
path lived), no −$1,000 day; B gave 16. Nothing is adopted from it.

## G87b: G87 with the shadow at 1 contract (registered 2026-11-04, before its run)

The same rule, variants and pass rule as G87, with the shadow fixed to 1 contract (`size_up_to` 1 in
`research/shadow_gate.py`), as NinjaTrader's code has it.

**G87b result (run once, 2026-11-04): rejected; the gate loses more accounts.**

| | 89 start dates: lost or frozen (NQ / index) | window, chart / NinjaTrader | index |
|---|---|---|---|
| U25 (today) | **11** (5 / 6) | $43,463 / $43,740 | $607,307 / $600,553 |
| A, $1,000, 1-contract shadow | 15 (9 / 6) | $43,574 / $42,875 | $596,406 / $593,321 |
| B, $1,500 | (not needed) | $43,820 / **$7,164, lost** | $601,979 / $593,280 |

Near the floor, the gate skips the first winners of a recovery (the shadow is still under its average when the market
turns), and the account that would have climbed out sits until the room is too small to trade. The lost accounts move
around under any rule here: G87 saved 10 of the 11 and lost 9 others. `protect_room` and the C# `NearFloorGate` stay
in the code, **off** (`verification/noise_v2/g87b_shadow_gate.txt`).

**G88 result (measured 2026-11-04): the cushion is what saves accounts.** Today's default (U25) on each account's
limits (the existing Funded growth / 100K / 150K modes), 5-minute bars:

| | 50K ($900 / $2,000) | 100K ($1,800 / $3,000) | 150K ($2,700 / $4,500) | 150K + G87's gate |
|---|---|---|---|---|
| 89 start dates: lost or frozen (NQ / index) | 11 (5 / 6) | **5** (3 / 2) | **4** (3 / 1) | **3** (0 / 3) |
| median 21-month net, NQ / index | $44,185 / $36,305 | $62,974 / $48,045 | $63,007 / $50,096 | $66,724 / $49,296 |
| window, chart / NinjaTrader | $43,463 / $43,740 | $46,142 / $45,796 | $33,902 / $33,115 | |
| index 2011-26, chart / NinjaTrader | $607,307 / $600,553 | $899,260 / $873,890 | $1,073,921 / $1,054,035 | |
| worst day (the account's daily rule) | −$899 ($1,000) | −$1,873 ($2,000) | −$2,719 ($3,000) | |
| days with a trade, window | 72% | 69% | 60% | |

The floor was never touched on the window or the index; NQ's January 2015 path is lost on all three (reported, as
G78's rule says). The 150K makes less on the window because its floor stops later (at +$4,500), so the fill-ins and
the bigger gap trades start later; it makes the most on the long histories.

**What the 50K can do (G35-G37, G87, G87b):** every rule tried moves which accounts die, not how many: about 11 of
89. With a $2,000 trailing drawdown, a long losing stretch for this strategy ends some new accounts whatever the rule.
A bigger account, or the same 50K's risk spread over more than one account, is what lowers it
(`verification/noise_v2/g88_account_sizes.txt`).

**Scorecard, G44-G88:** 45 rounds. Adopted: G60 (U19), G67b (U20), G67's data fix, G79 (U22), G80 (U23), G82 (U24),
G84 (U25). Rejected: 35. Measurements: G54, G55, G88.

## G89: the time stop re-checked on U25 (registered 2026-11-04, before its run)

**The idea:** G6 chose 60 minutes (and G9 rejected longer) on a bot that traded on 3 days in 10, before gap and go,
More trading days and 10-contract gap trades. With the trade mix changed this much, 45 and 90 minutes are re-checked.

**Variants:** U25 with `time_stop` 45 and 90.

**Adopt (the better by window net) on G78's rule**, against U25 (60): a higher net on the window and the index in both
executions, the floor never touched there, no more days at −$1,000 on any set, and on the 89 start dates no more lost
or frozen accounts than 11.

**G89 result (run once, 2026-11-04): rejected; 60 minutes stays.** 45 minutes: window $43,116 / $43,155, index
$597,657 / $586,740 (U25: $43,463 / $43,740, $607,307 / $600,553); its NQ 2015 path lived ($444,071). 90 minutes:
window $43,001 / $43,358, index $593,290 / $584,463 (`verification/noise_v2/g89_time_stop.txt`).

## G90: the take-profit re-checked on U25 (registered 2026-11-04, before its run)

**The idea:** G45 kept 2 noise units with the time stop, before gap and go, More trading days and 10-contract gap
trades. **Variants:** U25 with `take_profit` 1.5 and 2.5. **Adopt (the better by window net) on G78's rule**, against U25.

**G90 result (run once, 2026-11-04): rejected; 2 noise units stays.** 1.5: the index's account lost in both executions
(and NQ's in NinjaTrader's). 2.5: window $40,920 / $41,081, index $559,118 / $560,266, both below U25
(`verification/noise_v2/g90_take_profit.txt`).

## G91: the lock trigger re-checked on U25 (registered 2026-11-04, before its run)

**The idea:** the lock (stop to the entry plus 2.5 points once the trade is up 0.35 of its max loss) was set in v3.2 and
re-checked in G21, before gap and go and the rest. **Variants:** U25 with `lock_at` 0.25 and 0.5.
**Adopt (the better by window net) on G78's rule**, against U25.

**G91 result (run once, 2026-11-04): rejected; 0.35 stays.** 0.5: window $43,975 / $44,408 (more), index $584,580 /
$563,690 (less). 0.25: less on both (window $42,655 / $43,113, index $575,158 / $555,996)
(`verification/noise_v2/g91_lock.txt`).

## G92: the stop distance past the line re-checked on U25 (registered 2026-11-04, before its run)

**The idea:** the stop sits 0.24 noise units past the line (G22, before gap and go and the rest).
**Variants:** U25 with `stop_buffer` 0.18 and 0.30. **Adopt (the better by window net) on G78's rule**, against U25.

**G92 result (run once, 2026-11-04): rejected; a near miss at 0.18.** 0.18: window **$46,291 / $46,293** (U25: $43,463
/ $43,740), index $616,890 / **$595,276** (U25: $607,307 / $600,553), and a −$1,012 index day in the chart's
execution. 0.30: less everywhere (window $40,279 / $40,365) (`verification/noise_v2/g92_stop_buffer.txt`).

## G93: the stop 0.21 noise units past the line (registered 2026-11-04, before its run)

**The idea:** between G92's 0.18 (more on the window and the chart's index, a −$1,012 day) and today's 0.24.
**The variant:** U25 with `stop_buffer` 0.21. **Adopt on G78's rule**, against U25.

**G93 result (run once, 2026-11-04): rejected by one day.** Window $44,412 / $44,479, index $622,500 / $605,574 (both
above U25), NQ's 2015 account lived ($431,394 / $427,989), but a −$1,030 NQ day in the chart's execution (none at
−$1,000 in NinjaTrader's). The rule allows no more days at −$1,000 on any set, so 0.24 stays
(`verification/noise_v2/g93_stop_buffer21.txt`).

**Scorecard, G44-G93:** 50 rounds. Adopted: G60 (U19), G67b (U20), G67's data fix, G79 (U22), G80 (U23), G82 (U24),
G84 (U25). Rejected: 40. Measurements: G54, G55, G88.

## G94: G93's 0.21 stop with a 3-point sizing allowance (registered 2026-11-04, before its run)

**The idea:** G93 failed only on one −$1,030 day (a stop filled past its price on a full-size day). G76/G79's sizing
allowance is what removed such days before; 3 points (from 2) keeps $6 a contract more of the room for it.
**The variant:** U25 with `stop_buffer` 0.21 and `size_slip_pts` 3. **Adopt on G78's rule**, against U25.
**Caution, written before the run:** this is the third stop-buffer variant in a row (G92, G93), so a pass carries
more chance of luck than a first try; the 89 start dates are the check on that.

**G94 result (run once, 2026-11-04): rejected on the 89 start dates.** Window $43,941 / $44,342, index $622,303 /
$600,942, NQ's 2015 account lived, no −$1,000 day, but **13 lost or frozen of 89** (NQ 7, index 6) against U25's 11,
and the NQ median fell to $27,171 (U25: $44,185). As the caution said, the gain on the three sets didn't hold for new
accounts. 0.24 and 2 points stay (`verification/noise_v2/g94_sb21_s3.txt`, `g35_start_dates_u25sb21s3.csv`).

**Scorecard, G44-G94:** 51 rounds. Adopted: G60 (U19), G67b (U20), G67's data fix, G79 (U22), G80 (U23), G82 (U24),
G84 (U25). Rejected: 41. Measurements: G54, G55, G88.

## G95: calm-stretch fill-ins at 1 MNQ (registered 2026-11-04, before its run)

**The idea:** on a calm stretch (the last 10 sessions' ranges under 0.7 of the last 40's) the bot takes no entries.
U22's fill-in rule extended: once the floor has stopped and the account is $3,000 above it, the bot's signals on calm
days trade at 1 MNQ at its usual max loss a contract (`calm_small`), counted as fill-ins.
**The variant:** U25 with `calm_small`. **Adopt on G78's rule**, against U25.

**G95 result (run once, 2026-11-04): rejected; calm-day trades lose.** Window $43,197 / $42,728, index $603,157 /
$596,234, both below U25 (`verification/noise_v2/g95_calm_small.txt`). The calm filter's blocked trades are losers
even at 1 MNQ.

## G96: fill-ins at 2 MNQ with a $6,000 cushion (registered 2026-11-04, before its run)

**The idea:** the fill-ins (small gaps, drives, uptrend shorts) made money at 1 MNQ (G72). Once the account is $6,000
above the stopped floor (twice their cushion), they take 2 MNQ (`fill_qty2_room` 6000); below it, 1 as now.
**The variant:** U25 with `fill_qty2_room` 6000. **Adopt on G78's rule**, against U25.

**G96 result (run once, 2026-11-04): rejected by one day.** Window **$46,254 / $46,441**, index **$649,705 /
$638,929** (U25: $43,463 / $43,740, $607,307 / $600,553), but a −$1,023 index day in the chart's execution: 2016-05-16,
a +$230 gap trade (2 MNQ) widened the day's room, and the bot's 10:00 trade at 13 contracts exited 7.5 points past its
stop (−$1,253) (`verification/noise_v2/g96_fill2.txt`).

## G97: G96 with a 3-point sizing allowance (registered 2026-11-04, before its run)

**The idea:** at 3 points (from 2), that 10:00 trade sizes to 12 contracts and the day ends near −$926. Everything else
is G96. **The variant:** U25 with `fill_qty2_room` 6000 and `size_slip_pts` 3. **Adopt on G78's rule**, against U25.
**Caution:** a fix aimed at one known day; the 89 start dates are the check.

**G97 result (run once, 2026-11-04): passes; adopted.**

| 5-minute, chart / NinjaTrader | U25 | **U25 + 2-MNQ fill-ins from $6,000 + 3-point allowance** |
|---|---|---|
| window | $43,463 / $43,740 | **$45,340 / $45,396** |
| index | $607,307 / $600,553 | **$639,474 / $629,316** |
| NQ 2015-25 | lost (reported) | $466,564 / lost (reported) |
| days at −$1,000, floor touched | 0, never | 0, never |
| 89 start dates: lost or frozen | 11 | **11** |
| medians NQ / index | $44,185 / $36,305 | **$47,789 / $39,130** |

(`verification/noise_v2/g97_fill2_s3.txt`, `g35_start_dates_u25f2s3.csv`.)

**U26 (2026-11-04): fill-ins at 2 MNQ well above the floor, and a 3-point sizing allowance (G97).**
- **New setting:** "More trading days: fill-ins at 2 MNQ while the account is at least this far above the floor, $"
  (**6,000**); below it they stay at 1 MNQ. "Sizing: count this many points more slippage at each stop" now **3**.
  Both act on 5-minute charts only.
- **The file you trade, NinjaTrader simulator, 5-minute, from 2025-01-02: 704 trades, $45,289.92, 50.8% winners,
  profit factor 1.634, closed drawdown $4,333.80, worst day −$899.44, largest loss −$1,762.10.** Trade for trade with
  the model to 2026-03-09 (the data hole). 30-minute unchanged ($28,620.10, all 303 identical)
  (`verification/noise_v2/v38g_nt_g97_2026-11-04.txt`).

**Scorecard, G44-G97:** 54 rounds. Adopted: G60 (U19), G67b (U20), G67's data fix, G79 (U22), G80 (U23), G82 (U24),
G84 (U25), G97 (U26). Rejected: 43. Measurements: G54, G55, G88.

## Measured (2026-11-04): no losing slice of trades

At 1 contract over NQ 2015-25 and the index 2011-26 (`research/g98_trade_slices.py`), every slice of the bot's trades
makes money: longs ($23 a trade, t 4.7-5.7), shorts ($25-27, t 3.6-4.6), gap trades ($13-19, t 2.9-3.3), every check
time from 10:00 to 15:00, every weekday, and the trades after a loser ($29-30 a trade, more than the rest). So the
lost accounts are not a bad kind of trade to drop: they are runs of ordinary losers at the wrong time for a $2,000
drawdown.

## G98: gap contracts that grow with the cushion (registered 2026-11-04, before its run)

**The idea:** once the floor stops, the gap trade may take 10 MNQ at once, when the account is only about $2,000 above
the floor; one 09:35 stop then costs up to the whole day's $900. Here, once the floor has stopped, the gap trade's
contracts are at most 1 per $400 above the floor (`gap_go_room_per_c` 400: 5 at $2,000, 10 from $4,000), up to 10.
**The variant:** U26 with `gap_go_room_per_c` 400. **Adopt on G78's rule**, against U26 (and its 89 start dates' 11).

**G98 result (run once, 2026-11-04): no effect; rejected.** Every number is U26's: the gap trade is already capped by
the bot's own contract steps (1 + 1 per $1,500 of profit: 2 at +$2,000) and by the day's room, so 1 per $400 above
the floor never binds (`verification/noise_v2/g98_gap_room.txt`).

## G99: a giveback brake (registered 2026-11-04, before its run)

**The idea:** 7 of the 11 lost accounts made the first $2,000 and then gave it all back. Once the floor has stopped,
while the account's profit is under half of its best end-of-day profit (`giveback_brake` 0.5), every trade (the bot's,
gap and go, the fill-ins) takes 1 MNQ. It keeps trading, so the recovery's winners are taken (unlike G87's gate), at
the smallest size; above half of the best, everything is as now.
**The variant:** U26 with `giveback_brake` 0.5. **Adopt on G78's rule**, against U26.

**G99 result (run once, 2026-11-04): fails G78's rule by not being higher.** Window $45,340 / $45,396 (identical to
U26), index $639,432 / $629,489 (U26: $639,474 / $629,316), and NQ's 2015 path lived in both executions ($472,623 /
$470,273). The brake rarely acts where an account is doing well; what it is for is the accounts that give it back
(`verification/noise_v2/g99_giveback.txt`).

## G99b: the giveback brake on the survival-first rule (registered 2026-11-04, before the start dates are run)

The same variant as G99, judged on G87's survival-first rule (the ask is fewer lost accounts with the results kept):
**adopt only if**, on G35's 89 start dates, **fewer lost or frozen accounts than U26's 11**; the window's and the
index's net at least 95% of U26's in both executions (already known: 100%); no day at −$1,000 on any set; the floor
never touched on the window and the index.

**G99b result (run once, 2026-11-04): passes.** 89 start dates: **5 lost or frozen** (NQ 2 of 35, index 3 of 54)
against U26's 11; medians $43,402 NQ / $37,330 index (U26: $47,789 / $39,130); window and index nets 100% of U26's; no
−$1,000 day; floor never touched (`g35_start_dates_u26gb.csv`).

**A bug, found while building the NinjaTrader side:** with the brake on, the model set a gap trade to exactly 1
contract, even on a day whose room fitted none (it should be at most 1). The fix (`min(q, 1)`) is re-run in full
before adoption (G99c): the three sets in both executions and the 89 start dates, on G99b's rule.

**G99c result (run once, 2026-11-04): passes G99b's rule; adopted.** With the bug fixed: 89 start dates **10 lost or
frozen** (NQ 5, index 5) against U26's 11; window $45,340 / $45,396 and index $639,432 / $629,489 (100% of U26's);
NQ's 2015 path lived ($472,623 / $470,273); no −$1,000 day; floor never touched. The medians fell: $43,053 NQ /
$36,981 index (U26: $47,789 / $39,130). Honest reading: one account saved, at about $2,000-4,700 of the typical
account's 21 months (`verification/noise_v2/g99c_giveback.txt`, `g35_start_dates_u26gb.csv`).

**What the bug showed (G99b, 5 of 89):** the extra survivors were accounts near the floor that kept taking 1-MNQ gap
trades when the room no longer fitted one, and climbed back. Risking more than the room is not allowed, but the idea
that a nearly frozen account should keep trading small is G100.

**U27 (2026-11-04): the giveback brake (G99c).** New setting, group 1: "Giveback brake: once the floor has stopped,
1 MNQ per trade while the profit is under this share of its best", **0.5**. 5-minute charts only; not in Evaluation.
The dashboard's "today" line says when it is on. The file you trade, 5-minute window: unchanged, **704 trades,
$45,289.92** (the window's account never gives back half its best). `test_v38_giveback_brake`: with a 0.9 brake and a
$600 trailing drawdown (Custom mode), NinjaTrader's code and the model agree trade for trade on and off, and the brake
cuts the contracts.

## G100: a nearly frozen account keeps trading (registered 2026-11-04, before its run)

**The idea, from G99b:** when the room above the floor can't fit 1 contract of the gap trade's stop, the gap trade is
skipped today, and an account near the floor stops trading and freezes. Here it takes the gap trade at 1 MNQ with its
stop cut to the room, as the bot's own squeeze does (`gap_squeeze`), if the room is at least 10 points ($20) plus
costs: never more risk than the room.
**The variant:** U27 with `gap_squeeze`. **Adopt on G99b's rule** (fewer lost or frozen than U27's 10; the window's
and the index's net at least 95% of U27's; no −$1,000 day; floor never touched on the window and the index).

**G100 result (run once, 2026-11-04): rejected.** 89 start dates: 11 lost or frozen (NQ 5, index 6) against U27's
10; window and index unchanged. A gap trade squeezed to the room (often 10-30 points) is stopped out by the opening
noise and doesn't bring the account back; what kept G99b's accounts alive was risking more than the room, which is
not allowed (`verification/noise_v2/g100_gap_squeeze.txt`).

**Scorecard, G44-G100:** 57 rounds. Adopted: G60 (U19), G67b (U20), G67's data fix, G79 (U22), G80 (U23), G82 (U24),
G84 (U25), G97 (U26), G99c (U27). Rejected: 45. Measurements: G54, G55, G88.

**U28 (2026-11-04): the dashboard tracks the live account, and trades never risk more than the account's own room.**
At the user's ask (the dashboard must follow the live account, and the strategy must trade once an account is
connected). Before this, the dashboard's "Account P/L" was the strategy's own fills, which in NinjaTrader include the
backtest it replays on the chart's history before going live.
- **New group "6. Prop account":** its starting balance (**$50,000**), its highest end-of-day balance so far (0 = the
  start), and "never risk more than the account's own room above its floor (live)" (**on**).
- **Live, the dashboard now shows** the account's name, balance and net liquidation, today's realized and open P/L
  (from the account), the trades closed live since enabling (`SystemPerformance.RealTimeTrades`), and the prop floor
  from the account's own balance (its highest end-of-day balance, at least the start and the balance at go-live, less
  the trailing drawdown, never above the start) with the room above it and the profit. If the strategy counts more room
  than the account has, a CHECK line says so. Before going live it says it will show the account once enabled. The
  old line is now "Strategy P/L (its fills, history and live)".
- **The room cap:** live, a new trade (the bot's, gap and go, the fill-ins) never risks more than the account's room
  above its floor; the floor's high follows the account's balance at each day's close. It only ever makes a trade
  smaller. It is not used while the connection reports no balance (net liquidation 0), so it can't block trading, and
  not in Evaluation (no trailing floor). Backtests are unchanged.
- **Tests:** `test_v38_live_account_dashboard` (live on an account $1,700 under its start: the dashboard shows the
  account, the floor at $48,000 and $300 of room, the CHECK line, and the trades shrink; with the check off, the live
  trades are the backtest's) and `test_v38_live_without_account_values` (a connection with no balance: the trades are
  the backtest's and the dashboard says it is waiting). All 35 v3.8 tests and the other NinjaTrader tests pass (168).

**Will it trade once an account is connected? The conditions, all checked in the code (`OnBarUpdate`):**
1. **The chart:** MNQ (front month), a **5-minute** chart (any minute length that divides 30 runs; the 5-minute one is
   the tested one), Trading hours CME US Index Futures ETH, **Days to load 120 or more**. Any other bar type stops it
   with a setup warning on the dashboard.
2. **The strategy's settings:** Mode Funded growth, **"Trailing drawdown and contract steps from date" = your account's
   first trading day** (blank counts the chart's history as your account; a bad stretch there can leave it thinking
   it is at the floor and not trading), Account = your prop account, Calculate On bar close, Place orders on (default).
   Prop account starting balance: the account's start ($50,000), and its highest end-of-day balance if it has one.
3. **Enabling:** with the default "Wait until flat", if the replayed history ends in a position the strategy waits for
   that to close (the same day at most), then trades. The dashboard says LIVE with the account's name once it is.
4. **When it trades:** a gap-and-go trade at 09:35 New York on gap days, the bot's checks every half hour 10:00-15:00,
   and once the floor has stopped, the fill-ins. About 7 days in 10 have a trade (the model); some days none.

## G101: the giveback brake earlier, at 70% of the best profit (registered 2026-11-04, before its run)

**The idea:** U27's brake acts once the profit is under half of its best. At 0.7 it acts sooner in a drawdown.
**The variant:** U27 with `giveback_brake` 0.7. **Adopt on G99b's rule**, against U27 (fewer lost or frozen than 10 on
the 89 start dates; the window's and the index's net at least 95% of U27's in both executions; no −$1,000 day; floor
never touched on the window and the index).

**G101 result (run once, 2026-11-04): rejected on the net.** 89 start dates: 8 lost or frozen (NQ 4, index 4) against
U27's 10, but the index's net fell to 83% / 80% of U27's ($532,561 / $504,295), the window to $43,091 / $42,936 (95.0%
/ 94.6%), and the index median to $16,634 (U27: $36,981). Braking at 70% of the best catches ordinary pullbacks and
keeps a healthy account at 1 MNQ for long stretches. 0.5 stays (`verification/noise_v2/g101_giveback07.txt`).

**Scorecard, G44-G101:** 58 rounds. Adopted: G60 (U19), G67b (U20), G67's data fix, G79 (U22), G80 (U23), G82 (U24),
G84 (U25), G97 (U26), G99c (U27). Rejected: 46. Measurements: G54, G55, G88. (U28, the live-account dashboard and
room cap, is a safety change, not a G round.)

## Measured (2026-11-04): why the user's NinjaTrader run shows 101 trades and $7,046

The user's Strategy Analyzer run: MNQ DEC26, 5-minute, 1/1/2026-11/2/2026, 101 trades, $7,046.00, 0.98 trades a day
(about 103 trading days). The model, U28, NinjaTrader's execution (`research/user_runs.py`):

| | trades | days with a trade | net |
|---|---|---|---|
| account from 2025-01-02 (the reported window, 22 months) | 704 | 73% | $45,396 |
| a fresh account from 2026-01-02 (to 2026-10-16) | 198 | 49% | $9,580 |
| data from 2026-05-03 only (the user's DEC26 history), account from then | 139 | 58% | $9,600 |

- **The user's data starts in May:** the MNQ DEC26 contract's history begins 2026-05-03 (found earlier), so January-
  April has no bars; 101 trades at 0.98 a day is about five months.
- **$45k is 22 months:** the window's account was +$3,000 by August 2025 and traded bigger and more often from there.
  A fresh account in 2026 first reached +$3,000 in August 2026.
- **The fill-ins (most of the extra days) start only $3,000 above the stopped floor**, so a new account trades on
  about half the days until then.

## G102: fill-ins from day one (registered 2026-11-04, before its run)

**The ask:** trades every day. **The variant:** U28 with the fill-ins (small gaps, drives, uptrend shorts) from the
start at 1 MNQ (`fill_after_lock` off, `fill_min_room` 0; 2 MNQ still from $6,000 above the floor), with the giveback
brake on. G69/G70 tried this without the brake and lost new accounts.
**Adopt on G99b's rule**, against U28 (U27's numbers): fewer lost or frozen than 10 on the 89 start dates... and, since
the ask is days traded, also as a switch ("Fill-ins from day one", off) if it holds 10 or fewer with the nets at 95%.
Also reported: days with a trade for a fresh 2026 account.

**G102 result (run once, 2026-11-04): rejected; trading every day from the start loses new accounts.**

| | days with a trade (window / NQ / index) | window | index | 89 start dates: lost or frozen |
|---|---|---|---|---|
| U28 | 72% / – / 81% | $45,340 / $45,396 | $639,432 / $629,489 | 10 |
| fill-ins from day one | **86% / 85% / 1.6%** | $48,927 / $49,192 | **−$8 / −$18, lost in its first weeks** | **22** (NQ 8, index 14) |

The giveback brake doesn't change G69's finding: before the account has a cushion, the fill-ins' losers take a new
account to the floor about twice as often. The fill-ins stay behind the $3,000 cushion
(`verification/noise_v2/g102_fill_day1.txt`).

**Scorecard, G44-G102:** 59 rounds. Adopted 9 (and the data fix); rejected 47; measurements 3.

## G103: a one-week sprint to +$3,000 (registered 2026-11-04, before its run)

**The ask:** +$3,000 on a fresh 50K within a week. **The rule (`sprint_qty`, `sprint_days` 5, `sprint_target`
3000):** for the account's first 5 sessions, until its profit reaches $3,000, every bot and gap trade takes
`sprint_qty` contracts (still cut to the day's $900 budget and the room above the floor); after that, U28's sizing.
**Variants:** 5, 8 and 10 MNQ. **Measured on G35's 89 fresh-account starts:** the share at +$3,000 within 7 calendar
days, lost or frozen within 21 months, and the median net. No adoption as the default; the best (the most at +$3,000
in a week with lost or frozen at most 2x U28's 10) becomes an opt-in setting, with its odds stated.

**G103 result (run once, 2026-11-04): none qualifies.** G35's 89 fresh-account starts:

| | +$3,000 within 7 days | within 30 days | lost or frozen in 21 months | median 21-month net |
|---|---|---|---|---|
| U28 (today) | 0.0% | 4.5% | 10 of 89 | $39,445 |
| sprint 5 MNQ | 7.9% | 19.1% | 21 of 89 | $37,495 |
| sprint 8 MNQ | 13.5% | 21.3% | 22 of 89 | $37,335 |
| sprint 10 MNQ | 15.7% | 21.3% | 24 of 89 | $37,478 |

Every sprint more than doubles the lost accounts (the bar was at most 2x U28's 10), so none is recommended. The setting
("Sprint", `SprintContracts`) stays in the file at 0 (off), with these odds, for an account the user can afford to
lose (`verification/noise_v2/g103_sprint.txt`).

**Weekly profit, measured on the window's account (U28, NinjaTrader's execution, from 2025-01-02):** average $482 a
week, median $7; weeks at $3,000 or more: 5% overall, 0% in the first 15 months, 15-23% once the account had grown
(2026 Q2-Q3, at 10-15 contracts, average $800-1,640 a week). About 4 weeks in 10 lose money in every phase.

**Scorecard, G44-G103:** 60 rounds. Adopted 9 (and the data fix); rejected 48; measurements 3.

## G104: faster contract steps once the floor has stopped (registered 2026-11-04, before its run)

**The idea:** the slow part is growth. G5/G63's faster steps lost accounts early; here they start only once the floor
has stopped at the start (the first $2,000 made), with U27's giveback brake on: a contract per $1,000 of profit from
then (`profit_step_locked` 1000), $1,500 before.
**The variant:** U28 with `profit_step_locked` 1000. **Adopt on G78's rule**, against U28 (survival: no more lost or
frozen than 10 on the 89 start dates).

**G104 result (run once, 2026-11-04): rejected.** 89 start dates: 18 lost or frozen (NQ 8, index 10) against 10;
window $44,141 / $44,199 (U28: $45,340 / $45,396). Faster steps still cost accounts, brake or not
(`verification/noise_v2/g104_steps_locked.txt`).

## G105: up to 20 contracts (registered 2026-11-04, before its run)

**The idea:** the lost accounts die early, at small size; the most contracts (15) binds only on grown accounts, where
the weekly profit is made. Every trade still fits the day's $900 budget and the room above the floor.
**The variant:** U28 with `size_up_to` 20. **Adopt on G78's rule**, against U28 (no more lost or frozen than 10).

**G105 result (run once, 2026-11-04): rejected by one day.** 89 start dates: 10 lost or frozen (as U28); window
**$47,172 / $47,230**, index **$666,770 / $655,294**, NQ **$500,348 / $498,513** (all above U28); but a −$1,033 index
day in the chart's execution (`verification/noise_v2/g105_max20.txt`).

## G106: 20 contracts with a 4-point sizing allowance (registered 2026-11-04, before its run)

**The idea:** G105 failed on one day where a stop filled past its price at full size; the sizing allowance (G76/G97)
is what removes such days. **The variant:** U28 with `size_up_to` 20 and `size_slip_pts` 4.
**Adopt on G78's rule**, against U28.

**G106 result (run once, 2026-11-04): passes; adopted.** 89 start dates: 10 lost or frozen (as U28), medians $46,477
NQ / $36,500 index; window **$46,656 / $46,828**, index **$661,701 / $648,812**, NQ $495,184 / $492,844 (all above
U28); no −$1,000 day; floor never touched (`verification/noise_v2/g106_max20_s4.txt`).

**U29 (2026-11-04): up to 20 MNQ, with a 4-point sizing allowance (G106).** In Funded growth (the 50K) on a 5-minute
chart the most contracts is now 20 (15 on other charts and in the 100K / 150K modes, as tested), and "Sizing: count this
many points more slippage at each stop" is 4. **The file you trade, NinjaTrader simulator, 5-minute window: 704
trades, $46,711.93, profit factor 1.656, closed drawdown $4,191.81, worst day −$899.31.** 30-minute unchanged
($28,620.10) (`verification/noise_v2/v38g_nt_g106_2026-11-04.txt`).

**Scorecard, G44-G106:** 63 rounds. Adopted 10 (and the data fix): G60, G67b, G79, G80, G82, G84, G97, G99c, G106 and
U28's safety change aside. Rejected: 50. Measurements: 3.

## G107: fill-ins at 3 MNQ from $9,000 above the floor (registered 2026-11-04, before its run)

**The idea:** G97's fill-ins at 2 MNQ from $6,000 passed; one more contract each $3,000 of cushion, to 3 from $9,000
(`fill_qty3_room` 9000). **The variant:** U29 with `fill_qty3_room` 9000. **Adopt on G78's rule**, against U29.

**G107 result (run once, 2026-11-04): rejected on the window.** 89 start dates: 10 lost or frozen (as U29), medians
**$56,526 NQ / $42,470 index** (U29: $46,477 / $36,500); index $695,858 / $659,294 and NQ $516,796 / $516,484 (above
U29); but the window $46,145 / $46,283 against U29's $46,656 / $46,828. The rule asks for more on the window too
(`verification/noise_v2/g107_fill3.txt`).

## G108: more opening-drive fill-ins (registered 2026-11-04, before its run)

**The idea:** the drive fill-in needs a 09:30 body of half the 14-session average; at 0.3 more cushioned days trade.
**The variant:** U29 with `gap_go_drive_k` 0.3. **Adopt on G78's rule**, against U29.

**G108 result (run once, 2026-11-04): rejected on NinjaTrader's index.** Window $48,327 / $48,390 (above U29), 75% of
the window's days traded, index $663,561 (chart, above) but **$600,246** in NinjaTrader's (U29: $648,812); 89 start
dates 10 lost or frozen, medians $47,442 / $35,758 (`verification/noise_v2/g108_drive03.txt`).

**Scorecard, G44-G108:** 65 rounds. Adopted 10 (and the data fix); rejected 52; measurements 3.

## G109: 2-MNQ fill-ins from $5,000 above the floor (registered 2026-11-04, before its run)

**The idea:** G97's fill-ins go to 2 MNQ at $6,000 above the floor; at $5,000 the second contract comes sooner.
**The variant:** U29 with `fill_qty2_room` 5000. **Adopt on G78's rule**, against U29.

**G109 result (run once, 2026-11-04): rejected; no difference.** Window $47,053 / $46,807 (U29: $46,656 / $46,828),
index $661,701 / $648,718 (U29: $661,701 / $648,812), 10 lost or frozen (`verification/noise_v2/g109_fill2_5000.txt`).

**Scorecard, G44-G109:** 66 rounds. Adopted 10 (and the data fix); rejected 53; measurements 3.

## G110: a $950 daily budget (registered 2026-11-04, before its run)

**The idea:** in a grown account the day's budget is what caps a trade's size, and so the week's profit. $950 of the
$1,000 rule (from $900), with U29's 4-point sizing allowance and the live loss guard at $950 for the gap past a stop.
**The variant:** U29 with `daily_loss_limit` 950. **Adopt on G78's rule**, against U29 (no day at −$1,000 on any set).

**G110 result (run once, 2026-11-04): rejected; a $950 budget breaks the $1,000 rule.** Index: 4 days (chart) / 3
days (NinjaTrader's) at −$1,034; 11 lost or frozen of 89; window $46,808 / $45,676. $900 stays
(`verification/noise_v2/g110_budget950.txt`).

**Scorecard, G44-G110:** 67 rounds. Adopted 10 (and the data fix); rejected 54; measurements 3.

## G111: the gap trade's stop at the middle of the 09:30 bar (registered 2026-11-04, before its run)

**The idea:** the gap trade's stop is the 09:30 open. At the middle of the 09:30 bar's body (`gap_go_stop_frac` 0.5)
each contract risks half as much, so the same budget holds twice the contracts on a gap that keeps going.
**The variant:** U29 with `gap_go_stop_frac` 0.5. **Adopt on G78's rule**, against U29.

**G111 result (run once, 2026-11-04): rejected.** Window **$17,714 / $17,881** (U29: $46,656 / $46,828), 12 lost or
frozen of 89. A stop at the middle of the 09:30 bar is inside its normal noise: the gap trades stop out before they go
(`verification/noise_v2/g111_gap_stop_mid.txt`).

**Scorecard, G44-G111:** 68 rounds. Adopted 10 (and the data fix); rejected 55; measurements 3.

## G112: the range-position filter re-checked on U29 (registered 2026-11-04, before its run)

**The idea:** the close must sit in the top (bottom) 35% of the day's range for a long (short), `range_pos_min` 0.65,
set before gap and go, the fill-ins and 20 contracts. **Variants:** U29 with 0.55 and 0.75. **Adopt (the better by
window net) on G78's rule**, against U29.

**G112 result (run once, 2026-11-04): rejected; 0.65 stays.** 0.55: window $46,046 / $46,084 (index higher, $687,554 /
$664,192); 0.75: window $46,750 / $46,077, index $578,777 / $576,408. Neither beats U29's window ($46,656 / $46,828) in
both executions (`verification/noise_v2/g112_range_pos.txt`).

## G113: the calm-stretch threshold re-checked on U29 (registered 2026-11-04, before its run)

**The idea:** no entries while the last 10 sessions' average range is under 0.7 of the last 40's (`calm_k`), set
before gap and go, the fill-ins and 20 contracts. **Variants:** U29 with 0.6 and 0.8. **Adopt (the better by window
net) on G78's rule**, against U29.

**G113 result (run once, 2026-11-04): rejected; 0.7 stays.** 0.6: window $44,978 / $43,860, index $647,297 / $548,086;
0.8: window $27,716 / $27,712. Both below U29 (`verification/noise_v2/g113_calm.txt`).

**Scorecard, G44-G113:** 70 rounds. Adopted 10 (and the data fix); rejected 57; measurements 3.

## G114: the big-day threshold re-checked on U29 (registered 2026-11-04, before its run)

**The idea:** after a day whose range is over 1.5x the 10-session average, no entries its way the next day
(`big_day_k`), set before gap and go and the rest. **Variants:** U29 with 1.3 and 1.8. **Adopt (the better by window
net) on G78's rule**, against U29.

**G114 result (run once, 2026-11-04): rejected; 1.5 stays.** 1.3: window $9,670 / $14,885; 1.8: window $41,767 /
$41,600, index $650,677 / $642,004. Both below U29 (`verification/noise_v2/g114_big_day.txt`).

**Scorecard, G44-G114:** 71 rounds. Adopted 10 (and the data fix); rejected 58; measurements 3.

## G115: a random search of nine settings together (registered 2026-11-04, before its run)

**The idea:** one setting at a time has found each at its own best; settings that work together may not be. 32
combinations drawn at random (seed 115) around U29: `lock_at` 0.28-0.45, `lock_plus` 1.5-4, `take_profit` 1.8-2.4,
`stop_buffer` 0.20-0.28, `time_stop` 50/55/60/65/70/75, `fill_min_room` 2,500-4,000, `fill_qty2_room` 5,000-8,000,
`gap_go_locked_qty` 8-12, `giveback_brake` 0.4-0.6.
**Screen (chart's execution, 5-minute):** NQ and the index at least U29's, no day at −$1,000 on any set; of those, the
highest window net is the candidate. **Then, run once:** NinjaTrader's execution and the 89 start dates, on G78's
rule against U29. Selection bias is the risk (32 tries); the two later checks are on the sets and starts the screen
didn't rank on (NinjaTrader's execution, the 89 starts).

**Result (G115, run once): rejected at the screen.** None of the 32 combinations kept NQ and the index at least U29's
with no −$1,000 day: 11 of 32 lost the account on at least one set (net near $0), 1 of 32 beat U29's window, and the
best index net ($663,057, k=12) came with a $27,644 window and a −$1,000 day. U29's settings sit at a ridge: moving
several together loses more than it gains. Log: `verification/noise_v2/g115_search.txt`.

## G116: one setting at a time, the settings not re-checked on U29 (registered 2026-11-04, before its run)

**The idea:** G89-G114 re-checked the exits and filters on U25-U29; the max loss per contract, the after-loss stop,
the contract step, the last entry, the squeeze filter, the trend length, a loser limit, the noise lookback and the
entry line were last checked on older defaults. 18 variants, one setting each: `max_loss_per_trade` 150/225/250,
`after_loss_ml_mult` 1.0/1.67, `profit_step` 1,250/1,750, `last_entry_end` 14:30/15:30, `squeeze_min` 15/25, `trend_n`
40/60, `max_losers` 3, `lookback` 10/20, `entry_k` 0.9/1.1. **Screen and confirmation:** G115's (NQ and the index at
least U29's on the chart's execution, no −$1,000 day; the best window net goes on to NinjaTrader's execution and the 89
start dates on G78's rule). Row 0 is U29 itself, as the check.

**Screen (G116):** row 0 reproduces U29 (window $46,656, NQ $495,184, index $661,701). Four rows pass: the after-loss
max loss at 1.0 (window $48,001, NQ $530,631, index $703,794), `profit_step` 1,250 (window $45,983), `trend_n` 40
(window $45,066). The highest window net is `after_loss_ml_mult` 1.0, the candidate (package `U29al1`, variant
`u29al1`). A shorter lookback, a wider entry line and an earlier last entry each lose an account on some set. Log:
`verification/noise_v2/g116_sweep.txt`.

**G116 result (run once, 2026-11-04): rejected by one account.** NinjaTrader's execution: window $48,100 (U29 $46,828),
NQ $528,725, index $684,979 (U29 $648,812), floor never touched, no −$1,000 day. 89 start dates: 11 lost or frozen
(NQ 5, index 6) against U29's 10. U29 stays. Log: `verification/noise_v2/g116_after_loss_1.txt`.

## G117: the trend over 40 sessions (registered 2026-11-04, before its run)

**The variant:** U29 with `trend_n` 40, G116's second screen pass (chart's execution: window $45,066, NQ $507,848,
index $696,307). **Adopt on G78's rule** against U29 (NinjaTrader window $46,828, index $648,812; 10 lost or frozen).

## G118: a contract per $1,250 (registered 2026-11-04, before its run)

**The variant:** U29 with `profit_step` 1,250, G116's third screen pass (window $45,983, NQ $504,922, index $669,421).
**Adopt on G78's rule** against U29.

## G119: the after-loss max loss as the others' once the floor has stopped (registered 2026-11-04, before its run)

**The idea:** G116's after-loss max loss at 1.0 raised the net on every set in both executions but lost one more of
the 89 starts. Most lost starts go before the floor stops; this keeps U29's 1.33 until then and uses 1.0 after
(`after_loss_ml_locked` 1.0, a new research setting, off by default). **Adopt on G78's rule** against U29 (both
executions on all three sets, the 89 starts at most 10 lost or frozen).

**G117 and G118 results (run once, 2026-11-04): both rejected on the window.** NinjaTrader's execution: `trend_n` 40
window $45,125, NQ $511,121, index $679,687, 10 lost or frozen (NQ 3, index 7); `profit_step` 1,250 window $45,783,
NQ $494,952, index $665,123, 10 lost or frozen (NQ 5, index 5); U29's window $46,828. Log:
`verification/noise_v2/g117_g118.txt`.

**G119 result (run once, 2026-11-04): passes; adopted (U30).** Chart / NinjaTrader's execution: window **$48,035 /
$48,108** (U29 $46,656 / $46,828), NQ $530,579 / $528,411 (U29 $495,184 / $492,844), index $697,942 / $689,202 (U29
$661,701 / $648,812); the floor never touched, no −$1,000 day on any set (worst −$986). 89 start dates: **9 lost or
frozen** (NQ 5, index 4) against U29's 10. Log: `verification/noise_v2/g119_after_loss_locked.txt`.

**U30 (2026-11-04): once the floor has stopped, the trade after a loser risks $187.50 like the others (G119).** New
setting "After a losing trade, once the floor has stopped: max loss per trade" (`AfterLossLocked`, default 187.5; 0 =
U29's $250 throughout), in the Funded growth modes and Custom on the 5-minute chart. `test_v38_after_loss_locked`
checks NinjaTrader's code against the model trade for trade with it on and off.

## G120: up to 25 or 30 contracts on U30 (registered 2026-11-04, before its run)

**The idea:** the weekly profit in the grown phase comes from the contract steps (one more per $1,500, up to 20). G105/
G106 took the cap from 15 to 20 with no lost account more. **Variants:** U30 with `size_up_to` 25 and 30. **Adopt (the
better window net of those that pass) on G78's rule** against U30 (chart / NinjaTrader window $48,035 / $48,108, NQ
$530,579 / $528,411, index $697,942 / $689,202; 9 lost or frozen of 89).

**G120 result (run once, 2026-11-04): both pass; 30 adopted (U31).**

| | window, chart / NinjaTrader | NQ, chart / NinjaTrader | index, chart / NinjaTrader | 89 starts lost or frozen | medians NQ / index |
|---|---|---|---|---|---|
| U30 (20) | $48,035 / $48,108 | $530,579 / $528,411 | $697,942 / $689,202 | 9 | $47,365 / $37,735 |
| 25 | $49,866 / $49,942 | $543,338 / $541,620 | $716,440 / $708,036 | 9 | $47,364 / $36,263 |
| **30** | **$50,246 / $50,322** | $544,740 / $543,365 | $731,161 / $721,212 | 9 | $46,920 / $35,536 |

The floor never touched, no −$1,000 day on any set (worst −$986). The closed drawdown grows with the size (index
$22,351 → $26,289; the window's stays $4,780), and the 21-month medians of the 89 starts slip a little (they aren't in
G78's rule). 30 MNQ is 3 minis' worth, inside a 50K account's usual position limit (check yours). Log:
`verification/noise_v2/g120_max25_30.txt`.

## G121: up to 40 or 50 contracts on U31 (registered 2026-11-04, before its run)

**The idea:** G120's 25 and 30 both passed with the window's drawdown unchanged. 50 MNQ is a 50K account's usual
limit (5 minis). **Variants:** U31 (30) with `size_up_to` 40 and 50. **Adopt (the better window net of those that
pass) on G78's rule** against U31 (chart / NinjaTrader window $50,246 / $50,322, NQ $544,740 / $543,365, index
$731,161 / $721,212; 9 lost or frozen of 89).

**G121 result (run once, 2026-11-04): 50 passes and is adopted (U32); 40 fails on NQ.**

| | window, chart / NinjaTrader | NQ, chart / NinjaTrader | index, chart / NinjaTrader | 89 starts lost or frozen |
|---|---|---|---|---|
| U31 (30) | $50,246 / $50,322 | $544,740 / $543,365 | $731,161 / $721,212 | 9 |
| 40 | $50,252 / $50,328 | $544,597 / **$542,802** | $759,117 / $748,724 | 9 |
| **50** | **$50,252 / $50,328** | $555,059 / $553,246 | $784,932 / $773,197 | 9 |

The floor never touched, no −$1,000 day (worst −$986). The window hardly reaches 30 contracts (+$6); the gain is on
the long histories, once an account has grown. Closed drawdown on the index $26,289 → $32,071.
Log: `verification/noise_v2/g121_max40_50.txt`.

**U31/U32 (2026-11-04): up to 50 MNQ (G120, G121).** In Funded growth (the 50K) on a 5-minute chart "Most contracts"
is 50 (U29: 20); 15 elsewhere. 50 MNQ is 5 minis' worth, the usual 50K position limit. The bot steps one contract
per $1,500 of profit, so it passes 20 only after about $28,500 and reaches 50 after about $73,500.

## G122: U32's weekly P/L by the account's profit (a measurement, 2026-11-04)

`research/g122_weekly.py`, chart's execution, 5-minute; each week grouped by the profit at its start
(`verification/noise_v2/g122_weekly.csv`):

| profit at the week's start | window: weeks / average / ≥ $3,000 | NQ 2015-25 | index 2011-26 |
|---|---|---|---|
| under $10,000 | 67 / $204 / 1.5% | 58 / $174 / 1.7% | 26 / $421 / 3.8% |
| $10,000-30,000 | 24 / $1,462 / 16.7% | 16 / $1,425 / 12.5% | 42 / $876 / 19.0% |
| $30,000-75,000 | 3 / $504 / 0% | 74 / $579 / 10.8% | 42 / $863 / 14.3% |
| over $75,000 (up to 50 MNQ) | - | 401 / $1,195 / 15.7% | 711 / $986 / 14.1% |

**What it shows:** past about $10,000 the average week stops growing with the account (about $1,000; the median near
$0, half the weeks negative), even at 50 contracts. The daily budget is the cap: every trade is sized to the $900 left
for the day, so the day's risk is fixed whatever the balance, and the profit per week is the edge per dollar of
that risk (about +0.2 of the day's budget a day). $3,000 a week needs about +0.67 a day. That's where the next rounds
look: more profit per dollar of the day's risk (trade selection and exits on the full-size trades), not more size.

## G123: U32's trades once the account is $10,000 up (a measurement, 2026-11-04)

`research/g123_grown.py`, chart's execution (`verification/noise_v2/g123_grown.txt`). Contracts: median 2, 90th
percentile 10: a trade is sized to the day's $900 at the $187.50 stop, so about 4 MNQ for the day's first trade,
whatever the cap. By entry half-hour, the 13:00 and 14:30 entries lose on both long sets (NQ −$17,326 / −$18,953,
index −$19,827 / −$16,891); the 12:00 to 14:00 entries are mixed; 13:30 and 15:00 make the most per trade. Profit
comes from the targets and the 16:00 closes; the stops (back inside, max loss, gap stop) give most of it back.

## G124: no entries at the 13:00 and 14:30 checks (registered 2026-11-04, before its run)

**The variant:** U32 with `skip_checks` "780,870" (no new entry at the checks whose bar closes 13:00 and 14:30; exits
unchanged), all phases. Chosen from G123's long sets, so the window and the 89 starts are the honest checks. **Adopt
on G78's rule** against U32 (chart / NinjaTrader window $50,252 / $50,328, NQ $555,059 / $553,246, index $784,932 /
$773,197; 9 lost or frozen of 89).

**G124 result (run once, 2026-11-04): rejected on the window.** Chart / NinjaTrader: window **$44,395 / $44,463**
(U32 $50,252 / $50,328), NQ $578,056 / $565,909 (U32 $555,059 / $553,246), index $831,781 / $822,923 (U32 $784,932 /
$773,197); the floor never touched, no −$1,000 day; 89 start dates **6 lost or frozen** (NQ 4, index 2) against 9.
It held on the long sets it was chosen from and saved accounts, but lost 12% on the window, the set it wasn't chosen
on. Log: `verification/noise_v2/g124_skip_1300_1430.txt`.

## G125: G124 only until the floor has stopped (registered 2026-11-04, before its run)

**The idea:** G124's gain in survival comes from the account's first weeks; its loss on the window may come later.
**The variant:** U32 with `skip_checks` "780,870" and `skip_checks_early` (a new research setting): no entries at
13:00 and 14:30 until the floor has stopped, as U32 after. **Adopt on G78's rule** against U32, or on G99b's
survival-first rule (fewer lost or frozen, the net at least 95% of U32's on every set in both executions).

**G125 result (run once, 2026-11-04): passes G99b's survival-first rule; adopted (U33).** Chart / NinjaTrader: window
$50,219 / $50,337 (U32 $50,252 / $50,328), NQ $546,409 / $549,379 (U32 $555,059 / $553,246: 98.4% / 99.3%), index
$784,933 / $774,086 (U32 $784,932 / $773,197); the floor never touched, no −$1,000 day; 89 start dates **8 lost or
frozen** (NQ 4, index 4) against 9. Not G78's rule (NQ's chart net is lower), but every set keeps at least 95%.
Log: `verification/noise_v2/g125_skip_early.txt`.

**U33 (2026-11-04): no entries at 13:00 and 14:30 until the floor has stopped (G125).** New setting "No entries at
these checks until the floor has stopped" (`EarlyNoEntryChecks`, default "13:00,14:30"; blank = off), in the Funded
growth modes and Custom on the 5-minute chart. `test_v38_early_no_entry_checks` checks NinjaTrader's code against the
model with it on and off. **A fix found by its tests:** the milestone alert at a day's close counted the model's equity,
which books the 16:00 close only after the check, so a level reached on the day's last trade was alerted a day late;
it now counts the strategy's fills (`test_v38_milestones`).

## G126: each trade risks part of the day's budget left (registered 2026-11-04, before its run)

**The idea:** G122/G123: the day's first trades take the whole $900 left, so one loser ends the day before the
strongest checks (10:00, 13:30, 15:00). With `budget_frac` below 1 a trade may risk only that share of what is left
today (the steps and the cap unchanged). Last tested on v2.8 (`docs/RESULTS.md`), never with the growth sizing.
**Variants:** U33 with `budget_frac` 0.6 and 0.8. **Adopt (the better window net of those that pass) on G78's rule or
G99b's** against U33.

**G126 result (run once, 2026-11-04): rejected.** NinjaTrader's execution, U33 / 0.8 / 0.6: window $50,337 / $43,691 /
$32,294, NQ $549,379 / $417,950 / $320,051, index $774,086 / $604,657 / $432,290; 89 starts lost or frozen 8 / 7 / 6.
Fewer lost accounts, but 76-87% of the net at 0.8 (below G99b's 95%). Log: `verification/noise_v2/g126_budget_frac.txt`.

## G127: no new entries once the day is well up (registered 2026-11-04, before its run)

**The idea:** keep a big day instead of giving part of it back. `day_stop_profit` (a new research setting): no new
entries once today's closed P/L is at least this (open trades run as usual). **Variants:** U33 with $1,500 and $2,500.
**Adopt (the better window net of those that pass) on G78's rule or G99b's** against U33.

**G127 result (run once, 2026-11-04): rejected.** NinjaTrader's execution, $1,500 / $2,500: window $34,993 / $32,747
(U33 $50,337), NQ $414,216 / $415,775 (U33 $549,379), index $467,520 / $535,006 (U33 $774,086); 89 starts 8 / 8 lost
or frozen. The big days are where the profit is: stopping them costs 25-40%. Log:
`verification/noise_v2/g127_day_stop.txt`.

## G128: bigger bot trades, held by a day guard (registered 2026-11-04, before its run)

**The idea:** G123: once grown, the bot's trades are sized to the day's $900 at their full stop, but its average loser
is about half of that, so the day's budget is mostly unused. Size the bot's trades to `room_mult` x the budget left
(the gap trade as now), and hold the day with a guard like the live `LossGuard`: inside a bar, once today's closed P/L
plus the trade's open P/L at the bar's worst price reaches −$900 (or the room above the trailing floor less $100), the
trade closes at that price (at the bar's open if it opened past it), less a tick, and no more entries today. The
contract steps and the 50 cap are unchanged, so it acts only once the steps exceed what the budget fits.
**Variants:** U33 with `day_guard` 900 and `room_mult` 1.5 and 2.0 (new research settings).
**Adopt (the better window net of those that pass) on G78's rule or G99b's** against U33; no day at −$1,000 or worse
is part of both.

**G128 result: invalid (an error in the test, not a verdict).** The guard was checked only on bars where the bot's
own stop didn't fill; sized up, the stop sits past the guard, so it filled first: up to 247 days at −$1,000 or worse
(worst −$4,338). A live tick-level guard fires first. Log kept: `verification/noise_v2/g128_invalid.txt`.

**G128b (registered 2026-11-04, before its run):** G128 with the guard as a stop level: on every bar, wherever the
guard's price is tighter than the bot's stop, it is the stop in force (filled at it, or at the open past it, less a
tick; "Day guard"). Variants and pass rule as G128.

**G128b result (run once, 2026-11-04): rejected by one account (both variants).**

| | window, chart / NinjaTrader | NQ, chart / NinjaTrader | index, chart / NinjaTrader | worst day | 89 starts lost or frozen |
|---|---|---|---|---|---|
| U33 | $50,219 / $50,337 | $546,409 / $549,379 | $784,933 / $774,086 | −$986 | 8 |
| 1.5x | $53,839 / $53,978 | $644,158 / $659,430 | $908,505 / $824,253 | **−$1,002** | 9 |
| 2x | $53,988 / $53,692 | $689,320 / $690,819 | $1,104,428 / $1,028,705 | −$985 | 9 |

The floor never touched. 2x passes everything but the lost accounts (NQ 4, index 5 against 4 / 4). Log:
`verification/noise_v2/g128b_room_guard.txt`.

## G129: G128b's 2x only once the floor has stopped (registered 2026-11-04, before its run)

**The idea:** the extra lost start comes before the floor stops, where the larger room lets the steps' contracts fit
sooner. **The variant:** U33 with `day_guard` 900, `room_mult` 2.0 and `room_mult_locked` (a new research setting:
the 2x only once the floor has stopped). **Adopt on G78's rule or G99b's** against U33.

**G129 result (run once, 2026-11-04): rejected; the same as G128b to the dollar** (the 2x never acts before the floor
stops: the contract steps bind there). Three starts changed against U33: NQ 2015-04 now lost (the floor had just
stopped, $2,000 of room, and 2x days took it back to the start), index 2015-07 now lost (before the floor stopped, the
guard's $100 floor buffer closed trades early and ended the day), NQ 2022-07 now kept. Log:
`verification/noise_v2/g129_room_guard_locked.txt`.

## G130: the guard once the floor has stopped, 2x only with $6,000 of room (registered 2026-11-04, before its run)

**The variant:** U33 with `day_guard` 900 and `day_guard_locked` (the guard only once the floor has stopped), and
`room_mult` 2.0 with `room_mult_room` 6000 (2x only while the account is at least $6,000 above the floor, the bot's own
2-contract fill-in threshold, not a new number). New research settings. **Adopt on G78's rule or G99b's** against U33.

**G130 result (run once, 2026-11-04): rejected on the window by $66.** Chart / NinjaTrader: window $50,152 / $50,271
(U33 $50,219 / $50,337), NQ $672,830 / $677,861 (U33 $546,409 / $549,379), index $1,104,428 / $1,028,705 (U33
$784,933 / $774,086); the floor never touched, no −$1,000 day; 89 starts 8 lost or frozen (as U33). Log:
`verification/noise_v2/g130_guard_room6000.txt`.

## G131: G130 with 2x from $3,000 of room (registered 2026-11-04, before its run)

**The variant:** G130 with `room_mult_room` 3000 (the "More trading days" cushion, the bot's other existing threshold).
**Adopt on G78's rule or G99b's** against U33.

**G131 result (run once, 2026-11-04): rejected on NinjaTrader's window by $75.** Chart / NinjaTrader: window **$50,692
/ $50,262** (U33 $50,219 / $50,337), NQ $689,320 / $690,819, index $1,104,428 / $1,028,705; the floor never touched,
no −$1,000 day; 89 starts 8 lost or frozen (as U33). On the window the 2x is neutral (+$473 / −$75); on the long sets
+26% / +33%. Log: `verification/noise_v2/g131_guard_room3000.txt`.

## G132: G131 at 3x and 4x (registered 2026-11-04, before its run)

**The idea:** with the guard holding each day at −$900 whatever the size, a bigger room only makes the winners bigger
and the guard days more frequent. **Variants:** G131 with `room_mult` 3.0 and 4.0. **Adopt (the better window net of
those that pass) on G78's rule or G99b's** against U33.

**G132 result (run once, 2026-11-04): 4x passes G78's rule; 3x fails (−$1,000 days).**

| | window, chart / NinjaTrader | NQ, chart / NinjaTrader | index, chart / NinjaTrader | worst day | 89 starts lost or frozen |
|---|---|---|---|---|---|
| U33 | $50,219 / $50,337 | $546,409 / $549,379 | $784,933 / $774,086 | −$986 | 8 |
| 3x | $54,593 / $53,617 | $857,367 / $860,118 | $1,149,209 / $1,082,025 | **−$1,193** | 8 |
| **4x** | **$54,882 / $53,906** | **$853,467 / $879,638** | **$798,835 / $795,591** | −$998 | 8 |

The floor never touched. 4x's worst day is $2 from the line, so before adoption it gets G132r. Log:
`verification/noise_v2/g132_room3_4.txt`.

## G132r: 4x with the guard's fills 2 points worse (registered 2026-11-04, before its run)

**The check:** G132's 4x with `guard_slip_pts` 2 (every "Day guard" fill 2 points worse: up to $200 on 50 MNQ, a fast
market). **Pass:** no day at −$1,000 or worse and the floor never touched on any set in both executions, 89 starts no
worse than 8. If it fails, 4x is not adopted as is.

**G132r result (run once, 2026-11-04): fails; 4x is not adopted as is.** With the guard's fills 2 points worse:
window $53,338 / $50,142 but 3 days at −$1,000 or worse, NQ 317 / 390 and the index 467 / 513 such days (worst
−$1,125). The guard at −$900 leaves no room for its own slippage at 30-50 contracts. Log:
`verification/noise_v2/g132r_guard_slip2.txt`.

## G133: the guard leaves room for its own slippage (registered 2026-11-04, before its run)

**The variant:** G132's 4x with the guard at $950 less 2 points a contract held (`guard_reserve_pts` 2, a new research
setting: at 50 MNQ it fires at −$750, at 5 MNQ at −$930), **run under the stress** (`guard_slip_pts` 2: every guard
fill 2 points worse). **Adopt on G78's rule** against U33 (no day at −$1,000 or worse, the floor never touched, more
net on every set in both executions, 89 starts no more than 8 lost or frozen), all under the stress.

**G133 result (run once, 2026-11-04): rejected.** Under the 2-point stress: window $52,906 / **$46,496** (U33 $50,219 /
$50,337), NQ $793,084 / $777,147, index $756,969 / **$704,696** (U33 $784,933 / $774,086), one index day at −$1,038;
89 starts 8. At 30-50 contracts the guard pays its slippage on hundreds of days; that takes the gain. The sized-up bot
(G128-G133) is parked: its gain depends on guard fills a fast market won't give. Log:
`verification/noise_v2/g133_guard_reserve.txt`.

## G134: U33's grown-phase trades by contracts (a measurement, 2026-11-04)

`research/g134_sizes.py` (`verification/noise_v2/g134_sizes.txt`). Index, once $10,000 up: the bot's own trades make
$11-30 a contract; the gap trades $5-15 (1,840 of them at 2 MNQ, $5 a contract). The gap slot spends the morning's
budget for the least edge.

## G135: the gap trade's trigger and size re-checked on U33 (registered 2026-11-04, before its run)

**Screen (chart's execution, 5-minute):** U33 and seven variants, one setting each: `gap_go_k` 0.6 / 0.75 / 1.0,
`gap_go_locked_qty` 5 / 15, `gap_go_drive_k` 0.7, `gap_go_small_k` 0.2. A variant passes the screen with the window,
NQ and the index at least U33's and no −$1,000 day; the best window net goes on to NinjaTrader's execution and the 89
starts, on G78's rule or G99b's against U33.

**G135 result (run once, 2026-11-04): none passes the screen.** U33: window $50,219, NQ $546,409, index $784,933.
`gap_go_locked_qty` 15: $52,220 / $576,950 / $829,700 but one index day at −$1,000; `gap_go_drive_k` 0.7: $51,126 /
**$542,578** / $794,193; the rest lower somewhere. Log: `verification/noise_v2/g135_gap_screen.txt`.

## G136: 15 gap contracts sized for a jumped stop (registered 2026-11-04, before its run)

**The idea:** G135's 15 gap contracts failed only on one −$1,000 day, a gap stop filled past its price; G86's
`gap_slip_pts` sizes the gap trade as if its stop fills that many points worse. **Variants:** U33 with
`gap_go_locked_qty` 15 + `gap_slip_pts` 2, 15 + 4, 12 + 2. G135's screen, then NinjaTrader's execution and the 89 starts
for the best, on G78's rule or G99b's against U33.

**G136 result (run once, 2026-11-04): none passes the screen.** 15 + 2 points: window $51,544, NQ $573,949, index
$818,474; 15 + 4: $47,507 / $568,953 / $809,374; 12 + 2: $51,564 / $557,561 / $797,989; each keeps the index's
−$1,251 day (2015-08-26: 13 gap contracts stopped 47 points past the entry on the fill bar, the August 2015 crash),
which a 2-4 point allowance can't size for. 10 gap contracts stays. Log: `verification/noise_v2/g136_gap15.txt`.

## G137: contracts added once the lock arms, on U33 (registered 2026-11-04, before its run)

**The idea:** the profit is in a few big trend trades (G123: targets and 16:00 closes); `add_at_lock` adds contracts at
the next bar's open once a trade's lock arms, sharing its locked stop. Tried on v2.9's 30-minute chart (rejected), not
on the 5-minute growth bot. **Variants:** U33 with `add_at_lock` 2, 4, 8. G135's screen, then NinjaTrader's execution
and the 89 starts for the best, on G78's rule or G99b's against U33.

**G137 result (run once, 2026-11-04): rejected.** `add_at_lock` 2 / 4 / 8: the window's account lost (−$1,161 /
−$1,082 / −$1,594), 19-378 days at −$1,000 on the long sets: the added contracts' stop at the lock is far from their
fill, so a reversal costs more than the day's budget. Log: `verification/noise_v2/g137_add.txt`.

**U33 checks (2026-11-04):** the full suite, 667 passed (U34: 668); the NinjaTrader growth run (`research/v38_ninjatrader_run.py
grow`, rebuilt simulator) on the window: 701 trades, **$50,096.63**, profit factor 1.712, closed drawdown $4,779.88,
worst day −$899.31, at most 32 contracts; identical to the model up to the 2026-03-09 data hole, as before
(`verification/noise_v2/v38g_nt_u33.txt`). The Go live table is updated.

## G138: settings never tried on the growth bot, one at a time on U33 (registered 2026-11-04, before its run)

**Variants:** U33 with `storm_k` 1.6 / 2.0 (no entries on a session after a very wide stretch), `touch_entry` (enter on
the touch of the line, not the check), `limit_entry_frac` 0.5 (a limit halfway back to the line), `side_cooldown` 1,
`streak_k` 3 (skip a signal after three losers in a row), `eq_n` 20 (half size below the 20-trade equity average),
`confirm` (the last check past the line too). G135's screen, then NinjaTrader's execution and the 89 starts for the
best, on G78's rule or G99b's against U33.

**G138 result (run once, 2026-11-04): none passes the screen.** U33: window $50,219, NQ $546,409, index $784,933.
`storm_k` 1.6 / 2.0: $15,732 / $15,809 on the window; `touch_entry`: every account lost; `limit_entry_frac` 0.5:
$2,739; `side_cooldown` 1: **$73,577** on the window but NQ $420,757 and index $621,503 (−23% / −21%: a window-only
gain, not adopted); `streak_k` 3: $50,556 / $547,695 / **$768,674**; `eq_n` 20: $50,434 / $383,200 / $665,178;
`confirm`: $14,038. Log: `verification/noise_v2/g138_untried.txt`.

## G139: letting the winners run, on U33 (registered 2026-11-04, before its run)

**The idea:** G123: the targets (+$3,026 a trade on the index) and the 16:00 closes (+$1,869) are the profit.
**Variants:** U33 with `take_profit` 0 (none: the line, the lock and 16:00 close every trade), 2.5, 3.0; `tp_keep` 0.5
(half the contracts run on past the target); `tp_keep` 0.5 with `runner_lock` 0.5 (the runner's stop at half the
target's distance). G135's screen, then NinjaTrader's execution and the 89 starts for the best, on G78's rule or G99b's.

**G139 result (run once, 2026-11-04): none passes the screen.** `take_profit` 0 / 2.5 / 3.0: window $42,649 / $45,846 /
$45,832 (U33 $50,219); `tp_keep` 0.5: $43,046; with `runner_lock` 0.5: $43,308; all lower on the index. The 2.0
target stays. Log: `verification/noise_v2/g139_runners.txt`.

**What loses the accounts (U33's 8 of 89, `verification/noise_v2/g35_start_dates_u32ske.csv`):** 6 of them made the
floor stop (+$2,000), most reached +$3,000, then gave it all back over months (55-328 trades) to the starting balance;
2 lost $1,100-1,650 before the floor stopped.

## G140: the trend rules on both sides, on U33 (registered 2026-11-04, before its run)

**Variants:** U33 with `trend_side` 0 (longs below the 50-session trend at 1 contract too, as shorts above it),
`trend_n` 100, both, and `giveback_brake` 0.6 (G99's brake at 60%, for the slow giveback that loses the accounts).
G135's screen, then NinjaTrader's execution and the 89 starts for the best, on G78's rule or G99b's.

**G140 screen (2026-11-04):** `trend_side` 0: window $9,684 (out); `trend_n` 100: **window $52,734, NQ $556,989,
index $801,841**, no −$1,000 day (passes); both: $10,706 (out); `giveback_brake` 0.6: window $50,182 (out, below
$50,219). The candidate is `trend_n` 100 (package `U33t100`, variant `u33t100`). Log:
`verification/noise_v2/g140_trend_screen.txt`.

**G140 result (run once, 2026-11-04): rejected by one account.** Chart / NinjaTrader: window $52,734 / $52,848 (U33
$50,219 / $50,337), NQ $556,989 / $555,468 (U33 $546,409 / $549,379), index $801,841 / $825,888 (U33 $784,933 /
$774,086); the floor never touched, no −$1,000 day; 89 starts **9 lost or frozen** (NQ 6, index 3) against 8.
Log: `verification/noise_v2/g140_trend100.txt`.

**Near misses so far (pass everything but one part of the rule):** G116 (after-loss 1.0, one account), G128b (2x with
the guard, one account), G130 / G131 (2x once the floor stops: the window by $66 / $75), G140 (trend 100, one account).
Each was registered and run once; none is adopted.

## G141: the survival count on monthly starts (registered 2026-11-04, before its run)

**The idea:** the 89 quarterly starts move by ±1 account on small changes; four near misses failed on exactly one.
Monthly starts (`START_FREQ=MS`: 103 on NQ, 160 on the index, 263 in all, the 89 among them) measure the same thing with
three times the sample. **The check:** U33 and G140's `trend_n` 100 (which passed every other part of G78's rule) on
the monthly starts. **Adopt** `trend_n` 100 only if its lost-or-frozen count on the 263 is at most U33's. This is a
second look at G140 with a larger sample of the one part it failed, stated as such; the other parts stand as run.

**G141 result (run once, 2026-11-04): `trend_n` 100 rejected.** On 263 monthly starts: U33 **32 lost or frozen** (NQ
17 of 103, index 15 of 160: 12.2%), `trend_n` 100 33 (NQ 17, index 16). Medians U33 $46,629 / $37,252, trend 100
$39,324 / $44,160. **The larger sample's survival for U33 itself: about 1 fresh account in 8 is lost or frozen within
21 months** (the quarterly 89 said 1 in 11). Logs: `verification/noise_v2/g141_monthly_starts.txt`,
`verification/noise_v2/g35_start_dates_u32ske_MS.csv`.

**U33's lost starts (G141's 263):** 17 of 32 made the floor stop and slid back to the start balance; they cluster in
bad stretches (mid-2015, late 2019 to March 2020, mid-2022, 2011, 2013), so they're regime losses, not single days.

## G142: faster contract steps once the account is well up (registered 2026-11-04, before its run)

**The idea:** G134: the big trades come on days whose early wins widen the budget, and there the steps (1 per $1,500)
cap the size. Faster steps only above $10,000 of profit (`profit_step_fast`, `profit_step_fast_from`, new research
settings) leave the thin early zone, where the accounts are lost, as it is. **Variants:** U33 (row 0, the check) and
U33 with a contract per $750 above $10,000, per $500 above $10,000, per $750 above $20,000. G135's screen, then
NinjaTrader's execution and the 89 starts for the best, on G78's rule or G99b's.

**G142 screen (2026-11-04):** row 0 = U33 exactly. Per $750 above $10,000: **window $54,879, NQ $554,388, index
$786,440** (passes); per $500: index $784,902 (out by $31); per $750 above $20,000: index $784,279 (out). The candidate
is per $750 above $10,000 (package `U33fs`, variant `u33fs`). Log: `verification/noise_v2/g142_fast_steps_screen.txt`.

**G142 result (run once, 2026-11-04): passes G78's rule; adopted (U34).** Chart / NinjaTrader: window **$54,879 /
$54,874** (U33 $50,219 / $50,337), NQ $554,388 / $557,093 (U33 $546,409 / $549,379), index $786,440 / $776,796 (U33
$784,933 / $774,086); the floor never touched, no −$1,000 day (worst −$986); 89 starts 8 lost or frozen (as U33).
Log: `verification/noise_v2/g142_fast_steps.txt`.

**U34 (2026-11-04): faster contract steps above $10,000 of profit (G142).** In the Funded growth modes and Custom on
the 5-minute chart, the contract steps are one per $1,500 up to $10,000 of profit and one per $750 above it (new
settings "Faster contract steps" `FastSteps` 750, 0 = off, and `FastStepsFrom` 10,000); the 50 cap, the day's budget
and the floor's room still cut each trade. `test_v38_fast_steps` checks NinjaTrader's code against the model with it
on and off.

## G143: the faster steps' threshold and size around U34 (registered 2026-11-04, before its run)

**Variants:** U34 (row 0) with the faster steps from $6,000 (the 2-contract fill-in threshold), and per $500 above
$15,000. G135's screen against U34, then NinjaTrader's execution and the 89 starts for the best, on G78's rule.

**G143 result (run once, 2026-11-04): neither passes the screen.** U34: window $54,879, NQ $554,388, index $786,440.
From $6,000: **$53,522** / $556,845 / $790,841; per $500 above $15,000: $58,039 / **$553,099** / **$784,191**. U34's
$750 above $10,000 stays. Log: `verification/noise_v2/g143_steps2.txt`.

## G144: U34's weekly P/L by the account's profit (a measurement, 2026-11-04)

`research/g144_weekly_u34.py` (`verification/noise_v2/g144_weekly_u34.txt`), as G122 for U32:

| profit at the week's start | window: weeks / average / ≥ $3,000 | NQ 2015-25 | index 2011-26 |
|---|---|---|---|
| under $10,000 | 67 / $202 / 1.5% | 62 / $181 / 1.6% | 28 / $770 / 7.1% |
| $10,000-30,000 | 24 / **$1,660** / 16.7% | 17 / $1,305 / 11.8% | 35 / $364 / 17.1% |
| $30,000-75,000 | 3 / $504 / 0% | 69 / $604 / 10.1% | 47 / $1,089 / 14.9% |
| over $75,000 | - | 401 / $1,195 / 15.7% | 711 / $986 / 14.1% |

Over $75,000 the weeks are U32's to the dollar: by then the day's $900 budget, not the steps, sets every trade's size.

## G145: 23 random combinations of the growth settings around U34 (registered 2026-11-04, before its run)

**Variants (seed 145):** `profit_step` 1,250 / 1,500 / 1,750, `profit_step_fast` 600 / 750 / 900,
`profit_step_fast_from` 8,000 / 10,000 / 12,000, `gap_go_locked_qty` 8 / 10 / 12, `fill_qty2_room` 5,000-7,000,
`giveback_brake` 0.4-0.6, `fill_min_room` 2,500-3,500; row 0 is U34. **Screen:** G135's against U34 (window $54,879,
NQ $554,388, index $786,440, no −$1,000 day); the best window net among those passing goes on to NinjaTrader's
execution and the 89 starts, on G78's rule against U34. Selection over 23 tries is the risk; the confirmation sets
are the check.

**G145 screen (2026-11-04):** 1 of 23 passes: k9 (`profit_step` 1,250, `profit_step_fast` 600 from $10,000,
`giveback_brake` 0.4; the rest as U34): window $56,299, NQ $562,184, index $797,376. The four best windows ($58,611-
59,417, all with 12 gap contracts) each have one index day at −$1,000. Candidate: k9 (package `U34k9`, variant `u34k9`).
Log: `verification/noise_v2/g145_search.txt`.

**G145 result (run once, 2026-11-04): k9 rejected on the lost accounts.** Chart / NinjaTrader: window $56,299 /
$56,439 (U34 $54,879 / $54,874), NQ $562,184 / $560,169 (U34 $554,388 / $557,093), index $797,376 / $785,194 (U34
$786,440 / $776,796); no −$1,000 day; 89 starts **10 lost or frozen** (NQ 5, index 5) against 8: the $1,250 step adds
contracts in the thin early zone. Log: `verification/noise_v2/g145_k9.txt`.

## G146: k9 without the faster early step (registered 2026-11-04, before its run)

**The variant:** U34 with `profit_step_fast` 600 (above $10,000) and `giveback_brake` 0.4, the $1,500 step kept (the
parts of k9 that leave the early zone as it is). **Adopt on G78's rule** against U34 (89 starts at most 8).

**G146 result (run once, 2026-11-04): rejected.** Chart / NinjaTrader: window $57,170 / $57,330, NQ $560,431 /
$558,030, index $786,214 / **$773,831** (U34 $786,440 / $776,796); 89 starts **9** (NQ 5, index 4) against 8. Log:
`verification/noise_v2/g146.txt`.

## G147: 23 random combinations of the exit settings around U34 (registered 2026-11-04, before its run)

**Variants (seed 147):** `lock_at` 0.30-0.40, `lock_plus` 2-3 points, `take_profit` 1.9-2.15, `stop_buffer`
0.22-0.26, `time_stop` 55 / 60 / 65, `max_loss_per_trade` $162.50-200 (narrower than G115's, around today's values;
U30-U34 moved the bot since). Row 0 is U34. G135's screen against U34, then the best window among those passing on to
NinjaTrader's execution and the 89 starts, on G78's rule.

**G147 result (run once, 2026-11-04): none of the 23 passes the screen.** The best windows ($57,248, $56,097) each
come with an index day at −$1,000 and an index net $40,000-50,000 below U34's. U34's exits are still the ridge.
Log: `verification/noise_v2/g147_search.txt`.

**Scorecard, G115-G147 (this session's continuous run):** 33 rounds and checks (some with several variants).
Adopted: G119 (U30), G120 + G121 (U31/U32, up to 50 MNQ), G125 (U33), G142 (U34). Measurements: G122, G123, G134,
G144, the lost-account anatomy, G141's monthly starts. The rest rejected, most on one part of the rule (one account,
or the window by under $100).

## G148: G131's 2x with the day guard on U34, under the guard's slippage (registered 2026-11-04, before its run)

**The variant:** U34 with `day_guard` 900 (once the floor has stopped), `room_mult` 2.0 from $3,000 of room, run with
`guard_slip_pts` 2 (every guard fill 2 points worse). U34's faster steps let the 2x bind more often than on U33.
**Adopt on G78's rule** against U34 (unstressed), all of it under the stress.

**G148 result (run once, 2026-11-04): rejected on the −$1,000 days.** Under the stress, chart / NinjaTrader: window
**$69,795 / $69,069** (U34 $54,879 / $54,874), NQ $673,938 / $658,931, index $1,066,380 / $917,547; 89 starts 8; but
the window has one day at −$1,013 and the long sets 95-175 days past −$1,000 (worst −$1,125): the guard at −$900
leaves no room for its own slippage. Log: `verification/noise_v2/g148_room2_guard_stress.txt`.

## G149: G148 with the guard leaving room for its slippage (registered 2026-11-04, before its run)

**The variant:** G148 with `day_guard` 950 and `guard_reserve_pts` 2 (G133's size-aware guard: −$950 less 2 points a
contract held), under the same stress. **Adopt on G78's rule** against U34, all of it under the stress.

**G149 result (run once, 2026-11-04): rejected; the sized-up bot is parked for good.** Under the stress, chart /
NinjaTrader: window $63,249 / **$16,555**, NQ $679,368 / $664,638, index $1,064,621 / $923,254, one day past −$1,000
on NQ and the index (worst −$1,051). The window's two executions part by $46,000 on a few early fills: the 2x-with-guard
family (G128-G133, G148-G149) depends on fills too much to trust. Log: `verification/noise_v2/g149.txt`.

**U34 checks (2026-11-04):** the full suite, 668 passed; the NinjaTrader growth run on the window, $54,772.31, profit
factor 1.768, worst day −$899.31, up to 50 contracts, identical to the model up to the 2026-03-09 data hole
(`verification/noise_v2/v38g_nt_u34.txt`).

## G150: six single settings on U34 (registered 2026-11-04, before its run)

**Variants:** U34 (row 0) with `gap_go_exit` 09:50 / 10:00, `lookback` 12 / 16 sessions, `size_slip_pts` 3 / 5. G135's
screen against U34, then the best window among those passing on to NinjaTrader's execution and the 89 starts, on
G78's rule.

**G150 result (run once, 2026-11-04): none passes the screen.** Gap exit 09:50 / 10:00: window $46,002 / $38,434;
lookback 12: NQ's account lost; lookback 16: index $660,553; sizing allowance 3 points: an index day at −$1,000; 5
points: lower on every set. Log: `verification/noise_v2/g150_singles.txt`.

## G151: six rarely used settings on U34 (registered 2026-11-04, before its run)

**Variants:** U34 (row 0) with `tom_no_shorts` (no shorts at the turn of the month), `tom_mult` 1.5 (1.5x there),
`late_lock_from` 15:00 (a trade in profit at 15:00 locks), `time_lock` 30 (in profit after 30 minutes, locks),
`after_loss_same_side` (the after-loss rules only on the losing side), `big_day_against_tp` 1.0. G135's screen against
U34, then confirmation for the best, on G78's rule.

**G151 result (run once, 2026-11-04): none passes the screen.** Window (U34 $54,879): `tom_no_shorts` $53,736,
`tom_mult` 1.5 $54,850, `late_lock_from` 15:00 $54,566, `time_lock` 30 $54,832, `after_loss_same_side` $54,710,
`big_day_against_tp` 1.0 $11,781. Log: `verification/noise_v2/g151_rare.txt`.

## U34 from a fresh account (a measurement on 263 monthly starts, 2026-11-04)

`START_FREQ=MS research/g35_start_dates.py ... u33fs` (`verification/noise_v2/g35_start_dates_u33fs_MS.csv`): 21 months
from each month's first day, NinjaTrader's execution. **32 of 263 lost or frozen (12.2%, as U33)**; median 21-month
net **$39,454** (about $430 a week); +$3,000 within 7 days in none, within 30 days in 3.8%, median 138 days; +$50,000
within 21 months in 45.6% (median 16.8 months).

## G152: early-phase protections on U34, judged on 263 starts (registered 2026-11-04, before its run)

**Variants:** U34 with `steps_after_lock` (no contract steps until the floor has stopped), `trail_frac` 0.5 (size to
half the room above the floor), `trail_buffer` 500 (keep $500 of the room unused). **Adopt (the fewest lost) on G99b's
survival-first rule:** fewer lost or frozen than U34's 32 of the 263 monthly starts, and the net at least 95% of U34's
on the window, NQ and the index in both executions, no −$1,000 day, the floor never touched.

**G152 result (run once, 2026-11-04): all rejected.** On the 263 monthly starts (U34 32 lost or frozen):
`steps_after_lock` 36, `trail_frac` 0.5 34 (its full-set nets are U34's to the dollar), `trail_buffer` 500 88 (it
freezes: the window's account made −$802 on 61 trades). Log: `verification/noise_v2/g152_early_protection.txt`.

## G153: a smaller day budget until the floor has stopped (registered 2026-11-04, before its run)

**The idea:** 15 of U34's 32 lost starts go before the floor stops, in a few −$900 days of a volatile stretch.
`early_daily_loss` (a new research setting): the day's budget until the floor has stopped. **Variants:** U34 with $500
and $650. **Adopt (the fewest lost) on G99b's survival-first rule** on the 263 monthly starts, as G152.

**G153 result (run once, 2026-11-04): rejected.** 263 monthly starts: $500 36 lost or frozen, $650 33 (U34 32); the
full sets within $200 of U34. Early on the floor's room, not the day's budget, sets the size; a smaller day budget only
slows the recovery. Log: `verification/noise_v2/g153_early_budget.txt`.

## G154: a tighter max loss a contract until the floor has stopped (registered 2026-11-04, before its run)

**Variants:** U34 with `early_ml` 150 and 125 (the max loss per contract until the floor has stopped; $187.50 after).
**Adopt (the fewest lost) on G99b's survival-first rule** on the 263 monthly starts, as G152.

**G154 result (run once, 2026-11-04): rejected.** 263 monthly starts: `early_ml` 150 43 lost or frozen, 125 55 (U34
32): the tighter stops get hit more often. Log: `verification/noise_v2/g154_early_ml.txt`.

## G155: U34 with one part off, judged on 263 starts (registered 2026-11-04, before its run)

**The idea:** each part of U34 was adopted on the 89 quarterly starts; on the 263 monthly ones one may cost more
accounts than it earns. **Variants:** U34 without the fill-ins ("More trading days" off), without the opening-drive
fill-in, without the giveback brake, without U30's after-loss rule. **Adopt (the fewest lost) on G99b's survival-first
rule** on the 263 monthly starts (fewer than U34's 32, the net at least 95% of U34's on every set in both executions,
no −$1,000 day).

**G155 result (run once, 2026-11-04): every part of U34 stays.** 263 monthly starts (U34 32 lost or frozen) and the
NinjaTrader nets (U34 window $54,874, NQ $557,093, index $776,796): fill-ins off 33, $48,992 / $415,122 / $635,693;
the drive fill-in off 33, $52,727 / $438,101 / $652,587; the brake off **35** (the brake saves accounts), $54,874 /
$559,815 / $770,865; U30's after-loss rule off **30**, $52,850 / **$507,188** / $721,962 (NQ 91%, below G99b's 95%).
Log: `verification/noise_v2/g155_ablations.txt`.

## G156: U29, U33 and U34 at 2 ticks of slippage (a robustness measurement, 2026-11-04)

`research/g156_slip2.py`, the chart's execution with every market fill 2 ticks worse instead of 1
(`verification/noise_v2/g156_slip2.txt`):

| 2 ticks | window | NQ | index | days at −$1,000 |
|---|---|---|---|---|
| U29 (before this session's U30-U34) | **$13,660** | $453,799 | $632,936 | 0 |
| U33 | $47,194 | $505,409 | $740,858 | 0 |
| **U34** | **$52,137** | $509,357 | $742,460 | 0 |

U29's window account nearly stalls at 2 ticks; U34 keeps 95% of its 1-tick window net. The session's changes made the
bot both more profitable and less fragile to fills.

## G157: a bigger gap for the main gap trade once the floor has stopped (registered 2026-11-04, before its run)

**The idea:** G134: once grown, the gap trades make $5-15 a contract at up to 10 contracts and spend the morning's
budget. `gap_go_k_locked` (a new research setting): once the floor has stopped, the main gap trade needs a gap of this
x the average (0.5 before; the 1-contract small-gap and drive fill-ins unchanged). **Variants:** U34 with 0.75 and 1.0.
G135's screen against U34, then confirmation for the best on G78's rule.

**G157 result (run once, 2026-11-04): rejected.** 0.75: window $55,056, NQ $555,742, index **$765,364**; 1.0: $51,837
/ $514,745 / $730,559 (U34 $54,879 / $554,388 / $786,440). The gap trades earn their place. Log:
`verification/noise_v2/g157_gapk.txt`.

## G158: U34 at higher costs (a measurement, 2026-11-04)

`research/g158_costs.py` (`verification/noise_v2/g158_costs.txt`), the chart's execution:

| U34 at | window | NQ | index | days at −$1,000 |
|---|---|---|---|---|
| 1 tick, $0.62 a side (as tested) | $54,879 | $554,388 | $786,440 | 0 |
| 2 ticks (G156) | $52,137 | $509,357 | $742,460 | 0 |
| **3 ticks** | **$12,987** | **lost** | $705,594 | 0 |
| $1.00 a side | $52,351 | $541,544 | $754,302 | 1 (index) |
| 2 ticks and $1.00 a side | $12,295 | $496,327 | $695,864 | 0 |

**Live, the fills decide it:** at 1-2 ticks a fill the bot holds; at 3 ticks on every fill a fresh account can stall or
be lost. The journal's "entry slip ticks" / "exit slip ticks" columns (U7) show the real fills: if they average 3 or
more, stop and check the connection, the data feed and the order type.

## G159: a different target for late entries, on U34 (registered 2026-11-04, before its run)

**The idea:** G123: the 13:30 and 15:00 entries make the most per trade; a 15:00 entry has an hour to reach a target
set for a whole afternoon. **Variants:** U34 with `late_tp` 1.0 and 1.5 noise units for entries from the 15:00 check,
and 2.5 from the 13:30 check. G135's screen against U34, then confirmation for the best on G78's rule.

**G159 result (run once, 2026-11-04): none passes the screen.** From 15:00 at 1.0: $54,687 / $504,280 / $734,852;
at 1.5: $54,904 / **$519,757** / $780,321; from 13:30 at 2.5: $54,883 / $564,979 / **$766,103** (U34 $54,879 /
$554,388 / $786,440). Log: `verification/noise_v2/g159_late_tp.txt`.

## G160: U29 against U34 year by year (a measurement, 2026-11-04)

`research/g160_by_year.py` (`verification/noise_v2/g160_by_year.txt`), the chart's execution, net by exit year from one
continuous account. U34 is ahead on the index in 11 of 16 years, on NQ in 5 of 11; the gain is concentrated in the
trend years (2020: +$15,360 NQ / +$38,954 index; 2023: +$21,497 / +$11,190; 2025: +$39,391 / +$40,861) and gives some
back elsewhere (NQ 2018 −$18,377, index 2014 −$16,889). The faster steps and 50 contracts pay most when a big year
comes after the account has grown.

**The full suite after the live fill alert and the dashboard line: 668 passed.**

## G161: other early no-entry checks, on U34 (registered 2026-11-04, before its run)

**Variants:** U34 with the early no-entry checks (until the floor stops) at 13:00 only, 14:30 only, and 12:30 + 13:00
+ 14:30 (U34: 13:00 + 14:30). G135's screen against U34; the best window among those passing then on the 263
monthly starts and NinjaTrader's execution, on G78's rule (no more than U34's 32 lost or frozen).

**G161 screen (2026-11-04):** 13:00 only: $54,883 / $561,774 / $786,495 (passes); **14:30 only: $54,885 / $561,826 /
$786,498** (passes, the best window by $2); 12:30 + 13:00 + 14:30: index $782,753 (out). Candidate: 14:30 only
(package `U34sk870`, variant `u34sk870`). Log: `verification/noise_v2/g161_early_checks_screen.txt`.

**G161 result (run once, 2026-11-04): rejected on its registered rule.** NinjaTrader's execution: window $54,880
(U34 $54,874), NQ $559,733 ($557,093), index **$776,179** ($776,796, −$617); 263 monthly starts **31** lost or frozen
(U34 32). It fails G78's rule (registered) on the index by 0.08%; it would have passed G99b's survival-first rule,
which wasn't the one registered, so it is not adopted. Log: `verification/noise_v2/g161_sk870.txt`.

## G162: the commission saving of NQ minis, an upper bound (a measurement, 2026-11-04)

Every contract at $0.30 a side instead of $0.62 (as if every 10 MNQ went as 1 NQ at about $2 a side; in fact only
10-lots convert): window $58,310 (+$3,431), NQ $581,502, index $815,160 (`verification/noise_v2/g162_comm.txt`). The
real saving would be about half of that; routing two instruments in the live strategy isn't worth the risk for it.

## G163: four more single settings on U34 (registered 2026-11-04, before its run)

**Variants:** U34 with `max_losers` 2 (no entries after two losers in a day), `after_loss_qty_div` 2 (half the
contracts after a loser), `fed_no_shorts` off, `lock_intrabar` (the lock armed inside the bar). G135's screen against
U34, then confirmation for the best on G78's rule.

**G163 result (run once, 2026-11-04): none passes the screen.** `max_losers` 2: $51,450 / $539,789 / $795,882;
`after_loss_qty_div` 2: U34 to the dollar (the after-loss sizing already sets it); `fed_no_shorts` off: $53,837;
`lock_intrabar`: $53,200 / $543,061 / $831,279 (U34 $54,879 / $554,388 / $786,440). Log:
`verification/noise_v2/g163_singles2.txt`.

## G164: 20 random combinations of the survival settings, on 263 starts (registered 2026-11-04, before its run)

**Variants (seed 164), around U34:** `giveback_brake` 0.4-0.7, `fill_min_room` $2,000-4,000, `gap_go_locked_qty`
6-12, `after_loss_ml_mult` 1.2 / 1.33 / 1.5, the early no-entry checks (13:00 + 14:30, 14:30, 13:00, 12:30 + 13:00 +
14:30, 13:00 + 14:00 + 14:30). **Screen:** lost or frozen on the 263 monthly starts. **Then:** the fewest (ties: the
higher median) on the window, NQ and the index in both executions; **adopt on G99b's survival-first rule** against
U34 (fewer than 32 lost, every net at least 95% of U34's, no −$1,000 day, the floor never touched).

**G164 screen (2026-11-04), lost or frozen of 263 (U34 32):** k6 **25** (brake 0.5, cushion $3,500, 6 gap contracts,
after-loss 1.2, 13:00 + 14:30; medians $32,325 / $43,390), k11 25 (medians $14,968 / $26,635), k18 26, k14 26, k7 26;
the after-loss max loss at 1.2x (U34 1.33x) is in all five. By the registered rule k6 (fewest, then the higher median)
goes on to the full sets (package `U34g164k6`). Log: `verification/noise_v2/g164_survival_search.txt`.

**G164 result (run once, 2026-11-04): k6 rejected.** Chart / NinjaTrader: window $47,642 / $47,646 (87% of U34's),
NQ $515,398 / $513,935, index $714,263 / $701,413: below G99b's 95%. Log: `verification/noise_v2/g164_k6.txt`.

## G165: the after-loss max loss at 1.2x on U34 (registered 2026-11-04, before its run)

**The idea, from G164 (stated as a search result, not a fresh test of survival):** the after-loss max loss at 1.2x
(U34: 250/187.5 = 1.33x, i.e. $225 instead of $250 before the floor stops) is in all five of G164's best; G164's k14 is
U34 with only that change: 26 lost or frozen of 263 (U34 32), medians $37,057 / $50,259 (U34 $36,963 / $41,914).
**The check not yet seen:** the window, NQ and the index in both executions, and the 89 quarterly starts. **Adopt on
G99b's survival-first rule** (fewer lost on the 263, the net at least 95% of U34's on every set in both executions, no
−$1,000 day, the floor never touched).

**G165 result (run once, 2026-11-04): passes G99b's survival-first rule; adopted (U35).** Chart / NinjaTrader: window
**$54,906 / $55,707** (U34 $54,879 / $54,874), NQ $554,446 / $557,104 (U34 $554,388 / $557,093), index $786,440 /
$776,796 (as U34); the floor never touched, no −$1,000 day; 263 monthly starts **26 lost or frozen** (U34 32; NQ 13,
index 13), medians $50,259 / $37,057; 89 quarterly starts 8 (as U34). The survival number comes from the search that
suggested it (G164); the full sets are the check it hadn't seen. Log: `verification/noise_v2/g165_after_loss_12.txt`.

**U35 (2026-11-04): the trade after a loser risks $225, not $250, until the floor has stopped (G165).** In Funded growth
on the 5-minute chart "After a losing trade: max loss per trade" is $225 (1.2x; $250 on other charts); after the floor
stops U30's $187.50 applies. `test_v38_after_loss_225` checks NinjaTrader's code against the model at $225 and $250.

## G166: 20 random combinations of the survival settings around U35 (registered 2026-11-04, before its run)

**Variants (seed 166), around U35:** `after_loss_ml_mult` 1.0 / 1.1 / 1.2 / 1.25, `giveback_brake` 0.45-0.6,
`fill_min_room` $2,500-3,500, `max_loss_per_trade` $175 / $187.50 / $200, the early no-entry checks (13:00 + 14:30,
14:30, 13:00 + 14:00 + 14:30). As G164: the fewest lost or frozen on the 263 starts (ties: the higher median) goes on to
the full sets in both executions; **adopt on G99b's survival-first rule** against U35 (fewer than 26).

**G166 screen (2026-11-04), lost or frozen of 263 (U35 26):** k0 **21** (after-loss 1.1x, brake 0.6, cushion $3,000,
max loss $175, the early check at 14:30 only; medians $38,603 / $45,192), k15 21 (medians $28,629 / $40,382), k1 22,
k13 23. By the registered rule k0 goes on to the full sets. Log: `verification/noise_v2/g166_survival_search.txt`.

**G166 result (run once, 2026-11-04): k0 rejected.** Chart / NinjaTrader: window $47,800 / $47,923 (86% of U35's
$55,707), NQ $485,025 / $488,354, index $798,713 / $713,983. Log: `verification/noise_v2/g166_k0.txt`.

## G167: the after-loss max loss at 1.1x on U35 (registered 2026-11-04, before its run)

**The idea, from G166:** both of G166's best (21 lost) have `after_loss_ml_mult` 1.1 ($206); it isn't yet run alone.
**The variant:** U35 with `after_loss_ml_mult5` 1.1. **Run once:** the 263 monthly starts and the full sets in both
executions. **Adopt on G99b's survival-first rule** against U35 (fewer than 26 lost, every net at least 95%).

**G167 result (run once, 2026-11-04): passes G99b's survival-first rule by one account; adopted (U36).** Chart /
NinjaTrader: window $54,876 / $54,872 (U35 $54,906 / $55,707: 98.5%), NQ $561,717 / $557,051, index $786,440 /
$776,796 (as U35); no −$1,000 day, the floor never touched; 263 monthly starts **25 lost or frozen** (NQ 14, index 11)
against U35's 26, medians $49,426 / $37,626. A small gain, at the edge of the rule. Log:
`verification/noise_v2/g167_after_loss_11.txt`.

**U36 (2026-11-04): the after-loss max loss at $206.25 (1.1x) on the 5-minute chart (G167; U35: $225).**
`test_v38_after_loss_206` checks NinjaTrader's code against the model at $206.25 and $250.

## G168: the after-loss max loss at 1.0x on U36 (registered 2026-11-04, before its run)

**The idea:** G165 (1.2x) and G167 (1.1x) each saved accounts; 1.0x ($187.50, as every other trade) ends the line.
(On U29, G116's 1.0x lost one more of the 89.) **The variant:** U36 with `after_loss_ml_mult5` 1.0. **Run once:** the
263 monthly starts and the full sets in both executions. **Adopt on G99b's survival-first rule** against U36 (fewer
than 25 lost, every net at least 95%).

**G168 result (run once, 2026-11-04): passes G99b's survival-first rule; adopted (U37).** Chart / NinjaTrader: window
$54,710 / $54,865 (U36 $54,876 / $54,872), NQ $561,951 / $559,921 (U36 $561,717 / $557,051), index $786,440 / $776,796
(as U36); no −$1,000 day, the floor never touched; 263 monthly starts **20 lost or frozen** (NQ 11, index 9) against
U36's 25, medians $49,924 / $37,124; 89 quarterly starts 7 (U34-U36 8). Log: `verification/noise_v2/g168_after_loss_10.txt`.

**U37 (2026-11-04): on the 5-minute chart the trade after a loser risks $187.50 like every trade (G168).** "After a
losing trade: max loss per trade" is $187.50 in Funded growth on the 5-minute chart ($250 on others); U30's setting
(after the floor stops) is now the same value there. `test_v38_after_loss_same` checks NinjaTrader's code against the
model at $187.50 and $250; `test_v38_after_loss_locked` keeps testing U30's switch at $250.

**The after-loss line on the 263 starts:** 1.33x (U34) 32 lost, 1.2x (U35) 26, 1.1x (U36) 25, 1.0x (U37) 20, with the
nets unchanged within 1%. The wider stop after a loss was costing accounts.

## G169: 20 random combinations of the survival settings around U37 (registered 2026-11-04, before its run)

**Variants (seed 169), around U37:** `profit_step` $1,500 / 1,750 / 2,000 (slower early steps), `size_slip_pts` 3-6,
`giveback_brake` 0.45-0.55, `fill_min_room` $2,500-3,500, the early no-entry checks (13:00 + 14:30, 14:30, 13:00).
As G164: the fewest lost or frozen on the 263 starts (ties: the higher median) to the full sets in both executions;
**adopt on G99b's survival-first rule** against U37 (fewer than 20, every net at least 95%).

**G169 screen (2026-11-04), lost or frozen of 263 (U37 20):** k3 **16** (sizing allowance 6 points, brake 0.55,
cushion $2,500; medians $29,536 / $46,371), then four at 19. k3 goes on to the full sets. Log:
`verification/noise_v2/g169_survival_search.txt`.

**G169 result (run once, 2026-11-04): k3 rejected.** Chart / NinjaTrader: window $52,629 / $52,802 (96%), NQ $556,997
/ $555,092 (99%), index $777,906 / **$701,174** (90% of U37's $776,796). Log: `verification/noise_v2/g169_k3.txt`.

## G170: a larger sizing allowance alone on U37 (registered 2026-11-04, before its run)

**The idea, from G169:** the three best there have a 5-6 point sizing allowance (U37: 4): sizing each trade for a
stop that fills that much worse gives fewer contracts when the stop is near. **Variants:** U37 with `size_slip_pts` 5
and 6. **Run once:** the 263 monthly starts and the full sets in both executions. **Adopt (the fewest lost) on G99b's
survival-first rule** against U37 (fewer than 20, every net at least 95%).

**G170 result (run once, 2026-11-04): 5 points passes G99b's survival-first rule; adopted (U38).** 263 monthly starts:
5 points **19 lost or frozen** (NQ 10, index 9), 6 points 19, U37 20. Chart / NinjaTrader at 5: window $54,339 /
$54,417 (U37 $54,710 / $54,865: 99%), NQ $560,911 / $558,360, index $783,163 / $774,859 (99.6% / 99.8%); medians
$50,739 / $40,040 (U37 $49,924 / $37,124); no −$1,000 day, the floor never touched. 6 points: the same 19, lower nets.
Log: `verification/noise_v2/g170_size_slip.txt`.

**U38 (2026-11-04): the sizing counts a stop 5 points worse (G170; U29-U37: 4).** The "sizing allowance" setting
(`SizeSlip`) defaults to 5, on the 5-minute chart.

## G171: 20 random combinations of the exit settings around U38, on 263 starts (registered 2026-11-04, before its run)

**Variants (seed 171), around U38:** `lock_at` 0.30-0.38, `lock_plus` 2 / 2.5 / 3 points, `stop_buffer` 0.22-0.26,
`time_stop` 50 / 60 / 70. As G164: the fewest lost or frozen on the 263 starts (ties: the higher median) to the full
sets in both executions; **adopt on G99b's survival-first rule** against U38 (fewer than 19, every net at least 95%).

**G171 result (run once, 2026-11-04): none passes.** The best of the 20 lost 21 of 263 (U38 19); U38's exits stay.
Log: `verification/noise_v2/g171_survival_search.txt`.

**Scorecard, G148-G171:** adopted G165 (U35), G167 (U36), G168 (U37), G170 (U38), all on the survival-first rule:
fresh-account losses on 263 starts 32 → 26 → 25 → 20 → 19 with the nets within 1-2%. Rejected the rest; measurements
G156, G158, G160, G162.

## G172: no gap trades until the floor has stopped (registered 2026-11-04, before its run)

**The idea:** before the floor stops, a fresh account trades the bot's own signals and a 1-contract gap trade; 9-12
of U38's 19 lost starts go in that phase. `gap_go_after_lock` (an existing research setting): the gap trade only once
the floor has stopped. **The variant:** U38 with it. **Run once:** the 263 monthly starts and the full sets in both
executions. **Adopt on G99b's survival-first rule** against U38 (fewer than 19, every net at least 95%).

**G172 result (run once, 2026-11-04): rejected.** 263 monthly starts: **27 lost or frozen** (U38 19); nets within 1%.
The 1-contract gap trade helps a fresh account build the cushion that stops the floor. Log:
`verification/noise_v2/g172_gap_after_lock.txt`.

## G173: the early gap trade at up to 2 contracts (registered 2026-11-04, before its run)

**The idea, from G172:** the 1-contract gap trade before the floor stops saves accounts (27 lost without it, 19 with).
**The variant:** U38 with `gap_go_max_qty` 2 (up to 2 contracts before the floor stops, as the room allows; 10 after,
unchanged). **Run once:** the 263 monthly starts and the full sets in both executions. **Adopt on G99b's survival-first
rule** against U38 (fewer than 19, every net at least 95%).

**G173 result (run once, 2026-11-04): rejected.** 263 monthly starts: 20 lost or frozen (U38 19); nets within 1%.
One early gap contract stays. Log: `verification/noise_v2/g173_gap_qty2.txt`.

## G174: the giveback brake at 0.55 and 0.6 on U38 (registered 2026-11-04, before its run)

**The idea:** G155: the brake saves accounts (35 lost without it, 32 with, on U34); G169's best combinations had 0.55.
**Variants:** U38 with `giveback_brake` 0.55 and 0.6. **Run once:** the 263 monthly starts and the full sets in both
executions. **Adopt (the fewest lost) on G99b's survival-first rule** against U38 (fewer than 19, every net ≥ 95%).

**G174 result (run once, 2026-11-04): both rejected on NinjaTrader's index.** 0.55: 18 lost or frozen of 263, nets
99-100% except the index in NinjaTrader's execution, **$704,967** (91% of U38's $774,859); 0.6: 17 lost, the index
**$637,763** (82%). Log: `verification/noise_v2/g174_brake.txt`.

**U38 checks (2026-11-04):** the full suite, **669 passed**; the NinjaTrader growth run on the window $54,336.02
(`verification/noise_v2/v38g_nt_u38.txt`), identical to the model up to the 2026-03-09 data hole.

**G172-G174 and the lost starts (U38's 19 of 263):** 11 go before the floor stops, in the same bad stretches (mid-2015,
late 2019 to March 2020, mid-2011, mid-2013, September 2023): a fresh account started into a losing regime. The early
1-contract gap trade helps (G172), 2 contracts don't (G173), stronger brakes save one or two more but cost the index
in NinjaTrader's execution (G174).

## G175: the shadow gate through the whole early phase (registered 2026-11-04, before its run)

**The idea:** U38's early losses come from starting into a losing stretch. G87's shadow gate (a 1-contract paper
record of the bot; on a day its end-of-day equity is below its 20-session average, no new trade while the account is
within `protect_room` of its floor) was tested near the floor ($1,000-1,500). Here `protect_room` 2,100: the gate
covers the whole phase before the floor stops (the room is at most $2,000 there) and turns off once the account is
$2,100 above its floor. **The variant:** U38 with it. **Run once:** the 263 monthly starts and the full sets in both
executions. **Adopt on G99b's survival-first rule** against U38 (fewer than 19, every net at least 95%).

**G175 result (run once, 2026-11-04): rejected.** 263 monthly starts: 24 lost or frozen (U38 19), medians $29,145 /
**$9,185**; NinjaTrader NQ $485,775 (87%). Sitting out the early losing stretches also sits out their recoveries.
Log: `verification/noise_v2/g175_shadow_early.txt`.

## G176: the trend over 100 sessions on U38 (registered 2026-11-04, before its run)

**The idea:** G140/G141: on U33, `trend_n` 100 raised every net (window +5%, index +7%) and lost one account more (33
against 32 of 263). U35-U38 changed the early phase since. **The variant:** U38 with `trend_n` 100. **Run once:** the 263
monthly starts and the full sets in both executions. **Adopt on G78's rule** against U38 (more net on every set in both
executions, no more than 19 lost, no −$1,000 day, the floor never touched).

**G176 result (run once, 2026-11-04): rejected.** Chart / NinjaTrader: window $56,654 / $57,378 (U38 $54,339 /
$54,417), NQ **$554,231 / $551,907** (U38 $560,911 / $558,360), index $798,034 / $825,904 (U38 $783,163 / $774,859);
263 starts **20** lost (U38 19). Log: `verification/noise_v2/g176_trend100_u38.txt`.

## G177: 23 random combinations of the growth-phase sizing around U38 (registered 2026-11-04, before its run)

**Variants (seed 177):** `profit_step_fast` 600-850, `profit_step_fast_from` $8,000-15,000, `fill_qty2_room`
$5,000-7,000, `gap_go_locked_qty` 9-11, `gap_go_drive_k` 0.4-0.6; row 0 is U38. **Screen:** G135's against U38 (the
chart's nets at least U38's on all three sets, no −$1,000 day); the best window among those passing then goes on to
NinjaTrader's execution and the 263 monthly starts, **adopted on G78's rule** (no more than 19 lost).

**G177 screen (2026-11-04):** 2 of 23 pass. k11 (`profit_step_fast` 600 from $15,000, `fill_qty2_room` 5,000,
`gap_go_drive_k` 0.6): window **$57,714**, NQ $564,991, index $786,675 (U38 $54,339 / $560,911 / $783,163); k8: $54,860
/ $563,204 / $788,266. k11 goes on to NinjaTrader's execution and the 263 starts. Log:
`verification/noise_v2/g177_search.txt`.

**G177 result (run once, 2026-11-04): k11 rejected by one account.** Chart / NinjaTrader: window $57,714 / **$56,949**
(U38 $54,339 / $54,417), NQ $564,991 / $562,638 (U38 $560,911 / $558,360), index $786,675 / $779,569 (U38 $783,163 /
$774,859); no −$1,000 day, the floor never touched; 263 starts **20** lost (NQ 11, index 9) against 19. Log:
`verification/noise_v2/g177_k11.txt`.

## G178: the opening-drive fill-in at 0.6 on U38 (registered 2026-11-04, before its run)

**The idea, from G177:** k11 changed three settings; the drive trigger (`gap_go_drive_k` 0.6: a bigger 09:30 bar
needed) is the one that touches every set's first half hour. **The variant:** U38 with 0.6 alone. **Run once:** the 263
starts and the full sets in both executions. **Adopt on G78's rule** against U38 (or G99b's if it loses fewer).

**G178 result (run once, 2026-11-04): passes G78's rule; adopted (U39).** Chart / NinjaTrader: window $54,638 /
**$54,700** (U38 $54,339 / $54,417), NQ $563,486 / $560,920 (U38 $560,911 / $558,360), index $787,763 / $780,492 (U38
$783,163 / $774,859); no −$1,000 day, the floor never touched; 263 starts **19** lost (as U38; NQ 10, index 9), medians
$50,083 / $39,579. Log: `verification/noise_v2/g178_drive06.txt`.

**U39 (2026-11-04): the opening-drive fill-in needs a 09:30 bar of 0.6x the average body (G178; U26-U38: 0.5).**

## G179: G177's other two settings, each alone on U39 (registered 2026-11-04, before its run)

**Variants:** U39 with `profit_step_fast` 600 from $15,000 (instead of 750 from $10,000), and U39 with `fill_qty2_room`
5,000. **Run once:** the 263 starts and the full sets in both executions. **Adopt (the better window) on G78's rule**
against U39 (no more than 19 lost).

**G179 result (run once, 2026-11-04): both rejected.** U39: chart / NinjaTrader window $54,638 / $54,700, NQ $563,486
/ $560,920, index $787,763 / $780,492; 19 lost. Steps per $600 from $15,000: window **$56,806 / $57,130**, NQ $563,830 /
$561,265, index **$786,626 / $779,569** (−0.1%), 19 lost: fails G78 on the index by about $1,000. Fill-ins at 2 MNQ from
$5,000: $54,694 / $54,862, $564,800 / $562,296, $787,969 / $780,492, **20** lost. Log: `verification/noise_v2/g179.txt`.

## G180: the drive trigger at 0.7, and the small-gap trigger at 0.1, on U39 (registered 2026-11-04, before its run)

**Variants:** U39 with `gap_go_drive_k` 0.7, and U39 with `gap_go_small_k` 0.1 (a small gap at least 0.1x the average
for the 1-contract fill-in; U39: any). **Run once:** the 263 starts and the full sets in both executions. **Adopt (the
better window) on G78's rule** against U39 (no more than 19 lost), or G99b's if it loses fewer.

**G180 result (run once, 2026-11-04): both rejected.** Drive 0.7: window **$54,518** / $55,128 (U39 $54,638 /
$54,700), NQ $558,199 / $555,637 (lower), 19 lost. Small gap 0.1: window $54,638 / $54,700 (equal), index $788,154 /
**$774,760**, **20** lost. U39's 0.6 drive stays. Log: `verification/noise_v2/g180.txt`.

## G181: the More trading days cushion at $2,500 and $3,500 on U39 (registered 2026-11-04, before its run)

**Variants:** U39 with `fill_min_room` 2,500 and 3,500 (the fill-ins once the account is that far above the stopped
floor; U39: 3,000). **Run once:** the 263 starts and the full sets in both executions. **Adopt (the better window) on
G78's rule** against U39 (no more than 19 lost), or G99b's if it loses fewer.

**G181 result (run once, 2026-11-04): $2,500 passes G99b's survival-first rule; adopted (U40).** $2,500: 263 starts
**17 lost or frozen** (NQ 8, index 9) against U39's 19; chart / NinjaTrader window $54,622 / $54,710, NQ $563,490 /
$560,957, index $787,085 / $774,954 (all 99.3-100% of U39's); medians $51,488 / $38,803; no −$1,000 day, the floor
never touched. $3,500: 20 lost. Log: `verification/noise_v2/g181_cushion.txt`.

**U40 (2026-11-04): More trading days from $2,500 above the stopped floor (G181; U22-U39: $3,000).** The setting
"More trading days: cushion" defaults to 2,500.

## G182: the More trading days cushion at $2,000 and $2,250 on U40 (registered 2026-11-04, before its run)

**Variants:** U40 with `fill_min_room` 2,000 and 2,250 (U40: 2,500). **Run once:** the 263 starts and the full sets in
both executions. **Adopt (the fewest lost) on G99b's survival-first rule** against U40 (fewer than 17, every net at
least 95%), or G78's.

**G182 result (run once, 2026-11-04): both rejected.** 263 starts: $2,000 20 lost, $2,250 **24** (U40's $2,500: 17);
nets within 1%. Log: `verification/noise_v2/g182_cushion.txt`.

**A caveat on the survival counts (2026-11-04).** Neighbouring settings move the 263-start count by up to 7 ($2,250 →
24, $2,500 → 17, $3,000 → 19), so a difference of 1-2 accounts is within the noise. Of today's survival-rule adoptions,
U35 (32 → 26) and U37 (25 → 20) are well clear of it; U36 (−1), U38 (−1) and U40 (−2) are not, though none costs more
than 1% of net. Expect about 1 fresh account in 10 to 15 to be lost or frozen within 21 months, not a precise figure.

## G183: the survival gains on start dates they weren't chosen on (a check, registered 2026-11-04, before its run)

**The check:** U35-U40 were adopted on starts on the 1st of each month. The same 263 months started on the **15th**
(`START_FREQ=MID`) are a new sample: U34, U37 and U40 on it. **Read:** if U40 loses clearly fewer than U34 there too,
the survival gains are real; if not, they were fitted to the 1st-of-month sample. No adoption rides on it.

**G183 result (2026-11-04): the after-loss gains hold; the last three don't add.** Lost or frozen on the 263
mid-month starts: U34 **28**, U37 **22**, U40 **25** (on the 1st-of-month starts: 32 / 20 / 17). Over both samples
(526): U34 60 (11.4%), U37 42 (8.0%), U40 42 (8.0%). So U35-U37 (the after-loss max loss as every trade's) are a real
gain of about 3 accounts in 100; U38-U40 are neutral on survival (and within 1% on net). U40 stays the file: as safe as
U37 on the larger sample, with the same net. Medians on the mid-month starts: U40 $47,800 / $37,760, U37 $51,397 /
$37,937, U34 $48,237 / $35,674. Log: `verification/noise_v2/g183_mid_month.txt`.

**U40 checks (2026-11-04):** the full suite, **669 passed**; the NinjaTrader growth run on the window $54,700.08 (`verification/noise_v2/v38g_nt_u40.txt`), identical to the model up to the 2026-03-09 data hole.

## G184: a contract per $1,750 below $10,000 of profit, on U40, judged on 526 starts (registered 2026-11-04, before its run)

**The idea:** the early steps add contracts while the account is still thin; G169's better combinations had $1,750.
**The variant:** U40 with `profit_step` 1,750 (the faster $750 steps above $10,000 unchanged). **Run once:** the 526
starts (the 1st and the 15th of each month) and the full sets in both executions. **Adopt on G99b's survival-first
rule** against U40 (fewer than 42 of 526 lost, every net at least 95%).

**G184 result (run once, 2026-11-04): rejected.** 526 starts: **46** lost or frozen (22 + 24; U40 42); nets within
1-2%. Log: `verification/noise_v2/g184_step1750.txt`.

## G185: U40's weekly P/L by the account's profit (a measurement, 2026-11-04)

`research/g185_weekly_u40.py` (`verification/noise_v2/g185_weekly_u40.txt`), as G144 for U34: under $10,000 of profit
$175-430 a week; $10,000-30,000 **$1,637** a week on the window (17% of weeks at +$3,000), $1,627 on NQ, $639 on the
index; past $30,000 $714-1,177 a week, 12-15% of weeks at +$3,000. About the same as U34: today's later rounds bought
survival, not weekly profit.

## G186: no shorts at all in an uptrend, on U40, on 526 starts (registered 2026-11-04, before its run)

**The variant:** U40 with `trend_small` off (above the 50-session trend, no shorts at all; U40: 1-contract shorts there
once the floor stops). **Run once:** the 526 starts and the full sets in both executions. **Adopt on G78's rule**
against U40 (no more than 42 of 526 lost), or G99b's if it loses fewer.

**G186 result (run once, 2026-11-04): passes the letter of G99b, not adopted.** 526 starts: **40** lost or frozen
(17 + 23; U40 42); NinjaTrader window $52,315 (95.6%), NQ $539,350 (96.1%), index $745,291 (96.2%); no −$1,000 day.
But 2 of 526 is well inside the noise G182 showed, and the median fresh account falls by about a fifth (NQ $37,684 /
$37,339 against U40's $51,488 / $47,800). Trading 4% less net and a fifth less median for no measurable safety is the
wrong trade for this account, so U40 stays; this departs from the registered rule and is stated as such. **From G187
on, G99b needs a survival gain of at least 4 of the 526 starts.** Log: `verification/noise_v2/g186_no_uptrend_shorts.txt`.

## G187: half size on jobs-report days, on U40, on 526 starts (registered 2026-11-04, before its run)

**The idea:** G62 doubled the size on the first-Friday jobs reports (rejected); the other way: those days' 08:30 news
makes the morning wide, so half the contracts (`news_mult` 0.5, at least 1). **The variant:** U40 with it. **Run once:**
the 526 starts and the full sets in both executions. **Adopt on G78's rule** (no more lost than U40's 42), or G99b's
with a gain of at least 4 of the 526.

**G187 result (run once, 2026-11-04): rejected.** Chart / NinjaTrader: window **$53,412 / $52,599** (U40 $54,622 /
$54,700), NQ $570,957 / $567,981, index $785,535 / $774,439; 526 starts **47** lost or frozen (U40 42). Log:
`verification/noise_v2/g187_nfp_half.txt`.

## G188: no entries after three losers in a day, on U40, on 526 starts (registered 2026-11-04, before its run)

**The variant:** U40 with `max_losers` 3 (G116 tested it on U29 only). **Run once:** the 526 starts and the full sets
in both executions. **Adopt on G78's rule** (no more lost than 42), or G99b's with a gain of at least 4 of the 526.

**G188 result (run once, 2026-11-04): rejected.** 526 starts: **50** lost or frozen (U40 42); nets within 0.1%. Log:
`verification/noise_v2/g188_max_losers3.txt`.

## G189: the gap-slot fill-ins from day one, on U40 (registered 2026-11-04, before its run)

**Why:** G172 showed the early 1-contract gap trade saves accounts; G102 found *all* fill-ins from day one lost accounts
as a group, but never tried the gap-slot ones alone. **The variant:** U40 with `gap_fill_early` (the small-gap and
drive fill-ins of the gap slot also allowed before the floor has stopped). **Run once:** the 526 starts and the full
sets in both executions. **Adopt on G78's rule** (no more lost than 42), or G99b's with a gain of at least 4 of the 526.

**G189 result (run once, 2026-11-04): rejected.** 526 starts: **70** lost or frozen (36 + 34; U40 42). The window
gained (NinjaTrader $57,807 against $54,710) but the index fell (NinjaTrader $768,257 against $774,954). Like G102,
fill-ins before the floor stops cost accounts. Log: `verification/noise_v2/g189_gap_fill_early.txt`.

## G190: do the losing stretches show in the market beforehand? (a measurement, registered 2026-11-04, before its run)

**Why:** of U40's 42 dead starts, most made money first and gave it all back in a long losing stretch for this
strategy (2011, 2013, 2015, 2019-20, 2022); G87/G175's shadow gate used the bot's own record and sat out the recoveries
too. **The measurement** (`research/g190_regime.py`): U40's per-contract P/L over the next 20 sessions, by quintile of
four things known the evening before: the open-to-close efficiency (last 20 sessions), the range against its
100-session mean, the 5-minute returns' lag-1 autocorrelation (last 20 sessions), and the bot's own last 40 sessions.
**What would follow:** a filter is registered (G191) only if one quintile is the lowest on both NQ and the index and
well below the others; otherwise none.

**G190 result (2026-11-04): no filter follows.** Every quintile of every measure has a positive forward 20-session P/L
on both sets ($410-876 a contract). The lowest efficiency quintile is the lowest on both (NQ $526, index $466 against
$588-728), but only about 20% below the rest, and its share of stretches below −$300 (17%) is no higher than the others'
(13-20%). The losing stretches don't show in these beforehand. Log: `verification/noise_v2/g190_regime.txt`.

## G191: the gap trade in the giveback, on U40 (registered 2026-11-04, before its run)

**Why:** five dead U40 starts traced trade by trade (`index` 2011-04, 2013-07, 2013-12; `nq` 2015-06, 2019-11): after
the peak, the gap trades' stops cost $390-1,800 of each $2,000-3,300 giveback, and a 1-contract gap stop at the 09:30
open lost up to $404 in the volatile weeks (2011-08, 2015-08-24), twice the bot's own max loss a contract. **The
variants:** U40 with (a) `gap_go_cap` (the gap trade's stop no farther than the bot's max loss a contract) and (b)
`gap_skip_braked` (no gap-slot trade while the giveback brake is on). **Run once:** the 526 starts and the full sets in
both executions. **Adopt (the fewest lost) on G78's rule** (no more than 42 lost, higher nets) or G99b's (at least 4
fewer lost, every net at least 95%).

**G191 result (run once, 2026-11-04): (b) passes G99b's survival-first rule; adopted (U41).** 526 starts: (a) the
capped stop **45** lost or frozen, with NinjaTrader's index $749,885 (96.8%); (b) no gap trade while braked **38**
(17 + 21; U40 42). (b)'s nets, chart / NinjaTrader: window $54,622 / $54,710 (identical to U40: the brake never acts
there), NQ $563,437 / $553,165 (U40 $563,490 / $560,957: 98.6%), index $787,157 / $776,319 (U40 $787,085 / $774,954);
no −$1,000 day, the floor never touched. **The cost:** on the 526 starts the median 21-month net is $39,260 (U40
$42,114 on the same count) and +$50,000 is reached in 47.1% (U40 49.4%): an account that gives back half its profit
now waits for the bot's own trades to bring it back, without the gap trade's. Log:
`verification/noise_v2/g191_gap_braked.txt`.

**U41 (2026-11-04): no gap trade while the giveback brake is on (G191).** The setting "Giveback brake: no gap trade
while the brake is on" (`GapSkipBraked`) defaults to on (the Funded growth modes; it acts only on the 5-minute chart,
as the brake does). The dashboard's today line adds ", no gap trade" while the brake is on.

## G192: a $150 stop on every trade, on U41 (registered 2026-11-04, before its run)

**The ask (the user):** "just set stop loss at like 150". The bot's max loss is $187.50 a contract (93.75 points);
G154 tried $150 only until the floor stops (on U34: more accounts lost). **The variants:** U41 with (a)
`max_loss_per_trade` 150 on every trade, and (b) the same plus `gap_go_cap` (the gap trade's stop no farther than $150 a
contract, 75 points). **Run once:** the 526 starts and the full sets in both executions. **Adopt (the fewest lost) on
G78's rule** (no more than 38 lost, higher nets) or G99b's (at least 4 fewer lost, every net at least 95%).

## G193: a very small stop, $100 and $50, on U41 (registered 2026-11-04, before its run)

**The ask (the user):** "or something very small?" **The variants:** U41 with `max_loss_per_trade` (a) 100 (50 points)
and (b) 50 (25 points) on every trade, the gap trade's stop capped the same (`gap_go_cap`). **Run once:** the 526
starts and the full sets in both executions. **Adopt (the fewest lost) on G78's rule** (no more than 38 lost, higher
nets) or G99b's (at least 4 fewer lost, every net at least 95%), against U41 (or against G192's winner, if adopted).

## G194: a small stop with no take-profit, on U41 (registered 2026-11-04, before its run)

**The ask (the user):** "u can set take profit at like unlimited, but u can set stop loss [small]". G139 tried no
take-profit only with the $187.50 stop (less net). **The variants:** U41 with no take-profit (`take_profit` 0) and no
60-minute time stop (`time_stop` 0), so a trade ends at its stop, its lock (break-even once it is a max loss in profit)
or 16:00, and the stop at (a) $100 and (b) $50 a contract, the gap trade's capped the same. **Run once:** the 526 starts
and the full sets in both executions. **Adopt (the fewest lost) on G78's rule** (no more than 38 lost, higher nets) or
G99b's (at least 4 fewer lost, every net at least 95%), against U41 (or G192/G193's winner, if adopted).

## G195: a wide random search around U41, 300 combinations of 30 settings (registered 2026-11-04, before its run)

**The ask (the user):** "keep thinking outside the box and run a million ways". Earlier searches (G115, G145, G147,
G164-G177) moved 5-7 settings over about 23 combinations. **The search** (`research/g195_wide.py`, seed 195): 299
combinations, each moving about 7 of 30 settings at once (the noise lookback, entry multiple, take-profit, lock, max
loss, time stop, last entry, filters, trend, size steps, brake, gap trade, partial exits, cooldowns, short size,
after-loss target, day keep...); row 0 is U41. **Stage 1:** each on the window (the chart's execution). **Stage 2:** the
15 best on the window with no −$1,000 day, the floor never touched and at least U41's net, on NQ and the index.
**Stage 3:** any passing stage 2 (at least U41's net on NQ and the index, no −$1,000 day) goes to NinjaTrader's
execution and the 526 starts, best window first, at most three; **adopted on G78's rule** (no more than 38 lost) or
G99b's (at least 4 fewer lost, every net at least 95%). With 299 tries some will beat U41 on the window by chance; NQ,
the index and the 526 starts are the check against that.

**G192 result (run once, 2026-11-04): both rejected.** 526 starts: (a) $150 **95** lost or frozen, (b) with the gap
stop capped **80** (U41 38). The window gains (NinjaTrader $56,044 / $58,274 against $54,710), but NQ falls to $465,623
/ $461,585 (U41 $553,165: 84%), the index to $730,889 / $725,923, and both have an index day at **−$1,117** (past the
$1,000 limit): the smaller stop takes more contracts, and a stop that fills far past its price then costs more. Log:
`verification/noise_v2/g192_stop150.txt`.

**G195 result (run once, 2026-11-04): none passes stage 2; nothing goes on.** Stage 1: 22 of 299 beat U41 on the window
($54,622) with no −$1,000 day and the floor never touched, the best at **$73,777**; 12 touched the floor. Stage 2: all
15 best are lower on NQ or the index (U41 $563,437 / $787,157). The window's best mostly had a one-check cooldown after
a trade on a side (`side_cooldown`), which pays on the window and costs $140-200k on NQ and the index: a window fit.
The closest, k87 (`trend_n` 100, no time stop, the gap trade to break-even at 1x its risk, a lock from 15:00, a
4-point sizing allowance): window $58,043, index **$806,551**, NQ $555,239 (98.5%), so it fails by NQ; k133 (lookback
20, entry 0.9x, range position 0.55, last entry 15:30, at most four losers, $1,250 steps): NQ $550,705, index $608,681.
Log: `verification/noise_v2/g195_wide.txt`.

## G196: the wide search the other way round, judged first on NQ and the index (registered 2026-11-04, before its run)

**Why:** G195 picked on the 21-month window and its picks failed on the long histories. **The search:** the same 30
settings, a new draw (seed 196, 299 combinations, `ORDER=long`). **Stage 1:** each on NQ (2015-25) and the index
(2011-26), the chart's execution. **Stage 2:** the 15 best there (both nets at least U41's, no −$1,000 day, the floor
never touched; ranked by the sum of the two nets against U41's) on the window. **Stage 3:** any at least U41's net on
the window too goes to NinjaTrader's execution and the 526 starts, best first, at most three; **adopted on G78's rule**
(no more than 38 lost) or G99b's (at least 4 fewer lost, every net at least 95%).

**U41 checks (2026-11-04):** the full suite, **670 passed**; the NinjaTrader growth run on the window $54,700.08
(`verification/noise_v2/v38g_nt_u41.txt`), the same as U40's (the brake never acts there), identical to the model up to
the 2026-03-09 data hole.

**G193 result (run once, 2026-11-04): both rejected.** NinjaTrader's execution, window / NQ / index: $100 **$31,068** /
$609,219 / $800,791; $50 **$1,776** / $774,367 / $787,199 (U41 $54,710 / $553,165 / $776,319). The long histories gain,
but the window, where the account trades, loses 43% and 97%; at $50 only 40-48% of trades win (25 points is inside a
5-minute bar's noise), and the chart's index has three days past −$1,000. 526 starts: $100 **88** lost or frozen, $50
**66** (U41 38); medians $12,800-24,000 (U41 about $39,000). Log: `verification/noise_v2/g193_small_stops.txt`.

## G197: a tighter stop only once the account is well up, on U41 (registered 2026-11-04, before its run)

**Why, from G193:** a $100 stop made more on NQ and the index (+$56k / +$24k) but lost accounts and most of the window.
Most losses come before the cushion is built, and a tight stop there is what kills accounts (G154, G193). **The
variants:** U41 with the max loss at most (a) $100 and (b) $125 a contract once the profit is above $10,000
(`grown_ml`, `grown_from` 10,000; 5-minute bars), the gap trade unchanged. **Run once:** the 526 starts and the full
sets in both executions. **Adopt (the better window) on G78's rule** (higher nets on all three in both executions, no
−$1,000 day, the floor never touched, no more than 38 lost).

**G194 result (run once, 2026-11-04): both rejected.** NinjaTrader's execution, window / NQ / index: $100 with no target
**$34,294** / $540,598 / $539,582; $50 **$2,213** / $625,688 / $625,423 (U41 $54,710 / $553,165 / $776,319). Without the
target the winners give back to the lock or the line before 16:00: less than with the target (G193) on every set. 526
starts: **100** and **92** lost or frozen (U41 38). Log: `verification/noise_v2/g194_small_stop_no_target.txt`.

**G197 result (run once, 2026-11-04): both rejected.** 526 starts: both **38** lost or frozen (the same as U41: the
change acts only past $10,000). NinjaTrader's execution, window / NQ / index: $100 $41,745 / $503,653 / $596,620; $125
**$57,915** / $470,599 / $571,427 (U41 $54,710 / $553,165 / $776,319). $125 gains on the window, but loses 15% on NQ
and 26% on the index; medians fall too. G193's long-history gain came with the early phase's sizing, not from the
tight stop on a grown account. Log: `verification/noise_v2/g197_grown_ml.txt`.

**G196 result (run once, 2026-11-04): none passes stage 1; nothing goes on.** Of 299 combinations, 249 had no −$1,000
day and never touched the floor on NQ and the index; of those **2 beat U41 on NQ and 8 on the index, none on both** (U41
$563,437 / $787,157). The closest: k184 (range position 0.6, no time stop, last entry 15:30) NQ $558,865 (99.2%), index
**$815,563**; k242 (a lock from 14:00) $557,079 / $806,500; k17 ($1,250 steps, brake 0.6, cushion $2,000) $561,161 /
$799,057. With G195, about 600 random combinations of 30 settings: U41 sits at or near the top of this strategy's
settings on the long histories. Log: `verification/noise_v2/g196_wide_long.txt`.

## G198: G196's seven closest, judged on survival (registered 2026-11-04, before its run)

**Why:** G196's best combinations are within 3% of U41 on both long histories; none was checked on survival. **The
candidates:** the 7 of G196 with both NQ and index nets at least 97% of U41's, no −$1,000 day, the floor never touched
(k184, k27, k242, k17, k262, k237, k166). **Stage A:** each on the 263 starts on the 1st of the month. **Stage B:** the
one with the fewest lost, if fewer than U41's 17 there, goes on to the 263 mid-month starts and the full sets in both
executions. **Adopted on G99b's rule** (at least 4 fewer of the 526 lost than U41's 38, every net at least 95%, no
−$1,000 day, the floor never touched) or G78's.

**G198 result (run once, 2026-11-04): none goes on.** 263 starts on the 1st, lost or frozen (U41 **17**): k184 25, k27 25,
k242 30, k17 22, k262 50, k237 34, k166 24. Each of G196's closest loses more accounts than U41; no stage B. Log:
`verification/noise_v2/g198_survival.txt`.

## G199: the trend over 100 sessions, re-checked on U41 and 526 starts (registered 2026-11-04, before its run)

**Why:** `trend_n` 100 was a near miss three times (G140 on U33, G176 on U38: one account more of 263; G195's k87): it
raises the window and the index and costs NQ about 1%. It was never judged on the 526 starts. **The variant:** U41 with
`trend_n` 100. **Run once:** the 526 starts and the full sets in both executions. **Adopt on G78's rule** (higher nets
on all three in both executions, no more than 38 lost) or G99b's (at least 4 fewer lost, every net at least 95%).

## G200: what simple setups earn on the days U41 sits out (a measurement, registered 2026-11-04, before its run)

**Why:** U41 trades on about 72% of sessions; a second setup on the other 28% would add trades without crowding the
first. **The measurement** (`research/g200_idle_days.py`, 1 MNQ, commission and a tick each way): on the sessions with
no U41 trade, (A) last-half-hour momentum in the direction of the day so far, (B) the same in the direction of the
first half hour, (C) the opening-range breakout (first close beyond 09:30-10:00, a stop at the other side, out at
16:00), (D) a fade of the first half hour from 10:00 to 16:00; per year on NQ, the index and the window. **What would
follow:** a setup is registered as a fill-in (G201) only if it is positive on all three sets and in at least two thirds
of the years.

**G200 result (2026-11-04): D passes as measured, but the measure looks ahead.** Per MNQ after costs: D (the fade of the
first half hour) **+$7,486** on the window (2 of 2 years up), **+$43,230** on NQ (10 of 11), **+$69,156** on the index
(15 of 16); A and B are near zero, C (the breakout) loses every year (−$131,615 / −$153,695). But "a day U41 sits out"
is known only after its last entry check (15:00): those are the days price stayed inside the noise area, where a fade
wins by construction. So D can't be traded as measured; G201 measures the version a bot can trade. Log:
`verification/noise_v2/g200_idle_days.txt`.

## G201: the morning fade as it could be traded (a measurement, registered 2026-11-04, before its run)

**The setup, on every session:** at 10:00 (the 09:55 bar's close), 1 MNQ against the 09:30-10:00 move; out at 16:00,
or at U41's first entry of the day after 10:00 (at that entry's price), whichever comes first. Per MNQ after costs, per
year, on the window, NQ and the index; also split by whether U41 traded that day. **What would follow:** it goes on to a
fill-in test in the bot (G202) only if it is positive on all three sets and in at least two thirds of the years.

**G201 result (2026-11-04): no fill-in follows.** Traded as a bot could: window **+$1,253** per MNQ (1 of 2 years up), NQ
**−$818** (7 of 11), index **−$21,611** (8 of 16). The days U41 later trades give back what the quiet days make
(index −$89,468 against +$67,857): the bot's first entry is the fade's stop, and it comes after the move has gone
against the fade. G200's edge was the look-ahead. Log: `verification/noise_v2/g201_fade.txt`.

**G199 result (run once, 2026-11-04): rejected.** Chart / NinjaTrader: window $57,513 / $57,653 (U41 $54,622 / $54,710),
NQ $556,292 / $554,575 (U41 $563,437 / $553,165), index $799,358 / **$828,069** (U41 $787,157 / $776,319); no −$1,000
day, the floor never touched. But 526 starts: **59** lost or frozen (28 + 31; U41 38), on both start samples. Log:
`verification/noise_v2/g199_trend100_u41.txt`.

## G202: no fill-ins at all while the giveback brake is on, on U41 (registered 2026-11-04, before its run)

**Why, from G191:** taking the gap slot away from a braked account saved 4 of 526. The other fill-ins (the
1-contract shorts against the uptrend, `trend_small`) still trade while braked. **The variant:** U41 with
`fill_skip_braked` (no fill-in while the brake is on; the bot's own trades stay). **Run once:** the 526 starts and the
full sets in both executions. **Adopt on G78's rule** (higher nets on all three in both executions, no more than 38
lost) or G99b's (at least 4 fewer lost, every net at least 95%).

**G202 result (run once, 2026-11-04): rejected (no better on two of three).** 526 starts: **38** lost or frozen, the
same as U41. Chart / NinjaTrader: window $54,622 / $54,710 and index $787,157 / $776,319, identical to U41; NQ $563,636 /
**$561,003** (U41 $563,437 / $553,165). G78 asks for a higher net on all three, and the window and the index are only
equal; a braked account rarely meets a short fill-in. Log: `verification/noise_v2/g202_fill_skip_braked.txt`.

## G203: 40 random combinations of the survival settings around U41 (registered 2026-11-04, before its run)

**The search** (`research/g203_survival_search.py`, seed 203): 40 combinations, each moving about 4-5 of 18 settings
(the brake level, the fill-in cushion and 2-MNQ room, the early daily budget and max loss, the contract step, the sizing
allowance, the losers a day, the skipped checks, the lock, target, time stop, trend, calm, big-day and range filters,
the gap trigger, the after-loss max loss). **Stage A:** each on the 263 starts on the 1st (U41: 17). **Stage B:** the one
with the fewest lost (ties: the higher median), if 13 or fewer, goes on to the 263 mid-month starts and the full sets
in both executions. **Adopted on G99b's rule** (at least 4 fewer of the 526 than U41's 38, every net at least 95%, no
−$1,000 day, the floor never touched) or G78's.

**G203 stage A (2026-11-04):** 263 starts on the 1st, lost or frozen: **k18 12** (U41 17), k27 16, k2 / k9 17, the
rest 18-44. k18 (`giveback_brake` 0.6, `early_daily_loss` $750, `max_losers` 3, `time_stop` 45, `range_pos_min` 0.7,
`gap_go_k` 0.6) goes on to stage B; its medians are lower ($27,237 / $28,971 against U41's $34,175 / $49,488). Log:
`verification/noise_v2/g203_survival_search.txt`.

**G203 result (run once, 2026-11-04): k18 rejected by its nets.** 526 starts: **29** lost or frozen (12 + 17; U41 38),
9 fewer, the most saved by any change today. But chart / NinjaTrader: window $50,556 / $50,756 (U41 $54,622 / $54,710:
**92.8%**), NQ $535,793 / $535,359 (96.8%), index $777,279 / **$670,856** (86.4%); medians about $27,000-28,500 (U41
about $34,000-49,000). G99b asks for every net at least 95%. It is the clearest survival-for-profit trade found: about
1 account in 18 lost instead of 1 in 14, for about 7% less on the window and 14% less on the index in NinjaTrader's
execution. Log: `verification/noise_v2/g203_k18.txt`.

## G204: G203's k18 taken apart (registered 2026-11-04, before its run)

**Why:** k18 saved 9 of 526 accounts but cost 7-14% of the nets; it moves six settings. **The variants:** k18 with each
one of its six settings put back to U41's (six variants: without the brake at 0.6, without the $750 early budget,
without three losers a day, without the 45-minute time stop, without the 0.7 range filter, without the 0.6 gap
trigger), and the $750 early budget alone (it acts only before the floor stops). **Stage A:** each on the 263 starts on
the 1st (U41 17, k18 12). **Stage B:** the one with the fewest lost (ties: the higher median), if 13 or fewer, goes on
to the mid-month starts and the full sets in both executions. **Adopted on G99b's rule** (at least 4 fewer of the 526
than U41's 38, every net at least 95%) or G78's.

**G204 stage A (2026-11-04):** 263 starts on the 1st, lost or frozen (U41 17, k18 12): without the 0.6 brake **12**
(medians $32,059 / $44,475, against k18's $27,237 / $28,971), without the time stop 13, without the gap trigger 13,
without the early budget 14, without three losers 14, the early budget alone 16, **without the 0.7 range filter 29**:
the range filter carries the survival gain. "Without the brake" goes on to stage B. Log:
`verification/noise_v2/g204_k18_apart.txt`.

## G205: the range-position filter at 0.7 alone, on U41 (registered 2026-11-04, before its run)

**Why, from G204:** putting k18's range filter back to U41's 0.65 loses 29 of 263 instead of 12; the filter at 0.7
(`range_pos_min`) carries the survival gain. G112 last checked it on U29. **The variant:** U41 with `range_pos_min`
0.7 alone. **Run once:** the 526 starts and the full sets in both executions. **Adopt on G78's rule** (higher nets on all
three in both executions, no more than 38 lost) or G99b's (at least 4 fewer lost, every net at least 95%).

**G204 result (run once, 2026-11-04): k18 without the 0.6 brake passes G99b's survival-first rule; adopted (U42).** 526
starts: **28** lost or frozen (12 + 16; U41 38), 10 fewer. Chart / NinjaTrader: window $53,124 / $53,164 (U41 $54,622 /
$54,710: 97.2%), NQ $543,263 / $542,956 (96.4% / 98.2%), index $775,728 / $757,333 (98.5% / 97.6%); no −$1,000 day, the
floor never touched. Medians: $33,067 / $41,928 on the mid-month starts (U41 $33,994 / $42,358). Log:
`verification/noise_v2/g204_stage_b.txt`.

**G205 result (run once, 2026-11-04): rejected.** The range filter at 0.7 alone: 526 starts **39** lost or frozen (U41
38); NinjaTrader NQ $537,642 (97.2%). The survival gain needs the combination, not the filter alone. Log:
`verification/noise_v2/g205_range07.txt`.

**U42 (2026-11-04): five settings together (G204).** On the 50K's Funded growth: no new entry after **three losing
trades in a day** (`MaxLosersPerDay`), a **$750 day budget until the floor has stopped** (`EarlyDayBudget`; $900 after),
a **45-minute time stop** (60 before), entries only in the top **70%** of the day's range (0.65 before), and the gap
trade from **0.6x** the average gap (`GapTrigger`; 0.5 before). The giveback brake stays at 0.5.

## G206: U42's weekly P/L by the account's profit (a measurement, 2026-11-04)

`research/g206_weekly_u42.py` (`verification/noise_v2/g206_weekly_u42.txt`). Window, $10,000-30,000 up: 26 weeks,
**$1,532** average (U40 $1,637), 11.5% of weeks at +$3,000 or more; NQ $1,158 (U40 $1,627), the index $1,059 (U40
$639); past $75,000 the long histories average $967-1,158 a week. U42's gain is survival, not the grown phase.

## G207: 40 random combinations of the survival settings around U42 (registered 2026-11-04, before its run)

**The search** (`research/g207_survival_search.py`, seed 207): as G203, around U42, the same 18 settings with values
other than U42's. **Stage A:** each on the 263 starts on the 1st (U42: 12). **Stage B:** the one with the fewest lost
(ties: the higher median), if 8 or fewer, goes on to the mid-month starts and the full sets in both executions.
**Adopted on G99b's rule** against U42 (at least 4 fewer of the 526 than U42's 28, every net at least 95% of U42's, no
−$1,000 day, the floor never touched) or G78's.

**U42 checks (2026-11-04):** the full suite, **674 passed**; the NinjaTrader growth run on the window **$52,981.78**
(`verification/noise_v2/v38g_nt_u42.txt`): identical to the model on 30-minute bars, and on 5-minute bars up to the
2026-03-09 data hole.

**G207 result (2026-11-04): none goes on.** 263 starts on the 1st, lost or frozen (U42 12): the best k39 **10**, k32 11
(medians $35,176 / $53,658, against U42's $32,059 / $44,475), k29 / k40 12, the rest 13 or more. None reaches 8 or fewer;
U42 stays. Log: `verification/noise_v2/g207_survival_search.txt`.

## G208: G207's k32 and k39 on the full checks, against U42 (registered 2026-11-04, before its run)

**Why:** k32 (`fill_min_room` 3,000, `size_slip_pts` 6, `giveback_brake` 0.4, `take_profit` 1.75, `trend_n` 40) lost 11
of 263 with medians above U42's; k39 (`after_loss_ml_mult5` 0.9, `early_ml` 170, `big_day_k` 1.7) lost 10. Neither met
G207's stage-B bar, so this is a separate test. **Run once each:** the mid-month starts and the full sets in both
executions. **Adopt (the better window) on G78's rule** against U42 (higher nets on all three in both executions, no
−$1,000 day, the floor never touched, no more than 28 of 526 lost).

**G208 result (run once, 2026-11-04): both rejected by the window.** k32: 526 starts **25** lost or frozen (11 + 14; U42
28); NQ $600,213 / **$580,796** (U42 $543,263 / $542,956: +7%), index $777,163 / $753,984, but the window **$45,507** /
$46,148 (U42 $53,124 / $53,164: −13%). k39: **23** lost (10 + 13); window $49,380 / $49,505 (−7%), NQ $544,043 /
$543,826, index $770,155 / $751,338. G78 asks for a higher net on all three. Log: `verification/noise_v2/g208_k32_k39.txt`.

## G209: 30 random combinations of the grown-phase settings around U42 (registered 2026-11-04, before its run)

**Why:** U42's gains are in survival; the weekly P/L once grown is what falls short. These settings act only once the
floor has stopped, so they should leave the early accounts alone. **The search** (`research/g209_grown_search.py`, seed
209): `profit_step_fast` 600-850, `profit_step_fast_from` $8,000-15,000, `gap_go_locked_qty` 8-15, `fill_qty2_room`
$5,000-7,000, `fill_qty3_room` $9,000-12,000, `gap_go_k_locked` 0.5-1.0, `after_loss_ml_locked` 0.9-1.1; row 0 is U42.
**Screen:** the chart's nets at least U42's on all three sets, no −$1,000 day, the floor never touched. **Then:** the
best window among those passing goes to NinjaTrader's execution and the 526 starts, **adopted on G78's rule** (higher
nets on all three in both executions, no more than 28 lost).

**G209 screen (2026-11-04): 8 of 30 pass**, every one with 3-MNQ fill-ins from $9,000-12,000 above the floor
(`fill_qty3_room`; G107 tried $9,000 on U26). The best window, **k26** (`profit_step_fast` 700, `fill_qty3_room` 12,000,
`after_loss_ml_locked` 1.1): $57,252 / NQ $568,020 / index $801,072 (U42 $53,124 / $543,263 / $775,728), no −$1,000 day.
k26 goes on. (k17 and k1, with 15 gap contracts, made more but had an index day at −$1,000.) Log:
`verification/noise_v2/g209_grown_search.txt`.

**G209 result (run once, 2026-11-04): k26 rejected by two accounts.** Chart / NinjaTrader: window $57,252 / **$57,326**
(U42 $53,124 / $53,164), NQ $568,020 / $568,270 (U42 $543,263 / $542,956), index $801,072 / $790,230 (U42 $775,728 /
$757,333): higher everywhere, no −$1,000 day, the floor never touched. But 526 starts: **30** lost or frozen (12 + 18;
U42 28). Log: `verification/noise_v2/g209_k26.txt`.

## G210: G209's k14 and k15, without k26's after-loss change (registered 2026-11-04, before its run)

**Why:** k26 raised every net but lost 2 more accounts; it also moved the after-loss max loss once grown (1.1x). k14
(`profit_step_fast` 700 from $8,000, `fill_qty3_room` 9,000) and k15 (`profit_step_fast` 700, `fill_qty3_room` 9,000)
passed G209's screen without that change. **Run once each:** NinjaTrader's execution and the 526 starts. **Adopt (the
better window) on G78's rule** against U42 (higher nets on all three in both executions, no −$1,000 day, the floor never
touched, no more than 28 lost).

**G210 result (run once, 2026-11-04): both pass G78's rule; k14 adopted (U43).** 526 starts: k14 **28** lost or frozen
(12 + 16), k15 28 (U42 28). k14, chart / NinjaTrader: window $56,957 / **$57,000** (U42 $53,124 / $53,164: +7.2%), NQ
$583,372 / $568,316 (U42 $543,263 / $542,956: +4.7%), index $818,965 / $804,355 (U42 $775,728 / $757,333: +6.2%); no
−$1,000 day, the floor never touched. k15: $57,190 / $56,802, $565,874 / $583,632, $816,827 / $800,983. The better window
in NinjaTrader's execution (the one that trades) is k14's, which is also higher on the index in both. Medians: k14
$31,486 / $39,312 (1st), $32,754 / $39,966 (15th). Log: `verification/noise_v2/g210_k14_k15.txt`.

**U43 (2026-11-04): faster steps from $8,000, and 3-MNQ fill-ins from $9,000 above the floor (G210).** A contract per
$700 of profit above $8,000 (`FastSteps` 700, `FastStepsFrom` 8,000; U34-U42: $750 above $10,000), and the fill-in
trades at 3 MNQ while the account is $9,000 or more above the floor (`MoreDaysQty3Room`; 2 from $6,000 as before).

**U43 checks (2026-11-04):** the NinjaTrader growth run on the window **$56,437.51** (`verification/noise_v2/v38g_nt_u43.txt`):
identical to the model on 30-minute bars, and on 5-minute bars up to the 2026-03-09 data hole.

## G211: U43's weekly P/L by the account's profit (a measurement, 2026-11-04)

`research/g211_weekly_u43.py` (`verification/noise_v2/g211_weekly_u43.txt`). Window, $10,000-30,000 up: 26 weeks,
**$1,668** average (U42 $1,532), 11.5% at +$3,000 or more; NQ past $75,000 **$1,256** a week (U42 $1,158), the index
$1,022 (U42 $967).

## G212: 30 random combinations of the grown-phase settings around U43 (registered 2026-11-04, before its run)

**The search** (`research/g212_grown_search.py`, seed 212): `profit_step_fast` 600-650, `profit_step_fast_from`
$6,000-7,000, `fill_qty3_room` $7,000-10,000, `fill_qty2_room` $4,000-5,000, `gap_go_locked_qty` 11-12, `gap_go_k_locked`
0.5-0.75, `size_up_to` 60-75; row 0 is U43. **Screen and adoption as G209's**, against U43 (no more than 28 lost).

**G212 screen (2026-11-04): 5 of 30 pass.** The best window, **k18** (`profit_step_fast` 650, `fill_qty3_room` 8,000,
`fill_qty2_room` 4,000, `size_up_to` 75): $57,446 / NQ $587,643 / index $849,992 (U43 $56,957 / $583,372 / $818,965), no
−$1,000 day; it goes on. Every passing row raised the most contracts to 60-75 or moved the fill-in rooms down. Log:
`verification/noise_v2/g212_grown_search.txt`.

**G212 result (run once, 2026-11-04): k18 passes G78's rule; adopted (U44).** 526 starts: **28** lost or frozen (12 + 16;
U43 28). Chart / NinjaTrader: window $57,446 / **$57,475** (U43 $56,957 / $57,000), NQ $587,643 / $579,739 (U43 $583,372 /
$568,316), index $849,992 / **$828,138** (U43 $818,965 / $804,355); no −$1,000 day, the floor never touched. Median 21-month
net on the 526: $33,917 (U43 $33,395). Log: `verification/noise_v2/g212_k18.txt`.

**U44 (2026-11-04): $650 steps above $8,000, fill-ins at 2 MNQ from $4,000 and 3 from $8,000, up to 75 MNQ (G212).**
`FastSteps` 650, `MoreDaysQty2Room` 4,000, `MoreDaysQty3Room` 8,000, and the 50K's 5-minute chart up to 75 contracts.

**U44 checks (2026-11-04):** the full suite, **675 passed**; the NinjaTrader growth run on the window **$57,549.09** (`verification/noise_v2/v38g_nt_u44.txt`):
identical to the model on 30-minute bars, and on 5-minute bars up to the 2026-03-09 data hole.

## G213: U44's weekly P/L by the account's profit (a measurement, 2026-11-04)

`research/g213_weekly_u44.py` (`verification/noise_v2/g213_weekly_u44.txt`). Window, $10,000-30,000 up: 28 weeks,
**$1,483** average (U43 $1,668 over 26 weeks: the account moves through the band faster), 10.7% at +$3,000 or more; NQ
past $75,000 $1,256 a week, the index $1,067.

## G214: one more step of the grown-phase search, around U44 (registered 2026-11-04, before its run)

**The search** (`research/g214_grown_search.py`, seed 214): `profit_step_fast` 550-600, `profit_step_fast_from`
$6,000-7,000, `fill_qty3_room` $6,000-7,000, `fill_qty2_room` $3,000-3,500, `gap_go_locked_qty` 11-12, `gap_go_k_locked`
0.5-0.75, `size_up_to` 100; row 0 is U44. **Screen and adoption as G209's**, against U44 (no more than 28 lost). A
caution: G209, G212 and this search climb on the same data, so each step needs the long histories and the 526 starts,
not the window alone.

**G214 result (2026-11-04): none of 30 passes the screen.** Half (15) have a day at −$1,000 or worse; the rest are lower
somewhere than U44. Bigger and earlier grown-phase sizing has reached the daily limit: past U44, more size breaks the
$1,000 day. U44 stays. Log: `verification/noise_v2/g214_grown_search.txt`.

## G215: U44 at 2 ticks of slippage (a robustness measurement, registered 2026-11-04, before its run)

**Why:** U44 sizes bigger once grown (up to 75 MNQ); G156 measured U34 at 2 ticks. **The measurement:** U44 with
`slippage_ticks` 2 (every fill a tick worse than the tested 1) on the full sets in both executions and the 526 starts.
Reported, not judged; a −$1,000 day or a floor touch at 2 ticks would be flagged as a risk to fix.

**G215 result (2026-11-04): the nets hold at 2 ticks, survival does not.** Chart / NinjaTrader at 2 ticks: window $54,012 /
$54,035 (1 tick $57,446 / $57,475), NQ $539,072 / $538,954, index $801,371 / $709,120; no −$1,000 day, the floor never
touched. But 526 starts: **51** lost or frozen (14 + 37; 28 at 1 tick), most on NQ (37 of 206). A fresh account's
survival depends on fills near the tested 1 tick: the strategy's fill-quality alert (20 trades averaging more than 2
ticks worse) is the signal to check the connection and order route (G222: "Gentle start" doesn't help). Log:
`verification/noise_v2/g215_u44_slip2.txt`.

## G216: protecting a fresh account against worse fills, on U44 (registered 2026-11-04, before its run)

**Why, from G215:** at 2 ticks U44 loses 51 of 526 (28 at 1 tick). **The variants:** U44 with (a) `size_slip_pts` 8 (the
sizing counts a stop 8 points worse; 5 now), (b) `early_daily_loss` 600 (a $600 day until the floor stops; $750 now),
(c) both. **Stage A:** each on the 526 starts at 2 ticks. **Stage B:** the one with the fewest lost at 2 ticks, if 45 or
fewer, on the 526 starts and the full sets in both executions at 1 tick. **Adopted** if at 1 tick it loses no more than
U44's 28 and every net is at least 95% of U44's, with no −$1,000 day and the floor never touched.

**G216 result (2026-11-04): none goes on.** 526 starts at 2 ticks, lost or frozen (U44 51): (a) 8-point allowance 51,
(b) $600 early day 49, (c) both 49. None reaches 45: neither a bigger sizing allowance nor a smaller early budget wins back
the accounts that worse fills cost. U44 stays. Log:
`verification/noise_v2/g216_slip2_protect.txt`.

## G217: 40 random combinations of the survival settings around U44 (registered 2026-11-04, before its run)

**The search:** G207's (`research/g207_survival_search.py`, the same 18 settings) with seed 217, around U44. **Stage A:**
each on the 263 starts on the 1st (U44: 12). **Stage B:** the fewest lost (ties: the higher median), if 8 or fewer, on
the mid-month starts and the full sets in both executions. **Adopted on G99b's rule** against U44 (at least 4 fewer of
the 526 than 28, every net at least 95% of U44's, no −$1,000 day, the floor never touched) or G78's.

**G217 result (2026-11-04): none goes on.** 263 starts on the 1st, lost or frozen (U44 12): the best k20 **10**
(`size_slip_pts` 6, `skip_checks` 780 only, `lock_at` 0.3, `trend_n` 40, `big_day_k` 1.7; medians $30,853 / $59,163),
k2 / k26 12, the rest 13 or more. None reaches 8; U44 stays. Log: `verification/noise_v2/g217_survival_search.txt`.

## G218: G217's k20 on the full checks, against U44 (registered 2026-11-04, before its run)

**Why:** k20 lost 10 of 263 (U44 12) with the highest NQ median yet ($59,163). **Run once:** the mid-month starts and
the full sets in both executions. **Adopt on G78's rule** against U44 (higher nets on all three in both executions, no
−$1,000 day, the floor never touched, no more than 28 of 526 lost).

**G218 result (run once, 2026-11-04): rejected.** k20: the window **$15,044 / $7,545** (U44 $57,446 / $57,475) though NQ
$601,417 / $602,205 and the index $850,045 / $828,426 are higher; 526 starts 26 lost (10 + 16). A setting set that fits
the long histories and fails the window the account trades. Log: `verification/noise_v2/g218_k20.txt`.

## G219: a $950 day budget once the floor has stopped, on U44 (registered 2026-11-04, before its run)

**Why:** once grown, the $900 day budget caps every trade (G122, G185). G110 tried $950 on an old version. **The
variant:** U44 with `daily_loss_limit` 950 (the $750 early budget unchanged, so it acts only once the floor has
stopped). **Run once:** the 526 starts and the full sets in both executions. **Adopt on G78's rule** against U44 (higher
nets on all three in both executions, **no day at −$1,000 or worse**, the floor never touched, no more than 28 lost).

**G219 result (run once, 2026-11-04): rejected: three index days past −$1,000.** Nets rise (NinjaTrader window $58,593,
NQ $598,409, index $859,078) and 526 starts 29 lost, but the index has **3 days at −$1,034** in both executions: the
$100 left under the firm's limit is what absorbs a stop that fills past its price. The $900 budget stays. Log:
`verification/noise_v2/g219_day950.txt`.

## G220: 30 random combinations of the exit settings around U44 (registered 2026-11-04, before its run)

**The search** (`research/g220_exit_search.py`, seed 220): `take_profit` 1.75-2.5, `lock_at` 0.25-0.45, `lock_plus`
1-5, `time_stop` 30-60, `late_lock_from` 14:00 / 15:00, `time_lock` 30 / 60; row 0 is U44. **Screen and adoption as
G209's**, against U44 (the chart's nets at least U44's on all three sets, no −$1,000 day, the floor never touched; then
the best window to NinjaTrader's execution and the 526 starts, G78's rule, no more than 28 lost).

**G220 result (2026-11-04): none of 30 passes the screen.** Every exit change is lower than U44 on at least one set;
the closest, k5 (a 30-minute time stop, a lock from 15:00): window $60,611, NQ $575,382 (97.9%), index $836,675
(98.4%). U44's exits stay. Log: `verification/noise_v2/g220_exit_search.txt`.

## G221: 30 random combinations of the entry filters around U44 (registered 2026-11-04, before its run)

**The search** (`research/g221_filter_search.py`, seed 221): `calm_k` 0.6-0.8, `big_day_k` 1.3-1.7, `range_pos_min`
0.65 / 0.75, `squeeze_min` 15 / 25, `entry_k` 0.95-1.1, `lookback` 12 / 16, `gap_go_k` 0.55 / 0.7; row 0 is U44. **Screen
and adoption as G209's**, against U44 (no more than 28 lost).

**G221 result (2026-11-04): none of 30 passes the screen.** The closest, k12 (range position 0.65, gap trigger 0.55):
window $60,182, index $848,323 (99.8%), NQ $571,363 (97.2%). U44's filters stay. Log:
`verification/noise_v2/g221_filter_search.txt`.

## G222: does "Gentle start" help when fills are a tick worse? (a check of the advice, registered 2026-11-04, before its run)

**Why:** the advice (G215, the strategy's setting text) is to turn on "Gentle start" (`steps_after_lock`: no contract
steps until the floor has stopped) if live fills run 3+ ticks worse. It was never measured on U44. **The measurement:**
U44 with `steps_after_lock` on, at 2 ticks, on the 526 starts (U44 at 2 ticks: 51 lost). **What would follow:** the
advice stays if it loses clearly fewer (45 or fewer); otherwise the setting text and the docs say it doesn't help.

**G222 result (2026-11-04): "Gentle start" doesn't help.** U44 with it, at 2 ticks: 526 starts **52** lost or frozen (U44
51). The advice is withdrawn: the dashboard's fill warning now says to check the connection and order route, and the
setting's text says it doesn't help on U44. Log: `verification/noise_v2/g222_gentle_slip2.txt`.

**After G222 (2026-11-04):** the full suite, **675 passed**, on the final U44 file (the fill warning's new text).

## G223: a finer check grid on U44 (registered 2026-11-04, before its run)

**Why:** once grown, U44's day is capped by its budget, not by signals; more checks mean more chances at a trade that
fits it. A 15-minute grid was tried only on the v2.8 bot (docs/RESULTS.md). **The variants** (`research/g223_check_grid.py`):
U44 with checks every 15 minutes (`check_step` 15), the same from 09:45 (`first_check` 585), 09:45 with the half
hours, every 20 minutes, and every 15 minutes with the last entry at 14:30. **Screen as G209's** against U44 (the chart's
nets at least U44's on all three sets, no −$1,000 day, the floor never touched). A pass is reported; the NinjaTrader
strategy has only the half-hour grid, so adoption needs the grid built there first.

**G223 result (2026-11-04): one passes the screen, and it looks fragile.** Chart's execution, window / NQ / index (U44
$57,446 / $587,643 / $849,992): every 15 minutes $11,789 / $608,562 / $1,035,510; from 09:45 $64,793 / $585,198 /
$1,065,541; 09:45 alone $13,980 / $369,993 / $352,711; every 20 minutes $95,896 / $368,694 / $640,253; **every 15
minutes with the last entry at 14:30 $66,707 / $606,068 / $929,754** (passes). Neighbouring grids swing the window from
$12k to $96k: the result depends on which checks exist, not on a steady edge. Log: `verification/noise_v2/g223_check_grid.txt`.

## G224: G223's 15-minute grid (last entry 14:30) on the full checks (registered 2026-11-04, before its run)

**The variant:** U44 with `check_step` 15 and `last_entry_end` 870. **Run once:** NinjaTrader's execution on the full
sets and the 526 starts. **Adopt on G78's rule** against U44 (higher nets on all three in both executions, no −$1,000 day,
the floor never touched, no more than 28 lost), **and** a robustness condition given G223's swings: the same at 2 ticks
must lose no more of the 526 than U44 at 2 ticks (51). Adoption also needs the grid built in NinjaTrader with parity
tests; if that can't be done and tested today, a pass is recorded as pending, not adopted.

**G224 result (run once, 2026-11-04): rejected, by far.** NinjaTrader's execution: window $69,945, NQ $607,283, index
$905,429 (all above U44), no −$1,000 day. But 526 starts: **100** lost or frozen (U44 28); at 2 ticks **136** (U44 51).
The 15-minute grid trades more often at the start, and a fresh account can't carry the extra losers. Log:
`verification/noise_v2/g224_grid15.txt`.

## G225: the three-losers rule only until the floor has stopped (registered 2026-11-04, before its run)

**Why:** U42's three-losers limit is a survival rule; once grown, the day's $900 budget already bounds the day. **The
variants:** U44 with `max_losers_locked` (a new research setting: the loser limit once the floor has stopped) (a) 0 (no
limit) and (b) 4. **Run once:** the 526 starts and the full sets in both executions. **Adopt (the better window) on
G78's rule** against U44 (higher nets on all three in both executions, no −$1,000 day, the floor never touched, no more
than 28 lost).

**G225 result (run once, 2026-11-04): both rejected (neutral).** (a) no limit once grown: 526 starts 29 lost, window
$57,432 / $57,419; (b) four: 28 lost, window $57,435 / $57,458 (U44 $57,446 / $57,475), NQ and the index a little
higher. Within $20 of U44 on the window: once grown the day's budget, not the loser count, ends the day. Log:
`verification/noise_v2/g225_losers_locked.txt`.

## G226: the grown gap trade at 11 or 12 contracts, on U44 (registered 2026-11-04, before its run)

**Why:** G209's 15 gap contracts raised the nets but broke the $1,000 day; 11-12 were only tried inside combinations.
**The variants:** U44 with `gap_go_locked_qty` (a) 11 and (b) 12 (10 now). **Run once:** the 526 starts and the full
sets in both executions. **Adopt (the better window) on G78's rule** against U44.

**G226 result (run once, 2026-11-04): both rejected: an index day past −$1,000.** 11 contracts: window $59,537, NQ
$588,863, 28 lost, but an index day at **−$1,059**; 12: window $61,344, NQ $596,353, 28 lost, an index day at
**−$1,155** (a gap trade stopped past its price at the open). 10 stays. Log: `verification/noise_v2/g226_gap_qty.txt`.

## G227: 12 gap contracts sized for a stop 10 points worse, on U44 (registered 2026-11-04, before its run)

**Why, from G226:** 12 gap contracts raise every net but one index day reached −$1,155, a gap stop filled past its
price. G86 (U25: 15 contracts, 5 points) failed the same way. **The variants:** U44 with `gap_go_locked_qty` 12 and
`gap_slip_pts` (a) 10 and (b) 20 (the gap trade's sizing counts that many points more slippage at its stop). **Run
once:** the 526 starts and the full sets in both executions. **Adopt (the better window) on G78's rule** against U44.
The NinjaTrader strategy doesn't have `gap_slip_pts` yet; a pass is built there before adoption.

**G227 result (run once, 2026-11-04): both rejected.** The allowance removes the −$1,000 days (worst −$962 / −$941) and
keeps 27 lost, but every net falls below U44's: 10 points window $54,379, NQ $575,044, index $815,753; 20 points $47,528
/ $550,213 / $780,878 (U44 $57,475 / $579,739 / $828,138). The allowance costs more on ordinary gap days than the two
extra contracts earn. Log: `verification/noise_v2/g227_gap_slip.txt`.

## G228: a contract per $1,250 below $8,000, on U44 (registered 2026-11-04, before its run)

**The variant:** U44 with `profit_step` 1,250 (1,500 now; G184's 1,750 lost more on U40). **Run once:** the 526 starts
and the full sets in both executions. **Adopt on G78's rule** against U44 (higher nets on all three in both executions, no
−$1,000 day, the floor never touched, no more than 28 lost).

**G228 result (run once, 2026-11-04): rejected.** 526 starts **40** lost or frozen (21 + 19; U44 28); NQ $574,035 /
$577,333 (U44 $587,643 / $579,739); the window ($58,790) and the index ($838,761) gain. Faster early sizing costs fresh
accounts, as G184's slower sizing did the other way. Log: `verification/noise_v2/g228_step1250.txt`.

## G229: the early step at $1,400 and $1,600, on U44 (registered 2026-11-04, before its run)

**The variants:** U44 with `profit_step` (a) 1,400 and (b) 1,600. **Run once:** the 526 starts and the full sets in both
executions. **Adopt (the better window) on G78's rule** against U44, or G99b's (at least 4 fewer lost, every net at least
95%).

**G229 result (run once, 2026-11-04): both rejected; $1,400 by $59.** $1,400: 526 starts **26** lost (U44 28);
NinjaTrader window $58,485, NQ $589,951, index $829,784 (all above U44), chart window $57,584 and index $850,071 above,
but the chart's NQ **$587,584** against U44's $587,643. G78 asks for higher on all; G99b for 4 fewer lost. A near miss,
not adopted. $1,600: 28 lost, NinjaTrader window $57,316 (lower). Log: `verification/noise_v2/g229_step.txt`.

## Where it stands at the end of 2026-11-04 (U44)

**The file:** `ninjatrader/Strategies/MnqNoiseV38.cs`, Mode "Funded growth", the 5-minute MNQ chart, one 50K account.
Full suite 675 passed; NinjaTrader's growth run identical to the model (up to the stand-in data's 2026-03-09 hole).

| U44, measured | |
|---|---|
| Window Jan 2025 – Oct 2026, NinjaTrader's execution | **$57,549** net, 760 trades, worst day −$899, floor never touched |
| Fresh 50K accounts started on the 1st and the 15th of 263 months (NQ 2015-25, index 2011-26), 21 months each | **28 of 526 lost or frozen (about 1 in 19)**; median net $33,917 |
| The same at 2 ticks of slippage | 51 of 526 |
| Weekly, the account $10,000-30,000 up (window) | $1,483 average, 11% of weeks at +$3,000 or more |
| Weekly, past $75,000 (long histories) | $1,067-1,256 |

**Today (G189-G238, 50 rounds):** U41 (no gap trade while braked), U42 (G204's five survival settings: 38 → 28 lost),
U43 and U44 (faster grown-phase steps, 3-MNQ fill-ins, 75 MNQ: window $53,164 → $57,475, index +9%). Everything else was
rejected or a measurement. **Not reached:** $3,000 a week on average, or zero lost accounts. Past U44, every extra
contract or a bigger day budget broke the $1,000 day (G214, G219, G226), and the account's survival depends on fills
near the tested 1 tick (G215, G222).

## G230: a tighter stop for the trade after a loser, on U44 (registered 2026-11-04, before its run)

**Why:** G207's k39 (10 of 263 lost) included `after_loss_ml_mult5` 0.9; it was never tried alone since U37's 1.0.
**The variants:** U44 with the after-loss max loss at (a) 0.9x ($168.75) and (b) 0.8x ($150) on 5-minute bars, until
and after the floor stops (`after_loss_ml_mult5`, `after_loss_ml_locked`). **Run once:** the 526 starts and the full sets
in both executions. **Adopt (the fewer lost) on G78's rule** against U44, or G99b's (at least 4 fewer lost, every net at
least 95%).

**G230 result (run once, 2026-11-04): both rejected.** 0.9x: 526 starts **38** lost (U44 28), NQ $480,263 / $480,133
(−18%); 0.8x: 37 lost, NQ $483,390, index $728,790 (−12%). The window gains ($59,383 / $62,131) but the tighter
after-loss stop gets hit more on the long histories. Log: `verification/noise_v2/g230_after_loss.txt`.

## G231: a bigger gap for the grown gap trade, on U44 (registered 2026-11-04, before its run)

**Why:** the grown gap trade (10 contracts) is where the worst days come from (G226); G157 tried a bigger trigger once
grown on U34. **The variants:** U44 with `gap_go_k_locked` (a) 0.75 and (b) 1.0 (0.6 now, as before the floor stops).
**Run once:** the 526 starts and the full sets in both executions. **Adopt (the better window) on G78's rule** against U44.

**G231 result (run once, 2026-11-04): both rejected.** 0.75: 30 lost, NQ $569,653 / $562,087 (U44 $587,643 / $579,739);
1.0: 32 lost, every net lower. Fewer grown gap trades cost more than they save. Log:
`verification/noise_v2/g231_gap_k_locked.txt`.

## G232: the fill-ins' cushion at $2,000 and $3,000, on U44 (registered 2026-11-04, before its run)

**The variants:** U44 with `fill_min_room` (a) 2,000 and (b) 3,000 (2,500 now, G181 on U39). **Run once:** the 526 starts
and the full sets in both executions. **Adopt (the fewer lost) on G78's rule** against U44, or G99b's.

**G232 result (run once, 2026-11-04): both rejected.** $2,000: 30 lost, nets equal to U44 or a little lower; $3,000: 31
lost, the window $57,443 (U44 $57,475). The $2,500 cushion stays. Log: `verification/noise_v2/g232_fill_room.txt`.

## G233: the giveback brake at 0.4 and 0.6, on U44 (registered 2026-11-04, before its run)

**The variants:** U44 with `giveback_brake` (a) 0.4 and (b) 0.6 (0.5 now; G174 tried 0.55 / 0.6 on U38). **Run once:** the
526 starts and the full sets in both executions. **Adopt (the fewer lost) on G78's rule** against U44, or G99b's.

**G233 result (run once, 2026-11-04): both rejected.** 0.4: 32 lost, window unchanged, index $826,176 (lower); 0.6: 30
lost and the window **$14,368** (the brake at 60% acts on the window and costs most of its profit). 0.5 stays. Log: `verification/noise_v2/g233_brake.txt`.

## G234: the sizing allowance at 4 and 6 points, on U44 (registered 2026-11-04, before its run)

**The variants:** U44 with `size_slip_pts` (a) 4 and (b) 6 (5 now, G170 on U37). **Run once:** the 526 starts and the full
sets in both executions. **Adopt (the fewer lost) on G78's rule** against U44, or G99b's.

**G234 result (run once, 2026-11-04): both rejected.** 4 points: 28 lost, window $58,175 (higher), but the chart's NQ
$584,903 and NinjaTrader's index $824,368 below U44; 6 points: 28 lost, the window $56,141 (lower). 5 stays. Log:
`verification/noise_v2/g234_size_slip.txt`.

## G235: G229's $1,400 step with G234's 4-point allowance, on U44 (registered 2026-11-04, before its run)

**Why:** each was a near miss (G229 by $59 on the chart's NQ, 26 lost; G234 lower on two nets). **The variant:** U44 with
`profit_step` 1,400 and `size_slip_pts` 4. **Run once:** the 526 starts and the full sets in both executions. **Adopt on
G78's rule** against U44, or G99b's. Two near misses combined after the fact is a weaker test; a pass here is reported
with that caveat.

**G235 result (run once, 2026-11-04): rejected by NinjaTrader's index.** 526 starts **26** lost (U44 28); chart window
$58,301, NQ $596,531, index $856,839 and NinjaTrader window $59,263, NQ $597,954, all above U44, but NinjaTrader's index
**$824,406** against $828,138 (−0.45%). G78 asks for higher on all six; G99b for 4 fewer lost. Not adopted. Log:
`verification/noise_v2/g235_combined.txt`.

## G236: shorts at 0.75x and 1.25x, on U44 (registered 2026-11-04, before its run)

**Why:** the index has an upward drift; the bot's shorts and longs take the same size (`short_mult` 1). G195 drew
0.5 / 1.5 only inside combinations. **The variants:** U44 with `short_mult` (a) 0.75 and (b) 1.25. **Run once:** the 526
starts and the full sets in both executions. **Adopt (the better window) on G78's rule** against U44, or G99b's.

**G236 result (run once, 2026-11-04): both rejected.** 0.75x: 28 lost, every net lower (window $56,735, index $812,879);
1.25x: 29 lost, the window $52,044. Full-size shorts stay. Log: `verification/noise_v2/g236_short_mult.txt`.

## G237: no shorts against the uptrend, on U44 (registered 2026-11-04, before its run)

**Why:** U44's fill-ins include shorts against the 50-session uptrend (`trend_small`, from G65), now at up to 3 MNQ
(U43-U44's fill-in sizes); G186 removed them on U40 and lost more accounts. **The variant:** U44 with `trend_small` off.
**Run once:** the 526 starts and the full sets in both executions. **Adopt on G78's rule** against U44, or G99b's.

**G237 result (run once, 2026-11-04): rejected.** 29 lost (U44 28); every net lower (window $54,282, NQ $545,883, index
$757,430 in NinjaTrader's execution). The trend shorts stay. Log: `verification/noise_v2/g237_no_trend_small.txt`.

## G238: an earlier lock alone, on U44 (registered 2026-11-04, before its run)

**The variants:** U44 with `lock_at` (a) 0.3 and (b) 0.4 (0.35 now): the stop moves to the entry once the trade is that
many max losses in profit. **Run once:** the 526 starts and the full sets in both executions. **Adopt (the better window)
on G78's rule** against U44, or G99b's.

**G238 result (run once, 2026-11-04): both rejected.** 0.3: 35 lost (U44 28), window $55,146; 0.4: 44 lost, the index
$774,147. The 0.35 lock stays. Log: `verification/noise_v2/g238_lock_at.txt`.

## G239: the 15-minute grid only once the floor has stopped (registered 2026-11-04, before its run)

**Why, from G223-G224:** the 15-minute grid raised every net (NinjaTrader index +$77k) but lost 100 of 526 fresh accounts.
Here a fresh account keeps U44's half-hour entries: the 15-minute checks are on (`check_step` 15), and the checks
between the half hours (10:15, 10:45, ... 15:15) join U44's 13:00 and 14:30 in `skip_checks`, skipped only until the
floor has stopped (`skip_checks_early`). After that, entries at every 15-minute check. **The variants:** (a) the last
entry at 15:00 (U44's), (b) at 14:30 (G224's). **Run once:** the 526 starts and the full sets in both executions.
**Adopt (the better window) on G78's rule** against U44 (higher nets on all three in both executions, no −$1,000 day, the
floor never touched, no more than 28 lost). The NinjaTrader strategy has only the half-hour grid: a pass is built there,
with parity tests, before it is adopted.

## G240: 1,000 random combinations around U44 (registered 2026-11-04, before its run)

**The ask (the user):** "1000 more diff trials". **The search** (`research/g240_mega_search.py`, seed 240): 1,000
combinations, each moving 1-5 of 34 settings to values near U44's (entries and filters, exits, sizing and budget,
survival, the gap slot and fill-ins); row 0 is U44. **Stage 1:** each on the window, NQ and the index (the chart's
execution). **Screen:** all three nets at least U44's, no −$1,000 day, the floor never touched. **Stage 2:** the 10 best
passing (by the sum of the three nets against U44's) go to NinjaTrader's execution and the 526 starts; **the best window
among those meeting G78's rule** against U44 (higher nets on all three in both executions, no more than 28 lost) is
adopted. With 1,000 tries, some pass by chance; the 526 starts and NinjaTrader's execution are the check.

**G239 result (run once, 2026-11-04): both rejected.** On the 263 starts on the 1st alone: (a) **31** lost, (b) **37** (U44
12; the rule allows 28 of the 526), so the mid-month half can't save them. The window also splits between the
executions: (a) chart **$11,785** against NinjaTrader $70,327; the 15-minute grid's results hang on single fills. The
off-half-hour exits still act early (only the entries were held back). Log: `verification/noise_v2/g239_grid15_locked.txt`.

**G240 progress (2026-11-04, 22:42 UTC):** 196 of 1,000 done; 10 pass the screen so far (the best by the three nets: k44,
window $61,789 / NQ $611,515 / index $897,334). Stage 2 waits for the full 1,000. Partial log:
`verification/noise_v2/g240_mega_search_partial.txt`.

**G240 stage 1 (2026-11-04): 51 of 1,000 pass the screen.** The 10 best (k44, k776, k89, k221, k572, k694, k660, k3,
k365, k911) go to stage 2. Recurring settings among them: the after-loss max loss at 0.95x once grown, the trend over
45 or 75 sessions, the gap trade's break-even at 0.75 or 1.5, a lock from 14:00. Log: `verification/noise_v2/g240_mega_search.txt`.

**G240 result (2026-11-04): none of the 10 passes stage 2.** 526 starts, lost or frozen (U44 28): k221 **26**, k694 30,
k89 32, k3 35, k44 40, k911 42, k572 44, k776 46, k365 52, k660 66. k221, the only one at 28 or fewer, has NinjaTrader's
NQ at $512,806 (U44 $579,739). The screen used the chart's execution, and for the after-loss 0.95x rows NinjaTrader's
NQ fell from about $600,000 to $492,000-513,000: the chart's screen is not a safe filter. Log:
`verification/noise_v2/g240_stage2.txt`.

## G241: 10,000 random combinations around U44, screened in NinjaTrader's execution (registered 2026-11-04, before its run)

**Why, from G240:** the chart's screen let through settings that NinjaTrader's execution doesn't support, and most of the
best lost more accounts. **The search** (`research/g241_nt_search.py`, seed 241, G240's 34 settings): 10,000
combinations; row 0 reproduces U44 in NinjaTrader's execution ($57,475 / $579,739 / $828,138). **Stage 1:** each on the
window, NQ and the index in NinjaTrader's execution; the screen: all three nets above U44's, no −$1,000 day, the floor
never touched. **Stage 2:** the 40 best passing (by the sum of the three nets against U44's) on the 263 starts on the
1st. **Stage 3:** of those with 12 or fewer lost there (U44 12), the 5 with the fewest (ties: the higher window) on the
mid-month starts and the chart's execution. **Adopted:** the best window among those meeting G78's rule against U44
(higher nets on all three in both executions, no −$1,000 day, the floor never touched, no more than 28 of 526 lost).

**G241 progress (2026-11-04, 23:41 UTC):** 112 of 10,000 done in NinjaTrader's execution; 2 pass the screen so far (k74,
k13). Partial log: `verification/noise_v2/g241_nt_search_partial.jsonl`.

**G241 progress (2026-11-05, 00:43 UTC):** the container restarted and stopped the search at 232; restarted, it resumes
from the rows saved.

**G241 progress (2026-11-05, 01:10 UTC):** 392 of 10,000 done, 8 pass the screen. The container is reclaimed while the
session is idle, which stopped the detached run twice; it now runs as a tracked task in two-hour legs, resuming each
time.

**G241 progress (2026-11-05, 01:42 UTC):** 1,400 of 10,000 done, 45 pass the NinjaTrader screen; running steadily as a
tracked task.

**G241 stage 1 (2026-11-05): 264 of 10,000 pass the NinjaTrader screen** (all three nets above U44's, no −$1,000 day, the
floor never touched). The best by the three nets: k4403 (lock plus 2, trend 75, gap trigger 0.65) $62,838 / $634,566 /
$834,077; k356 (gap break-even 1.5, range 0.72, trend 55) $64,049 / $597,872 / $849,153. The 40 best go to stage 2 (263
starts on the 1st). Log: `verification/noise_v2/g241_nt_search.jsonl`.

**G241 stage 2 (2026-11-05):** of the 40, six lose **12** of the 263 starts on the 1st (U44 12), all with the trend over
45 sessions (`trend_n` 45): k1015, k1474, k1063, k1712, k2525, k6649. The 5 with the best NinjaTrader window go to stage 3:
k1015, k1474, k1063, k1712, k2525. Log: `verification/noise_v2/g241_stage2_starts.txt`.

**G241 result (2026-11-05): all five finalists pass G78's rule; k1015 adopted (U45, the best window).** 526 starts lost or
frozen: k1015 **25**, k1063 24, k1712 25, k1474 27, k2525 27 (U44 28). k1015 (`trend_n` 45, `fill_min_room` 2,750,
`fill_qty2_room` 5,000), chart / NinjaTrader: window $59,108 / **$59,167** (U44 $57,446 / $57,475), NQ $602,285 /
$603,956 (U44 $587,643 / $579,739), index $873,722 / $853,557 (U44 $849,992 / $828,138); no −$1,000 day, the floor never
touched. All five share the trend over 45 sessions. With 10,000 tries this is the kind of result that can pass by
chance; it passed the long histories, both executions and the 526 starts. Log: `verification/noise_v2/g241_stage3.txt`.

**U45 (2026-11-05): the trend over 45 sessions, fill-ins from $2,750 and at 2 MNQ from $5,000 (G241).** `TrendSessions`
45 on the 50K's Funded growth (and Custom; 50 in Evaluation and the bigger accounts), `MoreDaysCushion` 2,750,
`MoreDaysQty2Room` 5,000. The win-rate check's tested rate is now 49.7% (the window's, in NinjaTrader's execution; 61.2%
was v3.8's).

**U45 checks (2026-11-05):** the NinjaTrader growth run on the window **$58,609.81**, 756 trades, 49.7% winners, worst
day −$899.24 (`verification/noise_v2/v38g_nt_u45.txt`): identical to the model on 30-minute bars, and on 5-minute bars up
to the 2026-03-09 data hole. 526 starts: 25 lost (about 1 in 21), median net $36,403 (U44 $33,917).

## G242: 10,000 more combinations, around U45 (registered 2026-11-05, before its run)

**The search:** G241's (`research/g241_nt_search.py`, the same 34 settings) with `SEED=242`, around U45 (row 0 is U45:
NinjaTrader $59,167 / $603,956 / $853,557). **Stages and adoption as G241's**, against U45: stage 1 all three NinjaTrader
nets above U45's, no −$1,000 day, the floor never touched; stage 2 the 40 best on the 263 starts on the 1st; stage 3 the
5 with the fewest lost (at most U45's 12 there) on the mid-month starts and the chart's execution; adopted the best window
meeting G78's rule against U45 (no more than 25 of 526 lost).

**U45 checks (2026-11-05):** the full suite, **675 passed**. G242's row 0 reproduces U45 in NinjaTrader's execution
($59,167 / $603,956 / $853,557).

**G242 stage 1 (2026-11-05): 105 of 10,000 pass the NinjaTrader screen against U45.** The best by the three nets: k5922
(range 0.68, target 1.75, early budget $700, lookback 12) $63,966 / $657,515 / $862,072; k3975 $60,505 / $653,597 /
$884,771 (U45 $59,167 / $603,956 / $853,557). The 40 best go to stage 2. Log: `verification/noise_v2/g242_nt_search.jsonl`.

**G242 stage 2 (2026-11-05):** of the 40, three lose **11** of the 263 starts on the 1st (U45 12), all with the gap
trigger at 0.65 and the gap trade to break-even at 1.5x its risk (`gap_go_k` 0.65, `gap_go_be` 1.5): k2079, k8946,
k8599; k4039 / k5623 (the same rule set) lose 12. The five go to stage 3. Log: `verification/noise_v2/g242_stage2_starts.txt`.

**G242 result (2026-11-05): k8946 passes G78's rule; adopted (U46).** 526 starts lost or frozen: k2079 / k8946 / k8599
**23**, k4039 / k5623 26 (U45 25). k2079 and k8599 fail on the chart's NQ ($589,260 / $590,128 against U45's $602,285).
k8946 (`gap_go_k` 0.65, `gap_go_be` 1.5), chart / NinjaTrader: window $61,152 / **$61,255** (U45 $59,108 / $59,167), NQ
$609,486 / $611,194 (U45 $602,285 / $603,956), index $892,868 / $861,886 (U45 $873,722 / $853,557); no −$1,000 day, the
floor never touched. Log: `verification/noise_v2/g242_stage3.txt`.

**U46 (2026-11-05): the gap trade from 0.65x the average gap, its stop to break-even once a bar closes 1.5x its risk in
profit (G242).** `GapTrigger` 0.65 and the new `GapBreakEven` 1.5 (the 50K's Funded growth and Custom). Live, the gap
trade's stop order moves to the real fill plus a tick. The win-rate check's tested rate is 49.3%.

**U46 checks (2026-11-05):** the NinjaTrader growth run on the window **$60,557.54**, 760 trades, 49.3% winners, worst day
−$899.24 (`verification/noise_v2/v38g_nt_u46.txt`): identical to the model on 30-minute bars, and on 5-minute bars up to
the 2026-03-09 data hole. 526 starts: **23 lost (about 1 in 23)**, median net **$39,513** (U45 $36,403); +$3,000 in a
median 145 days; +$50,000 within 21 months in 47.0%. The NinjaTrader tests, 48 passed (a new one for the gap
break-even; three sample-size checks narrowed because the short sample now stays at 1 MNQ on 5-minute bars).

## G243: 10,000 more combinations, around U46 (registered 2026-11-05, before its run)

**The search:** G241's (`research/g241_nt_search.py`, the same 34 settings) with `SEED=243`, around U46 (row 0 is U46:
NinjaTrader $61,255 / $611,194 / $861,886). **Stages and adoption as G241's**, against U46: stage 1 all three NinjaTrader
nets above U46's, no −$1,000 day, the floor never touched; stage 2 the 40 best on the 263 starts on the 1st; stage 3 the
5 with the fewest lost (at most U46's 11 there) on the mid-month starts and the chart's execution; adopted the best window
meeting G78's rule against U46 (chart $61,152 / $609,486 / $892,868; no more than 23 of 526 lost).

**U46 checks (2026-11-05):** the full suite, **677 passed**. G243's row 0 reproduces U46 in NinjaTrader's execution
($61,255 / $611,194 / $861,886).

**Progress (2026-11-05 18:45 UTC):** 7,668 of 10,001 rows screened, 50 pass stage 1 so far (partial log
`verification/noise_v2/g243_nt_search_partial.jsonl`). No stage 2 yet; nothing adopted from G243 so far.

**Progress (2026-11-05 19:45 UTC):** 9,500 of 10,001 rows screened; stage 2 starts by itself when the screen ends.

## G244: 10,000 more combinations, around the version current after G243 (registered 2026-11-05, before its run)

**The search:** G241's (`research/g241_nt_search.py`, the same 34 settings) with `SEED=244`, around the version in the
file when G243 is decided (U46, or G243's adoption if one is made); row 0 must reproduce that version's NinjaTrader
nets exactly or the run is stopped. **Stages and adoption as G241's**, against that version: stage 1 all three
NinjaTrader nets above its own, no −$1,000 day, the floor never touched; stage 2 the 40 best on the 263 starts on the 1st;
stage 3 the 5 with the fewest lost (at most the current version's count there) on the mid-month starts and the chart's
execution; adopted the best window meeting G78's rule against the current version (no more of 526 lost). Run once.

**G243 stage 1 done (2026-11-05 20:00 UTC):** all 10,001 rows (`verification/noise_v2/g243_nt_search.jsonl`); 62 pass
stage 1, the 40 best go to stage 2. Stage 2 in progress (`verification/noise_v2/g243_stage2_partial.txt`).

**G243 stage 2 done:** all 40 on the 263 starts on the 1st (`verification/noise_v2/g243_stage2.txt`; U46 loses 11).
Three lose at most 11: k6546 (10), k7849 (11), k3044 (11); they go to stage 3.

**G243 stage 3 (2026-11-05):** lost of 263 on the 1st + of 263 mid-month; nets NinjaTrader's execution / the chart's
(window / NQ / index); every row no −$1,000 day, the floor never touched.

| | lost (1st + mid) | NinjaTrader nets | chart nets |
|---|---|---|---|
| U46 | 11 + 12 = **23** | $61,255 / $611,194 / $861,886 | $61,152 / $609,486 / $892,868 |
| k6546: fast steps from $9,000, sizing slippage 4 pts, giveback brake 0.45 | 10 + 11 = **21** | $61,661 / $618,986 / $873,759 | $61,661 / $617,427 / $900,190 |
| k3044: range pos 0.72, 4 losers, early budget $650 | 11 + 11 = **22** | $61,375 / $614,476 / $886,483 | $61,506 / $617,195 / $905,391 |
| k7849: take profit 1.9, 3-MNQ fill-ins from $7,000 | 11 + 15 = 26 | $61,427 / $660,447 / $879,269 | $60,396 / $659,431 / $880,589 |

**Decision:** k6546 and k3044 meet G78's rule against U46 (all six nets higher, no more lost); k7849 fails (26 lost,
chart window lower). **Adopted: k6546 (U47)**, the better NinjaTrader window (and fewer lost). Note: its sizing counts 4
points of stop slippage instead of 5, so it trades slightly bigger; the tests' slippage is unchanged, and survival
remains sensitive to real slippage (G222). Logs: `verification/noise_v2/g243k*_chart.txt`, `g243k*_mid.txt`.

**U47 (2026-11-05): G243's k6546.** `SizeSlip` 4 (G170: 5), `GivebackBrake` 0.45 (G99c: 0.5), `FastStepsFrom` 9000
(G210: 8000); all three apply on 5-minute bars only, as before. The win-rate check's tested rate stays 49.3%.

**U47 checks (2026-11-05):** the NinjaTrader tests, 48 passed. The NinjaTrader growth run on the window **$61,096.19**
(U46 $60,557.54), 760 trades, 49.3% winners, profit factor 1.665, closed drawdown $6,106.23, worst day −$899.24
(`verification/noise_v2/v38g_nt_u47.txt`): identical to the model on 30-minute bars, and on 5-minute bars up to the
2026-03-09 data hole (as U46). 526 starts: **21 lost at the floor, 22 lost or frozen** (U46 23 / 23), median net
**$46,561** in 21 months (U46 $39,513); +$3,000 in a median 144 days (within 30 days in 4.2%); +$50,000 within 21 months
in 51.9% (U46 47.0%).

**U47 checks, full suite (2026-11-05):** **677 passed**. G244 runs around U47 (base `u47_J`: U46 plus k6546).

**G244 progress (2026-11-05 21:45 UTC):** running around U47; row 0 reproduces U47 in NinjaTrader's execution
($61,661 / $618,986 / $873,759). Partial log `verification/noise_v2/g244_nt_search_partial.jsonl`.

## G245: support and resistance, breakout and retest (the user's video; registered 2026-11-05, before its run)

**From the video** (TikTok, MNQ 1-minute chart, 6 MNQ): a support (resistance) is where the market turned up (down)
more than once; wait for a close through it, then for the retest back to the level, and enter on the retest; their
trade risked $132 for $150 (11 points for 12.5).

**The rules** (`research/g245_sr_retest.py`, 5-minute RTH bars, the chart we trade): a pivot high (low) is a bar's high
(low) at least (at most) the 3 bars on each side, known 3 bars later; a level is a confirmed pivot with an earlier pivot
of the same kind that session within 0.05% of its price. A close beyond the level from 09:45 is the breakout; within 12
bars, a bar that comes back to the level and closes beyond it again is the retest: enter at its close (09:45-15:30, one
trade at a time, each level once). Stop 11 points and target 12.5 points at 24,500, scaled with the price; stop first
when both are in one bar; out at 16:00. 1 MNQ, $1.24 commission and a tick each way. U47's trades as the day split.

**Pass rule (to build it into the bot as an idle-day add-on, a separate pre-registered test):** on U47's idle days, a
positive net per MNQ on the window, NQ and the index, with NQ and the index up in at least two thirds of their years.
Otherwise rejected. Run once.

**G245 result (2026-11-05): rejected.** Per MNQ after costs (`verification/noise_v2/g245_sr_retest.txt`):

| | trades | net | winners | years up | idle days net (years up) |
|---|---|---|---|---|---|
| window | 455 | −$2,309 | 40.7% | 0 of 2 | −$1,754 (0 of 2) |
| NQ 2015-25 | 3,218 | −$17,698 | 41.2% | 0 of 11 | −$10,590 (0 of 11) |
| index 2011-26 | 4,891 | −$22,593 | 42.6% | 0 of 16 | −$13,949 (0 of 16) |

It loses in every year of every set, on U47's days and on its idle days: with a target only 1.14x the stop it needs
about 47% winners to break even before costs, and the retests win about 41%. The file is unchanged (U47).

## G246: the prior day's high and low, breakout and retest, 2:1 (registered 2026-11-05, before its run)

The user's two YouTube videos (Micah Thomas, "I Taught a Complete Beginner My $10k/Month Trading Strategy" and "How To
Start Day-Trading in 2026") are the same creator's support and resistance strategy; YouTube refuses this server the
audio and captions, so only the titles, descriptions and chapters were read. **G246** tests the levels most traders draw
instead of G245's intraday pivots: the prior RTH session's high and low (`research/g246_prior_day_retest.py`); the
breakout, retest and entry as G245; stop 11 points and target **22 points** at 24,500 (2:1), scaled with the price.
**Pass rule as G245's** (U47's idle days: positive per MNQ on all three sets, NQ and the index up in two thirds of
their years). Run once.

**G246 result (2026-11-05): rejected.** Per MNQ after costs (`verification/noise_v2/g246_prior_day_retest.txt`): window
200 trades −$1,391 (26.0% winners; idle days −$1,117), NQ 1,114 trades −$7,511 (27.8%; idle days up 1 of 11 years),
index 1,666 trades −$10,063 (28.7%; idle days up 0 of 16). A 2:1 target needs about 33% winners before costs; the
retests of the prior day's levels win 26-29%. The file is unchanged (U47).

**G244 speed-up (2026-11-05, at row 2,698):** `WINDOW_FIRST=<U47's window net>` in `research/g241_nt_search.py`: a
combination that can't beat U47 on the window (or has a −$1,000 day or touches the floor there) skips NQ and the index.
Stage 1 needs all three, so the outcome is identical; only 13-16% pass the window, so the screen runs about 5x faster.
Rows that stop early carry only the window's columns.

## The user's firm: Take Profit Trader 50K (2026-11-05)

The user named the firm: **Take Profit Trader, 50K**. Its help center (takeprofittraderhelp.zendesk.com, read
2026-11-05; articles updated Aug-Nov 2026) says:
- **No trading bots or algos** on any account (Universal Trading Policies #1, "Automated trading systems, bots, or
  algorithmic execution tools are not permitted"; PRO rule 1, "All trades must be manually executed by the trader").
  Violations "may result in profit forfeiture, account reset, account closure, or removal from the platform".
- **Maximum position size 60 micros** on the 50K (Rule 2). U47 goes to 75 MNQ on the 5-minute chart.
- **No daily loss limit** in the Test rules (Rules 1-6) or the PRO rules.
- **Drawdown $2,000.** Test: end-of-day trailing (Rule 3). **PRO: intraday trailing, including unrealized gains**, until
  the minimum balance reaches the starting balance ($50,000); the buffer for withdrawals is $52,000. The bot's model is
  end-of-day trailing, so on PRO the first $2,000 of growth is riskier than modelled.
- **PRO / PRO+: flat from one minute before to one minute after FOMC (Wednesdays 14:00), NFP and CPI (08:30).** The bot
  trades from 09:30, so only FOMC applies; on Fed days it may hold a long through 14:00.
- Test only: best day under 50% of the profit (Rule 5), at least 3 trading days. Positions closed by 16:55.

## G247: 60 MNQ at most, the firm's limit (registered 2026-11-05, before its run)

A compliance change, adopted whatever its numbers: `size_up_to` 60 instead of 75 (U47 otherwise). Measured once on the
three sets in both executions and the 526 starts (`run247.sh`), to report its cost.

**G247 result (2026-11-05): adopted as U48 (compliance).** 60 MNQ at most instead of 75; chart / NinjaTrader nets
(window / NQ / index) $61,612 / $630,505 / $893,328 and $61,612 / $632,038 / $875,038 (U47 $61,661 / $617,427 /
$900,190 and $61,661 / $618,986 / $873,759); no −$1,000 day, the floor never touched. 526 starts: 21 lost at the floor,
22 lost or frozen (as U47), median net **$47,023** (U47 $46,561), +$50,000 within 21 months in 52.1%. Logs
`verification/noise_v2/g247_{c,n,s,m}.txt`. G244 keeps U47 (75) as its base; anything it adopts is re-checked at 60.

## G248: the 526 starts under the PRO account's intraday drawdown (registered 2026-11-05, before its run)

Take Profit Trader's PRO drawdown trails **intraday from the highest balance including open profit** and stops at the
starting balance. `research/g248_pro_intraday.py` reruns U48 on the 526 starts (the bot unchanged: it sizes from the
end-of-day floor) and marks every open trade at each bar's high and low; an account is lost when its marked balance
reaches the floor. Two bounds for the order inside a bar: "worst order" (the bar's best mark raises the floor before
its worst mark) and "best order" (the worst mark first). A measurement, no pass rule: if PRO loses clearly more than
the end-of-day count (22), the bot needs a PRO mode that sizes from the intraday floor before it goes on a PRO account.

**G248 result (2026-11-05):** under the PRO account's intraday trailing drawdown, U48 as it is loses **55 of 526**
(18 + 13 on NQ / the index on the 1st, 11 + 13 mid-month; the same in both bar orders) against **21** at the floor
under the Test account's end-of-day rule; 41 starts lost only under the PRO rule. The nets are identical (the bot is
unchanged). **On a PRO account the bot must size from the intraday floor** (G249). Logs
`verification/noise_v2/g248_pro_u48*.{txt,csv}`.

## G249: a PRO mode, the floor from the intraday peak and a guard above it (registered 2026-11-05, before its run)

**The rule** (new research settings `trail_intraday`, `pro_guard` in `mnqbot/noise.py`): the trailing peak follows the
marked balance intraday (each bar's favourable extreme of the open trades, from the next bar), so the floor, the
sizing and the floor's stop all use TPT's PRO floor; and every open trade's stop is tightened to the price where the
balance would be **$100 above the floor** (after commission), as a resting stop. U48 otherwise.
**Measured once:** the 526 starts under the PRO rule (G248's check, worst order) and the nets on the three sets in both
executions. **Adopt as the PRO mode** (a separate mode; the Test account keeps U48) if the PRO losses fall to at most
27 of 526 (half of U48's 55), whatever the nets; then built into the C# file with parity tests.

**G249 result (2026-11-05): rejected as registered.** Under the PRO rule the 526 starts lose **38** (12 + 9 on the 1st,
11 + 6 mid-month; U48 55), above the pass line of 27, and the median net falls to **$32,772** (U48 $47,023): the guard
closes the early trades sooner and the higher floor shrinks the sizes. The nets on the long sets hardly move (the floor
stops early there): chart $61,612 / $632,164 / $893,356, NinjaTrader $61,612 / $622,740 / $854,239. Logs
`verification/noise_v2/g249_*`, `g248_pro_g249_*.csv`. The PRO account's extra losses all come before its floor
stops (the first $2,000 of profit); after that the floor is fixed at $50,000 and the two rules are the same.

## G250: Take Profit Trader's 50K Test in one week (registered 2026-11-05, before its run)

The user is on TPT's 50K Test and has about a week to pass it into PRO. **Measured** (`research/g250_test_week.py`,
no adoption rule): a fresh Test every Monday (NQ 2015-25, the index 2011-26), 5 sessions, under TPT's rules as its help
center states them (+$3,000 with the best day under half the profit and 3+ trading days; the $2,000 end-of-day trailing
floor, stopping at the start, failing the Test when the marked balance touches it; no daily loss limit; 60 MNQ at most).
U48 with every trade at `sprint_qty` contracts (0 = U48's own sizing; 5, 10, 15, 20), cut to the room above the floor,
and no day budget short of the floor. Reported: passed, failed and still open after the week, per sprint size.

**G250 result (2026-11-05): the Test can't be passed in a week.** 1,339 weekly starts (`verification/noise_v2/g250_test_week.{txt,csv}`;
a 30-MNQ row was added to the registered list as an extra measurement):

| every trade at | passed in the week | failed in the week | still open |
|---|---|---|---|
| U48's own size | 0.0% | 0.0% | 100% |
| 5 MNQ | 0.9% | 7.1% | 92% |
| 10 MNQ | 0.9% | 20.6% | 78% |
| 15 MNQ | 0.6% | 26.7% | 73% |
| 20 MNQ | 0.6% | 29.8% | 70% |
| 30 MNQ | 0.4% | 32.3% | 67% |

(2019 onward: at most 1.1% passed.) The bot trades about one day in three early on, and the consistency rule needs
+$3,000 spread over at least three winning days with none above half the profit; a bigger size only fails more Tests.
TPT's Test has no time limit (Rule 5: "You may take as long as you want"); the bot's median time to +$3,000 is about
144 days (G247's 526 starts).

**U48 checks (2026-11-05):** the full suite, 677 passed; the NinjaTrader tests passed; the NinjaTrader growth run on the window **$61,047.16**, 760
trades, 49.3% winners, most contracts 60 (`verification/noise_v2/v38g_nt_u48.txt`), parity as U47.

## G251: the Test in two weeks (registered 2026-11-05, before its run)

The user asked for two weeks. G250's measurement with **10 sessions**, `sprint_qty` 0 / 5 / 10 / 15 / 20, each with and
without a **day stop** (`day_stop_profit` $1,400: no new entries once the day is up $1,400, so no day reaches half of
the $3,000; the consistency rule). Reported as G250. No adoption rule: the user picks with the odds in hand.

## A firm that allows the bot: Lucid Trading's LucidDirect 50K (read 2026-11-05)

From Lucid's help center (support.lucidtrading.com): **"Automated trading systems and trade copiers are permitted"**
(Other Trading Activities); **LucidDirect is straight-to-funded, no evaluation**; the 50K: **$2,000 end-of-day trailing
drawdown, locking at $50,100 once the account closes above $52,100**; a $1,200 daily loss limit that is a **soft breach**
(trading stops until the next session, the account is kept), then 60% of the highest end-of-day profit; **40 micros at
most**; positions closed by 16:45; news trading allowed; HFT, microscalping and hedging prohibited. Payouts: 90%, the
first after $3,000 of profit with the largest day at most 20% of the cycle's profit, $2,000 at most each for the first
three.

## G252: U48 on LucidDirect's 50K rules (registered 2026-11-05, before its run)

U48 with `size_up_to` 40 and the floor stopping at the start plus $100 (`trail_cap` 100). Measured once (`run252.sh`):
the three sets in both executions and the 526 starts (their "lost" check counts the floor at the start, $100 lower than
Lucid's). Adopted as a **LucidDirect preset** (a mode, the 50K Funded growth otherwise) if no −$1,000 day, the floor
never touched, and no more than 26 of 526 lost or frozen (U48's 22 plus a margin for the smaller cap).

**G252: cancelled before its result (2026-11-05), at the user's request** ("remove that lucid stuff"); the LucidDirect
mode was taken out of the file again (revert of 525c230). The bot trades on any account added in NinjaTrader.

**G251 result (2026-11-06): no setting passes the Test in two weeks with any regularity.** 1,338 two-week starts
(`verification/noise_v2/g251_test_2weeks.txt`, `g251_test_10sessions.csv`), NQ / the index:

| every trade at | day stop | passed in 2 weeks | failed in 2 weeks |
|---|---|---|---|
| U48's own size | none / $1,400 | 0.2-0.4% | 0.0-0.1% |
| 5 MNQ | none | 3.9% / 3.5% | 15.2% / 13.9% |
| 5 MNQ | $1,400 | **4.9% / 3.9%** | 14.8% / 14.0% |
| 10 MNQ | $1,400 | 4.3% / 3.9% | 33.6% / 32.7% |
| 15 MNQ | $1,400 | 3.6% / 2.9% | 40.5% / 39.8% |
| 20 MNQ | $1,400 | 3.4% / 2.4% | 42.0% / 40.6% |

The best is 5 MNQ with the day stop: about 1 pass in 20-25 two-week tries, against about 1 failed Test in 7. Bigger
sizes fail far more often and pass no more often.

## G253: a search for passing the Test within two weeks (registered 2026-11-06, before its run)

The user asked for searches aimed at their target. `research/g253_test_search.py`, G251's measure (10 sessions, TPT's
Test rules): **stage 1**, 200 random combinations of the sprint size (3-8 MNQ), the day stop ($800-1,400) and 11
entry/exit settings, on the index's Monday starts 2011-2018 (development); **stage 2**, the 10 with the most passes
(failures at most 15%) on NQ 2015-25 and the index 2019-26 (unseen). **A setting is offered to the user** if on stage 2
it passes more than G251's best (4.9% NQ / 3.9% index; overall about 4.5%) with failures at most 15%, stated with its
odds. Run once. (G244's stage 2 is paused to give it the processors; it resumes from its saved rows.)

**G253 result (2026-11-06): k61 offered and built in (U49).** Stage 1 (index 2011-18, 405 two-week starts each): the
best ten passed 8.4-10.6% with 9.6-14.6% failed. Stage 2, on unseen weeks (NQ 2015-25 and the index 2019-26, 933
starts): k111 10.3% passed / 13.6% failed, k175 10.1% / 13.2%, k20 10.0% / 15.3%, **k61 9.3% / 9.5%**, k119 9.1% /
14.5% (G251's best: about 4.5% / 14.5%). With the user's rule (don't lose the account) the pick is **k61**, the fewest
failures for nearly the most passes: 4 MNQ on every trade for the first 10 sessions until +$3,000, no new entries once
the day is up $1,200, the noise area over 16 sessions with entries at 0.8x it, the top 70% of the day's range, at most
2 losers a day, a 60-minute time stop, take profit 1.0, lock at 0.25, no trend or big-day filter, a calm filter of 0.8,
no skipped checks, and a $2,000 day budget (the floor's room binds first). In two weeks about 81% of Tests are still
open (neither passed nor failed). Logs `verification/noise_v2/g253_*`.

**U49 (2026-11-06): Mode "Test sprint" (k61), the default.** Full suite: **678 passed**. New settings `NoiseSessions` (14), `EntryWidth` (1.0),
`DayProfitStop` (0) in `MnqNoiseV38.cs` (the engine's `EntryK`, `DayStopProfit`, `Lookback`), a 10-session sprint in
this mode. "Funded growth" is U48 unchanged. NinjaTrader tests: **49 passed** (a new parity test, `test_v38_test_sprint`:
the mode trade for trade against the model, with its 4-MNQ sprint trades).

## G254: G253 again, narrower, around its best (registered 2026-11-06, before its run)

The user wants the Test passed within two weeks. `research/g254_test_search.py`: G253's two stages and measure, 200 new
combinations (seed 254) from a narrower space around k61 / k111 / k175 (sprint 3-6 MNQ, day stop $1,000-1,450, the
noise area 12-20 sessions, entries at 0.7-1.0x, range position 0.6-0.75, calm 0-0.9, take profit 0.75-1.5, lock
0.2-0.33, 0-3 losers, time stop 30-60 or none, big-day filter off or 1.5; no trend filter, no skipped checks).
**Replaces U49's k61 as the Test sprint** only if on stage 2 (unseen weeks) it fails at most k61's 9.5% and passes more
than k61's 9.3%. Run once.

**G254 result (2026-11-06): no replacement; U49's k61 stays.** Stage 2 (933 unseen two-week starts): k85 12.0% passed
/ 19.8% failed, k7 11.7% / 17.6%, k116 10.9% / 16.7%, k153 10.8% / 16.0%, k122 9.8% / 13.7%; none passed more than
9.3% while failing at most 9.5% (`verification/noise_v2/g254_test_search.txt`, `g254_stage*.csv`). Across G251-G254 the
two-week pass rate tops out near 10-12%, and every step above k61's 9.3% costs failures (17-20% at 11.7-12.0%).

## G255: the two-week Test search, 600 combinations, five more settings (registered 2026-11-06, before its run)

`research/g255_test_search.py`: G253's two stages and measure, 600 combinations (seed 255), G254's space (sprint 3-5)
plus five settings the NinjaTrader file already has: the stop buffer (0.12-0.3 sigma), the lock's points (1-5), the
squeeze filter (0-20), the last entry (15:00 / 15:30) and the gap trigger (0.5-0.8). **Replaces k61 as the Test sprint**
only if on stage 2 (unseen weeks) it passes more than 9.3% and fails at most 9.5%. Run once. (G244 paused again.)

**G255 progress (2026-11-06 03:45 UTC):** 71 of 600 combinations done on stage 1; the best so far with failures at most
10%: 10.1% passed / 7.2% failed (k20), 8.4% / 5.2% (k36). Stage 2 decides.

**G255 progress (2026-11-06 04:45 UTC):** stage 1 continuing (results saved row by row); stage 2 decides.

**G255 result (2026-11-06): no replacement as registered.** Stage 2 (933 unseen starts), the ten by stage-1 passes:
k78 13.6% passed / 18.5% failed, k342 13.2% / 19.0%, k334 12.8% / 19.4%, k91 11.6% / 18.0%, k242 11.1% / 14.6%, k514
10.7% / 12.9%, k299 10.7% / 14.1%; none failed at most 9.5% while passing more than 9.3%
(`verification/noise_v2/g255_test_search.txt`, `g255_stage*.csv`).

## G256: G255's lowest-failure combinations on unseen weeks (registered 2026-11-06, before its run)

G255's stage 2 took the ten with the most stage-1 passes; five others had far fewer stage-1 failures: k317 11.6% /
6.4%, k484 10.6% / 6.9%, k20 10.1% / 7.2%, k225 10.4% / 7.4%, k153 10.6% / 7.9% (passed at least 10%, failed at most
10%, the five lowest failures). `research/g256_low_fail.py` runs these five on G255's stage-2 weeks. **Replaces k61**
only if one passes more than 9.3% and fails at most 9.5% there (the best by passes among those that do). Run once.

**G256 result (2026-11-06): k317 replaces k61 (U50).** On G255's stage-2 weeks (933 unseen starts): **k317 10.0% passed
/ 9.1% failed** (k61 9.3% / 9.5%), k484 12.0% / 10.6%, k153 9.9% / 11.3%, k20 10.6% / 11.9%, k225 10.9% / 12.0%
(`verification/noise_v2/g256_low_fail.txt`, `g256_stage2.csv`). k317: 4 MNQ for the first 10 sessions until +$3,000, a
$1,100 day profit stop, the noise area over 18 sessions with entries at 0.7x it, the top 70% of the range, 3 losers a
day, a 30-minute time stop, take profit 0.75, lock at 0.2 (+2.5 points), calm 0.7, no trend / big-day / squeeze filter,
entries to 15:30, the gap trade from 0.5x, stop buffer 0.24.

**U50 (2026-11-06): the Test sprint mode is k317.** Full suite: **678 passed**. NinjaTrader tests 49 passed (`test_v38_test_sprint` now k317, trade
for trade against the model).

## G257: the two-week Test search close to k317 (registered 2026-11-06, before its run)

`research/g257_test_search.py`: G255's two stages and measure, 300 combinations (seed 257) in a narrow space around
k317 (sprint 3-5, day stop $1,000-1,200, noise 16-22 sessions, entries 0.6-0.75x, range 0.65-0.75, calm 0.6-0.8, take
profit 0.6-0.9, lock 0.15-0.25 / +1.5-3.5 points, 2-4 losers, time stop 20-45, stop buffer 0.18-0.3, squeeze 0 / 10, gap
0.4-0.6; entries to 15:30, no trend / big-day filter). **Replaces k317** only if on stage 2 it passes more than 10.0%
and fails at most 9.1%. Run once.

**G257 progress (2026-11-06 06:45 UTC):** stage 1 running (results saved row by row).

**G257 progress (2026-11-06 07:45 UTC):** stage 1 past halfway; stage 2 decides.

**G257 result (2026-11-06): no replacement as registered.** Stage 2 (933 unseen starts), the ten by stage-1 passes:
k239 13.1% / 17.8%, k285 13.0% / 15.2%, k115 12.5% / 14.9%, k46 12.0% / 17.7%, k188 11.9% / 14.7%, k140 11.7% / 12.8%,
k49 11.1% / 13.9%; none failed at most 9.1% while passing more than 10.0% (`verification/noise_v2/g257_*`).

## G258: G257's lowest-failure combinations on unseen weeks (registered 2026-11-06, before its run)

As G256 for G255: G257's stage-1 combinations with at least 10% passed and at most 10% failed (four: k55 10.1% / 7.4%,
k5 10.9% / 7.7%, k183 10.1% / 7.9%, k192 10.4% / 8.4%) on the stage-2 weeks (`research/g258_low_fail.py`). **Replaces
k317** only if one passes more than 10.0% and fails at most 9.1% there. Run once.

**G258 result (2026-11-06): no replacement; k317 stays.** On the stage-2 weeks: k5 9.8% / 10.1%, k55 10.7% / 11.1%,
k192 9.2% / 12.6%, k183 7.8% / 13.0% (`verification/noise_v2/g258_*`). Across G253-G258 (1,300 combinations, the best
of each confirmed on 933 unseen two-week starts), nothing beats k317's 10.0% passed with at most 9.1% failed; passes
above about 11% come only with failures of 13-19%.

## G259: the Test sprint with entry checks every 15 or 10 minutes (registered 2026-11-06, before its run)

k317 as it is, with the entry checks every 15 or 10 minutes (`check_step`) instead of every 30 (more chances in ten
sessions). `research/g259_checks.py`, G253's measure on its development and unseen weeks. **Replaces k317** (and is
built into the NinjaTrader file, which has the 30-minute grid only today) if on the unseen weeks it passes more than
10.0% and fails at most 9.1%. Run once.

**G259 result (2026-11-06): rejected.** Unseen weeks: every 15 minutes 10.4% passed / 14.9% failed, every 10 minutes
8.6% / 15.1%, k317 (30 minutes) 10.0% / 9.1% (development: 9.4% / 7.9%, 10.4% / 11.9%, 11.6% / 6.4%;
`verification/noise_v2/g259_checks.txt`). The extra checks add weaker breakouts: about as many passes, far more
failures. k317 stays.

**G244 result (2026-11-06): rejected.** Stage 1: 113 of 10,000 beat U47 in NinjaTrader's execution; stage 2 (the 40 best
on the 1st's 263 starts): three at U47's 10 lost (k150, k2589, k8673). Stage 3: each loses 15 mid-month (10 + 15 = 25
of 526 against U47's 21), and k150 / k2589's chart window is lower ($60,544 against $61,661). Funded growth stays U48.
Logs `verification/noise_v2/g244_*`.

## G260: the Test sprint with a trailing stop or half off at 1R (registered 2026-11-06, before its run)

k317 with one exit change each: a trailing stop 10 / 20 / 40 points behind the best price (`trail_points`), half the
position off at 1R (`partial_at` 1.0, from the bar after the fill), or the runner keeping half the target once locked
(`runner_lock` 0.5). `research/g260_exits.py`, G253's measure on its development and unseen weeks. **Replaces k317**
(built into the NinjaTrader file with parity tests) if on the unseen weeks it passes more than 10.0% and fails at most
9.1%. Run once.

**G260 result (2026-11-06): rejected.** Unseen weeks (passed / failed): k317 10.0% / 9.1%; trail 10 points 9.6% / 9.0%,
20 points 9.1% / 8.7%, 40 points 8.9% / 9.0%; half off at 1R 8.5% / 9.5%; runner lock 0.5 identical to k317 (it never
binds with take profit 0.75) (`verification/noise_v2/g260_exits.txt`). The trailing stops fail a little less but pass
less; none passes more than 10.0%. k317 stays.

## G261: the two-week Test search, 600 combinations with exit timing (registered 2026-11-06, before its run)

`research/g261_test_search.py`: G255's stages and measure, 600 combinations (seed 261), G255's space plus a trailing
stop (off / 20 / 40 points), a time lock (off / 30 / 60 minutes) and a late-day lock (off / 14:30 / 15:00). **Replaces
k317** only if on stage 2 it passes more than 10.0% and fails at most 9.1%; as G256, the five lowest-failure stage-1
combinations (at least 10% passed, at most 10% failed) also go to stage 2 under the same rule. Run once.

**G261 progress (2026-11-06 09:45 UTC):** stage 1 running (results saved row by row).

**G261 progress (2026-11-06 10:50 UTC):** 168,032 of 243,000 stage-1 rows; resumed after its task's time limit.

**G261 result, main stage 2 (2026-11-06): no replacement.** The ten by stage-1 passes on 933 unseen starts: k315 13.4% /
17.4%, k339 13.4% / 16.2%, k154 13.3% / 17.8%, k405 13.2% / 17.7%, k140 13.1% / 14.8%, k564 11.6% / 13.9%; none at most
9.1% failed (`verification/noise_v2/g261_*`). Its registered low-failure check runs next (`research/g261b_low_fail.py`):
k250 10.6% / 6.9%, k88 10.1% / 7.2%, k178 10.6% / 7.7%, k103 10.1% / 8.6%, k290 10.9% / 8.9% on stage 1.

**G261 low-failure check (2026-11-06): no replacement; k317 stays.** On the 933 unseen starts: k250 9.5% / 8.9%, k178
10.8% / 9.4%, k88 6.6% / 10.2%, k103 9.8% / 10.8%, k290 9.1% / 14.4% (`verification/noise_v2/g261b_*`). k178 passes
more than k317 but fails 9.4% against 9.1%; k250 fails less but passes less. Across G253-G261 (1,900 combinations)
k317 remains the best two-week balance.

## G262: 10,000 more combinations around U48's Funded growth (registered 2026-11-06, before its run)

G241's search and stages (`research/g241_nt_search.py`, the window first) with `SEED=262` around U48 (the 60-MNQ cap;
row 0 must reproduce U48 in NinjaTrader's execution: $61,612 / $632,038 / $875,038). Stage 2 the 40 best on the 263
starts on the 1st; stage 3 the 5 with the fewest lost (at most U48's 10 there) on the mid-month starts and the chart's
execution. **Adopted into Funded growth** if G78's rule holds against U48 (chart $61,612 / $630,505 / $893,328; at most
22 of 526 lost or frozen; no −$1,000 day; the floor never touched). The Test sprint mode is not affected. Run once.

**G262 progress (2026-11-06 12:45 UTC):** row 0 reproduces U48 in NinjaTrader's execution ($61,612 / $632,038 /
$875,038); partial log `verification/noise_v2/g262_nt_search_partial.jsonl`.

**G262 result (2026-11-06): rejected.** Stage 1: 130 of 10,000 beat U48 in NinjaTrader's execution on all three sets;
stage 2: three at U48's 10 lost on the 1st (k5856, k3547, k3652). Stage 3 (mid-month lost; chart window / NQ / index):
k5856 13, $61,433 / $667,326 / $892,677; k3547 13, $60,792 / $667,152 / $892,244; k3652 13, $63,023 / $650,724 /
$892,522. Each loses more than U48 at the floor (k5856 9 + 13 = 22, the others 10 + 13 = 23, against U48's 21) and each misses one chart net (U48 $61,612 /
$630,505 / $893,328). Funded growth stays U48. Logs `verification/noise_v2/g262_*`.

## G263: G262 again with SEED=263 (registered 2026-11-06, before its run)

G262's search, stages and adoption rule against U48, with `SEED=263` (10,000 new combinations). Run once.

**G263 progress (2026-11-06 13:45 UTC):** partial logs `verification/noise_v2/g263_*_partial.*`.

**G263 result (2026-11-06): rejected, a near miss.** Stage 1: 119 of 10,000 beat U48 in NinjaTrader's execution;
stage 2: one at or under U48's 10 lost on the 1st, **k7885** (time lock 45 minutes, range position 0.68, fast steps
$600, fill-ins from $2,250, lock +2 points): 9 on the 1st, 11 mid-month, **20 of 526 lost at the floor, 21 lost or
frozen** (U48 21 / 22). NinjaTrader nets $61,736 / $659,997 / $877,877 (U48 $61,612 / $632,038 / $875,038), all
higher; the chart's $61,455 / $680,661 / $902,204 (U48 $61,612 / $630,505 / $893,328): **the window $157 lower**, so
G78's rule fails, and G99b's needs 4 fewer lost. Not adopted. (The first stage-2 run wrote nothing: the chain script
called G262's finished stage-2 script by name; stage 2 was rerun for G263's own 40.) Logs `verification/noise_v2/g263_*`.

## G264: G262 again with SEED=264 (registered 2026-11-06, before its run)

G262's search, stages and adoption rule against U48, with `SEED=264`. Run once.

**G264 progress (2026-11-06 15:45 UTC):** screening (partial log `verification/noise_v2/g264_nt_search_partial.jsonl`).

**G264 result (2026-11-06): rejected.** Stage 1: 108 of 10,000 beat U48 in NinjaTrader's execution; stage 2: two at or
under U48's 10 lost on the 1st (k2834, k372). Stage 3: each loses 13 mid-month (more than U48's 21 in all) and misses a
chart net: k2834's window $61,187, k372's index $892,522 (U48 $61,612 / $893,328; k372 repeats G262's k3652 exactly).
Funded growth stays U48. Logs `verification/noise_v2/g264_*`.

## G265: G262 again with SEED=265 (registered 2026-11-06, before its run)

G262's search, stages and adoption rule against U48, with `SEED=265`. Run once.

**G265 result (2026-11-06): rejected; the seed series stops here.** Stage 1: 130 of 10,000 beat U48 in NinjaTrader's
execution; stage 2's two picks (k3345, k8649) are the same trading as G262's k3652 and G264's k372 (lock +2 points, the
drive fill-in at 0.7x): 10 + 13 = 23 of 526 lost (U48 21) and the chart's index $892,522 (U48 $893,328). Four seeds
(G262-G265, 40,000 combinations) around U48 found only that candidate and G263's near miss k7885; the random search
around U48 has run dry. Funded growth stays U48. Logs `verification/noise_v2/g265_*`.

## G266: the Test sprint without Mondays and/or Fridays (registered 2026-11-06, before its run)

k317 with no new trades on Mondays, on Fridays, or on both (the ten sessions still count those days).
`research/g266_weekdays.py`, G253's measure on its development and unseen weeks. **Replaces k317** (with a weekday
setting in the NinjaTrader file and a parity test) if on the unseen weeks it passes more than 10.0% and fails at most
9.1%. Run once.

**G266 result (2026-11-06): rejected.** Unseen weeks (passed / failed): k317 10.0% / 9.1%; no Mondays 8.4% / 6.9%; no
Fridays 6.6% / 7.9%; neither 4.4% / 5.1% (development: 11.6% / 6.4%, 5.9% / 6.4%, 6.2% / 5.9%, 2.7% / 3.5%;
`verification/noise_v2/g266_weekdays.txt`). Fewer trading days cut the passes more than the failures. k317 stays.

## G267: the Test sprint with a day loss budget (registered 2026-11-06, before its run)

k317 sizes each trade to $2,000 of room (the floor binds first); here the day's loss budget is $600, $800 or $1,000
instead (`daily_loss_limit`: trades sized to what is left of it, no new trade once used). `research/g267_day_budget.py`,
G253's measure on its development and unseen weeks. **Replaces k317** if on the unseen weeks it passes more than 10.0%
and fails at most 9.1%. Run once.

**G267 result (2026-11-06): rejected.** Unseen weeks (passed / failed): k317 10.0% / 9.1%; day budget $1,000 9.0% /
9.5%; $800 8.7% / 7.4%; $600 6.9% / 4.6% (`verification/noise_v2/g267_day_budget.txt`). A tighter day budget fails less
but passes less in the same proportion; none passes more than 10.0%. k317 stays.

## G268: the Test sprint without the gap trade, or longs only (registered 2026-11-06, before its run)

k317 without the 09:35 gap trade (`gap_go` off), with longs only (`short_mult` 0), or both.
`research/g268_sides.py`, G253's measure on its development and unseen weeks. **Replaces k317** if on the unseen weeks
it passes more than 10.0% and fails at most 9.1%. Run once.

**G268 result (2026-11-06): rejected.** Unseen weeks (passed / failed): k317 10.0% / 9.1%; no gap trade 8.7% / 7.3%;
longs only 4.1% / 5.9%; both 1.3% / 3.5% (`verification/noise_v2/g268_sides.txt`). The shorts and the gap trade carry a
large share of the passes. k317 stays.

## G269: the Test sprint keeps its size past +$3,000 (registered 2026-11-06, before its run)

k317 drops to U48's sizing at +$3,000, but the Test also needs the best day under half the profit, which can take more
than $3,000; here the 4 MNQ stay until +$3,500, +$4,000 or +$5,000 (`sprint_target`). `research/g269_sprint_target.py`,
G253's measure on its development and unseen weeks. **Replaces k317** if on the unseen weeks it passes more than 10.0%
and fails at most 9.1%. Run once.

**G269 result (2026-11-06): adopted (U51).** Unseen weeks (passed / failed): k317 10.0% / 9.1%; to +$3,500 10.7% /
9.1%; to +$4,000 11.4% / 9.1%; **to +$5,000 11.5% / 9.1%** (development 11.6-11.9% / 6.4-6.7%;
`verification/noise_v2/g269_sprint_target.txt`). The 4 MNQ kept past $3,000 add passes (the consistency rule's extra
profit comes sooner) and no failures: the floor has stopped by then.

**U51 (2026-11-06): the Test sprint keeps its 4 MNQ to +$5,000.** Full suite: **678 passed**. The engine's `SprintTarget` 5000 in "Test sprint"
mode (3000 elsewhere). NinjaTrader tests 49 passed (`test_v38_test_sprint` with the +$5,000 target, trade for trade).

## G270: U51's Test sprint, bigger once the floor has stopped (registered 2026-11-06, before its run)

New research setting `sprint_qty_locked`: once the trailing floor has stopped at the start (+$2,000 at an end of day),
the sprint's trades take this many MNQ instead of 4 (still cut to the day's and the floor's room). Variants: 5, 6, 8
MNQ, on U51 (sprint to +$5,000). `research/g270_sprint_locked.py`, G253's measure. **Replaces U51's Test sprint** if on
the unseen weeks it passes more than 11.5% and fails at most 9.1%. Run once.

**G270 result (2026-11-06): rejected.** Unseen weeks (passed / failed): U51 11.5% / 9.1%; 5 MNQ once locked 11.5% /
9.9%; 6 MNQ 10.9% / 10.1%; 8 MNQ 10.6% / 10.5% (`verification/noise_v2/g270_sprint_locked.txt`). Bigger trades after
the floor stops add failures (losses back to the stopped floor) and no passes. U51 stays; the research setting
`sprint_qty_locked` stays in the model at 0 (off).

## G271: U51's Test sprint with a higher day profit stop (registered 2026-11-07, before its run)

U51 stops new entries once the day is up $1,100 (k317's, chosen for a $3,000 target); with the sprint now running to
+$5,000, a day up to $1,300 / $1,500 / $2,000 may still keep the best day under half the profit. `research/g271_day_stop.py`,
G253's measure. **Replaces U51's day stop** if on the unseen weeks it passes more than 11.5% and fails at most 9.1%.
Run once.

**G271 result (2026-11-07): rejected.** Unseen weeks (passed / failed): U51 ($1,100) 11.5% / 9.1%; $1,300 9.6% / 9.0%;
$1,500 8.7% / 9.1%; $2,000 6.8% / 9.2% (`verification/noise_v2/g271_day_stop.txt`). A bigger day makes the
consistency rule harder (the best day must stay under half the profit), so passes fall. U51 stays.

## G272: U51's Test sprint with a lower day stop or another size (registered 2026-11-07, before its run)

U51 (4 MNQ to +$5,000, day stop $1,100) against a day stop of $900 or $1,000, and a sprint of 3 or 5 MNQ.
`research/g272_sprint_grid.py`, G253's measure. **Replaces U51's setting** if on the unseen weeks it passes more than
11.5% and fails at most 9.1%. Run once.

**G272 result (2026-11-07): rejected.** Unseen weeks (passed / failed): U51 11.5% / 9.1%; day stop $1,000 12.2% / 9.6%;
$900 12.4% / 9.5%; 3 MNQ 7.0% / 4.1%; 5 MNQ 14.3% / 17.3% (`verification/noise_v2/g272_sprint_grid.txt`). The lower
day stops pass a little more but fail more (9.5-9.6% against 9.1%); 5 MNQ nearly doubles the failures. U51 stays.

## G273: U51's Test sprint with the gap trade at another size (registered 2026-11-07, before its run)

New research setting `sprint_gap_qty`: during the sprint the 09:35 gap trade takes this many MNQ instead of the
sprint's 4 (still cut to the room). Variants 2, 6, 8. `research/g273_sprint_gap.py`, G253's measure. **Replaces U51's
gap size** if on the unseen weeks it passes more than 11.5% and fails at most 9.1%. Run once.

**G273 result (2026-11-07): adopted (U52).** Unseen weeks (passed / failed): U51 (gap at 4) 11.5% / 9.1%; **gap at 2
12.1% / 8.5%**; gap at 6 10.6% / 14.1%; gap at 8 10.9% / 17.7% (development: 11.9% / 6.7%, 10.9% / 6.2%, 11.1% /
12.3%, 11.1% / 15.8%; `verification/noise_v2/g273_sprint_gap.txt`). On the development weeks gap-at-2 passed a little
less (10.9% against 11.9%) and failed less; on the unseen weeks, the pre-registered test, it passes more and fails less.

**U52 (2026-11-07): the Test sprint's gap trade at 2 MNQ.** Full suite: **678 passed**. The engine's new `SprintGapQty` (2 in "Test sprint" mode, 0
= the sprint's size elsewhere); the model's `sprint_gap_qty`. NinjaTrader tests 49 passed (`test_v38_test_sprint` with
it, trade for trade).

## G274: U52's Test sprint with another gap trigger (registered 2026-11-07, before its run)

U52 (k317's gap trade from 0.5x the average gap, at 2 MNQ) with the trigger at 0.35x, 0.65x or 0.8x (`gap_go_k`).
`research/g274_gap_trigger.py`, G253's measure. **Replaces U52's trigger** if on the unseen weeks it passes more than
12.1% and fails at most 8.5%. Run once.

**G274 result (2026-11-07): rejected.** Unseen weeks (passed / failed): U52 (0.5) 12.1% / 8.5%; 0.35 12.3% / 8.6%; 0.65
12.1% / 8.8%; 0.8 11.7% / 8.8% (`verification/noise_v2/g274_gap_trigger.txt`). Within a few tenths of a point; none
passes more while failing at most 8.5%. U52 stays.

## G275: U52's Test sprint with another gap break-even (registered 2026-11-07, before its run)

U52 moves the gap trade's stop to break-even once a bar closes 1.5x its risk in profit (G242); here at 0.75x, 1.0x, or
never (`gap_go_be`). `research/g275_gap_be.py`, G253's measure. **Replaces U52's setting** if on the unseen weeks it
passes more than 12.1% and fails at most 8.5%. Run once.

**G275 result (2026-11-07): adopted by its rule (U53), by the smallest margin.** Unseen weeks (passed / failed): U52
(1.5x) 12.1% / 8.5%; 0.75x 12.0% / 8.4%; 1.0x 12.0% / 8.4%; **no break-even 12.2% / 8.4%** (development: 10.9% / 6.2%
for 1.5x, 0.75x and 1.0x; 10.9% / 6.4% for none; `verification/noise_v2/g275_gap_be.txt`). The difference is one week of
933 either way: within noise, adopted because the pre-registered rule says so (and it removes a rule from the sprint).

**U53 (2026-11-07): no gap break-even in the Test sprint.** Full suite: **678 passed**. `GapBreakEven` 0 in "Test sprint" mode (Funded growth keeps
1.5). NinjaTrader tests 49 passed (`test_v38_test_sprint` with it).

## G276: U53's Test sprint with the gap trade out at another time (registered 2026-11-07, before its run)

U53 closes the gap trade at the 09:55 bar's open (`gap_go_exit` 595); here at 09:45, 10:10 or 10:25.
`research/g276_gap_exit.py`, G253's measure. **Replaces U53's setting** if on the unseen weeks it passes more than
12.2% and fails at most 8.4%. Run once.

**G276 result (2026-11-07): rejected.** Unseen weeks (passed / failed): U53 (09:55) 12.2% / 8.4%; 09:45 10.5% / 8.6%;
10:10 10.9% / 8.8%; 10:25 11.3% / 8.9% (development a little better for the others: 11.1-11.4% / 5.7-5.9% against
10.9% / 6.4%; `verification/noise_v2/g276_gap_exit.txt`). The development gain does not carry to the unseen weeks.
U53 stays.

## G277: the two-week Test search around U53 (registered 2026-11-07, before its run)

`research/g277_test_search.py`: G253's two stages and measure, 300 combinations (seed 277) around U53 with its
sprint fixes held (4 MNQ to +$5,000, the gap trade at 2 MNQ from 0.5x, no gap break-even), varying the day stop
($1,000-1,200), noise sessions (16-20), entry width (0.65-0.75), range position (0.65-0.75), calm (0.6-0.8), take
profit (0.6-1.0), lock (0.15-0.25 / +1.5-3.5 points), losers (2-4), time stop (20-45), stop buffer (0.18-0.3).
**Replaces U53's Test sprint** if on stage 2 it passes more than 12.2% and fails at most 8.4%; as G256, the five
lowest-failure stage-1 combinations (at least 11% passed, at most 8% failed) also go to stage 2 under the same rule.
Run once.

## G278: U53 over 2, 3, 4 and 6 weeks (registered 2026-11-07, before its run)

The user asked for 25% passes. A measurement, no adoption rule: U53's Test sprint (4 MNQ for the first 10 sessions,
then the 50K's growth sizing) under G250's Test rules, the share passed and failed within 10, 15, 20 and 30 sessions,
NQ 2015-25 and the index 2011-26 Monday starts (`research/g278_horizon.py`). Earlier rounds found no edge on the S&P
(G56) or overnight (G57), so more sessions are the remaining source of passes.

**G278 result (2026-11-07):** U53's Test sprint, 1,322 Monday starts (`verification/noise_v2/g278_horizon.{txt,csv}`):

| within | passed | failed |
|---|---|---|
| 2 weeks (10 sessions) | 12.0% | 7.9% |
| 3 weeks (15) | 15.4% | 8.6% |
| 4 weeks (20) | 18.0% | 9.6% |
| 6 weeks (30) | 21.0% | 10.5% |

(The 2-week row here, all starts together, is 12.0% / 7.9%; G275's unseen-weeks split is 12.2% / 8.4%.) Passes keep
coming after the sprint ends; 25% is beyond 6 weeks. A follow-up measures 8 and 12 weeks (40 and 60 sessions).

**G278 follow-up (2026-11-07):** within 8 weeks (40 sessions) 24.8% passed / 10.9% failed; within 12 weeks (60) 31.2% /
12.9% (`verification/noise_v2/g278_horizon_long.{txt,csv}`). U53 reaches about 25% passes at 8 weeks.

## G279: the Test sprint tuned for three weeks (registered 2026-11-07, before its run)

The user's new horizon: three weeks (15 sessions). U53 there: 15.4% passed / 8.6% failed (G278). `research/g279_three_weeks.py`:
U53 with the sprint over 15 sessions instead of 10, at 4 or 5 MNQ, with a day stop of $1,100 or $900; development and
unseen weeks as G253, measured over 15 sessions. **Offered to the user** with its odds if on the unseen weeks it passes
more than U53 does over 15 sessions there with failures at most 10%; a variant failing more is reported, not adopted.
Run once.

**G279: cancelled before its result (2026-11-07)** — the user's "3 weeks" was a typo for 2 weeks; the two-week target
(G253's measure) stands. G277's two-week search continues.

## G280: the "speedrun" (the user's video), measured (registered 2026-11-07, before its run)

**The video** ("speedrunning a 25k lucid"): a $90 Lucid 25K evaluation, 2 NQ in one trade with a stop about 26 points
away (nearly the whole $1,000 drawdown), the target in one move; passed in 4 minutes. One all-in bracket per attempt:
if it fails, the fee buys the next. (Not possible at TPT's 50K Test: the best day must be under half the profit, with
at least 3 trading days.)

**The measurement** (`research/g280_speedrun.py`, no adoption rule): every NQ session 2015-2025 with a bot entry (U53's
signal settings, no gap trade) is one attempt; the first entry opens a bracket with the stop 25 / 50 / 100 points away
and the target 1.0 / 1.25 / 1.5 x that; walked on 1-minute bars, stop first when a minute reaches both. The same
entries reversed are the coin-flip baseline. Reported: wins, losses and attempts per pass, all years and 2020-25.

**G280 result (2026-11-07):** 1,704 NQ sessions with a bot entry (`verification/noise_v2/g280_speedrun.{txt,csv}`).
Wins per attempt, the bot's direction / the reverse (2020-25 in brackets for the bot):

| stop | target 1.0x | 1.25x | 1.5x |
|---|---|---|---|
| 25 points | 54.5% (55.1%) / 42.4% | 49.4% (50.5%) / 37.4% | 45.3% (46.6%) / 33.3% |
| 50 points | 53.5% (55.8%) / 45.0% | 47.5% (49.1%) / 39.2% | 42.3% (44.0%) / 34.1% |
| 100 points | 48.2% (52.5%) / 40.5% | 40.9% (45.6%) / 33.9% | 35.6% (40.4%) / 28.7% |

The bot's direction wins 6-12 points more often than the reverse: a real edge on the first entry. With the target 1.25x
the drawdown, about every second attempt passes (2 fees per pass); every failed attempt is a failed evaluation. This
does not fit TPT's 50K Test (one day can't be more than half the profit; 3 days minimum). Not built into the file
without the user's go-ahead: it fails about half of all evaluations by design.

## G281: one bracket a day on the bot's first entry, for the Test in two weeks (registered 2026-11-07, before its run)

From G280's edge (the bot's first entry wins 6-12 points more often than its reverse). `research/g281_daily_bracket.py`:
each session only the bot's first entry, one MNQ bracket (stop 25 / 50 points, target 1.0 / 1.25 / 1.5 x), sized for
about $800 / $1,000 / $1,200 at the target and never a full stop past the floor less $100; costs as elsewhere; TPT's
Test rules over 10 sessions from every Monday; NQ (1-minute paths). Development: Mondays 2015-2019; unseen: 2020-2025.
**Built into the file as the Test sprint** only if the best development setting, on the unseen weeks, passes more than
U53 does there (to be measured on the same NQ 2020-25 weeks with G253's measure) and fails at most as often. Run once.

**G281 as first run: not valid (a modelling error, not a verdict).** It filled every stop exactly at the stop, so a
loss could never pass the sizing's $100 above the floor and no Test ever failed (0% failed in every cell; passes up to
17.9% development / 25.0% unseen; `verification/noise_v2/g281_daily_bracket_exact_fills.*`). Real stops slip, more so
when a minute opens past them. **G281b** (registered now, before its run, same grid and rule): a stop fills at the stop
or at the opening price of the minute that opened past it, whichever is worse, and a further tick.

**G281b result (2026-11-07): rejected.** With gap-through stop fills the pass and fail counts are unchanged (no Test
touches the floor: the sizing keeps a full stop above it; `verification/noise_v2/g281b_daily_bracket.{txt,csv}`). The
best development setting (stop 25 points, target $1,200 a day; R 1.0 and 1.25 tie at 17.9%) passes 22.9% / 25.0% on the
unseen 2020-25 weeks, against U53's 16.5% passed / 11.9% failed on the same NQ weeks. **But** a check of how the open
Tests end (G281c, `verification/noise_v2/g281c_frozen.txt`): **55-61% end with less than one contract's stop above the
floor** (frozen: the account cannot take another trade), development and unseen alike. The "no failures" is the floor
reached by inches, not avoided. Counting frozen as lost, it loses the account far more often than U53. Rejected; U53
stays.

## G282: the sprint's push in the last sessions (registered 2026-11-07, before its run)

At two weeks, 274 of U53's 1,322 open Tests end between +$1,000 and +$3,000 (G278's rows): close, but out of time.
`research/g282_push.py`: U53's Test sprint, but from session 8 or 9 of the 10, while the Test is up at least $1,000 or
$2,000, the sprint takes 6 or 8 MNQ (8 variants; the gap trade stays at 2 MNQ; the day's and the floor's room still cut
the size). G253's measure. The best development variant (passes more than U53 there and fails no more; most passes)
replaces U53 only if on the unseen weeks it passes more than 12.2% and fails at most 8.4%. None qualifying: rejected.
Run once.

**G282 result (2026-11-07): rejected.** Development (index 2011-18, 405 weeks): U53 10.9% passed / 6.4% failed; the
variants that pass more and fail no more are from session 8 at 6 MNQ if up $2,000 (11.4% / 6.4%, the best) and from
session 9 at 6 MNQ if up $2,000 (11.1% / 6.4%). On the unseen weeks (933) the chosen variant passes 11.9% and fails 8.4%,
against U53's 12.2% / 8.4%. It passes fewer: rejected, U53 stays. (The pushes that add passes there, e.g. from 8 at 6 if
up $1,000 at 12.8%, add failures too: 9.0%.) `verification/noise_v2/g282_push.txt`.

## G283: the sprint sized from a fixed dollar risk (registered 2026-11-07, before its run)

U53's sprint takes 4 MNQ whatever the trade's stop distance. `research/g283_risk_size.py`: each bot trade's size is
instead its risk ($300, $450 or $600) over its own initial stop's distance plus costs, 1 to 6 or 8 MNQ (the engine's
E50R sizing; 6 variants; the gap trade stays at 2 MNQ; the day's and the floor's room still cut the size). G253's
measure; the same rule as G282 (the best development variant that passes more than U53 there and fails no more replaces
U53 only if on the unseen weeks it passes more than 12.2% and fails at most 8.4%). Run once.

**G283 result (2026-11-07): rejected at the development step.** Development (index 2011-18, 405 weeks): U53 10.9%
passed / 6.4% failed; fixed-risk sizing $300 up to 6 / 8 MNQ 1.2% / 1.0%, 1.7% / 1.2%; $450 2.2% / 3.2%, 3.0% / 3.0%;
$600 5.7% / 4.4%, 6.2% / 7.2%. No variant passes more than U53, so none goes to the unseen weeks (that part of the run
was stopped; it could not change the verdict). The bot's own stops are wide (the noise line), so a fixed dollar risk
buys 1-3 MNQ and the Test runs out of time. U53 stays. `verification/noise_v2/g283_risk_size.txt`.

**G277 result (2026-11-07): rejected.** Stage 1 (300 combinations, index 2011-18, 405 weeks; U53 there 10.9% / 6.4%):
the best pass 12.6% / 10.9% (k270), 12.1% / 8.9% (k247), 11.9% / 11.6% (k296). Stage 2 (the top 10, 933 unseen weeks;
U53 12.2% / 8.4%): k296 13.8% passed / 10.6% failed, k270 13.2% / 12.3%, k104 12.0% / 7.4%, k3 11.5% / 8.6%, the rest
10.9-11.5% passed with 10.6-12.2% failed. None passes more than 12.2% while failing at most 8.4%. The more passes,
the more failures, as in G253-G261. The low-failure check found no stage-1 combination with at least 11% passed and at
most 8% failed (the lowest-failure ones pass 2-6%), so it had nothing to run. U53 stays.
`verification/noise_v2/g277_test_search.txt`, `g277_stage1.csv`, `g277_stage2.csv`.

## G284: the sprint's defence near the floor (registered 2026-11-07, before its run)

G277's k296 passes 13.8% of the unseen weeks but fails 10.6%. `research/g284_defence.py`: with less than $1,000 or
$1,500 above the trailing floor, the sprint takes 1 or 2 MNQ instead of 4 (the gap trade stays at 2; the room still cuts
the size), on U53 and on k296 (8 variants, and the two bases). G253's measure; the same rule as G282: the best
development variant that passes more than U53 there and fails no more replaces U53 only if on the unseen weeks it
passes more than 12.2% and fails at most 8.4%. Run once.

**G284 result (2026-11-07): adopted as U54.** `verification/noise_v2/g284_defence.txt`:

| variant | development passed | failed | unseen passed | failed |
|---|---|---|---|---|
| U53 | 10.9% | 6.4% | 12.2% | 8.4% |
| U53, 1 MNQ under $1,000 | 10.6% | 1.5% | 11.6% | 3.4% |
| U53, 2 MNQ under $1,000 | 10.4% | 4.4% | 11.8% | 6.1% |
| U53, 1 / 2 MNQ under $1,500 | 8.1% / 8.4% | 0.2% / 1.5% | 8.8% / 9.6% | 1.5% / 4.0% |
| k296 | 11.9% | 11.6% | 13.8% | 10.6% |
| k296, 1 MNQ under $1,000 | 10.9% | 3.0% | 13.0% | 4.4% |
| **k296, 2 MNQ under $1,000** | **11.4%** | **5.9%** | **13.6%** | **6.8%** |
| k296, 1 / 2 MNQ under $1,500 | 9.6% / 10.4% | 1.2% / 4.2% | 11.5% / 12.3% | 1.5% / 3.8% |

The only development variant that passes more than U53 there (10.9%) and fails no more (6.4%) is k296 with 2 MNQ under
$1,000 (11.4% / 5.9%). On the 933 unseen weeks it passes 13.6% and fails 6.8%, against U53's 12.2% / 8.4%: more passes
and fewer failures. **U54** = Mode "Test sprint" with G277's k296 settings (losers 4, time stop 45, take profit 0.6,
lock 0.25 / +2.5 points, stop buffer 0.3, a $1,000 day profit stop; the rest as U53) and the sprint at 2 MNQ whenever
less than $1,000 is left above the trailing floor (`SprintLowRoom` / `SprintLowQty` in the engine; the gap trade stays
at 2 MNQ). NinjaTrader's code matches the model trade for trade on the test sample, which reaches the defence
(`test_v38_test_sprint`). Still far from 25% in two weeks; G282-G283 and G277 showed the passes come with failures, and
this is the first change since U53 that lowers failures while adding passes.

## G284b: how U54's Tests end (registered 2026-11-07, before its run)

G281c's lesson: fewer failures can mean accounts left stuck just above the floor. `research/g284b_frozen.py`: on the
933 unseen weeks, the share of U53's and U54's two-week Tests that end passed, failed, open with less than $500 above
the trailing floor (near-frozen), or open with more. **U54 is reverted to U53** if its failed plus near-frozen share is
higher than U53's. Run once.

**G284b result (2026-11-07): U54 reverted to U53.** On the 933 unseen weeks (`verification/noise_v2/g284b_frozen.{txt,csv}`):

| | passed | failed | open, under $500 above the floor | open, $500+ above | failed + near-frozen |
|---|---|---|---|---|---|
| U53 | 12.2% | 8.4% | 13.9% | 65.5% | 22.3% |
| U54 | 13.6% | 6.8% | 17.9% | 61.7% | 24.7% |

U54's defence turns some failures into Tests left just above the floor (median room of the open Tests $1,352 vs U53's
$1,582). Failed plus near-frozen is higher than U53's, so by the registered rule U54 is reverted: the file's Test sprint
is U53 again (the engine keeps `sprint_low_room` off by default, for research). The passes it adds (13.6% vs 12.2%) are
real, but they come at the cost of more accounts that can barely trade.

## G285: a bigger sprint in stormy stretches (registered 2026-11-07, before its run)

G18 found the storms pay. `research/g285_storm_sprint.py`: U53's Test sprint takes 5 or 6 MNQ when the last 10
sessions' average range is above 1.1x, 1.25x or 1.4x the last 40's, and 4 MNQ otherwise (6 variants; the gap trade
stays at 2; the room still cuts the size). G253's measure, plus G284b's near-frozen count (open with less than $500
above the floor). The best development variant (more passes than U53 there, failures no higher) replaces U53 only if
on the unseen weeks it passes more than 12.2%, fails at most 8.4%, and failed + near-frozen is at most U53's 22.3%.
Run once.

**G285 result (2026-11-07): rejected.** Development (405 weeks): U53 10.9% passed / 6.4% failed / 20.5% failed or
near-frozen; every stormy-stretch variant fails more (6.9-9.9%; failed or near-frozen 21.7-24.4%), so none qualifies.
On the unseen weeks too (U53 12.2% / 8.4% / 22.3%) the variants pass 12.0-13.4% with 7.7-11.3% failed and 22.8-27.4%
failed or near-frozen. A bigger sprint in storms adds failures as fast as passes. U53 stays.
`verification/noise_v2/g285_storm_sprint.txt`.

## G286: the sprint until the Test is passed (registered 2026-11-07, before its run)

22 of U53's 1,322 two-week Tests (G278) end open at +$3,000 or more: the consistency rule (best day under half the
profit) holds them back, and the sprint stops at +$5,000. `research/g286_until_pass.py`: the sprint stays on until the
pass rule is met (at least +$3,000, the best day under half of it, 3 days with a trade), at 4 MNQ, or at 2 or 3 MNQ once
the Test is up $3,000 (3 variants; the gap trade stays at 2). G253's measure and G285's rule: the best development
variant (more passes than U53, failures no higher) replaces U53 only if on the unseen weeks it passes more than 12.2%,
fails at most 8.4%, and failed + near-frozen is at most 22.3%. Run once.

**G286 result (2026-11-07): rejected.** Development (405 weeks): U53 10.9% passed / 6.4% failed; kept on until passed
at 4, 3 or 2 MNQ from $3,000: 10.4%, 10.4%, 10.1% passed (6.2% failed). Unseen (933): 12.0%, 11.1%, 10.8% against U53's
12.2% (failures and near-frozen unchanged). Fewer passes: past +$5,000 U53 hands over to the growth sizing, which by then
takes more than 4 MNQ, and that finishes the consistency rule sooner than a sprint held at 4 or less. U53 stays.
`verification/noise_v2/g286_until_pass.txt`.

## G287: a bigger sprint from +$3,000 until the Test is passed (registered 2026-11-07, before its run)

G286: past +$5,000 the growth sizing (more than 4 MNQ) finishes the consistency rule sooner than a sprint held at 4,
and G269 found the size kept past +$3,000 adds passes and no failures (the floor has stopped by then).
`research/g287_pass_push.py`: G286's sprint until the pass rule is met, at 5, 6 or 8 MNQ once the Test is up $3,000
(4 before; 3 variants; the gap trade stays at 2). G253's measure and G285's rule (development: more passes than U53,
failures no higher; unseen: more than 12.2% passed, at most 8.4% failed, failed + near-frozen at most 22.3%). Run once.

**G287 result (2026-11-07): rejected.** Development (405 weeks): U53 10.9% passed; 5, 6, 8 MNQ from +$3,000 until
passed: 10.4%, 10.6%, 10.6% (6.2% failed). Unseen (933): 11.8%, 11.5%, 11.3% against U53's 12.2% (failures and
near-frozen unchanged). Bigger trades from +$3,000 make bigger single days, and the best day must stay under half the
profit, so the Test takes longer. U53 stays. `verification/noise_v2/g287_pass_push.txt`.

## G288: a day profit stop that keeps the consistency rule (registered 2026-11-07, before its run)

G271 raised the day profit stop for every day (rejected: big days break the rule that the best day is under half the
profit); G287 found bigger days slow the Test. `research/g288_day_stop_consistent.py`: U53's $1,100 day profit stop
rises, on a day when it is more, to 0.8x, 0.9x or 0.95x the Test's profit before today (so a bigger day comes only when
it stays under the rest of the profit; 3 variants). G253's measure and G285's rule (development: more passes than U53,
failures no higher; unseen: more than 12.2% passed, at most 8.4% failed, failed + near-frozen at most 22.3%). Run once.

**G288 result (2026-11-07): rejected.** Development (405 weeks): U53 10.9% passed; the day stop raised to 0.8x, 0.9x,
0.95x the profit before today: 9.6%, 8.9%, 8.9% (6.4% failed, unchanged). Unseen (933): 8.7%, 7.8%, 7.8% against U53's
12.2% (failures and near-frozen unchanged). The stop only blocks new entries: the trade still open runs past it, so a
day allowed up to 0.9x the earlier profit often ends above it, and then it is more than half the profit. The flat
$1,100 keeps that overshoot small. U53 stays. `verification/noise_v2/g288_day_stop_consistent.txt`.

## G289: the day profit stop closes the open trade too (registered 2026-11-07, before its run)

G288: the trade still open runs past the day profit stop, and a day above half the profit holds the Test back.
`research/g289_day_cap.py`: the day profit stop ($1,100 as U53, or $1,300 or $1,500) also closes the open trade, with a
limit at the price where the day's P/L reaches it (whole ticks; as the take-profit, only beyond it by a tick; 3
variants). G253's measure and G285's rule (development: more passes than U53, failures no higher; unseen: more than
12.2% passed, at most 8.4% failed, failed + near-frozen at most 22.3%). Run once.

**G289 as first run (2026-11-07): not valid for adoption (a modelling error).** Development (405 weeks): day cap $1,100 /
$1,300 / $1,500: 10.9% / 12.8% / 13.3% passed, 5.7% / 5.9% / 5.9% failed (U53 10.9% / 6.4%); unseen (933): 13.1% /
13.5% / 15.0% passed, 7.3% / 7.5% / 8.0% failed, failed or near-frozen 20.9% / 21.7% / 21.8% (U53 12.2% / 8.4% /
22.3%); `verification/noise_v2/g289_day_cap_first_run.txt`. But the model checked the take-profit before the day's cap,
so on a bar that reached both it filled at the farther price; a real account's nearer limit fills first. **G289b**
(registered now, before its run; same variants and rule): the nearer of the take-profit and the day's cap is the one
that fills (`research/g289_day_cap.py`, mnqbot/noise.py).

**G289b result (2026-11-07): adopted as U55.** The nearer of the take-profit and the day's cap fills
(`verification/noise_v2/g289b_day_cap.txt`):

| | development passed | failed | failed or near-frozen | unseen passed | failed | failed or near-frozen |
|---|---|---|---|---|---|---|
| U53 | 10.9% | 6.4% | 20.5% | 12.2% | 8.4% | 22.3% |
| day cap $1,100 | 10.1% | 5.4% | 19.8% | 12.8% | 7.3% | 21.1% |
| day cap $1,300 | 12.3% | 5.7% | 20.5% | 13.8% | 7.4% | 22.0% |
| **day cap $1,500** | **13.6%** | **5.9%** | **20.0%** | **15.6%** | **7.9%** | **22.2%** |

The best development variant with more passes than U53 and failures no higher is the $1,500 cap (13.6% / 5.9%). On the
933 unseen weeks it passes 15.6%, fails 7.9%, and fails or ends near-frozen 22.2%: all three inside the rule (the last
by 0.1 point). **U55** = Mode "Test sprint" with a $1,500 day profit stop that also closes the open trade: the bracket's
target goes to the price where today's P/L reaches $1,500 when that is nearer than the take-profit (at entry, in ticks
from the fill, and each bar after). Engine: `DayCapExit` (C#), `day_cap_exit` (mnqbot/noise.py). NinjaTrader's code
matches the model trade for trade on the test sample, which reaches the day cap (`test_v38_test_sprint`). Full
suite: **678 passed**. Still far from 25% in two weeks.

## G290: more of the day cap (registered 2026-11-07, before its run)

G289b's passes rose with the cap ($1,100 → $1,500). `research/g290_cap_more.py`, on U55: the cap at $1,700 or $2,000,
and G277's k296 settings with the $1,500 cap (3 variants). G253's measure and the rule raised to U55's numbers: the best
development variant (more passes than U55 there, failures no higher) replaces U55 only if on the unseen weeks it passes
more than 15.6%, fails at most 7.9%, and failed + near-frozen is at most 22.2%. Run once.

**G290 result (2026-11-07): rejected.** U55 reproduced (development 13.6% / 5.9% / 20.0%, unseen 15.6% / 7.9% / 22.2%).
The cap at $1,700: development 10.9% / 6.2%, unseen 11.8% / 8.0%; at $2,000: 7.4% / 6.4%, 8.8% / 7.7%; k296 with the
$1,500 cap: 13.8% / 11.6% (development), 14.6% / 11.3% (unseen). A cap past $1,500 lets one day reach half of the
$3,000 target, so the consistency rule holds the Test back; k296 fails too often. U55 stays.
`verification/noise_v2/g290_cap_more.txt`.

## G291: the sprint's size under the day cap (registered 2026-11-07, before its run)

G272 chose 4 MNQ before the day cap existed; the cap now limits a day's gain. `research/g291_cap_size.py`, on U55: the
sprint at 5 or 6 MNQ under the $1,500 cap, and the cap at $1,400 with 4 MNQ (3 variants). G253's measure and G290's rule
(development: more passes than U55, failures no higher; unseen: more than 15.6% passed, at most 7.9% failed, failed +
near-frozen at most 22.2%). Run once.

**G291 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% passed / 5.9% failed / 20.0% failed or
near-frozen): the cap at $1,400 11.9% / 5.9% / 20.0%; the sprint at 5 MNQ 17.5% / 9.9% / 30.9%; at 6 MNQ 18.3% / 15.6%
/ 36.3%. Unseen (933; U55 15.6% / 7.9% / 22.2%): $1,400 15.0% / 7.5% / 21.2%; 5 MNQ 17.7% / 12.0% / 29.8%; 6 MNQ 19.6% /
18.3% / 37.8%. More contracts add passes but more failures (6 MNQ: about one extra failure for each extra pass); none
qualifies. U55 stays. `verification/noise_v2/g291_cap_size.txt`.

## G292: the two-week search under the day cap (registered 2026-11-07, before its run)

G277's search, redone under U55's day cap: `research/g292_cap_search.py`, 300 combinations (seed 292) of U53's entry and
exit settings (noise sessions 16-20, entry width 0.65-0.75, range position 0.65-0.75, calm 0.6-0.8, take profit 0.6-1.0,
lock 0.15-0.25 / +1.5-3.5 points, losers 2-4, time stop 20-45, stop buffer 0.18-0.3), with U55's sprint (4 MNQ to
+$5,000, gap at 2 MNQ, no gap break-even) and its $1,500 day cap held. Stage 1 on the development weeks; the 10 best by
passes with failures at most 6.5% go to stage 2 (the unseen weeks). **Replaces U55's settings** if on stage 2 it passes
more than 15.6%, fails at most 7.9%, and failed + near-frozen is at most 22.2%. Run once (resumable after a restart).

**G292 result (2026-11-07): rejected.** Stage 1 (300 combinations, 405 development weeks; U55 there 13.6% / 5.9% /
20.0%): the best with failures at most 6.5% pass 12.1-13.3%, none above U55's own 13.6%. Stage 2 (the top 10, 933 unseen
weeks; U55 15.6% / 7.9% / 22.2%): k157 17.1% passed / 9.9% failed / 26.0% failed or near-frozen, k73 17.0% / 9.4% /
23.7%, k147 16.1% / 9.0% / 22.4%, k52 15.6% / 9.0%; the rest 12.8-14.9% passed (6.5-8.8% failed). Nothing passes more
than 15.6% while failing at most 7.9%: under the cap, as before it, the extra passes come with extra failures. U55's
settings stand. `verification/noise_v2/g292_cap_search.txt`, `g292_stage1.csv`, `g292_stage2.csv`.

## G293: the gap trade's size under the day cap (registered 2026-11-07, before its run)

G273 put the sprint's gap trade at 2 MNQ before the day cap existed. `research/g293_cap_gap.py`, on U55: the gap trade at
3 or 4 MNQ (2 variants). G253's measure and G290's rule (development: more passes than U55, failures no higher; unseen:
more than 15.6% passed, at most 7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G293 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): the gap trade at 3 MNQ 14.1%
/ 7.4% / 23.0%, at 4 MNQ 14.8% / 6.9% / 25.7%: more passes but more failures, so neither qualifies. Unseen (933; U55
15.6% / 7.9% / 22.2%): 15.2% / 9.0% / 23.4% and 14.8% / 9.3% / 25.9%. U55 stays.
`verification/noise_v2/g293_cap_gap.txt`.

## G294: the day lock (registered 2026-11-07, before its run)

The day cap keeps good days from growing too big; a good day can still turn around. `research/g294_day_lock.py`, on
U55: once today's P/L, with the open trade at its best price since entry (bar highs / lows through the last bar), reaches
$800, $1,000 or $1,200, the trade's stop goes no lower than the price where today's P/L is $300, $500 or $700 (3
variants; whole ticks on NinjaTrader's grid). G253's measure and G290's rule (development: more passes than U55,
failures no higher; unseen: more than 15.6% passed, at most 7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G294 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): the day lock at $1,000 keeping
$500 13.6% / 5.9% (a tie, not more), at $1,200 keeping $700 13.3% / 5.9%, at $800 keeping $300 13.3% / 6.2%: none passes
more than U55. Unseen (933; U55 15.6% / 7.9% / 22.2%): 14.5% / 7.7% / 22.4%, 14.7% / 7.8% / 22.0%, 15.8% / 6.8% / 22.3%
(the last fails less but turns failures into near-frozen Tests, and it did not qualify on development). U55 stays.
`verification/noise_v2/g294_day_lock.txt`.

## G295: U55 over 2, 3, 4, 6 and 8 weeks (registered 2026-11-07, before its run)

A measurement, as G278 for U53 (no adoption rule): U55's Test sprint, the share of Tests passed, failed and near-frozen
within 10, 15, 20, 30 and 40 sessions, NQ 2015-25 and the index 2011-26 Monday starts (`research/g295_horizon.py`).

**G295 result (2026-11-07):** U55's Test sprint, 1,322 Monday starts (1,318 at 8 weeks;
`verification/noise_v2/g295_horizon.{txt,csv}`), against U53 (G278):

| weeks | U55 passed | failed | near-frozen | U53 passed | failed |
|---|---|---|---|---|---|
| 2 | 15.1% | 7.4% | 14.2% | 12.0% | 7.9% |
| 3 | 18.5% | 8.2% | 13.3% | 15.4% | 8.6% |
| 4 | 20.3% | 8.9% | 12.8% | 18.0% | 9.6% |
| 6 | 24.2% | 9.8% | 12.7% | 21.0% | 10.5% |
| 8 | 27.1% | 10.3% | 13.4% | 24.8% | 10.9% |

U55 passes 2-3 points more than U53 at every horizon and fails less. About a quarter of Tests pass within 6-8 weeks;
within two weeks, 15%.

## G296: new entries stop before the day cap (registered 2026-11-07, before its run)

U55's $1,500 is both the day profit stop (no new entries) and the cap (the open trade closed there).
`research/g296_entry_stop.py`, on U55: new entries stop at $1,000, $1,200 or $1,300 of today's P/L, while the open
trade is still closed at $1,500 (3 variants; `day_cap_at` in mnqbot/noise.py). G253's measure and G290's rule
(development: more passes than U55, failures no higher; unseen: more than 15.6% passed, at most 7.9% failed, failed +
near-frozen at most 22.2%). Run once.

**G296 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): new entries stopping at
$1,000 / $1,200 / $1,300 with the cap at $1,500: 11.9% / 6.2%, 13.1% / 6.2%, 12.6% / 6.2%: fewer passes, more failures;
none qualifies. Unseen (933; U55 15.6% / 7.9% / 22.2%): 14.8% / 8.1%, 15.6% / 7.9%, 15.9% / 7.9% (failed or near-frozen
22.0-22.1%): within noise of U55. U55 stays. `verification/noise_v2/g296_entry_stop.txt`.

## G297: a losing-streak pause in the Test sprint (registered 2026-11-07, before its run)

The engine's streak rule (v2.1 study; tested for funded growth only) on the two-week Test: `research/g297_streak.py`, on
U55: after 3 or 4 losing trades in a row (across days; a winner resets the count) the next 1 or 2 entry signals are
skipped (3 variants: 3 / 1, 3 / 2, 4 / 2). G253's measure and G290's rule (development: more passes than U55, failures no
higher; unseen: more than 15.6% passed, at most 7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G297 result (2026-11-07): rejected at the development step.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): skip 1
after 3 losers 11.6% / 8.6% / 22.0%; skip 2 after 3 losers 11.4% / 7.4% / 22.2%; skip 2 after 4 losers 13.1% / 6.2% /
18.8%: none passes more than U55. Unseen (933; U55 15.6% / 7.9% / 22.2%): 15.9% / 6.5% / 20.5%, 15.0% / 8.4% / 21.5%,
15.8% / 6.5% / 19.9%. The unseen weeks look better for two variants, but the rule picks on the development weeks first,
and changing it after seeing the unseen results would make them no longer unseen. Not adopted; U55 stays.
`verification/noise_v2/g297_streak.txt`.

## G298: a smaller sprint after a losing trade today (registered 2026-11-07, before its run)

`research/g298_after_loss.py`, on U55: after one losing trade today the sprint takes 2 or 3 MNQ for the rest of the day,
or 2 MNQ after two (3 variants; `sprint_after_loss_qty` / `sprint_after_loss_n`; the gap trade stays at 2). G253's
measure and G290's rule (development: more passes than U55, failures no higher; unseen: more than 15.6% passed, at most
7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G298 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): 2 MNQ after one loser today
5.7% / 3.5% / 12.3%; 3 MNQ after one 9.1% / 5.9% / 15.6%; 2 MNQ after two 10.6% / 5.4% / 18.3%: fewer passes, none
qualifies. Unseen (933; U55 15.6% / 7.9% / 22.2%): 9.2% / 4.2% / 13.5%, 12.5% / 5.8% / 18.2%, 14.0% / 6.3% / 19.0%.
Smaller trades after a loser cut failures and near-frozen Tests a lot (2 MNQ after one: failed or near-frozen 13.5%
against 22.2%) but cut the passes more. U55 stays. `verification/noise_v2/g298_after_loss.txt`.

## G299: an earlier last entry in the Test sprint (registered 2026-11-07, before its run)

The sprint searches kept the last entry at 15:00-15:30. `research/g299_last_entry.py`, on U55: no new entries after
12:00, 13:00 or 14:00 (3 variants; `last_entry_end`). G253's measure and G290's rule (development: more passes than U55,
failures no higher; unseen: more than 15.6% passed, at most 7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G299 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): the last entry at 12:00 4.2% /
3.5%, 13:00 8.9% / 4.7%, 14:00 10.6% / 5.4%. Unseen (933; U55 15.6% / 7.9% / 22.2%): 6.5% / 4.4%, 10.4% / 6.4%, 12.3% /
7.6%. The afternoon trades carry a large share of the passes; stopping earlier cuts them more than the failures. U55
stays. `verification/noise_v2/g299_last_entry.txt`.

## G300: the trend filter under the day cap (registered 2026-11-07, before its run)

The sprint turned the 50K's trend filter off (G253, before the cap). `research/g300_trend.py`, on U55: shorts while the
close is above its 45-session average take 1 MNQ (`trend_small`, as the 50K's growth mode), or are skipped; or the same
1 MNQ with a 20-session average (3 variants; `trend_side` -1). G253's measure and G290's rule (development: more passes
than U55, failures no higher; unseen: more than 15.6% passed, at most 7.9% failed, failed + near-frozen at most 22.2%).
Run once.

**G300 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): the trend filter at 45
sessions, shorts against it at 1 MNQ or skipped: 9.1% / 4.0% (both); at 20 sessions 8.9% / 4.2%. Unseen (933; U55 15.6% /
7.9% / 22.2%): 12.0% / 7.4%, 12.4% / 7.4%, 11.4% / 7.0%. The shorts against the uptrend carry passes in a two-week Test;
filtering them cuts passes more than failures, as G253 found before the cap. U55 stays.
`verification/noise_v2/g300_trend.txt`.

## G301: the big-day rule under the day cap (registered 2026-11-07, before its run)

The sprint turned v2.3's big-day rule off (the searches after G253 held `big_day_k` 0). `research/g301_big_day.py`, on
U55: after a day whose range is above 1.5x, 2x or 2.5x the average, no entries in that day's direction the next day (3
variants). G253's measure and G290's rule (development: more passes than U55, failures no higher; unseen: more than
15.6% passed, at most 7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G301 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): big day 1.5x 13.6% / 5.4% /
19.3% (a tie in passes), 2x 13.8% / 6.4% (more failures), 2.5x the same as U55 (it never applies). None qualifies.
Unseen (933; U55 15.6% / 7.9% / 22.2%): 15.2% / 7.8% / 20.9%, 16.0% / 7.8% / 21.5%, 15.6% / 7.9% / 22.2%: within noise.
U55 stays. `verification/noise_v2/g301_big_day.txt`.

## G302: the sprint's max loss a contract (registered 2026-11-07, before its run)

The sprint has kept the 50K's $187.50 a contract (about 94 points; `max_loss_per_trade`), never searched. It caps the
initial stop and sets the lock's trigger (lock_at x the max loss). `research/g302_max_loss.py`, on U55: $125, $150 or
$250 a contract (3 variants). G253's measure and G290's rule (development: more passes than U55, failures no higher;
unseen: more than 15.6% passed, at most 7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G302 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): the max loss a contract at $125
8.9% / 7.4%, $150 11.6% / 7.2%, $250 11.9% / 7.7%: fewer passes and more failures either way. Unseen (933; U55 15.6% /
7.9% / 22.2%): 12.2% / 7.7%, 13.5% / 8.6%, 14.9% / 9.0%. $187.50 sits at the best point. U55 stays.
`verification/noise_v2/g302_max_loss.txt`.

## G303: G138's untried rules on the Test sprint (registered 2026-11-07, before its run)

G138 tried these on the growth bot only. `research/g303_cooldown.py`, on U55: after a losing trade, skip the next 1 or
2 entry signals on that side (`side_cooldown`); or half size while the equity is below its 20-trade average (`eq_n`
20) (3 variants). G253's measure and G290's rule (development: more passes than U55, failures no higher; unseen: more
than 15.6% passed, at most 7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G303 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): side cooldown 1 9.6% / 5.4% /
19.0%, side cooldown 2 8.4% / 4.7% / 14.6%, half size below the 20-trade equity average 9.9% / **2.0%** / **9.6%**.
Unseen (933; U55 15.6% / 7.9% / 22.2%): 14.3% / 7.5% / 19.4%, 12.2% / 5.3% / 18.2%, 11.5% / **4.0%** / **13.4%**. None
passes more. The equity filter halves the failures and near-frozen Tests on both sets at a cost of about a quarter of
the passes; a natural follow-up is the filter with a bigger sprint (G304). U55 stays.
`verification/noise_v2/g303_cooldown.txt`.

## G304: the equity filter with a bigger sprint (registered 2026-11-07, before its run)

G303: half size below the 20-trade equity average halves the failures but costs about a quarter of the passes.
`research/g304_eq_size.py`, on U55: that filter with the sprint at 5, 6 or 8 MNQ (halved, rounded, while below the
average; 3 variants). G253's measure and G290's rule (development: more passes than U55, failures no higher; unseen:
more than 15.6% passed, at most 7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G304 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): the equity filter with the
sprint at 5 MNQ 12.3% / 3.2% / 14.1%, 6 MNQ 15.3% / 8.1% / 24.9%, 8 MNQ 17.0% / 16.8% / 36.8%. Unseen (933; U55 15.6% /
7.9% / 22.2%): 13.9% / 6.5% / 19.4%, 16.5% / 10.7% / 28.7%, 19.3% / 19.2% / 39.5%. With the filter, the size that
gets back U55's passes (6 MNQ) also brings back more failures than U55. None qualifies; U55 stays.
`verification/noise_v2/g304_eq_size.txt`.

## G305: the day guard in the Test sprint (registered 2026-11-07, before its run)

G128's day guard (a tick-level exit where today's P/L reaches minus the guard; tried on the growth bot only) on the
two-week Test: `research/g305_day_guard.py`, on U55: the guard at $800, $1,000 or $1,200 (3 variants; `day_guard`). G253's
measure and G290's rule (development: more passes than U55, failures no higher; unseen: more than 15.6% passed, at most
7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G305 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): the day guard at $1,000 13.6% /
4.4% / 18.5%, $1,200 13.6% / 5.2% / 19.0%, $800 12.8% / 3.5% / 18.5%: fewer failures but no more passes, so none
qualifies. Unseen (933; U55 15.6% / 7.9% / 22.2%): 15.0% / 6.5% / 22.3%, 15.2% / 6.5% / 22.4%, 13.8% / 7.8% / 22.8%:
the failures it saves end as near-frozen Tests instead (as G284), and the passes fall. U55 stays.
`verification/noise_v2/g305_day_guard.txt`.

## G306: a bigger sprint behind the day guard (registered 2026-11-07, before its run)

G305's $1,000 day guard and G301's 1.5x big-day rule each cut development failures at the same passes. Here the saving
is spent on size: `research/g306_guard_size.py`, on U55: the sprint at 5 MNQ with the day guard at $1,000 or $800, or with
the $1,000 guard and the big-day rule at 1.5x (3 variants). G253's measure and G290's rule (development: more passes
than U55, failures no higher; unseen: more than 15.6% passed, at most 7.9% failed, failed + near-frozen at most
22.2%). Run once.

**G306 result (2026-11-07): rejected on the unseen weeks.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): 5 MNQ with
the $1,000 guard **17.8% / 5.2%** (but 27.4% failed or near-frozen), with the $800 guard 16.3% / 3.7% / 26.4%, with the
$1,000 guard and the big-day rule 16.3% / 5.7% / 26.9%. The best development variant (5 MNQ, $1,000 guard) on the unseen
weeks (933; U55 15.6% / 7.9% / 22.2%): 17.0% passed but 9.8% failed and 28.4% failed or near-frozen; the others 16.2-16.8%
/ 9.8-10.0%. The guard holds the failures down on development but not on the unseen weeks, and in both the near-frozen
Tests grow. U55 stays. `verification/noise_v2/g306_guard_size.txt`.

## G307: the sprint on jobs-report days (registered 2026-11-07, before its run)

G62 found the bot makes 2.5-3.4x its usual dollars on the monthly jobs-report days (tried on the growth bot only).
`research/g307_jobs_days.py`, on U55: on those days (`research/nfp_dates.csv`) the sprint's bot trades take 0.5x, 1.5x
or 2x its 4 MNQ (2, 6 or 8; `news_mult`; the day's and the floor's room still cut it; 3 variants). G253's measure and
G290's rule (development: more passes than U55, failures no higher; unseen: more than 15.6% passed, at most 7.9% failed,
failed + near-frozen at most 22.2%). Run once.

**G307 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): jobs days 0.5x 13.1% / 6.7%,
1.5x 13.8% / 6.2%, 2x 14.1% / 6.7%: the passes it adds come with more failures, so none qualifies. Unseen (933; U55
15.6% / 7.9% / 22.2%): 14.5% / 7.8% / 21.2%, 16.2% / 7.8% / 22.7%, 16.3% / 8.5% / 23.4%. About one jobs day falls in a
two-week Test, too few to move it much either way. U55 stays. `verification/noise_v2/g307_jobs_days.txt`.

## G308: the day's first trade bigger (registered 2026-11-07, before its run)

G280: the bot's first entry of a day wins 54.5% at a 1:1 bracket (42.4% reversed). `research/g308_first_trade.py`, on
U55: the sprint's first bot trade of the day at 5 or 6 MNQ and the later ones at 3 or 4 (5 / 3, 6 / 3, 6 / 4; the gap
trade stays at 2; the room still cuts the size; `sprint_first_qty` / `sprint_later_qty`). G253's measure and G290's
rule (development: more passes than U55, failures no higher; unseen: more than 15.6% passed, at most 7.9% failed, failed
+ near-frozen at most 22.2%). Run once.

**G308 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): first 5 / later 3 MNQ 8.9% /
4.9%, 6 / 3 10.1% / 6.7%, 6 / 4 15.8% / 10.6%. Unseen (933; U55 15.6% / 7.9% / 22.2%): 12.0% / 6.4%, 14.5% / 8.1%, 18.3%
/ 10.7%. The later trades carry as many passes as the first; a bigger first trade adds failures at the rate a bigger
sprint does (G291). U55 stays. `verification/noise_v2/g308_first_trade.txt`.

## G309: is U55's gain over U53 real? (a check on saved results, 2026-11-07)

`research/g309_paired.py`: G278's and G295's two-week rows, the same 1,322 Monday starts. U55 passes 51 Tests U53 does
not, and U53 passes 9 that U55 does not; U55 fails 3 that U53 does not, U53 fails 9 that U55 does not. Over a bootstrap
of calendar quarters (4,000 draws), the passes gained: **+3.2 points (95%: +1.9 to +4.5; never at or below zero)**; the
failures: −0.45 points (95%: −0.9 to 0.0). The day cap's extra passes are not noise; its saving in failures is small.
`verification/noise_v2/g309_paired.txt`.

## G310: a green afternoon kept green (registered 2026-11-07, before its run)

The Test needs three trading days and the best day under half the profit; a day that is up by the afternoon can still
turn red. `research/g310_late_stop.py`, on U55: from 13:00 (or 14:00), no new entries once today's P/L is at least $500
(or $750 from 13:00) (3 variants; `day_stop_late_from` / `day_stop_late`). G253's measure and G290's rule (development:
more passes than U55, failures no higher; unseen: more than 15.6% passed, at most 7.9% failed, failed + near-frozen at
most 22.2%). Run once.

**G310 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): from 13:00 at $500 11.9% /
6.7%, from 13:00 at $750 13.3% / 6.4%, from 14:00 at $500 11.6% / 6.7%: fewer passes, more failures. Unseen (933; U55
15.6% / 7.9% / 22.2%): 14.5% / 7.1%, 15.2% / 7.4%, 15.3% / 7.8%. The afternoon entries on a green day add more passes
than red days. U55 stays. `verification/noise_v2/g310_late_stop.txt`.

## G311: the near misses together (registered 2026-11-07, before its run)

Five rules each came close alone (fewer failures for about the same passes, or the reverse): G297's streak pause (skip
2 signals after 4 losers), G301's big-day rule (1.5x), G305's day guard ($1,000), G294's day lock ($800 keeping $300),
G307's jobs days (1.5x). `research/g311_combo_search.py`: every combination of the five on U55, with the sprint at 4 or
5 MNQ (64 variants; variant 0 is U55 itself). Stage 1 on the development weeks; the 10 best by passes with failures at
most U55's 5.9% go to stage 2 (the unseen weeks). **Replaces U55's settings** if on stage 2 it passes more than 15.6%,
fails at most 7.9%, and failed + near-frozen is at most 22.2%. Run once (resumable).

## G312: size up while the account is up and alive (registered 2026-11-07, before its run)

The user (2026-11-07): "size up, trade more, up to you, as long as the account is up and not down and dead". A
measurement, no adoption rule by itself: U55's Test sprint at 4, 5, 6 and 8 MNQ, with or without G305's $1,000 day guard
(8 variants), on all two-week Monday starts (NQ 2015-25, the index 2011-26): passed, failed, **up and alive** (profit
above zero after the two weeks, not failed), and the median two weeks (`research/g312_size_scan.py`). U55 now (G295's
rows): up and alive 56.0%, passed 15.1%, failed 7.4%.

**G312 adoption rule (added 2026-11-07, before its results; the user: "just get it done").** A variant replaces U55
only if (a) on all starts it fails at most U55's 7.4%, ends up and alive at least as often (56.0%) and passes more, and
(b) on the unseen starts alone (NQ 2015-25 and the index 2019-26) it passes more than 15.6%, fails at most 7.9%, and
failed + near-frozen is at most 22.2% (G290's rule). The most passes among those that qualify; none qualifying: U55 stays.

**G311 result (2026-11-07): rejected.** Stage 1 (64 variants, 405 development weeks; U55 13.6% / 5.9% / 20.0%): the top
10 with failures at most 5.9% are all the 5 MNQ sprint with the day guard, passing 16.3-17.8% (failed 4.2-5.7%, failed
or near-frozen 21.7-27.9%). Stage 2 (933 unseen weeks; U55 15.6% / 7.9% / 22.2%): 16.4-17.7% passed, 7.7-10.1% failed,
**25.8-28.7% failed or near-frozen**. The closest, 5 MNQ with the streak pause, the big-day rule, the guard and the day
lock (k62), passes 16.4% and fails 7.7%, but 25.8% of its Tests end failed or near-frozen against U55's 22.2%: the guard
turns failures into accounts left at the floor. None qualifies; U55 stays.
`verification/noise_v2/g311_combo_search.txt`, `g311_stage1.csv`, `g311_stage2.csv`.

**G312 result (2026-11-07): U55 stays.** All 1,338 two-week starts (`verification/noise_v2/g312_size_scan.{txt,csv}`):

| sprint | passed | failed | up and alive | median two weeks | unseen passed | failed | failed or near-frozen |
|---|---|---|---|---|---|---|---|
| **4 MNQ (U55)** | 15.0% | 7.3% | **55.8%** | $328 | 15.6% | 7.9% | 22.2% |
| 4, guard $1,000 | 14.6% | 5.9% | 55.7% | $315 | 15.0% | 6.5% | 22.3% |
| 5 | 17.6% | 11.4% | 52.5% | $255 | 17.7% | 12.0% | 29.8% |
| 5, guard | 17.3% | 8.4% | 53.0% | $253 | 17.0% | 9.8% | 28.4% |
| 6 | 19.2% | 17.5% | 48.7% | $269 | 19.6% | 18.3% | 37.8% |
| 6, guard | 18.8% | 10.8% | 51.0% | $223 | 18.8% | 11.5% | 34.8% |
| 8 | 20.7% | 21.6% | 43.8% | $84 | 20.8% | 22.6% | 47.1% |
| 8, guard | 19.7% | 14.4% | 45.3% | $0 | 19.9% | 14.8% | 42.0% |

Sizing up passes more Tests but leaves fewer accounts up and alive: from 55.8% at 4 MNQ to 43.8% at 8, and the median
two weeks falls. The user's rule ("up and not dead") is best met at 4 MNQ. None qualifies under the rule written
before the results; U55 stays.

## G313: no entries against a big opening gap, in the Test sprint (registered 2026-11-07, before its run)

G53's gap block (growth bot only, mixed). `research/g313_gap_block.py`, on U55: on a day that opens more than 0.5%, 1%
or 1.5% from the prior close, no bot entries against the gap (3 variants; `gap_block`). G253's measure and G290's rule
(development: more passes than U55, failures no higher; unseen: more than 15.6% passed, at most 7.9% failed, failed +
near-frozen at most 22.2%). Run once.

**G313 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): no entries against a 0.5% /
1% / 1.5% gap: 11.6% / 7.9%, 13.3% / 6.4%, 13.3% / 5.9%. Unseen (933; U55 15.6% / 7.9% / 22.2%): 14.5% / 8.1%, 14.9% /
8.3%, 15.2% / 8.1%. Fewer passes and more failures; the trades against a gap are not the bad ones. U55 stays.
`verification/noise_v2/g313_gap_block.txt`.

## G314: Fed announcement days in the Test sprint (registered 2026-11-07, before its run)

The sets' Fed-day rule is off in G253's measure (the data sets carry their own no-trade dates). `research/g314_fed_days.py`,
on U55, with the scheduled Fed days of `research/fomc_dates.csv`: no shorts before 14:00 on those days (`fed_no_shorts`),
or no trading at all that day (2 variants). G253's measure and G290's rule (development: more passes than U55, failures
no higher; unseen: more than 15.6% passed, at most 7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G314 result (2026-11-07): rejected on the unseen weeks.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): no shorts
before 14:00 on Fed days 13.6% / 5.7% (a tie in passes); no trading on Fed days **13.8% / 5.4% / 18.8%** (the best,
qualifies). Unseen (933; U55 15.6% / 7.9% / 22.2%): no trading on Fed days 14.9% / 7.3% / 21.4%: fewer passes, so it
does not replace U55; no shorts before 14:00 15.8% / 7.9% / 22.0% (within noise, and it did not qualify on development).
U55 stays. `verification/noise_v2/g314_fed_days.txt`.

## G315: the gap trade off, or smaller; or no entries after 15:00 (registered 2026-11-07, before its run)

A profile of U55-style trades (4 MNQ, no floor) on the development weeks only (index 2011-18, 5,028 trades;
scratchpad script, not a test): the 09:35 gap trade nets about break-even (gap exits +$24,076, gap stops −$20,593),
and the 15:00 hour's entries average $4.70 against $10-33 for the hours 10:00-14:00. `research/g315_gap_off.py`, on
U55: the gap trade off (`gap_go` False), the gap trade at 1 MNQ, or no bot entries after 15:00 (3 variants). G253's
measure and G290's rule (development: more passes than U55, failures no higher; unseen: more than 15.6% passed, at
most 7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G315 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): gap trade off 11.9% / 5.9%,
gap trade 1 MNQ 12.6% / 6.4%, last entry 15:00 12.6% / 6.7%. Unseen (933; U55 15.6% / 7.9% / 22.2%): 13.2% / 7.0%, 14.1%
/ 7.8%, 14.8% / 7.7%. Though the gap trade nets little over eight years, inside a two-week Test its early wins carry
passes; and the 15:00 entries add passes despite their small average. U55 stays. `verification/noise_v2/g315_gap_off.txt`.

## G316: no entries at the weak checks (registered 2026-11-07, before its run)

G315's profile of the development weeks: entries filled in the 11:00 hour average $10.60 and in the 15:00 hour $4.70,
the hours 10:00 and 12:00-14:00 $24-33. `research/g316_skip_checks.py`, on U55: no entries at the 11:00 and 11:30 checks,
or at 15:00 and 15:30, or at all four (3 variants; `skip_checks`). G253's measure and G290's rule (development: more
passes than U55, failures no higher; unseen: more than 15.6% passed, at most 7.9% failed, failed + near-frozen at most
22.2%). Run once.

**G316 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): no 11:00 / 11:30 checks 10.6% /
8.1%, no 15:00 / 15:30 11.1% / 6.4%, neither 9.6% / 5.7%. Unseen (933; U55 15.6% / 7.9% / 22.2%): 11.9% / 9.0%, 13.8% /
7.6%, 9.6% / 6.6%. An hour's average P/L over eight years does not say which entries a two-week Test needs: fewer entries,
fewer passes. U55 stays. `verification/noise_v2/g316_skip_checks.txt`.

## G317: the sprint sized by volatility (registered 2026-11-07, before its run)

G285 sized up in stormy stretches and added failures. The reverse: `research/g317_vol_size.py`, on U55: the sprint takes
4 MNQ x (the last 40 sessions' average range / the last 10's), rounded, within 3-5, 2-6 or 2-8 MNQ (bigger in calm
stretches, smaller in stormy ones; 3 variants; `sprint_vol_lo` / `sprint_vol_hi`; the gap trade stays at 2). G253's
measure and G290's rule (development: more passes than U55, failures no higher; unseen: more than 15.6% passed, at most
7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G317 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): volatility-sized 3-5 MNQ 10.6%
/ 7.2%, 2-6 10.9% / 7.7%, 2-8 the same (the ratio never reached 7). Unseen (933; U55 15.6% / 7.9% / 22.2%): 13.5% / 9.6%,
13.6% / 10.5%, 13.6% / 10.5%. Bigger trades in calm stretches fail more and pass less: the calm stretches' breakouts are
the weaker ones (G18, G285: the storms pay). U55 stays. `verification/noise_v2/g317_vol_size.txt`.

## G318: the opening drive as a filter (registered 2026-11-07, before its run)

`research/g318_drive.py`, on U55: when 09:30-10:00 moves more than 0.15x, 0.25x or 0.35x the last 10 sessions' average
range (as a share of the open), no bot entries against that move for the rest of the day (3 variants; `drive_filter_k`;
new in mnqbot/noise.py). G253's measure and G290's rule (development: more passes than U55, failures no higher; unseen:
more than 15.6% passed, at most 7.9% failed, failed + near-frozen at most 22.2%). Run once.

**G318 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9% / 20.0%): no entries against a 0.15x /
0.25x / 0.35x opening drive: 12.1% / 5.4%, 12.3% / 5.2%, 13.1% / 5.9%. Unseen (933; U55 15.6% / 7.9% / 22.2%): 14.5% /
7.8%, 14.8% / 7.9%, 15.0% / 7.8%. Fewer passes, hardly fewer failures: the reversals against the morning's move pay
their share. U55 stays. `verification/noise_v2/g318_drive.txt`.

## G319: the time lock under the day cap (registered 2026-11-07, before its run)

G261 searched G13's time lock before the cap. `research/g319_time_lock.py`, on U55: a trade still in profit 30, 60 or 90
minutes after its fill gets the lock (its stop to the entry plus lock_plus; 3 variants; `time_lock`). G253's measure and
G290's rule (development: more passes than U55, failures no higher; unseen: more than 15.6% passed, at most 7.9%
failed, failed + near-frozen at most 22.2%). Run once.

**G319 result (2026-11-07): rejected.** Development (405 weeks; U55 13.6% / 5.9%): time lock 30 / 60 / 90 minutes 13.3% /
5.7%, 13.6% / 5.9%, 13.6% / 5.9%. Unseen (933; U55 15.6% / 7.9% / 22.2%): 15.4% / 8.0%, 15.6% / 7.9%, 15.6% / 7.9%. The
30-minute time stop and the lock already settle almost every trade before 60 minutes; no change. U55 stays.
`verification/noise_v2/g319_time_lock.txt`.

## G320: the sprint's handover under the day cap (registered 2026-11-07, before its run)

G269 kept the sprint's 4 MNQ to +$5,000 before the cap existed. `research/g320_sprint_target.py`, on U55: to +$3,500,
+$4,000 or +$6,000 instead (3 variants; `sprint_target`). G253's measure and G290's rule (development: more passes than
U55, failures no higher; unseen: more than 15.6% passed, at most 7.9% failed, failed + near-frozen at most 22.2%). Run
once.

**G320 result (2026-11-07): rejected (no effect).** Development: all three the same as U55 (13.6% / 5.9%). Unseen: +$3,500
15.6% / 7.9%, +$4,000 15.4% / 7.9%, +$6,000 15.6% / 7.9%. Under the $1,500 cap a Test past +$3,500 has nearly always
passed already, so the handover point hardly matters. U55 stays. `verification/noise_v2/g320_sprint_target.txt`.

## G321: today's rules, 200 random combinations (registered 2026-11-07, before its run)

`research/g321_rule_search.py`: 200 random combinations (seed 321; variant 0 is U55) on U55 of the streak pause (4 / 2 or
3 / 1), the big-day rule (1.5x or 2x), the day guard ($1,000 or $1,200), the day lock ($800 / $300), jobs days 1.5x, the
opening-drive filter (0.35x), the equity filter (eq_n 20), the side cooldown (1), 3 MNQ after two losers, and the late
stop (from 14:00 at $500), with the sprint at 4 or 5 MNQ. Stage 1 on the development weeks; the 10 best by passes with
failures at most U55's 5.9% **and failed or near-frozen at most its 20.0%** go to stage 2. **Replaces U55's settings** if
on stage 2 it passes more than 15.6%, fails at most 7.9%, and failed + near-frozen is at most 22.2%. Run once (resumable).

**G321 result (2026-11-07): adopted (U56, pending NinjaTrader parity).** Stage 1 (200 variants, 405 development weeks;
U55 13.6% / 5.9% / 20.0%): the best, k30, **14.1% / 3.7% / 16.8%**. Stage 2 (933 unseen weeks; U55 15.6% / 7.9% /
22.2%): **k30 16.0% passed, 6.9% failed, 21.5% failed or near-frozen**, inside all three bounds; k107 15.8% / 6.0% /
20.8% next; the other eight 12.5-15.5% passed. k30 = U55 with G297's streak pause (skip 2 signals after 4 losers in a
row), the big-day rule at 1.5x (10 sessions), a $1,200 day guard (G128's tick-level exit, no new entries after it
fires), and 1.5x the sprint's size on jobs-report days (6 MNQ). The gain is mostly in failures (−1.0 point, near-frozen
−0.7); passes +0.4. `verification/noise_v2/g321_rule_search.txt`, `g321_stage1.csv`, `g321_stage2.csv`.

**G321b (registered 2026-11-07, before its run): the confirmation as the bot trades.** NinjaTrader's stop must sit on
the tick grid; G321's model filled the day guard at its exact price (off the grid; found by the new parity test).
`research/g321b_confirm.py`: U55 against U56 = k30 with the guard's stop on the grid (`day_guard_grid`; a long's rounds
up, so it never loses more). **U56 replaces U55** only if on the development weeks it passes more than U55 with failures
no higher, and on the unseen weeks passes more than 15.6%, fails at most 7.9%, and failed + near-frozen is at most 22.2%.
Run once.

**G321b result (2026-11-07): confirmed; adopted as U56.** Development (405 weeks): U55 13.6% / 5.9% / 20.0%; **U56 14.1%
passed / 3.7% failed / 16.8% failed or near-frozen**. Unseen (933): U55 15.6% / 7.9% / 22.2%; **U56 16.0% / 6.6% /
21.7%**. `verification/noise_v2/g321b_confirm.txt`.

**U56 (2026-11-07): the Test sprint with G321's four rules.** On top of U55: after 4 losing trades in a row (across days)
the next 2 entry signals are skipped (`StreakK` / `StreakSkip`); after a session whose range is above 1.5x the last 10
sessions' average, no entries its way the next day (`BigDayK` 1.5); a day guard: the stop goes no lower than where
today's P/L (or the room above the floor less $100) reaches −$1,200, on the tick grid, and no new entries that day once
it fires (`SprintDayGuard`, the live bracket's stop never wider than it); on the monthly jobs-report days the sprint's
size is 1.5x (6 MNQ; `NewsDates` 2010-2028 by BLS's rule, `NewsMult`). NinjaTrader's code matches the model trade for
trade on the test sample (which reaches the streak, big-day and jobs-day rules) and with a $300 guard (which fires;
`test_v38_test_sprint_day_guard`). Full suite: **679 passed**. The gain over U55 is mostly in failures; still far from
25% in two weeks.

## G322: more on top of U56 (registered 2026-11-07, before its run)

U56 fails less than U55, so it may carry more size. `research/g322_u56_more.py`: U56 with the sprint at 5 MNQ, U56 with
the opening-drive filter at 0.35x (G321's runner-up k107 had it), and both (3 variants). G253's measure; the rule at
U56's numbers: the best development variant (more passes than U56's 14.1%, failures no higher than 3.7%) replaces U56
only if on the unseen weeks it passes more than 16.0%, fails at most 6.6%, and failed + near-frozen is at most 21.7%.
Run once.

**G322 result (2026-11-07): rejected.** Development (405 weeks; U56 14.1% / 3.7% / 16.8%): the drive filter 14.3% / 4.0%
(more failures), 5 MNQ 16.8% / 5.9%, 5 MNQ + drive 17.0% / 6.2%: the variants that pass more all fail more. Unseen (933;
U56 16.0% / 6.6% / 21.7%): 15.5% / 6.4%, 17.3% / 11.4% / 27.4%, 17.3% / 10.8% / 27.3%. A fifth contract still costs far
more in failures than it adds in passes. U56 stays. `verification/noise_v2/g322_u56_more.txt`.

## G323: the entry and exit settings re-searched on U56 (registered 2026-11-07, before its run)

`research/g323_u56_search.py`: G292's search space (noise sessions 16-20, entry width 0.65-0.75, range position
0.65-0.75, calm 0.6-0.8, take profit 0.6-1.0, lock 0.15-0.25 / +1.5-3.5 points, losers 2-4, time stop 20-45, stop
buffer 0.18-0.3), 200 combinations (seed 323), with U56's sprint, cap and four rules held. Stage 1 on the development
weeks; the 10 best by passes with failures at most U56's 3.7% and failed or near-frozen at most its 16.8% go to stage 2.
**Replaces U56's settings** if on stage 2 it passes more than 16.0%, fails at most 6.6%, and failed + near-frozen is at
most 21.7%. Run once (resumable).

**G323 result (2026-11-07): rejected.** Stage 1 (200 combinations on U56, 405 development weeks; U56 14.1% / 3.7% /
16.8%): with failures at most 3.7% and failed or near-frozen at most 16.8%, the best pass only 8.9-10.9%. Stage 2 (933
unseen weeks; U56 16.0% / 6.6% / 21.7%): 9.9-13.0% passed. U56's own settings (k317 with U55's cap) sit above every
combination that keeps its failures this low. U56 stays. `verification/noise_v2/g323_u56_search.txt`, `g323_stage1.csv`,
`g323_stage2.csv`.

## G324: U56's neighbours (registered 2026-11-07, before its run)

`research/g324_u56_tune.py`: 60 random neighbours (seed 324; variant 0 is U56) of U56's rules: the streak pause (4 / 2,
3 / 2, 5 / 2, 4 / 1, 4 / 3), the big-day rule (1.5x, 1.25x, 1.75x), the day guard ($1,200, $1,000, $1,400; on the grid),
jobs days (1.5x, 1.25x, 2x) and the day cap ($1,500, $1,400, $1,600). Stage 1 on the development weeks; the 10 best by
passes with failures at most U56's 3.7% and failed or near-frozen at most its 16.8% go to stage 2. **Replaces U56's
settings** if on stage 2 it passes more than 16.0%, fails at most 6.6%, and failed + near-frozen is at most 21.7%. Run
once (resumable).

**G324 result (2026-11-07): rejected.** Stage 1 (60 neighbours, 405 development weeks): U56 reproduced (14.07% / 3.70% /
16.79%; it fell just outside the selection's 3.7% by rounding, and it is the base, not a candidate). Every neighbour that
passes as much fails more (k40 14.3% / 6.2%; k33, k45 14.1% / 5.4%, 4.2%); the three inside the failure bounds pass
7.9-9.4%. Stage 2 (933 unseen weeks): those three 9.3-11.1% passed. U56's values are the best of their neighbourhood.
U56 stays. `verification/noise_v2/g324_u56_tune.txt`, `g324_stage1.csv`, `g324_stage2.csv`.

## G325: the Fed days' size on U56 (registered 2026-11-08, before its run)

U56 trades 1.5x on the jobs-report days. `research/g325_fed_size.py`: U56 with the scheduled Fed announcement days
(`research/fomc_dates.csv`) at 1.5x or 0.5x the sprint's size (2 variants; `news2_dates` / `news2_mult`). G253's measure
and G322's rule (development: more passes than U56's 14.1%, failures no higher than 3.7%; unseen: more than 16.0%
passed, at most 6.6% failed, failed + near-frozen at most 21.7%). Run once.

**G325 result (2026-11-08): rejected.** Development (405 weeks; U56 14.1% / 3.7% / 16.8%): Fed days 0.5x 13.8% / 3.2%,
1.5x 14.1% / 3.7% / 18.3% (no more passes). Unseen (933; U56 16.0% / 6.6% / 21.7%): 15.2% / 6.5%, 16.1% / 7.0% / 22.4%.
The eight Fed days a year move a two-week Test little either way. U56 stays. `verification/noise_v2/g325_fed_size.txt`.

## G326: U56 over 2, 3, 4, 6 and 8 weeks (registered 2026-11-08, before its run)

A measurement, as G295 for U55 (no adoption rule): U56's Test sprint, the share of Tests passed, failed and near-frozen
within 10, 15, 20, 30 and 40 sessions, NQ 2015-25 and the index 2011-26 Monday starts (`research/g326_horizon.py`).

**G326 result (2026-11-08):** U56's Test sprint, 1,322 Monday starts (`verification/noise_v2/g326_horizon.{txt,csv}`),
against U55 (G295):

| weeks | U56 passed | failed | near-frozen | U55 passed | failed |
|---|---|---|---|---|---|
| 2 | 15.6% | 5.8% | 14.4% | 15.1% | 7.4% |
| 3 | 19.3% | 6.2% | 13.5% | 18.5% | 8.2% |
| 4 | 21.1% | 6.6% | 13.5% | 20.3% | 8.9% |
| 6 | 25.3% | 7.6% | 13.2% | 24.2% | 9.8% |
| 8 | 29.0% | 8.6% | 13.0% | 27.1% | 10.3% |

U56 passes a little more than U55 at every horizon and fails about a fifth less. A quarter of Tests pass within 6
weeks (25.3%); within two weeks, 15.6%.

## G327: the losers a day on U56 (registered 2026-11-08, before its run)

U56's day guard and streak pause now limit a bad day. `research/g327_losers.py`: U56 with at most 2, 4 or 5 losing
trades a day instead of 3 (3 variants; `max_losers`). G253's measure and G322's rule (development: more passes than
14.1%, failures no higher than 3.7%; unseen: more than 16.0% passed, at most 6.6% failed, failed + near-frozen at most
21.7%). Run once.

**G327 result (2026-11-08): rejected.** Development (405 weeks; U56 14.1% / 3.7% / 16.8%): 2 losers a day 8.6% / 5.9%, 4
13.3% / 4.4%, 5 13.3% / 5.2%. Unseen (933; U56 16.0% / 6.6% / 21.7%): 12.0% / 6.2%, 15.5% / 8.6%, 15.9% / 8.3%. Three
losers a day stays the best. U56 stays. `verification/noise_v2/g327_losers.txt`.

## G328: no entries either way after a big day, on U56 (registered 2026-11-08, before its run)

`research/g328_big_day_both.py`: U56 with the big-day rule blocking both sides the next day (`big_day_both`), at 1.5x or
at 2x the 10-session average range (2 variants). G253's measure and G322's rule (development: more passes than 14.1%,
failures no higher than 3.7%; unseen: more than 16.0% passed, at most 6.6% failed, failed + near-frozen at most 21.7%).
Run once.

**G328 result (2026-11-08): rejected.** Development (405 weeks; U56 14.1% / 3.7% / 16.8%): no entries either way after a
1.5x day 10.4% / 4.2%, after a 2x day 12.8% / 4.0%. Unseen (933; U56 16.0% / 6.6% / 21.7%): 13.8% / 5.1% / 18.4%, 15.1% /
5.5% / 21.2%: fewer failures but fewer passes. U56 stays. `verification/noise_v2/g328_big_day_both.txt`.

## G329: further rules on top of U56, 150 random combinations (registered 2026-11-08, before its run)

`research/g329_u56_rules.py`: 150 random combinations (seed 329; variant 0 is U56) on U56 of the opening-drive filter
(0.35x / 0.5x), the equity filter (eq_n 20 / 40), the side cooldown, 3 MNQ after two losers, the late stop (from 14:00
at $500), the gap block (1.5%), Fed days (1.5x / 0.5x), the gap trade's size (1 / 3), the day lock ($800 / $300) and the
time lock (30 minutes), with the sprint at 4 or 5 MNQ. Stage 1 on the development weeks; the 10 best by passes with
failures at most U56's 3.7% and failed or near-frozen at most its 16.8% go to stage 2. **Replaces U56's settings** if on
stage 2 it passes more than 16.0%, fails at most 6.6%, and failed + near-frozen is at most 21.7%. Run once (resumable).

## G330: why U56's Tests fail (a measurement on the development weeks only, 2026-11-08)

`research/g330_autopsy.py`: the 15 failed two-week Tests of U56 among the 405 development weeks (index 2011-18), their
trades up to the failure. Not one blowout: the worst day averages −$896 (at most −$1,200, the guard; below −$1,000 in 4
of 15), and the failed Tests have 5-11 losing days (median 7) before the floor, on day 2-9 (median 7). The losses are
the breakouts that fall back ("Back inside": 60 trades, −$12,267; "Max loss" 13, −$9,273; "Stop passed" 41, −$5,169;
time stops 18, −$5,075), spread over every hour and both sides (longs −$10,125, shorts −$9,542); the gap trade nets
−$843. Failure is a choppy stretch, not one bad day. `verification/noise_v2/g330_autopsy.txt`.

## G331: the chop pause (registered 2026-11-08, before its run)

From G330: `research/g331_chop_pause.py`: U56 with no trading for a session after 2, 3 or 4 sessions in a row that closed
with a loss (3 variants; `red_days_pause`; the day off resets the run). G253's measure and G322's rule (development: more
passes than 14.1%, failures no higher than 3.7%; unseen: more than 16.0% passed, at most 6.6% failed, failed +
near-frozen at most 21.7%). Run once.

**G329 result (2026-11-08): adopted as U57.** Stage 1 (150 combinations, 405 development weeks; U56 14.1% / 3.7% /
16.8%): within the failure bounds the best was U56 itself; next k34 (U56 + the day lock at $800 keeping $300) 13.8% /
3.7% / 16.8%. Stage 2 (933 unseen weeks; U56 16.0% / 6.6% / 21.7%): **k34 16.1% passed / 6.1% failed / 21.5% failed or
near-frozen**, inside all three bounds (the registered rule); the other nine 11.1-15.1% passed. A small gain, mostly in
failures. `verification/noise_v2/g329_u56_rules.txt`, `g329_stage1.csv`, `g329_stage2.csv`.

**U57 (2026-11-08): U56 with the day lock.** Once today's P/L, with the open trade at its best price since entry (bar
highs / lows through the last bar), reaches $800, the trade's stop goes no lower than where today's P/L is $300 (on the
tick grid with the line; `DayLockAt` / `DayLockKeep` in the C#, `day_lock_at` / `day_lock_keep` in the model).
NinjaTrader's code matches the model trade for trade on the test sample, which reaches the day lock. Full suite: **679 passed**.

**G331 result (2026-11-08): rejected.** Development (405 weeks; U56 14.1% / 3.7% / 16.8%): a day off after 2 / 3 / 4
losing days 11.1% / 3.0%, 13.6% / 3.2%, 13.6% / 3.7%: fewer failures but fewer passes, none qualifies. Unseen (933; U56
16.0% / 6.6% / 21.7%): 11.8% / 6.2%, 15.3% / 6.4%, 15.5% / 6.6%. Sitting out after a losing run also sits out the
recoveries: the day after a run of losses pays about as well as any other. U57 stays.
`verification/noise_v2/g331_chop_pause.txt`.

## G332: confirmed entries on U57 (registered 2026-11-08, before its run)

G330: U56's failures are the breakouts that fall back inside. `research/g332_confirm.py`, on U57: an entry only when the
previous check also closed past the line (`confirm`), or, after a losing trade on a side, the next entry that side only
when past the line by 0.1 or 0.25 of the noise (`side_margin`) (3 variants). G253's measure; the rule at U57's numbers
(development: more passes than U57 there, failures no higher; unseen: more than 16.1% passed, at most 6.1% failed,
failed + near-frozen at most 21.5%). Run once.

**G332 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): two checks past the line 6.4% /
3.7%; past by 0.1 / 0.25 noise after a loss that side 10.9% / 3.7%, 10.6% / 3.0%. Unseen (933; U57 16.1% / 6.1% / 21.5%):
8.1% / 5.6%, 13.2% / 6.5%, 13.3% / 5.4%. Waiting for confirmation misses the early, best part of the breakouts. U57
stays. `verification/noise_v2/g332_confirm.txt`.

## G333: the day lock's levels (registered 2026-11-08, before its run)

`research/g333_lock_grid.py`: U57 with the day lock at $600 / $200, $600 / $300, $800 / $200, $800 / $500, $1,000 / $300
or $1,000 / $500 instead of $800 / $300 (6 variants). G253's measure and G332's rule (development: more passes than U57's
13.8%, failures no higher than 3.7%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most
21.5%). Run once.

**G333 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): the best, $1,000 keeping $300,
14.1% / 3.7% (qualifies); the others 12.8-13.6%. On the unseen weeks (933; U57 16.1% / 6.1% / 21.5%) it passes 15.6% and
fails 7.4%: not better. The other levels: 14.4-15.6% passed, 5.6-7.4% failed. U57's $800 / $300 stays.
`verification/noise_v2/g333_lock_grid.txt`.

## G334: a shorter sprint on U57 (registered 2026-11-08, before its run)

G330: the failed Tests reach the floor around day 7 (2-9). `research/g334_sprint_days.py`: U57 with the sprint's 4 MNQ
for the first 5, 7 or 8 sessions instead of 10, then the 50K's growth sizing (3 variants; `sprint_days`). G253's measure
and G332's rule (development: more passes than U57's 13.8%, failures no higher than 3.7%; unseen: more than 16.1%
passed, at most 6.1% failed, failed + near-frozen at most 21.5%). Run once.

**G334 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): the sprint for 5 / 7 / 8
sessions 6.2% / 1.5%, 10.4% / 2.7%, 11.6% / 3.2%. Unseen (933; U57 16.1% / 6.1% / 21.5%): 6.9% / 2.9%, 11.0% / 3.8%,
13.1% / 4.6%. A shorter sprint lowers the failures and the passes together (8 sessions: −3 points of passes for −1.5 of
failures). U57 stays. `verification/noise_v2/g334_sprint_days.txt`.

## G335: smaller near the finish (registered 2026-11-08, before its run)

The prop-firm guides read on 2026-11-08 advise trading smaller near the profit target. `research/g335_near_finish.py`:
U57 with the sprint at 2 or 3 MNQ once the Test is up $2,000, or at 2 MNQ from $2,500 (3 variants; `sprint_near_from` /
`sprint_near_qty`). G253's measure and G332's rule (development: more passes than U57's 13.8%, failures no higher than
3.7%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most 21.5%). Run once.

**G335 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7%): 2 MNQ from +$2,000 9.1%, 3 MNQ from
+$2,000 11.6%, 2 MNQ from +$2,500 12.8% (failures unchanged at 3.7%). Unseen (933; U57 16.1% / 6.1%): 12.0%, 14.6%,
15.5% (failures 5.9-6.1%). Above +$2,000 the floor has nearly stopped and failures are rare, so smaller trades there only
slow the pass. U57 stays. `verification/noise_v2/g335_near_finish.txt`.

## G336: small changes to U57, 150 random combinations (registered 2026-11-08, before its run)

`research/g336_u57_mix.py`: 150 random sets of a few changes (seed 336; variant 0 is U57) to U57's take profit (0.6 /
0.9), lock (0.15 / 0.25; +1.5 / +3.5 points), time stop (20 / 45), stop buffer (0.18 / 0.3), entry width (0.65 / 0.75),
range position (0.65 / 0.75), calm (0.6 / 0.8), day guard ($1,000 / $1,400) and streak pause (3 / 2, 5 / 2). Stage 1 on
the development weeks; the 10 best by passes with failures at most U57's 3.7% and failed or near-frozen at most its
16.8% go to stage 2. **Replaces U57's settings** if on stage 2 it passes more than 16.1%, fails at most 6.1%, and failed
+ near-frozen is at most 21.5%. Run once (resumable).

**G336 result (2026-11-08): rejected.** Stage 1 (150 sets, 405 development weeks; U57 13.8% / 3.7% / 16.8%): the best,
k103 (time stop 45, calm 0.8), 14.1% / 3.0% / 15.6%; U57 itself second. Stage 2 (933 unseen weeks; U57 16.1% / 6.1% /
21.5%): U57 tops the list; the others pass 13.4-15.4% (k103 14.8% / 5.0% / 19.2%). No change to U57's settings beats it
on the unseen weeks. U57 stays. `verification/noise_v2/g336_u57_mix.txt`, `g336_stage1.csv`, `g336_stage2.csv`.

## G337: the entry width by side (registered 2026-11-08, before its run)

NQ has drifted up. `research/g337_side_width.py`: U57 (entry width 0.7 both sides) with longs at 0.65 and shorts at 0.75,
0.7 / 0.8, 0.6 / 0.7, or the reverse 0.7 / 0.6 (4 variants; `entry_k_short`, new in mnqbot/noise.py). G253's measure and
G332's rule (development: more passes than U57's 13.8%, failures no higher than 3.7%; unseen: more than 16.1% passed, at
most 6.1% failed, failed + near-frozen at most 21.5%). Run once.

**G337 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7%): longs 0.6 / shorts 0.7 13.6% / 3.5%,
0.65 / 0.75 12.6%, 0.7 / 0.6 12.3%, 0.7 / 0.8 13.1%: none passes more. Unseen (933; U57 16.1% / 6.1%): 14.7-15.6% passed.
The same width both sides stays best. U57 stays. `verification/noise_v2/g337_side_width.txt`.

## G338: a tighter max-loss stop alone (registered 2026-11-08, before its run)

G330: in the failed Tests the max-loss exits average −$713. G302 changed the max loss itself, which also moves the lock's
trigger. `research/g338_max_loss_frac.py`: U57 with only the max-loss stop at 0.6x, 0.75x or 0.9x of the max loss (in
the bracket and while in the trade), the lock's trigger and the sizing unchanged (3 variants; `max_loss_frac`, new in
mnqbot/noise.py). G253's measure and G332's rule (development: more passes than U57's 13.8%, failures no higher than
3.7%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most 21.5%). Run once.

**G338 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7%): the max-loss stop at 0.6x / 0.75x /
0.9x 11.4% / 3.5%, 12.8% / 4.2%, 13.1% / 3.2%. Unseen (933; U57 16.1% / 6.1%): 13.6% / 4.2%, 14.7% / 5.3%, 14.8% / 6.3%.
A tighter stop is hit more often by moves that come back; the passes fall more than the failures. U57 stays.
`verification/noise_v2/g338_max_loss_frac.txt`.

## G339: the noise area's sessions on U57 (registered 2026-11-08, before its run)

G336 left the noise area's length out. `research/g339_lookback.py`: U57 with the noise area averaged over 14, 16, 20 or
22 sessions instead of 18 (4 variants; `lookback`). G253's measure and G332's rule (development: more passes than U57's
13.8%, failures no higher than 3.7%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most
21.5%). Run once.

**G339 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7%): 14 / 16 / 20 / 22 sessions 9.6% / 3.5%,
11.1% / 4.4%, 13.1% / 4.0%, 11.1% / 5.4%. Unseen (933; U57 16.1% / 6.1% / 21.5%): 14.7%, 14.9%, 16.1% / 6.4% / 22.0%,
14.5%. 18 sessions stays best. U57 stays. `verification/noise_v2/g339_lookback.txt`.

## G340: the turn of the month on U57 (registered 2026-11-08, before its run)

G151 tried the turn of the month on the growth bot only. `research/g340_turn_of_month.py`: U57 with, on the last session
of each month and the first three of the next (from the data's own sessions), no shorts (`tom_no_shorts`), or the
sprint's size at 1.5x or 0.5x (`news2_dates` / `news2_mult`) (3 variants). G253's measure and G332's rule (development:
more passes than U57's 13.8%, failures no higher than 3.7%; unseen: more than 16.1% passed, at most 6.1% failed, failed +
near-frozen at most 21.5%). Run once.

**G340 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7%): no shorts at the turn of the month
11.6% / 4.2%, 0.5x there 11.9% / 4.2%, 1.5x there 14.6% / 5.2% (more failures). Unseen (933; U57 16.1% / 6.1% / 21.5%):
13.0% / 6.4%, 12.0% / 5.8%, 16.3% / 7.0% / 23.4%. The turn of the month moves passes and failures together. U57 stays.
`verification/noise_v2/g340_turn_of_month.txt`.

## G341: further rules on top of U57, 150 random combinations (registered 2026-11-08, before its run)

G329's search again (seed 341), on U57 (variant 0): the opening-drive filter (0.35x / 0.5x), the equity filter (eq_n 20
/ 40), the side cooldown, 3 MNQ after two losers, the late stop, the gap block, Fed days (1.5x / 0.5x), the gap trade's
size (1 / 3), the time lock, jobs days (1.25x / 2x instead of 1.5x), the big-day rule (1.25x / 2x instead of 1.5x) and
the losers a day (2 / 4), with the sprint at 4 or 5 MNQ (`research/g341_u57_rules.py`). Stage 1 on the development
weeks; the 10 best by passes with failures at most U57's 3.7% and failed or near-frozen at most its 16.8% go to stage 2.
**Replaces U57's settings** if on stage 2 it passes more than 16.1%, fails at most 6.1%, and failed + near-frozen is at
most 21.5%. Run once (resumable).

**G341 result (2026-11-08): rejected.** Stage 1 (150 combinations, 405 development weeks; U57 13.8% / 3.7% / 16.8%): U57
first; the others within the failure bounds 10.4-12.8%. Stage 2 (933 unseen weeks; U57 16.1% / 6.1% / 21.5%): U57 tops
the list; the others 11.6-14.4% passed. Of note for a safer mode: k68 (5 MNQ with the equity filter at 40 trades, Fed days
0.5x, the gap trade at 1 MNQ, jobs days 1.25x, the big-day rule at 2x, the time lock) passes 14.4% and fails **2.9%**
(failed or near-frozen 14.6%) on the unseen weeks: half U57's failures for 1.7 points fewer passes. U57 stays.
`verification/noise_v2/g341_u57_rules.txt`, `g341_stage1.csv`, `g341_stage2.csv`.

## G342: U57 over 2, 3, 4, 6 and 8 weeks (registered 2026-11-08, before its run)

A measurement, as G326 for U56: U57's Test sprint, passed, failed and near-frozen within 10, 15, 20, 30 and 40 sessions,
all Monday starts (`research/g342_horizon.py`).

**G342 result (2026-11-08):** U57's Test sprint, 1,322 Monday starts (`verification/noise_v2/g342_horizon.{txt,csv}`):
2 weeks 15.6% passed / 5.4% failed / 14.8% near-frozen; 3 weeks 19.2% / 6.0%; 4 weeks 21.1% / 6.2%; 6 weeks 25.6% /
7.1%; 8 weeks 28.9% / 8.3%. Against U56 (G326) the same passes with slightly fewer failures at every horizon.

## G343: the gap trade on U57 (registered 2026-11-08, before its run)

G274 / G276 set the gap trade before the day cap. `research/g343_gap_trade.py`: U57 with the 09:35 gap trade's trigger at
0.4x or 0.65x instead of 0.5x (`gap_go_k`), or held to 10:15 instead of 09:55 (`gap_go_exit`) (3 variants). G253's
measure and G332's rule (development: more passes than U57's 13.8%, failures no higher than 3.7%; unseen: more than
16.1% passed, at most 6.1% failed, failed + near-frozen at most 21.5%). Run once.

**G343 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): the gap trigger at 0.65x 14.1%
/ 3.2% / 15.8% (the best: more passes, fewer failures), out at 10:15 14.1% / 3.7%, the trigger at 0.4x 13.3% / 4.2%. On
the unseen weeks (933; U57 16.1% / 6.1% / 21.5%) the 0.65x trigger passes 16.1% (150 weeks, the same as U57), fails 5.9%
and fails or ends near-frozen 21.0%: not more passes, so it does not replace U57 (the rule asks for more). Out at 10:15
15.1%; 0.4x 16.5% / 6.3%. U57 stays. `verification/noise_v2/g343_gap_trade.txt`.

## G344: the paper's VWAP stop on U57 (registered 2026-11-08, before its run)

The noise-area paper trails its stop at the day's VWAP; the sprint never tried it. `research/g344_vwap_stop.py`: U57 with
the stop also never looser than the day's VWAP as of the last 30-minute check, or as of every bar (2 variants;
`vwap_stop` "checks" / "bars"). G253's measure and G332's rule (development: more passes than U57's 13.8%, failures no
higher than 3.7%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most 21.5%). Run once.

**G344 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): the VWAP stop at the checks
11.9% / 4.7% / 16.8%, every bar 11.4% / 4.2% / 17.0%: fewer passes, more failures. Unseen (933; U57 16.1% / 6.1% /
21.5%): 15.5% / 6.4% / 20.9% and 15.4% / 6.2% / 20.9%. The VWAP stop closes breakouts on their first pullback, before the
lock. U57 stays. `verification/noise_v2/g344_vwap_stop.txt`.

## G345: the prior day's high and low as a size rule (registered 2026-11-08, before its run)

Day traders watch the prior session's high and low; G246 traded them alone. `research/g345_prior_day.py`: U57 with the
entry's size at 1.5x when the signal close is past the prior session's 09:30-16:00 high (long) or low (short), at 0.5x
when it is not, or 1.5x past and 0.75x not (3 variants; `pdhl_mult` / `pdhl_in_mult`, new in mnqbot/noise.py, rounded,
at least 1; the floor's and the day's room still cut the size). G253's measure and G332's rule (development: more passes
than U57's 13.8%, failures no higher than 3.7%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen
at most 21.5%). Run once.

**G345 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): 1.5x past the prior day's high /
low 16.5% / 6.7% / 28.4% (more passes, far more failures), 1.5x past and 0.75x inside 16.0% / 6.7%, 0.5x inside 10.1% /
4.0%. None within the failure bound. Unseen (933; U57 16.1% / 6.1% / 21.5%): 18.0% / 11.8% / 30.0%, 15.3% / 10.6%, 11.6%
/ 3.6%. The breakouts past the prior day's range are the better trades, but 6 MNQ on them doubles the failures. U57
stays. `verification/noise_v2/g345_prior_day.txt`.

## G346: a little bigger past the prior day's range (registered 2026-11-08, before its run)

From G345's development weeks: `research/g346_prior_day_small.py`: U57 with 5 MNQ instead of 4 when the signal close is
past the prior session's high (long) or low (short) (`pdhl_mult` 1.25), and the same with 3 MNQ when it is not
(`pdhl_in_mult` 0.75) (2 variants). G253's measure and G332's rule (development: more passes than U57's 13.8%, failures
no higher than 3.7%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most 21.5%). Run once.

**G346 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): 5 MNQ past the prior day's range
15.6% / 5.2% / 24.4%, with 3 MNQ inside 14.8% / 6.2%: more passes, but past the failure bound. Unseen (933; U57 16.1% /
6.1% / 21.5%): 16.3% / 9.1% / 26.9% and 13.9% / 7.9%. Even one contract more on those breakouts adds failures faster than
passes. U57 stays. `verification/noise_v2/g346_prior_day_small.txt`.

## G347: the size past and inside the prior day's range, a grid (registered 2026-11-08, before its run)

G345 / G346: past the prior day's range the trades are better, inside they fail more. `research/g347_prior_day_grid.py`:
U57 with 4, 5 or 6 MNQ past the prior session's high (long) / low (short) and 1, 2 or 3 MNQ inside (`pdhl_mult` 1.0 /
1.25 / 1.5 and `pdhl_in_mult` 0.25 / 0.5 / 0.75 on the sprint's 4; 9 variants, two of them G345 / G346 again). G253's
measure and G332's rule (development: the best by passes with failures no higher than U57's 3.7%, and more passes than
its 13.8%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most 21.5%). Run once.

**G347 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): within the failure bound only
4 past / 3 inside (11.1% / 3.7%); every 5 or 6 past fails 6.2-7.7%. Unseen (933; U57 16.1% / 6.1% / 21.5%): 4 past / 3
inside 13.7% / 4.2%. The grid reads the other way from G345's guess: the size past the prior day's range drives the
failures, while fewer contracts inside cut passes and leave the failures where they were (4 past / 1 inside: 8.6% /
4.0%). U57 stays. `verification/noise_v2/g347_prior_day_grid.txt`.

## G348: bigger inside the prior day's range (registered 2026-11-08, before its run)

From G347's development weeks: `research/g348_inside_bigger.py`: U57 with 5 or 6 MNQ when the signal close is inside the
prior session's range and 4 past it, or 3 past with 4 or 5 inside (`pdhl_in_mult` 1.25 / 1.5, `pdhl_mult` 0.75 on the
sprint's 4; 4 variants). G253's measure and G332's rule (development: the best by passes with failures no higher than
U57's 3.7%, and more passes than its 13.8%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at
most 21.5%). Run once.

**G348 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): 4 past / 5 inside 14.1% / 4.2%,
4 / 6 14.3% / 5.4% (past the failure bound); 3 past / 4 or 5 inside 6.2% / 2.5%, 8.4% / 2.2%. Unseen (933; U57 16.1% /
6.1% / 21.5%): 4 / 5 17.0% / 6.8% / 22.8%, 4 / 6 17.7% / 7.1%, 3 / 4 10.0% / 4.5%, 3 / 5 11.5% / 5.6%. More contracts on
either kind of breakout buy passes with failures; the split does not escape it. U57 stays.
`verification/noise_v2/g348_inside_bigger.txt`.

## G349: the prior-day size rule mixed with U57's levels, 150 random combinations (registered 2026-11-08, before its run)

`research/g349_u57_prior_mix.py`: 150 random sets (seed 349; k 0 is U57) of the size past the prior day's range (0.75x /
1.25x), inside it (0.75x / 1.25x / 1.5x), the gap trigger 0.65x, the day guard ($1,000 / $1,400), the day lock ($1,000
keeping $300 / $600 keeping $200), the gap trade at 1 MNQ, jobs days (1.25x / 2x), the big-day rule at 2x, the time lock
and the equity filter (40 trades), with the sprint at 3, 4 or 5 MNQ. Stage 1 on the development weeks; the 10 best by
passes with failures at most U57's 3.7% and failed or near-frozen at most its 16.8% go to stage 2. **Replaces U57's
settings** if on stage 2 it passes more than 16.1%, fails at most 6.1%, and failed + near-frozen is at most 21.5%. Run
once (resumable).

**G349 result (2026-11-08): rejected.** Stage 1 (150 sets, 405 development weeks; U57 13.8% / 3.7% / 16.8%): the best,
k48 (5 MNQ, 1.25x past and 0.75x inside the prior day's range, the gap trigger 0.65x at 1 MNQ, the guard $1,400, jobs
days 1.25x, the big-day rule 2x, the equity filter at 40), 15.6% / 2.5% / 16.0%; k17 and k72 14.1%. Stage 2 (933 unseen
weeks; U57 16.1% / 6.1% / 21.5%): U57 tops the list; k48 15.1% / 6.0%, k17 15.6% / 6.6%. Of note for a safer mode: **k19**
(4 MNQ, 1.25x past and 1.5x inside, the gap trigger 0.65x at 1 MNQ, the guard $1,400, the day lock at $600 keeping $200,
jobs 1.25x, big day 2x, the equity filter at 40) passes 15.5% and fails **3.9%** (failed or near-frozen 17.5%) on the
unseen weeks, and k144 (5 MNQ, 0.75x past, 1.5x inside, the lock at $1,000, the gap trade at 1 MNQ, jobs 1.25x, big day
2x, the equity filter) 15.0% / **3.0%** / 16.3%: both nearer U57's passes than G341's k68 (14.4% / 2.9%). U57 stays.
`verification/noise_v2/g349_u57_prior_mix.txt`, `g349_stage1.csv`, `g349_stage2.csv`.

## G350: G349's lowest-failure sets, bigger (registered 2026-11-08, before its run)

G349's three sets with the fewest development failures among those near U57's passes (k19 13.8% / 1.0%, k35 13.1% /
0.7%, k53 13.1% / 1.2%; chosen on the development weeks, though their G349 unseen results were seen) with the sprint at
5 and 6 MNQ, and at their own size again (`research/g350_low_fail_bigger.py`; 9 variants). G253's measure and G332's rule
(development: the best by passes with failures no higher than U57's 3.7%, and more passes than its 13.8%; unseen: more
than 16.1% passed, at most 6.1% failed, failed + near-frozen at most 21.5%). Run once.

**G350 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): within the failure bound the
best is k35 at 5 MNQ, 15.6% / 2.7% / 16.5% (k53 at 5 15.1% / 2.7%; k19 at 5 15.8% / 4.4%, past the bound; every set at 6
MNQ fails 6.2-7.9%). Unseen (933; U57 16.1% / 6.1% / 21.5%): k35 at 5 MNQ 15.2% / 7.7% / 23.4%; k53 at 5 16.3% / 7.0%;
k19 at 5 17.3% / 9.1%; at 6 MNQ 17.9-19.0% passed, 9.9-13.0% failed. The development weeks' low failures do not carry
over once the size goes up. U57 stays. `verification/noise_v2/g350_low_fail_bigger.txt`.

## G351: bigger once the Test is up (registered 2026-11-08, before its run)

The prop-trading advice read on 2026-11-08: trade small until there is a cushion, then press with the market's money.
G335 tried smaller near the finish; G282 / G287 bigger in the last sessions or past +$3,000. `research/g351_house_money.py`:
U57 with 5 MNQ once the Test is up $1,000 or $1,500; or 3 MNQ to start, 4 once up $500; or 3 to start, 5 once up $1,000
(4 variants; `sprint_near_from` / `sprint_near_qty`; the floor's room still cuts the size). G253's measure and G332's
rule (development: the best by passes with failures no higher than U57's 3.7%, and more passes than its 13.8%; unseen:
more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most 21.5%). Run once.

**G351 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): 5 MNQ once up $1,500 16.0% /
3.7% / 17.0% (the best within the bound), once up $1,000 15.6% / 3.7%; 3 MNQ to start 10.6-12.1% / 1.7-2.2%. Unseen
(933; U57 16.1% / 6.1% / 21.5%): 5 once up $1,500 15.9% / 6.1% / 21.8%, not more passes; once up $1,000 16.4% / 6.4%;
3 to start 12.9% / 3.0% and 11.9% / 3.2%. Starting smaller cuts both; pressing once up gained on the development weeks
only. U57 stays. `verification/noise_v2/g351_house_money.txt`.

## G352: pressing higher up (registered 2026-11-08, before its run)

From G351's development weeks (pressing once up gained there) and G335 (failures are rare past +$2,000):
`research/g352_press_higher.py`: U57 with 5 or 6 MNQ once the Test is up $2,000, or 6 once up $1,500 (3 variants;
`sprint_near_from` / `sprint_near_qty`). G253's measure and G332's rule (development: the best by passes with failures no
higher than U57's 3.7%, and more passes than its 13.8%; unseen: more than 16.1% passed, at most 6.1% failed, failed +
near-frozen at most 21.5%). Run once.

**G352 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): 5 MNQ once up $2,000 15.1% /
3.7% (the best within the bound), 6 once up $2,000 14.6% / 3.7%, 6 once up $1,500 15.6% / 4.0%. Unseen (933; U57 16.1% /
6.1% / 21.5%): 15.6% / 6.0%, 15.8% / 6.1%, 16.7% / 6.4% / 22.1%. Past +$2,000 bigger trades reach the $1,500 day cap
sooner, and a big day there sets the consistency rule's bar higher. U57 stays. `verification/noise_v2/g352_press_higher.txt`.

## G353: the check grid on U57 (registered 2026-11-08, before its run)

G259 tried 10- and 15-minute checks on k317, before the day cap, guard and lock. `research/g353_check_step.py`: U57 with
the entry checks (and the noise area's grid) every 15 or every 60 minutes instead of 30 (2 variants; `check_step`).
G253's measure and G332's rule (development: the best by passes with failures no higher than U57's 3.7%, and more passes
than its 13.8%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most 21.5%). Run once.

**G353 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): checks every 15 minutes 9.9% /
5.7%, every 60 minutes 5.9% / 4.0%. Unseen (933; U57 16.1% / 6.1% / 21.5%): 12.4% / 8.0%, 5.8% / 4.5%. Thirty minutes
stays best by far. U57 stays. `verification/noise_v2/g353_check_step.txt`.

## G354: the 30-minute checks a quarter hour later (registered 2026-11-08, before its run)

`research/g354_check_shift.py`: U57 with the checks every 30 minutes from 09:45 or from 10:15 (at :15 and :45, the last
at 15:15 / 15:45 within the 15:30 entry end... as the grid falls) instead of from 10:00 (2 variants; `first_check` 585 /
615; the noise area on the same grid). G253's measure and G332's rule (development: the best by passes with failures no
higher than U57's 3.7%, and more passes than its 13.8%; unseen: more than 16.1% passed, at most 6.1% failed, failed +
near-frozen at most 21.5%). Run once.

**G354 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): checks from 09:45 6.7% / 5.9%,
from 10:15 5.7% / 5.4%. Unseen (933; U57 16.1% / 6.1% / 21.5%): 8.9% / 8.8%, 8.5% / 8.5%. A drop this large says U57's
settings are fitted to the round half hours (the 30-minute bars' closes, the gap trade's 09:35-09:55 window and the
10:00 first check); the shifted grid was not re-tuned, so this rejects the shift with U57's settings only. U57 stays.
`verification/noise_v2/g354_check_shift.txt`.

## G355: four order mechanics on U57 (registered 2026-11-08, before its run)

Knobs of mnqbot/noise.py from the v2.4-v2.8 studies never run on the Test sprint. `research/g355_mechanics.py`: U57 with
(1) 2 MNQ more at the next bar's open once the lock arms, sharing the exits (`add_at_lock` 2); (2) each check's entry as
a limit halfway back to the line, working until the next check (`limit_entry_frac` 0.5); (3) besides the checks, stop
orders resting at the noise lines from 10:00, once a side per half hour (`touch_entry`); (4) until the first check after
the fill, only the max-loss stop (`grace`) (4 variants). G253's measure and G332's rule (development: the best by passes
with failures no higher than U57's 3.7%, and more passes than its 13.8%; unseen: more than 16.1% passed, at most 6.1%
failed, failed + near-frozen at most 21.5%). Run once.

**G355 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): 2 MNQ more at the lock 3.7% /
3.7%; the limit entry 3.0% / 3.2%; stop entries at the lines 4.4% / 3.2%; the max-loss-only grace 13.6% / 3.7%. Unseen
(933; U57 16.1% / 6.1% / 21.5%): 6.9% / 5.5%, 5.7% / 2.7%, 5.1% / 5.7%, 16.1% / 6.1% / 21.4% (the grace changes almost
nothing). The collapse of the first three (the limit and stop entries also leave most Tests far from both ends) was not
traced trade by trade: these knobs predate the day cap, guard and lock and may not work as meant with them; either way
they are not a way forward from U57. U57 stays. `verification/noise_v2/g355_mechanics.txt`.

## G356: done after a target, or the afternoon's own target (registered 2026-11-08, before its run)

`research/g356_late_targets.py`: U57 with no new entries for the day once a take-profit fills (`after_target_done`), or
with the entries from checks closing at 13:00 or later taking 0.5 or 1.0 noise units as their take-profit instead of
0.75 (`late_tp` / `late_tp_from` 780) (3 variants). G253's measure and G332's rule (development: the best by passes with
failures no higher than U57's 3.7%, and more passes than its 13.8%; unseen: more than 16.1% passed, at most 6.1% failed,
failed + near-frozen at most 21.5%). Run once.

**G356 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): done after a take-profit 5.7% /
3.2%; the afternoon's take-profit 0.5 11.4% / 4.2%, 1.0 12.8% / 3.7%. Unseen (933; U57 16.1% / 6.1% / 21.5%): 9.5% /
4.8%, 12.9% / 6.4%, 16.0% / 6.3%. Trading on after a target pays: the second winner of a day is common. U57 stays.
`verification/noise_v2/g356_late_targets.txt`.

## G357: a side's losing run, or a runner past the target (registered 2026-11-08, before its run)

`research/g357_side_run_runner.py`: U57 with the next signal on a side skipped after 2 or 3 losing trades in a row on that
side, across days (`side_run_k` 2 / 3, `side_run_skip` 1; a winner on that side resets it), or with half the contracts
kept open past the take-profit, their stop at the entry plus half the target's distance (`tp_keep` 0.5, `runner_lock`
0.5) (3 variants). G253's measure and G332's rule (development: the best by passes with failures no higher than U57's
3.7%, and more passes than its 13.8%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most
21.5%). Run once.

**G357 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): skipping a side after 2 / 3
losers there 12.3% / 4.7%, 13.3% / 3.5%; the runner 8.4% / 4.0%. Unseen (933; U57 16.1% / 6.1% / 21.5%): 12.5% / 5.5%,
14.9% / 5.3%, 10.3% / 7.1%. A side's losing run does not predict its next trade well enough, and the runner gives back
the target's money (as G4 / G139 / G260 found). U57 stays. `verification/noise_v2/g357_side_run_runner.txt`.

## G358: bigger once the day is green, or a squeezed contract (registered 2026-11-08, before its run)

G10 / G11 pressed a green day in growth mode only. `research/g358_day_up_squeeze.py`: U57 with 1.5x the contracts (6 MNQ)
once today's closed P/L is above $0 or above $300 (`day_up_mult` 1.5, `day_up_from` 0 / 300; the room still cuts it), or,
when not even 1 contract fits the room, 1 MNQ with its max loss cut to the room if that leaves at least 20 points of stop
(`squeeze_min` 20) (3 variants). G253's measure and G332's rule (development: the best by passes with failures no higher
than U57's 3.7%, and more passes than its 13.8%; unseen: more than 16.1% passed, at most 6.1% failed, failed +
near-frozen at most 21.5%). Run once.

**G358 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): 6 MNQ once the day is green
14.8% / 5.9%, once up $300 15.3% / 4.7% (past the failure bound); the squeezed contract 13.8% / 3.7% (no change).
Unseen (933; U57 16.1% / 6.1% / 21.5%): 16.6% / 7.5%, 16.0% / 7.1%, 16.1% / 6.1%. Pressing a green day is one more way to
buy passes with failures. U57 stays. `verification/noise_v2/g358_day_up_squeeze.txt`.

## G359: the max loss scaled by the noise (registered 2026-11-08, before its run)

U57's max loss is a fixed $187.50 a contract; G302 / G338 moved the fixed amount. `research/g359_ml_sigma.py`: U57 with
the max loss set at each check to 0.6, 0.9 or 1.2 x the noise (sigma) x the close x $2 a contract (`ml_sigma`, G51; wider
on wild days, tighter on calm ones; about $187.50 at 0.9 when sigma x close is about 104 points) (3 variants). G253's
measure and G332's rule (development: the best by passes with failures no higher than U57's 3.7%, and more passes than
its 13.8%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most 21.5%). Run once.

**G359 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): the max loss at 0.6 / 0.9 / 1.2
x the noise 10.9% / 4.9%, 12.1% / 3.5%, 11.6% / 3.7%. Unseen (933; U57 16.1% / 6.1% / 21.5%): 12.0% / 6.8%, 14.3% / 6.6%,
12.3% / 8.3%. (The registration's "about $187.50 at 0.9" was an estimate, not measured.) The fixed max loss stays. U57
stays. `verification/noise_v2/g359_ml_sigma.txt`.

## G360: no entries once the day is stretched (registered 2026-11-08, before its run)

New logic: a breakout late in a day that has already moved far is often near its end. `research/g360_exhaustion.py`:
U57 with no new entries at a check once today's high-low range since 09:30 is above 1.25x, 1.5x or 2x the average of the
last 10 sessions' ranges (3 variants; `exhaust_k`, new in mnqbot/noise.py; open trades run as usual). G253's measure and
G332's rule (development: the best by passes with failures no higher than U57's 3.7%, and more passes than its 13.8%;
unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most 21.5%). Run once.

**G360 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): no entries past 1.25x / 1.5x /
2x the usual range 7.9% / 4.7%, 8.9% / 4.2%, 13.1% / 4.0%. Unseen (933; U57 16.1% / 6.1% / 21.5%): 11.9% / 4.3%, 13.5% /
4.9%, 15.2% / 6.3%. The stretched days are the trend days that pay for the bot; late breakouts on them are not spent.
U57 stays. `verification/noise_v2/g360_exhaustion.txt`.

## G361: breakouts out of a quiet half hour (registered 2026-11-08, before its run)

New logic (the "tight base before the breakout" of the setups traders teach): `research/g361_quiet_half_hour.py`: U57
with new entries at a check only when the high-low range since the previous check (09:30 for the first; the check's own
bar included) is at most 0.5, 0.75 or 1.0 x the check's noise (sigma) x the close (3 variants; `squeeze_k`, new in
mnqbot/noise.py). G253's measure and G332's rule (development: the best by passes with failures no higher than U57's
3.7%, and more passes than its 13.8%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most
21.5%). Run once.

**G361 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): a quiet half hour at most 0.5 /
0.75 / 1.0 x the noise 2.5% / 1.5%, 5.2% / 2.5%, 7.2% / 3.5%. Unseen (933; U57 16.1% / 6.1% / 21.5%): 3.9% / 4.9%, 5.8% /
4.9%, 7.9% / 5.7%. The bot's breakouts come out of fast half hours; asking for a quiet one removes the good ones and
keeps the failures. U57 stays. `verification/noise_v2/g361_quiet_half_hour.txt`.

## G362: breakouts out of a fast half hour (registered 2026-11-08, before its run)

G361's mirror: `research/g362_fast_half_hour.py`: U57 with new entries at a check only when the high-low range since the
previous check (as G361) is at least 0.5, 1.0 or 1.5 x the check's noise x the close (3 variants; `thrust_k`, new in
mnqbot/noise.py). G253's measure and G332's rule (development: the best by passes with failures no higher than U57's
3.7%, and more passes than its 13.8%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at most
21.5%). Run once.

**G362 result (2026-11-08): rejected.** Development (405 weeks; U57 13.8% / 3.7% / 16.8%): a fast half hour at least 0.5 /
1.0 / 1.5 x the noise 6.9% / 2.7%, 1.7% / 1.0%, 1.0% / 0.5%. Unseen (933; U57 16.1% / 6.1% / 21.5%): 10.2% / 4.6%, 5.3%
/ 2.3%, 1.6% / 1.2%. With G361 this corrects G361's reading: the half hour's range sorts neither way; any filter on it
mostly removes trades, good and bad alike. U57 stays. `verification/noise_v2/g362_fast_half_hour.txt`.

## G363: U57's win rate (a measurement, registered 2026-11-08, before its run)

The user asks for at least 80% winning trades with many trades. `research/g363_win_rate.py`: U57's trades in each
two-week Test (all 10 sessions, not cut at the pass or fail; development and unseen starts as G253): the share of
winners (P/L above $0 after costs), trades a session, the average winner, loser and trade.

**G363 result (2026-11-08):** U57 wins **48.5%** of its trades on the development Tests (404 Tests, 8,699 trades, 2.15 a
session; average winner $238, loser −$176, trade +$25) and **50.4%** on the unseen ones (889 Tests, 17,920 trades, 2.02
a session; $271 / −$207 / +$34). A breakout bot: half its trades lose small, the winners pay. 80% winners needs a
different shape of trade. `verification/noise_v2/g363_win_rate.txt`.

## G364: small targets, wide stops: a high-win-rate grid (registered 2026-11-08, before its run)

The user's new bar: at least 80% winning trades, trading every day. A high win rate comes from a target nearer than the
stop. `research/g364_win_rate_grid.py`: U57 with the take-profit at 0.1, 0.15, 0.2 or 0.3 noise units (U57 0.75), the
stop buffer at 0.24 (U57) or 0.5, and the max-loss stop at 1x or 1.5x (16 variants). Per variant: G253's passed /
failed / near-frozen, and over all 10 sessions of each Test the share of winning trades, trades a session, the share of
sessions with a trade, and the average trade. **A candidate** must, on both the development and the unseen Tests: win
at least 80% of its trades, trade on at least 90% of the sessions, make more than $0 a trade after costs, and fail no
more Tests than U57 (development 3.7%, unseen 6.1%); among candidates, the most unseen passes. Run once.

**G364 result (2026-11-08): no candidate.** The highest win rate, the 0.1 take-profit with the 0.5 stop buffer, wins
72.3% of trades on both the development and the unseen Tests, at 2.7-3.0 trades a session, but makes $1.50 / $3.48 a
trade and passes 2.0% / 5.6% of Tests with 5.7% / 7.2% failed (U57: 48.5-50.4% winners, +$25-34 a trade, 13.8% / 16.1%
passed). No variant reaches 80% winners; every step toward it shrinks the winners until the costs eat them. Also measured:
**U57 trades on only 62-68% of sessions** (its filters sit out the rest; G364's variants the same). U57 stays.
`verification/noise_v2/g364_win_rate_grid.txt`.

## G365: an earlier break-even lock, for more winners (registered 2026-11-08, before its run)

A trade that reaches a small profit and then comes back can end as a small winner instead of a loser.
`research/g365_early_lock.py`: U57 (lock at 0.2 max losses, +2.5 points) with the lock at 0.05 or 0.1 max losses and the
stop then at the entry +1.0 or +2.5 points, with the take-profit at 0.3 or 0.75 (U57) (8 variants). G364's measures and
candidate rule (both sets: at least 80% winners, a trade on at least 90% of the sessions, more than $0 a trade, failures
no higher than U57's 3.7% / 6.1%; the most unseen passes). Run once.

**G365 result (2026-11-08): no candidate.** Win rates 45-53% on both sets (U57 48.5% / 50.4%): an earlier lock turns some
losers into scratches, but the stop at entry + 1-2.5 points is hit by ordinary noise, and after costs most scratches
are small losers. Passes fall (unseen 5.5-11.1%, U57 16.1%). U57 stays. `verification/noise_v2/g365_early_lock.txt`.

## G366: trading every session (registered 2026-11-08, before its run)

The user asks for a trade every day; U57 trades on 62-68% of sessions (G364). `research/g366_every_day.py`: U57 without
the calm filter (`calm_k` 0), without the range-position filter (`range_pos_min` 0), without the streak pause
(`streak_k` 0), without all three, and without all three at the entry width 0.5 instead of 0.7 (5 variants). G364's
measures. **Replaces U57** if on both sets it trades on more sessions than U57 and the Tests meet G332's rule
(development: more passes than 13.8%, failures at most 3.7%; unseen: more than 16.1% passed, at most 6.1% failed,
failed + near-frozen at most 21.5%). Run once.

**G366 result (2026-11-08): rejected.** Sessions with a trade, development / unseen (U57 68.0% / 62.4%): no calm filter
71.7% / 66.0% (passes 13.6% / 16.6%, failures 4.0% / 6.3%: past both failure bounds); no streak pause 69.7% / 63.9%;
no range-position filter 68.7% / 63.1%; none of the three 74.0% / 68.5% (10.4% / 14.4% passed, 4.7% / 7.0% failed);
also at entry width 0.5 80.5% / 75.3%, but 38% winners and 8.9% / 11.6% passed. The days U57 sits out are mostly days
with no breakout past the noise area at all; forcing trades on them adds losers. (Sessions after a failed Test count as
untraded here.) U57 stays. `verification/noise_v2/g366_every_day.txt`.

## G367: a new strategy, the failed-breakout fade (registered 2026-11-08, before its run)

For the user's 80% winners: trade against the breakouts that fail. `research/g367_fade.py` (its own simulator; the Test
measure is g250_test_week.one with these trades in place of the noise bot's): at a 30-minute check (10:00-15:30), when
the previous check closed past U57's entry line (the noise area at width 0.7, 18 sessions) and this one closes back
inside, enter the other way at the next bar's open; target 0.15 or 0.3 x the check's noise (sigma x the close), stop
0.6 or 1.0 x the noise the other side, out at 16:00 otherwise (4 variants). One position at a time, at most 4 a day, no
new entry once the day's closed P/L is up $1,500 or down $1,200; 4 MNQ, $0.62 a side a contract, 1 tick of slippage on
market and stop fills, the stop first when a bar reaches both. G364's measures and candidate rule (both sets: at least
80% winners, a trade on at least 90% of the sessions, more than $0 a trade, failures no higher than U57's 3.7% / 6.1%;
the most unseen passes). Run once.

**G367 result (2026-11-08): no candidate.** The fade with a 0.15 target and a 1.0 stop **wins 83% of its trades** on both
sets (83.1% / 83.2%), but **loses money**: −$5.27 / −$4.73 a trade, 0.0% / 1.0% of Tests passed and 11.1% / 20.2% failed.
The 0.15 / 0.6 version wins 78-79% at −$3.55 / +$0.99 a trade; 0.3 / 0.6 wins 66-67% at +$29 / +$12 a trade (passes
1.5% / 2.1%, failed 11.6% / 21.0%). It trades on 45-49% of sessions, 0.55-0.64 trades a session. 80% winners are
reachable by fading, but each loser (a failed fade, the breakout going on) takes several winners with it; per trade it
is about break-even before the Test, and the Test's floor ends it more often than U57 (6.1% unseen).
`verification/noise_v2/g367_fade.txt`.

## G368: the fade's levels (registered 2026-11-08, before its run)

G367's fade loses on the breakouts that go on. `research/g368_fade_levels.py`: G367's fade with the stop 1.0 noise away
(G367) or past the day's extreme so far (the high for a short, the low for a long, + 0.1 noise; no trade if the fill is
already past it), and the target 0.15 or 0.3 noise away or at the day's 09:30 open when it lies the trade's way (else
0.3 noise) (6 variants; the rest as G367). G364's measures and candidate rule (both sets: at least 80% winners, a trade
on at least 90% of the sessions, more than $0 a trade, failures no higher than U57's 3.7% / 6.1%; the most unseen
passes). Run once.

**G368 result (2026-11-08): no candidate.** The 0.15 target with the stop past the day's extreme wins **82.0% / 82.6%**
of trades (development / unseen) at −$1.51 / +$4.28 a trade, 0.57-0.63 trades a session on 45-49% of sessions, 0.0% /
0.4% of Tests passed and 11.6% / 17.6% failed. The target at the open wins 62-64% (+$45 / +$2 a trade, 35% of unseen Tests
failed). At about 80% winners the fade makes a few dollars a trade at best: too little to reach $3,000 in ten sessions,
and its rare large losers end Tests far more often than U57 (6.1%). U57 stays. `verification/noise_v2/g368_fade_levels.txt`.

## G369: more regular-hours trades: U57 plus the trend pullback (registered 2026-11-08, before its run)

The user: trade more in 09:30-16:00 and make more. The trend pullback (`trendpb`, research/patterns.py, 3R) was the one
pattern that held up on held-out history (docs/RESULTS.md, "The ONYX models"). `research/g369_add_pullback.py`: U57 with
the pullback's trades added in the same Test account, entries to 12:00 or to 15:30, sized to $250 or $500 of risk
(1-10 MNQ) (4 variants; two positions can be open at once, and the pullback does not see U57's day rules, so a real
build would need them shared). `patterns.execute` now also returns each trade's exit time and prices. Measures: G253's
Test and G364's, plus the net per session. **A candidate** must trade more a session than U57 on both sets and meet
G332's rule (development: more passes than 13.8%, failures at most 3.7%; unseen: more than 16.1% passed, at most 6.1%
failed, failed + near-frozen at most 21.5%). Run once.

**G369 result (2026-11-08): no candidate.** Trades a session, development / unseen (U57 2.15 / 1.92): +2-6% with the
pullback to 12:00, +40-47% with it to 15:30 (2.99-3.05 / 2.74-2.83, a trade on 84-88% of sessions). Net a session (all
10 sessions of each Test, at the sprint's size; U57 $54 / $65): $56-70 / $71-96. But the Tests fail far more often
(unseen 12.9-43.6% against U57's 6.1%) and pass less (12.4-14.3% against 16.1%). Part of that is the test's shortcut:
U57 sizes to its own room and does not see the pullback's losses, so it oversizes after them; a shared build would
size both from one room, with fewer passes from the smaller size. Either way, more trades here buy a little more money
with many more blown Tests. U57 stays. `verification/noise_v2/g369_add_pullback.txt`.

## G370: U57 plus the fade when U57 is flat (registered 2026-11-08, before its run)

`research/g370_u57_plus_fade.py`: U57 with G368's best-win-rate fade (target 0.15 noise, stop past the day's extreme) at
1 or 2 MNQ, keeping only the fade trades during which U57 has no position (2 variants; the same shortcut as G369: U57
does not see the fade's P/L). Measures as G369. **A candidate** must, on both sets, meet G332's rule (development: more
passes than 13.8%, failures at most 3.7%; unseen: more than 16.1% passed, at most 6.1% failed, failed + near-frozen at
most 21.5%) with more trades a session than U57. Run once.

**G370 result (2026-11-08): no candidate.** With the fade on when U57 is flat: winners 56.5% / 58.3% (development / unseen;
U57 48.5% / 50.4%), 2.73 / 2.46 trades a session (U57 2.15 / 1.92), a trade on 77% / 72% of sessions (68% / 62%), net a
session $60-65 / $73-81 (U57 $54 / $65). Passes 14.1-14.3% / 15.2-15.5% (U57 13.8% / 16.1%) but failures 6.4-10.9% /
11.3-14.9% (U57 3.7% / 6.1%), with the same shortcut as G369. U57 stays. `verification/noise_v2/g370_u57_plus_fade.txt`.

## G371: the funded account month by month (a measurement, registered 2026-11-08, before its run)

The user's goal is $750 a day. `research/g371_funded_by_month.py`: the funded growth mode (U48's settings: 50K, $2,000
end-of-day trailing floor, $900 daily loss, 60-minute time stop, sizes growing with the account) from a fresh start on
the first Monday of every quarter (index 2011-2025, NQ 2015-2024), 12 months each. Per month since the start: $ per
session (mean and median), the share of sessions at $750 or more, and the share of starts whose floor has been
touched (end of day) by then.

**G371 result (2026-11-08):** 95 starts (index 2011-2025, NQ 2015-2024), 12 months each. $ per session by month since the
start: 1 $30, 2 $35, 3 $34, 4 $45, 5 $65, 6 $33, 7 $61, 8 $71, 9 $85, 10 $102, 11 $94, 12 $122; over the year $64 (index)
/ $67 (NQ). The median session is $0 (most sessions have no trade or a scratch); sessions at $750 or more: 1.5% in month 1,
8-9% by months 10-12. No start touched the floor at an end of day. A single funded account does not reach $750 a
session on average in its first year; the long histories' ~$225 a session (U48's nets) come from the later years, at
the larger sizes. `verification/noise_v2/g371_funded_by_month.txt`.

## G372: one funded account, faster sizing (registered 2026-11-08, before its run)

The user: one account, $750 a day, "a little riskier" is fine as long as the account is not lost.
`research/g372_faster_growth.py`: the funded growth mode (U48: 1 MNQ, +1 per $1,500, the $650 steps from $9,000)
starting at 4, 6 or 8 MNQ, a contract more per $1,000 or $600 of profit, the $650 steps from $3,000, the max loss at
$187.50 (U48) or $125 a contract (12 variants plus U48; the $900 daily loss, which caps the size, and everything else
as U48). *Revised before any result was seen:* the first version (1-4 MNQ, and a bug that kept the position's max loss
at 1 MNQ's $187.50 however many contracts) was stopped at the user's request ("do not start at 1") with no output. Fresh starts on the first Monday of every quarter, 12 months each; **lost** = the
balance with the open trade at its worst price touches the floor at any time (stricter than G371's end of day; the
P/L after a loss counts as $0). Per variant: $ per session over the 12 months, months 1-3 and 10-12, the best month's
average, and the share of starts lost. **Rule:** the variant with the most $ per session on the development starts
(index 2011-2018) among those losing at most 5% of them is adopted for the funded mode if on the unseen starts (index
2019-2025, NQ 2015-2024) it also loses at most 5% and makes more a session than U48. Run once.

**G372 result (2026-11-08): rejected.** U48 (1 MNQ) makes $39 / $76 a session over the year on the development / unseen
starts ($18 / $40 in months 1-3, $73 / $116 in months 10-12, the best month $115 / $139) and loses 3.2% / 3.1% of the
accounts (the open trade at its worst price touching the floor; G371's end-of-day check saw none). Starting at 4-8 MNQ
loses **27-43% / 27-49%** of the accounts within the year and makes $35-62 / $55-94 a session (the best months $72-105 /
$104-136), the P/L after a loss counted as $0. None loses at most 5%. The $900 daily loss and the $2,000 floor leave room
for about 4-5 contracts at $187.50 at the start; more contracts mean tighter stops ($125: fewer winners) or the floor.
No variant comes near $750 a session. U48 stays the funded mode. `verification/noise_v2/g372_faster_growth.txt`.

**A quick look after G372 (not registered; one path per set, 2026-11-08):** U48 funded from 2015-04-06 on NQ, $ a
session by calendar year: 2015 $26, 2016 $258, 2017 $81, 2018 $314, 2019 $184, 2020 $354, 2021 $123, 2022 $269, 2023
$253, 2024 $161, 2025 (to June) $933. From 2019-01-07 on the index: 2019 $18, 2020 $474, 2021 $151, 2022 $256, 2023
$112, 2024 $203, 2025 $482, 2026 (to September) $205. One account passes $750 a session for a year only once in these
two paths, years in, at the sizes it has grown to by then.

## G373: a new angle, size the trend days: the opening drive (registered 2026-11-08, before its run)

The bot's money is in a few trend days (docs/RESULTS.md); G318 used the opening drive only to block entries against
it. Here it sizes: `research/g373_drive_size.py`: the funded mode (U48) where, when 09:30-10:00 moves more than 0.25 or
0.5 x the average of the last sessions' ranges, entries with that move take 2x or 1.5x the contracts and entries
against it 1x or 0.5x (6 variants: 2x / 1x, 2x / 0.5x, 1.5x / 1x at each threshold; `drive_size_k`, `drive_mult`,
`drive_against_mult`, new in mnqbot/noise.py; the room still cuts the size). G372's measure and rule (development:
the most $ a session among variants losing at most 5% of the starts; unseen: at most 5% lost and more $ a session than
U48). Run once.

**G373 result (2026-11-08): rejected.** Development (index 2011-18 starts; U48 $39.2 a session, 3.2% lost): the drive past
0.25 $44-50 but 6.4% lost; past 0.5 $36.6-38.1 with 0% lost. Among variants losing at most 5%, U48 makes the most, so
nothing goes forward. Unseen (U48 $75.7, 3.1% lost): past 0.25 $83-91 (10.8-14.0% lost), past 0.5 $81-82 (7.8-9.6%
lost); the best months $161-177 against $139. Sizing up with the opening drive adds $5-15 a session and two to four
times the lost accounts. U48 stays. `verification/noise_v2/g373_drive_size.txt`.

## G374: tilt the size toward the trend days, not up (registered 2026-11-08, before its run)

G373: entries with the opening drive pay more, but sizing them up adds lost accounts. Here the extra size on them is
paid for by smaller size elsewhere. `research/g374_drive_tilt.py`: the funded mode (U48) with the drive past 0.25 or 0.5,
entries with it / against it / on days with no such drive (and before 10:00) at 1.5x / 0.5x / 0.75x, 2x / 0.5x / 0.5x,
or 1.5x / 0.75x / 0.75x the contracts (6 variants; `drive_none_mult`, new in mnqbot/noise.py). G372's measure and rule.
Run once.

**G374 result (2026-11-08): rejected, the nearest miss so far.** Development (U48 $39.2 a session, 3.2% lost): the pick,
the drive past 0.5 with 1.5x with it / 0.5x against / 0.75x on other days, **$43.9 with 0% lost**. Unseen (U48 $75.7,
3.1% lost): **$80.1, but 6.2% lost**, past the 5% bound. The others at 0.25: $86-89 with 10.8-12.4% lost. The tilt keeps
most of G373's gain with fewer lost accounts, but on the unseen starts still twice U48's. U48 stays.
`verification/noise_v2/g374_drive_tilt.txt`.

## G375: add to the trend days' winners (registered 2026-11-08, before its run)

The trend-day angle again, without more risk at entry: add contracts only once a trade is locked in profit.
`research/g375_add_trend_days.py`: the funded mode (U48) adding 2 or 4 MNQ at the next bar's open once the lock arms,
sharing the trade's exits (`add_at_lock`), on every trade or only on trades with the opening drive past 0.5
(`add_drive_only`, new in mnqbot/noise.py) (4 variants). G372's measure and rule (development: the most $ a session
among variants losing at most 5% of the starts; unseen: at most 5% lost and more $ a session than U48). Run once.

**G375 result (2026-11-08): rejected.** Development (U48 $39.2 a session, 3.2% lost): adding 2 / 4 at the lock on every
trade $52.3 / $48.1 with 32% / 49% lost; on drive days only $39.2 / $32.8 with 6.6% / 25.8% lost. No variant within 5%
lost beats U48, so nothing goes forward. Unseen (U48 $75.7, 3.1%): 2 on drive days only $80.3 with 4.7% lost; every
trade $48-54 with 33-61% lost. Adding at the lock turns the lock's small wins into full losers when the trade comes back.
U48 stays. `verification/noise_v2/g375_add_trend_days.txt`.

## G376: let the trend days run (registered 2026-11-08, before its run)

The trend-day angle on the exit side, no extra size: `research/g376_drive_runners.py`: the funded mode (U48, take-profit
2.0 noise units) where entries in the direction of an opening drive past 0.25 or 0.5 take a 3.0 take-profit or none
(the stops, lock and 16:00 close as before) (4 variants; `drive_tp`, new in mnqbot/noise.py). G372's measure and rule
(development: the most $ a session among variants losing at most 5% of the starts; unseen: at most 5% lost and more $
a session than U48). Run once.

**G376 result (2026-11-08): rejected.** Development (U48 $39.2 a session, 3.2% lost): $35.2-38.7, 0-3.2% lost; none makes
more than U48. Unseen (U48 $75.7, 3.1%): $60.5-75.0. The 2.0 take-profit already lets the trend days run far enough.
U48 stays. `verification/noise_v2/g376_drive_runners.txt`.

## G377: more tries on the trend days, fewer on the others (registered 2026-11-08, before its run)

`research/g377_drive_losers.py`: the funded mode (U48: 3 losers a day) with the day's loser limit at 5 on days with an
opening drive past 0.25 or 0.5 and 3 on the others, or 3 / 2, or 4 / 2 (6 variants; `drive_losers`, new in
mnqbot/noise.py). G372's measure and rule (development: the most $ a session among variants losing at most 5% of the
starts; unseen: at most 5% lost and more $ a session than U48). Run once.

**G377 result (2026-11-08): rejected.** Development (U48 $39.2 a session, 3.2% lost): $31.1-38.5, 0-3.2% lost; none beats
U48. Unseen (U48 $75.7, 3.1%): $70.5-74.8. More tries on drive days add nothing; fewer on the others cost. U48 stays.
`verification/noise_v2/g377_drive_losers.txt`.

## G378: the user's video: the morning range swept, then reclaimed (registered 2026-11-08, before its run)

The video (TikTok @whaley_nq, MNQ 1-minute, Oct 28): price sweeps the "NY AM Low", reclaims it ("CISD"), long 9 MNQ with
the stop under the sweep and the target at the "NY AM High", +$2,214. One trade, picked by its poster. As a rule
(`research/patterns.py` setups `amsweep` / `amsweep_cisd`, new; `research/g378_am_sweep.py`): the 09:30-10:00 range;
after 10:00, once price trades below its low (above its high), the first 5-minute close back inside the range (with
`_cisd` also above the previous bar's high / below its low) enters at the next open; stop a tick past the sweep's
extreme; target the range's other side, 1R or 2R; entries to 12:00 or to 15:30 (12 variants). patterns.py's execution
($500 risk, 1-10 MNQ, a tick of slippage, $0.62 a side, one trade at a time, flat at 16:00). **Rule:** the variant with
the best profit factor on NQ 2015-2019 (at least 50 trades a year) passes if it has a profit factor of at least 1.2 and
makes money on NQ 2020-2025, the index 2011-2026 and the 2025-2026 stand-in; only then is it tried with the funded bot.
Run once.

**G378 result (2026-11-08): rejected.** The best on NQ 2015-2019, `amsweep` to 15:30 with a 2R target, has a profit factor
of 1.10 there (+$6,846 a year at $500 risk, 286 trades a year) and loses on every other set: NQ 2020-2025 0.87 (−$9,966 a
year), the index 0.98 (−$1,170), the stand-in 0.90 (−$7,075). Every one of the 12 variants has a profit factor under 1
on all three later sets (0.72-0.99). The video's trade is one morning; as a rule the sweep-and-reclaim of the 09:30-10:00
range loses after costs. `verification/noise_v2/g378_am_sweep.txt`.

## G379: size by the volatility regime, funded (registered 2026-11-08, before its run)

`research/g379_vol_regime.py`: the funded mode (U48) with each entry's contracts times the ratio of the last calm_short
sessions' average range to the last calm_long sessions' (bigger when the market has woken up), or its inverse (smaller
then), kept within 0.5-1.5x or 0.75-2x (4 variants; `vol_pro`, `vol_lo`, `vol_hi`, new in mnqbot/noise.py; G317 tried
the inverse on the Test sprint only). G372's measure and rule. Run once.

**G379 result (2026-11-08): rejected.** Development (U48 $39.2 a session, 3.2% lost): $34.6-37.8 at 3.2% lost; none beats
U48, so nothing goes forward. Unseen (U48 $75.7, 3.1%): against the regime (smaller when the market has woken up)
$82.3 / $81.3 at 3.2% / 3.1% lost; with it $74.5-75.4 at 6.3%. The inverse-volatility sizing is the best unseen result at
U48's loss rate so far (+$6.6 a session), but it lost $1.7 a session on the development starts, so by the rule it is
not adopted. U48 stays. `verification/noise_v2/g379_vol_regime.txt`.

## G380: the day lock on the funded account (registered 2026-11-09, before its run)

U57's day lock (G294 / U57) protects a green day in the Test; the funded mode has never had it.
`research/g380_funded_day_lock.py`: U48 with the day lock at $800 keeping $300, $1,500 keeping $750, or $3,000 keeping
$1,500 (3 variants; `day_lock_at` / `day_lock_keep`). G372's measure and rule. Run once.

**G380 result (2026-11-09): rejected.** Development (U48 $39.2 a session, 3.2% lost): the pick, the lock at $800 keeping
$300, $41.5 with 0% lost. Unseen (U48 $75.7, 3.1%): $71.6 at 3.1%, less than U48; the others $69.5-74.4. U48 stays.
`verification/noise_v2/g380_funded_day_lock.txt`.

## G381: the funded account's exits again (registered 2026-11-09, before its run)

`research/g381_funded_exits.py`: U48 as G372 runs it (take-profit 2.0 noise units, time stop 45 minutes from the U48
settings file, which overrides the runner's 60; G371 / G372's "60-minute time stop" wording was wrong, the runs used 45)
with the take-profit at 1.5, 2.5 or 3.0, or the time stop at 30 or 90 minutes (5 variants). G372's measure and rule.
Run once.

**G381 result (2026-11-09): rejected.** Development (U48 $39.2 a session, 3.2% lost): the pick, take-profit 2.5, $41.1 at
3.2%. Unseen (U48 $75.7, 3.1%): $71.8 at 4.7%, less than U48; the others $63.9-74.7. U48's exits stay.
`verification/noise_v2/g381_funded_exits.txt`.

## G382: the Test sprint's signal settings on the funded account (registered 2026-11-09, before its run)

The funded mode (U48) enters at the full noise line (entry width 1.0) over 14 sessions, skips the 13:00 and 14:30
checks and stops entries at 15:00; the Test sprint (k317, G253-G270) found 0.7 over 18 sessions, every check, to 15:30.
`research/g382_funded_signals.py`: U48 with the entry width 0.85 or 0.7, the noise over 18 sessions, every check with
entries to 15:30, or all of k317's together (5 variants). G372's measure and rule. Run once.

**G382 result (2026-11-09): rejected.** Development (U48 $39.2 a session, 3.2% lost): every check with entries to 15:30
$57.9 but 6.6% lost; all of k317's $47.5 with 16.5% lost; entry width 0.7 $37.9 (3.2%), 0.85 $37.9 (6.4%), 18 sessions
$29.7 (6.4%). Within 5% lost U48 makes the most. Unseen (U48 $75.7, 3.1%): every check $73.4 (3.2%), the rest $54.8-73.3.
The sprint's signal settings suit a two-week push, not the funded account's year. U48 stays.
`verification/noise_v2/g382_funded_signals.txt`.

## G383: the funded mode's levers together, 60 random combinations (registered 2026-11-09, before its run)

The funded mode was tuned for long-run net (G1-G262); G372's measure is the first year's $ a session with the account
kept. `research/g383_funded_mix.py`: 60 random sets (seed 383; the first is U48) of: start at 2 MNQ ($375 max loss), a
contract per $1,000, the fast steps from $3,000, G379's inverse-volatility size (0.5-1.5x), G374's drive tilt, every
check with entries to 15:30, take-profit 2.5, time stop 90, the big-day rule at 2.0, the day lock at $800 / $300.
G372's measure and rule (development: the most $ a session among sets losing at most 5% of the starts; unseen: at most
5% lost and more $ a session than U48). Run once.

**G383 result (2026-11-09): rejected.** Development (U48 $39.2 a session, 3.2% lost): within 5% lost the best is fast steps
+ inverse-volatility size + drive tilt + every check to 15:30 + take-profit 2.5, **$55.7 at 3.4%**; starting at 2 MNQ
makes $48-68 but loses 13-29%. Unseen (U48 $75.7, 3.1%): the pick makes $76.5 but loses **6.3%**, past the bound. The
best unseen at most 5% lost: "step, vol, checks, day lock" $83.3 (4.7%) and "step, drive, checks, tp, big day" $83.4
(4.8%); the most unseen at any loss $87.4 (17.4% lost). The development gain does not carry over. U48 stays.
`verification/noise_v2/g383_funded_mix.txt`.

## G384: size by weekday, chosen on the development years (registered 2026-11-09, before its run)

Step 1 (development data only): U48's trades on the index 2011-2018 (one continuous run), $ a contract by the entry's
weekday; the weakest and the strongest weekday are named. Step 2 (`research/g384_weekday.py`): U48 with the weakest at
0.5x, the strongest at 1.5x, or both (3 variants; `weekday_mult`, new in mnqbot/noise.py, at least 1 contract). G372's
measure and rule. Run once.

**G384 step 1 (development only):** U48 on the index 2011-2018, $ a contract by entry weekday: Monday $20.29 (651 trades),
Tuesday $19.12 (730), **Wednesday $7.33** (736), Thursday $12.62 (780), **Friday $26.73** (650). Step 2's variants:
Wednesdays 0.5x, Fridays 1.5x, both.

**G384 result (2026-11-09): rejected, narrowly.** Development (U48 $39.2 a session, 3.2% lost): the pick, Wednesdays 0.5x
and Fridays 1.5x, **$57.2 with 0% lost**; Fridays 1.5x alone $52.8 (0%), Wednesdays 0.5x alone $43.8 (0%). Unseen (U48
$75.7, 3.1%): the pick **$81.0 but 6.1% lost**, past the 5% bound; Fridays 1.5x alone $86.1 at 4.6%; Wednesdays 0.5x
alone $73.6. U48 stays. `verification/noise_v2/g384_weekday.txt`.

## G385: size by the check's time, chosen on the development years (registered 2026-11-09, before its run)

Step 1 (development data only): U48's trades on the index 2011-2018 (one continuous run), $ a contract by the signal's
check time (bar end); the two weakest and the two strongest checks with at least 200 trades are named. Step 2
(`research/g385_check_time.py`): U48 with the weakest two at 0.5x, the strongest two at 1.5x, or both (3 variants;
`check_mult`, new in mnqbot/noise.py). G372's measure and rule. Run once.

**G385 step 1 (development only):** U48 on the index 2011-2018, $ a contract by fill time (the check's close): 09:35 (the
gap trade, not a check) $12.02 (1,334); **10:00 $24.57** (372); **10:30 $11.59** (303); **11:00 $20.08** (256); 11:30
$5.24 (198); **12:00 $39.07** (223); 12:30-15:00 $14.97-24.65 (126-158 each). With 200+ trades only 10:00, 10:30, 11:00
and 12:00 qualify: the weakest two 10:30 and 11:00, the strongest two 12:00 and 10:00.

**G385 result (2026-11-09): rejected.** Development (U48 $39.2 a session, 3.2% lost): the pick, both, $59.0 with 0% lost.
Unseen (U48 $75.7, 3.1%): $70.6 with 10.8% lost; 10:00 and 12:00 at 1.5x $75.1 (10.8%); 10:30 and 11:00 at 0.5x $68.0
(3.1%). The check-time pattern of 2011-2018 does not hold later: a development-chosen tilt, like G383 / G384, looks
strong in-sample and fades. U48 stays. `verification/noise_v2/g385_check_time.txt`.

## G386: the chop pause on the funded account (registered 2026-11-09, before its run)

G331 tried it on the Test sprint only. `research/g386_funded_chop_pause.py`: U48 with no trading for a session after 2,
3 or 4 sessions in a row that closed with a loss (3 variants; `red_days_pause`). G372's measure and rule. Run once.

**G386 result (2026-11-09): rejected.** Development (U48 $39.2 a session, 3.2% lost): the pick, a day off after 3 losing
days, $44.8 with 0% lost. Unseen (U48 $75.7, 3.1%): $61.3 at 3.1%; after 2 $53.7, after 4 $68.5. As in G331, the day
after a losing run pays as well as any other. U48 stays. `verification/noise_v2/g386_funded_chop_pause.txt`.

## G387: the day's loss budget before the floor stops (registered 2026-11-09, before its run)

U48 sizes each day to a $750 budget until the floor has stopped (`early_daily_loss`), $900 after (`daily_loss_limit`,
under the $1,000 daily loss). `research/g387_day_budget.py`: U48 with the early budget at $900, at $900 with the day's
at $950, or at $600 (3 variants). G372's measure and rule. Run once.

**G387 result (2026-11-09): not adopted.** Development (U48 $39.22 a session, 3.2% lost): the pick, the early budget at
$600, **$39.25** (+$0.03) at 3.2%; $900 $38.5 (6.4%); $900 / $950 $36.1 (6.4%). Unseen (U48 $75.72, 3.1%): **$76.21**
(+$0.49, +0.6%) at 3.1%. It meets the letter of G372's rule, which set no minimum gain; a change of 3 cents a session on
the development starts and 49 cents on the unseen ones is noise, not an improvement worth a new NinjaTrader build, so
U48 stays. (Later rules in this series will name a minimum gain.) `verification/noise_v2/g387_day_budget.txt`.

## G388: U48 plus the Williams breakout in the bot's gaps (registered 2026-11-09, before its run)

The Williams volatility breakout (rounds 97-101, docs/RESULTS.md) was the one outside setup positive with t >= 2 on all
three data sets; added in the bot's gaps it lifted $ a week by $85-130 on the older bot. `research/g388_williams_gaps.py`
rebuilds it on 5-minute bars (k 0.5, the first side only, entries by 15:00, stop 0.25 x yesterday's range, contracts to
$200 or $400 of risk, out at the close) and keeps a Williams trade only while no U48 trade is open (2 variants; U48 does
not see the Williams P/L when it sizes). G372's measure and rule with the minimum gain (development: the most $ a
session among variants losing at most 5% of the starts and at least 10% above U48; unseen: at most 5% lost and at least
10% more $ a session than U48). Run once.

**G388 result (2026-11-09): rejected.** Development (U48 $39.2 a session, 3.2% lost): with the Williams trades in the gaps
at $200 risk, **97% of the accounts lost**, $2.3 a session; at $400 all lost. Unseen (U48 $75.7, 3.1%): 82.5% / 95.1%
lost. A trace (index from 2012-04-02): U48 alone has a −$2,050 month without touching the floor; the Williams trades add
about −$700 in that month and the floor is touched. Part of this is the test's shortcut (U48 sizes to a room that does
not count the Williams P/L, so it oversizes after Williams losses); a shared build would size both from one room and
make less. Either way, at a $2,000 trailing floor the account has no spare room for a second strategy. U48 stays.
`verification/noise_v2/g388_williams_gaps.txt`.

## G389: the funded levers together again, 100 random combinations (registered 2026-11-09, before its run)

`research/g389_funded_mix2.py`: 100 random sets (seed 389; the first is U48) of: a contract per $1,000, the fast steps
from $3,000, inverse-volatility size (0.5-1.5x or 0.75-1.25x), the drive tilt (1.5 / 0.5 / 0.75 or 1.25 / 0.75), Wednesdays
0.5x or Fridays 1.25x, every check to 15:30 or only 13:00 skipped, take-profit 2.5 or 1.75, time stop 90 or 60, the
big-day rule at 2.0, the day lock ($800 / $300 or $1,500 / $750), the early budget $600, 2 or 4 losers a day. G372's
measure with the minimum gain (development: the most $ a session among sets losing at most 5% and at least 10% above
U48; unseen: at most 5% lost and at least 10% more $ a session than U48). Run once.

**G389 result (2026-11-09): rejected.** Development (U48 $39.2 a session, 3.2% lost): the pick (the most $ within 5% lost,
at least 10% above U48) "step, drive, weekday, checks, time stop, day lock, early budget" **$67.2 with 0% lost** (+71%).
Unseen (U48 $75.7, 3.1%): **$75.6 with 8.0% lost**: the gain vanishes and the losses rise. The next development picks:
$50.2 → unseen $96.2 at 6.3% lost; $46.8 → $99.6 at 6.2%; $45.8 → $77.9 at 3.2%. The best unseen within 5% lost,
"fast, drive, tp, time stop, big day, early budget, losers", $102.0 at 3.1%, was not a development pick (it made $26.2 there, less than U48);
choosing it now would be choosing on the unseen weeks. Large combinations fit the development years and do not hold. U48 stays.
`verification/noise_v2/g389_funded_mix2.txt`.

## G390: faster steps once the cushion is big (registered 2026-11-09, before its run)

U48 adds a contract per $1,500 of profit, then per $650 from $9,000 (G142). `research/g390_fast_steps.py`: the faster steps
at $400 or $300 from $9,000, or $400 from $6,000 (3 variants). G372's measure and rule with the 10% minimum gain. Run
once.

**G390 result (2026-11-09): rejected.** Development (U48 $39.2 a session, 3.2% lost): $37.5-39.9 (at most +1.7%), short of
the 10% minimum. Unseen (U48 $75.7, 3.1%): $77.1-79.4 at 3.1%. Few accounts pass $9,000 within the first year, so the
faster steps barely act in it. U48 stays. `verification/noise_v2/g390_fast_steps.txt`.

## G391: one funded account over three years (a measurement, registered 2026-11-09, before its run)

When does one account reach $750 a session? `research/g391_three_years.py`: U48 funded from the first Monday of every
quarter (index 2011-2023, NQ 2015-2022), run 36 months each: by month since the start, the $ a session (lost accounts at
$0 from the loss), the share of starts making $750 a session or more that month, and the share lost (intraday check).

**G391 result (2026-11-09):** 80 starts, 36 months each. $ a session by month: 1 $32, 6 $39, 12 $128, 18 $167, 24 $170,
30 $200, 36 $188; it levels off at about **$190-230 a session from month 22** (best month average $290, month 34). The
share of starts making $750 or more in a month: 0-2.5% in year one, 4-9% in years two and three. Lost: 2.5% (by month 6;
none after). The plateau suggests the $900 daily loss budget, not the account's growth, caps the size. `verification/
noise_v2/g391_three_years.txt`.

## G392: what caps the funded account (a measurement, registered 2026-11-09, before its run)

To check the plateau's cause: G391's run with the bot's daily loss budget at $900 (U48), $2,000 or $3,000 (hypothetical:
the account's $1,000 daily loss rule allows only the first), months 25-36 only reported (`research/g392_day_cap.py`).
Not a candidate for the bot.

**G392 result (2026-11-09):** months 25-36, 80 starts: U48 ($900 day budget) **$215 a session**, 7.7% of months at $750+,
2.5% lost; a $2,000 budget $267, 14.2%, 3.8% lost; a $3,000 budget $309, 18.0%, 3.8% lost. The day budget does cap the
grown account, but even three times U48's (past the account's $1,000 daily loss rule) gives $309 a session in year three.
On one 50K account with this signal, $750 a session on average is not in reach of size alone.
`verification/noise_v2/g392_day_cap.txt`.

## G393: the grown account's day budget in smaller pieces (registered 2026-11-09, before its run)

G392: the day budget caps the grown account. U48 lets a trade risk all of the day's budget left (`budget_frac` 1), so a
big loser ends the day. `research/g393_budget_frac.py`: U48 with each trade risking half or two thirds of what is left
(2 variants), 36 months from quarterly starts; judged on months 13-36: development (index starts 2011-2016) the most $ a
session within 5% lost and at least 10% above U48; unseen (index 2017-2023, NQ 2015-2022) at most 5% lost and at least
10% more than U48. Run once.

**G393 result (2026-11-09): rejected.** Months 13-36: development (23 starts; U48 $143.7 a session, 4.3% lost) half the
budget $91.7, two thirds $102.9; unseen (57 starts; U48 $212.7, 1.8%) $97.9 / $134.4. Smaller pieces cut the size of
every trade, including the trend days'. U48 stays. `verification/noise_v2/g393_budget_frac.txt`.

## G394: the grown account's daily limits (registered 2026-11-09, before its run)

`research/g394_grown_limits.py`: U48 with 4 or 5 losers a day once the floor has stopped (`max_losers_locked`; U48 3), or
the day budget at $975 instead of $900 (still under the $1,000 daily loss) (3 variants). G393's measure and rule (months
13-36). Run once.

**G394 result (2026-11-09): rejected.** Months 13-36: development (U48 $143.7 a session, 4.3% lost) the $975 day budget
$155.8 (+8.4%, short of the 10% minimum), 4 or 5 losers $138.1; unseen (U48 $212.7, 1.8%) $224.3 (+5.5%), $213.5-213.6.
The extra $75 of daily budget buys about 5-8% more, in line with G392, and leaves only $25 against slippage before the
$1,000 daily loss. U48 stays. `verification/noise_v2/g394_grown_limits.txt`.

## G395: the year-one near misses on the grown account (registered 2026-11-09, before its run)

G382 / G379 / G374 helped on some sets in year one; the grown account (months 13-36) has more cushion.
`research/g395_grown_signals.py`: U48 with every check and entries to 15:30, the inverse-volatility size (0.5-1.5x),
the drive tilt (1.5 / 0.5 / 0.75), or every check with the inverse-volatility size (4 variants). G393's measure and rule
(months 13-36; 10% minimum gain on development and unseen, at most 5% lost). Run once.

**G395 result (2026-11-09): rejected.** Months 13-36: development (U48 $143.7 a session, 4.3% lost) $132.7-143.4; unseen
(U48 $212.7, 1.8%) $196.1-212.5. None makes more than U48 on the grown account. U48 stays.
`verification/noise_v2/g395_grown_signals.txt`.

## G396: one bigger account (a measurement, registered 2026-11-09, before its run)

G391 / G392: on a 50K the day budget caps the bot at about $200 a session. `research/g396_bigger_account.py`: U48 as it
is, on a 50K ($2,000 floor, $900 day budget, $750 before the floor stops), a 100K-style account ($3,000 floor, $1,800 /
$1,500) and a 150K-style account ($4,500 floor, $2,700 / $2,250), the rest of U48's 50K settings unchanged (not tuned
for the bigger accounts). G391's starts and 36 months; by year: $ a session, months at $750+, lost (intraday, each
account's own floor). A measurement, not a candidate.

**G396 result (2026-11-09):** $ a session by year (80 starts): 50K (U48) $68 / $171 / $215 (lost 2.5%); 100K-style $84 /
$217 / $278 (1.2%); 150K-style $91 / $208 / $323 (0%). Months at $750+: 2-8% (50K), 3-14% (100K), 4-19% (150K). Even
a 150K-style account with U48's untuned settings averages about $320 a session in year three; $750 a session on average
is not reached on any single account size tested. `verification/noise_v2/g396_bigger_account.txt`.

## G397: the 150K-style account's sizing (registered 2026-11-09, before its run)

`research/g397_150k_sizing.py`: G396's 150K-style account ($4,500 floor, $2,700 / $2,250 day budgets) with U48's sizing,
or starting at 2 or 3 MNQ ($187.50 a contract), a contract per $1,000, or a cap of 100 contracts (4 variants). Months
1-36; development (index starts 2011-2016) the most $ a session within 5% lost and at least 10% above the 150K as U48;
unseen (index 2017-2023, NQ 2015-2022) at most 5% lost and at least 10% more. Run once.

**G397 result (2026-11-09): starting at 2 MNQ passes for the 150K-style account.** Development (150K as U48 $137.2 a
session, 0% lost): start 2 MNQ **$154.9** (+13%, 0% lost); cap 100 $141.9; +1 per $1,000 $118.6; start 3 MNQ $91.4 (13%
lost). Unseen (150K as U48 $235.7, 0%): start 2 MNQ **$275.7** (+17%, 1.8% lost); year three $356 a session. This is
for a 150K-style account only (the user's is a 50K; U48 there is unchanged). The best one-account figure measured:
about $276 a session over three years, $356 in year three. `verification/noise_v2/g397_150k_sizing.txt`.

## G398: the 150K-style pick tuned further (registered 2026-11-09, before its run)

`research/g398_150k_more.py`: G397's pick (150K-style, start 2 MNQ) with a cap of 100 contracts, the fast $650 steps from
$6,000, or the day budget at $2,900 (under a $3,000 daily loss) (3 variants). G397's measure and rule against the pick.
Run once.

**G398 result (2026-11-09): rejected.** Development (G397's pick $154.9 a session, 0% lost): cap 100 $149.1, fast steps
from $6,000 $129.0, $2,900 day budget $135.8; none above the pick. Unseen (pick $275.7, 1.8%): $253.9-284.2. G397's pick
stays the best 150K-style setting: about $276 a session over three years, $356 in year three.
`verification/noise_v2/g398_150k_more.txt`.

## G399: G397's pick on the user's 50K (registered 2026-11-09, before its run)

The user: "do that on a 50k account". `research/g399_50k_start2.py`: U48 on the 50K starting at 2 MNQ ($187.50 a
contract), alone or with a cap of 100 contracts (2 variants), 36 months. G397's measure and rule against U48 (10%
minimum gain on development and unseen, at most 5% lost). Run once.

**G399 result (2026-11-09): rejected.** Months 1-36: development (U48 $107.5 a session, 4.3% lost) start 2 MNQ $85.8 with
**26.1% lost**; unseen (U48 $169.1, 1.8%) $146.5 with **15.8% lost**. On the 50K's $2,000 floor, 2 MNQ at the start loses
one account in six to four and makes less, the lost accounts counted at $0. U48 stays.
`verification/noise_v2/g399_50k_start2.txt`.

## G400: a big search on the 50K with the day budget free and the floor guarded (registered 2026-11-09, before its run)

The user: "fk this limit shit. just trade under right signals but have protected losses so i dont lose the account...
10000 trials". 10,000 sets would take about four days here (about 35 seconds a set over 80 starts x 36 months); this
runs 300. `research/g400_big_search.py`: 300 random sets (seed 400; the first is U48) over the day budget ($900 / $1,500
/ $2,000 / $3,000), the early budget ($750 / $1,000 / $1,500), a floor guard (the trade closed inside the bar before the
floor: off / $100 / $300 buffer), start 1 or 2 MNQ, steps $1,500 / $1,000, the fast steps from $9,000 / $6,000, the cap
60 / 100, take-profit 2.0 / 2.5, time stop 45 / 90, 3 / 4 losers, inverse-volatility size, the drive tilt, every check.
Measures (36 months; development index starts 2011-2016, unseen index 2017-2023 and NQ 2015-2022): $ a session, starts
lost (intraday floor check), share of days below −$1,000, worst day. **Rule:** on development, among sets losing at most
5% of the starts, the most $ a session; it is recommended if on unseen it also loses at most 5% and makes at least 10%
more than U48. Days below −$1,000 are reported (they break a $1,000 daily loss rule if the account has one). Results
appended in chunks to `verification/noise_v2/g400_big_search.csv` (resumable). Run once.

## G401: 2-5 contracts on the 50K (a measurement for the user, registered 2026-11-09, before its run)

The user: "change it to 2-5 contracts max" and "how much trades it takes a day". `research/g401_two_to_five.py`: U48 on
the 50K as it is, starting at 2 MNQ with at most 5, or 1 to 5 (2 variants), 36 months (G397's starts): $ a session,
trades a session, lost, year three.

**G401 result (2026-11-09):** 36 months. Development (23 starts) / unseen (57): U48 $107.5 / $169.1 a session, 1.53 /
1.57 trades a session, 4.3% / 1.8% lost, year three $173 / $232; **2-5 MNQ** $60.9 / $83.1, 1.21 / 1.38 trades,
**26.1% / 15.8% lost**, year three $78 / $95; **1-5 MNQ** $70.6 / $91.8, 1.55 / 1.60 trades, 4.3% / 1.8% lost, year three
$101 / $109. A 5-contract cap halves the grown account's $ a session; starting at 2 loses one account in four to six.
The bot is not changed (the NinjaTrader settings "Contracts" and "Most contracts" in Custom mode do this if wanted).
`verification/noise_v2/g401_two_to_five.txt`.

**G400 addendum (2026-11-09, while the run is in progress; interim development rows had been looked at, unseen not):**
the user asks for consistency ("dont have 1 good day and then endless bad days"). Before any recommendation, the set
the rule picks is re-run on the unseen starts with U48 for: the share of green weeks and green months, the longest
run of losing weeks, and the worst calendar month. It is recommended only if it is at least as consistent as U48 on
green months and the longest losing run.

**G400 addendum 2 (2026-11-09, before the unseen results):** the final check also reports, for the pick and U48 on the
unseen starts, trades a session and the share of green days among traded days; the user asks for as many trades as it
can and green days.

**G400 addendum 3 (2026-11-09):** the user's target is 80-90% green days; the final check reports the pick's share
against it.

**G400 result (2026-11-09): not recommended.** The run stopped at the session's 2-hour limit for a background job after
all 300 development sets and 180 of the 300 unseen ones (results in `verification/noise_v2/g400_big_search_final.csv`).
The rule's pick was among those done: on development (U48 $107.5 a session, 4.3% lost) the most $ within 5% lost is
"$2,000 day budget, a contract per $1,000, the fast steps from $6,000, inverse-volatility size, every check to 15:30",
**$143.1 with 0% lost**; on unseen (U48 $169.1, 1.8%) **$220.9 (+31%) with 3.5% lost**, 12.2% of days below −$1,000,
worst day −$2,000: it meets the $ / lost rule. The addenda's check (`research/g400_consistency.py`, unseen starts, 36
months; `verification/noise_v2/g400_consistency.txt`): pick / U48 $224.5 / $171.3 a session, trades a session 1.48 /
1.57, **green days (of traded days) 38.1% / 35.9%**, green weeks 42.9% / 45.7%, **green months 57.8% / 64.9%**, longest
run of losing weeks 5.3 / 5.3, worst month −$12,230 / −$6,215. It is less consistent than U48 on green months (and
weeks), so by the addendum it is not recommended. U48 stays. (Measured here for the first time: U48 ends about 36% of
its traded days and 65% of its months green; the money comes from fewer, larger winning days.)

## G402: more green days on the 50K (registered 2026-11-09, before its run)

The user wants mostly green days; U48 ends 36% of its traded days green (G400's check). `research/g402_green_days.py`:
U48 with a day lock at $300 keeping $100 or at $500 keeping $250, or no new entries once the day is up $400 or $800 (4
variants), 36 months. **Rule:** on development (index starts 2011-2016) and unseen (index 2017-2023, NQ 2015-2022) both:
green days at least 5 points above U48, $ a session at least 90% of U48's, lost at most 5%, green months no fewer. Run
once.

**G402 result (2026-11-09): rejected.** Green days of traded days, development / unseen (U48 37.1% / 35.9%): day lock
$300/$100 40.1% / 39.6% ($117 / $146 a session, unseen 10.5% lost); $500/$250 39.5% / 38.3% ($122 / $160); stop at +$400
40.4% / 40.3% ($53 / $67); +$800 39.0% / 38.5% ($64 / $92). None adds 5 points of green days at 90% of U48's $; capping
the green days removes the big days the money comes from. U48 stays. `verification/noise_v2/g402_green_days.txt`.

## G403: half off at a small profit, for green days (registered 2026-11-09, before its run)

`research/g403_partials.py`: U48 closing half the contracts at 0.5 or 1.0 times the max loss a contract in profit (the
limit working from the bar after the fill), or at 0.5 with the rest's stop then at the entry (3 variants; `partial_at`,
`partial_be`). G402's measure and rule (green days +5 points at 90% of U48's $, at most 5% lost, green months no fewer,
on development and unseen). Run once.

**G403 result (2026-11-09): rejected.** Green days, development / unseen (U48 37.1% / 35.9%): half off at 0.5R 39.9% /
39.5% at $64 / $78 a session (U48 $110 / $171); at 1R 38.7% / 38.1% at $92 / $124. At most 4 points more green days
for a quarter to half of the money. (The break-even variant ran identical to plain 0.5R: `partial_be` did not act in this
execution; not investigated, as the plain partial already fails.) U48 stays. `verification/noise_v2/g403_partials.txt`.

## G404: the trade lock sooner, for green days (registered 2026-11-09, before its run)

`research/g404_early_lock.py`: U48 (lock at 0.35 max losses, +2.5 points) with the lock at 0.25 or 0.2, or at 0.2 with
the stop at entry +5 points (3 variants). G402's measure and rule. Run once.

**G404 result (2026-11-09): rejected.** Green days, development / unseen (U48 37.1% / 35.9%): 37.0-37.5% / 35.7-36.9%,
no gain; $ a session lower ($94-99 / $128-163) and development losses 8.7-13.0%. A sooner lock does not make more days
green. U48 stays. `verification/noise_v2/g404_early_lock.txt`.

## G405: a nearer target or a shorter time stop, for green days (registered 2026-11-09, before its run)

`research/g405_target_time.py`: U48 (take-profit 2.0 noise units, time stop 45 minutes) with the take-profit at 1.5 or
1.0, or the time stop at 30 minutes (3 variants). G402's measure and rule. Run once.

**G405 result (2026-11-09): rejected.** Green days, development / unseen (U48 37.1% / 35.9%): 36.6-37.2% / 35.7-36.3%,
no gain; $ a session unseen $103-158 against $171. Across G402-G405 no exit or day rule moves U48's green days by more
than about 4 points: the bot's days are mostly small losses and a few large wins by construction. U48 stays.
`verification/noise_v2/g405_target_time.txt`.

## G406: fewer tries a day, for green days (registered 2026-11-09, before its run)

`research/g406_fewer_tries.py`: U48 (3 losers a day) with 2 or 1 loser a day, or no new entries once a take-profit fills
(3 variants). G402's measure and rule. Run once.

**G406 result (2026-11-09): rejected.** Green days, development / unseen (U48 37.1% / 35.9%): 2 losers 36.5% / 35.7%, 1
loser 35.8% / 35.0%, done after a take-profit 39.3% / 36.9% ($63 / $132 a session against $110 / $171). No gain in green
days worth the money. U48 stays. `verification/noise_v2/g406_fewer_tries.txt`.

## G407: the trend filter over three years (registered 2026-11-09, before its run)

U48 sizes trades against the 45-session trend to 1 MNQ (`trend_n` 45, `trend_small`). `research/g407_trend_filter.py`:
no trend filter, or the trend over 20 or 100 sessions (3 variants), 36 months on the 50K. Rule: on development and
unseen, at least 10% more $ a session than U48, at most 5% lost, green months no fewer. Run once.

**G407 result (2026-11-09): rejected.** Development (U48 $109.7 a session, 4.3% lost): trend over 20 sessions $133.1
(+21%, 0% lost, green months 67.1% vs 63.9%), over 100 $128.2, none $115.7. Unseen (U48 $171.3, 1.8%): over 20 $168.4
(−2%), over 100 $169.3, none $154.7. The development gain does not carry over. U48 stays.
`verification/noise_v2/g407_trend_filter.txt`.

## G408: a search around G400's pick, judged on money and consistency (registered 2026-11-09, before its run)

`research/g408_local_search.py`: 150 random sets (seed 408; U48 and G400's pick first) of: the day budget ($900 / $1,200
/ $1,500 / $2,000), steps ($1,500 / $1,250 / $1,000), fast steps from $9,000 / $6,000, inverse-volatility size (off /
0.5-1.5 / 0.75-1.25), checks (U48's / every to 15:30 / only 13:00 skipped), a day lock (off / $1,500 keep $750 / $2,500
keep $1,250), a floor guard ($200 buffer), the early budget ($750 / $600 / $900), the trend over 45 / 20 / 100 sessions.
36 months, development and unseen. **Rule:** on development, among sets losing at most 5% with green months at least
U48's, the most $ a session; recommended if on unseen it loses at most 5%, makes at least 10% more than U48, and has
green months at least U48's and a longest losing-week run no longer. Run once (resumable; results in
`verification/noise_v2/g408_local_search.csv`, copied to `g408_local_search_final.csv` when recorded).

**G408 result (2026-11-09): not recommended.** Development (U48 $109.7 a session, 4.3% lost, green months 63.9%): the pick
("$2,000 day budget, $1,500 steps, the fast steps from $6,000, inverse-volatility size 0.75-1.25x, only 13:00 skipped,
the day lock at $1,500 keeping $750") **$156.4 (+42%)**, 0% lost, green months 64.0%. Unseen (U48 $171.3, 1.8%, green
months 64.9%, longest losing run 5.3 weeks): **$219.3 (+28%)**, 3.5% lost, but **green months 61.5%** and a longest
losing run of 5.5 weeks: less consistent than U48, so by the rule not recommended. The next development picks: $153.8 →
$193.5 unseen (5.3% lost, 60.1% green months); $141.8 → $182.4 (1.8%, 60.7%); $141.6 → $198.8 (0%, **65.8%**, longest run
6.0). More money keeps coming with less steady months. U48 stays. `verification/noise_v2/g408_local_search_final.csv`.

## G409: a fresh check of G408's candidates (registered 2026-11-09, before its run)

`research/g409_fresh_check.py`: U48, G408's pick, and G408's steadiest strong set ("G408 steady": $1,200 day budget,
$1,250 steps, inverse-volatility 0.75-1.25x, the day lock $1,500 / $750, the trend over 20 sessions; unseen $198.8 a
session, 0% lost, 65.8% green months, not the rule's pick) on starts no search used: 12 months from the first Monday of
each quarter, NQ 2023-2024, the index 2024-2025, the MNQ stand-in from 2025. Caveat: the price history from 2023 on was
also inside G400-G408's unseen 36-month windows, so this is a check on new start dates, not fully new data. **Rule:** a
candidate is recommended if here it makes at least 10% more a session than U48, loses at most 5%, and has green months
no fewer. Run once.

**G409 result (2026-11-09): neither recommended.** 16 fresh starts (the log's "5" is a printing slip: it divided the
start count by the number of sets), 12 months each: U48 $30.4 a session, 6.2% lost (1 of 16), green days 43.1%, green
months 63.0%; G408's pick $32.4 (+7%, short of +10%), 6.2%, 59.9% green months; G408 steady $26.8 (−12%), 6.2%, 61.5%.
Neither beats U48 on these starts. U48 stays. `verification/noise_v2/g409_fresh_check.txt`.

## G410: a wide search on the 50K, money and consistency (registered 2026-11-09, before its run)

The user: "keep running and keep adding more". `research/g410_wide_search.py`: 200 random sets (seed 410; U48 first)
over the day budget ($900 / $1,200 / $1,500), steps ($1,500 / $1,250), take-profit (2.0 / 1.75 / 2.5), time stop (45 /
30 / 60), the trade lock (0.35 / 0.3 / 0.45), losers a day (3 / 2 / 4), inverse-volatility 0.75-1.25x, a mild drive
tilt (1.25 / 0.75), Wednesdays 0.75x, checks (U48's / only 13:00 skipped / every to 15:30), the day lock $1,500 / $750,
the big-day rule at 2.0, the trend over 45 / 20 / 100 sessions, the entry width 1.0 / 0.9. G408's measure and rule
(development: within 5% lost and green months at least U48's, the most $; unseen: at most 5% lost, at least 10% more
$, green months and the longest losing run no worse), then G409's fresh-start check (at least 10% more than U48 there,
at most 5% lost, green months no fewer) before any recommendation. Run once (resumable).

**G410 result (2026-11-09): not recommended.** Development (U48 $109.7 a session, green months 63.9%): the pick ("$1,500
day budget, take-profit 1.75, time stop 60, lock 0.3, 2 losers a day, the mild drive tilt, Wednesdays 0.75x, only 13:00
skipped, the day lock $1,500 / $750, the trend over 20 sessions") **$177.4 (+62%)**, 0% lost, green months 65.3%. Unseen
(U48 $171.3, 1.8% lost, green months 64.9%): **$208.5 (+22%)**, 1.8% lost, but **green months 62.4%**, longest losing
run 5.4 weeks: less consistent, so not recommended. Of the next five development picks, the best unseen are $220.8
(5.3% lost, 63.6%) and $217.1 (1.8%, 62.7%); none keeps U48's green months. Third search in a row (G400, G408, G410)
where more money comes with fewer green months. U48 stays. `verification/noise_v2/g410_wide_search_final.csv`.

## G411: the wide search again, consistency first (registered 2026-11-09, before its run)

`research/g411_wide_search2.py`: G410's knobs plus Fridays 1.25x, the early budget $600 and the fast steps from $6,000;
200 random sets (seed 411; U48 first); G408's measure. **Rule (consistency first):** on development, among sets losing
at most 5% with green months at least 3 points above U48's, the most $; recommended if on unseen it loses at most 5%,
makes at least 10% more than U48, keeps green months at least U48's and the longest losing run no longer, and then
passes G409's fresh-start check. Run once (resumable).

## G412: the breakout on gold, smaller and wider (registered 2026-11-09, before its run)

The user's chart (Micro Gold, 1-minute): "open urself to diff markets". Round 68 (docs/RESULTS.md) tried gold at 8 MGC
and $200 a trade: fees and slippage ate it ($19.71 / $2.27 a day, t 1.74 / 0.20). `research/g412_gold.py`: round 68's
engine on gold at 1 or 2 MGC with $100 / $200 / $300 of max loss a contract (6 variants). **Pass (round 68's bar):** a
variant with t >= 2.5 on 2011-2018 and t >= 1.5 on 2019 - Sep 2026, $ a day above 0 in both; only then is it tried on the
account with the Nasdaq bot. Run once.

**G412 result (2026-11-09): rejected.** Gold, 2011-2018 / 2019 - Sep 2026: the best, 2 MGC at $300 a contract, $8.48 /
$2.55 a day, t 1.64 / 0.43, 4.4-4.5 trades a week, 40% winners; every variant t 1.21-1.64 / 0.20-0.43, below the bar
(2.5 / 1.5). Smaller size cuts the costs but the breakout has almost no edge on gold, least of all in the recent years
(a $1-3 a day). Gold is not added. `verification/noise_v2/g412_gold.txt`.

## G413: other markets, small and wide (registered 2026-11-09, before its run)

The user: "explore diff markets for my goals". `research/g413_markets.py`: round 68's engine on silver, crude, the euro
(round 68 at 3-20 contracts and $200; here 1 or 2 at $100 / $200 / $300 a contract, as G412 did for gold), and two
markets never tried, the DAX and the Euro Stoxx 50 (Eurex micros, EUR 1 a point; whether the user's account can trade
them is not checked). **Pass (round 68's bar):** t >= 2.5 on 2011-2018 and t >= 1.5 on 2019 - Sep 2026 with $ a day
above 0 in both; only a passing market goes on to an account test with the Nasdaq bot. Run once.

**G413 result (2026-11-09): rejected, every market.** Best t on 2011-2018 / 2019-2026 across the 6 variants each:
DAX 0.80 / −0.26 (at most $4.60 a day), Euro Stoxx 50 t 0.43 on 2019-2026 ($3-6 a day), crude 0.31, silver 0.06, the
euro below; none near the bar (2.5 / 1.5). With round 68 (gold, silver, crude, euro) and G412 (gold), the Nasdaq
breakout has no worthwhile edge on any other market in the data. `verification/noise_v2/g413_markets.txt`.

## G414: seven more markets (registered 2026-11-09, before its run)

The user: "search every and all markets". `research/g414_more_markets.py`: G413's test on the FTSE 100, the CAC 40,
Brent, the pound, the Australian and New Zealand dollars and the dollar index (HistData 1-minute, 2011 - Sep 2026,
downloaded today; sessions and contract values in the script; which of these the account can trade is not checked).
The Dow and the Russell are not in the free data; the Nikkei, Hang Seng and ASX sessions cross midnight in New York
time and do not fit the engine. Round 68's bar. Run once.

**G414 result (2026-11-09): rejected, every market.** The best t of each market on either period: Brent 0.85 (2011-18;
−2.77 on 2019-26), FTSE −0.45, dollar index −0.50, CAC −1.50, pound −8.0, Australian dollar −9.7, New Zealand dollar
−12.4. Every variant of every market loses on 2019-2026. Across G412-G414 and round 68 (13 markets: gold, silver, crude,
Brent, the euro, the pound, the Australian and New Zealand dollars, the dollar index, the DAX, the Euro Stoxx 50, the
FTSE, the CAC), the noise-area breakout has no edge outside the US stock indices, and the S&P (MES) had none either
(docs/RESULTS.md). `verification/noise_v2/g414_more_markets.txt`.

**G411 result (2026-11-10): not recommended.** Only 2 of 200 sets lose at most 5% with green months 3 points above
U48's on development. The pick ("$1,500 day budget, take-profit 2.5, time stop 60, lock 0.45, inverse-volatility,
the mild drive tilt, Wednesdays 0.75x, the day lock, Fridays 1.25x, the early budget $600, the fast steps from $6,000")
makes $160.1 (+46%) with green months 67.4% on development; unseen $187.8 (+10%) with 3.5% lost but **green months
58.5%** (U48 64.9%): fails. The other, $158.0 → unseen $188.1 (0% lost, green months 63.6%), also falls short of U48's
green months. Fourth search in a row (G400, G408, G410, G411): steadier months on the development years do not stay
steadier on the unseen ones. U48 stays. `verification/noise_v2/g411_wide_search2_final.csv`.

## G415: the final pick for the 50K (registered 2026-11-10, before its run)

The user: "50k is all u get. Either size up, trade more, idc. Pick what u think is best and get my results"; only the
$2,000 drawdown matters. The two best money-first picks so far: G400's (unseen 36 months $224.5 a session, 3.5% lost)
and G410's ($208.5, 1.8% lost). `research/g415_final_pick.py`: both and U48 on G409's 16 fresh start dates, 12 months
each. **Rule:** the pick with the most $ a session there that makes at least 10% more than U48 and loses at most 5%
becomes the bot's funded mode (built into NinjaTrader with parity and the full test suite); if neither, U48 stays.
Run once.

**G415 result (2026-11-10): U48 stays.** On the 16 fresh starts (12 months): U48 **$30.4 a session**, 6.2% lost, green
months 63.0%; G400's pick $21.1 (−30%), 6.2% lost, 54.2%; G410's pick $15.1 (−50%), 0% lost, 63.5%. Neither beats U48
where no search looked. The money-first picks of the big searches (G400-G411) were fitted to the years they were chosen
on; the bot as it is (U48 funded, U57 for the Test) is the best measured for the 50K.
`verification/noise_v2/g415_final_pick.txt`.

## G416: size by how the previous session closed (registered 2026-11-10, before its run)

Hourly round. Not tested before: G386 paused after losing runs; nothing sized the next session by the last one's sign.
`after_green_mult` / `after_red_mult` in `mnqbot/noise.py` (off by default): the session after a green (red) one, every
entry takes that multiple of its contracts (at least 1; flat sessions count as neither). `research/g416_after_day.py`:
U48 with (green, red) = (1.5, 1), (1.25, 1), (1, 1.5), (1, 1.25), (1, 0.5), (0.5, 1). G372's 12-month measure and
rule, with the minimum gain: development pick = the most $ a session within 5% lost and at least 10% above U48; it
passes only if on unseen it loses at most 5% and makes at least 10% more $ a session than U48; then G409's fresh-start
check before anything is built. Run once.

**G416 result (2026-11-10): rejected.** Development (U48 $39.2 a session, 3.2% lost): the pick (within 5% lost, at least
10% above U48) "after green x1.5" **$46.9 with 0% lost** (+20%); "after red x1.5" made $50.7 but lost 16.3%. Unseen
(U48 $75.7, 3.1%): the pick **$79.5 with 0% lost, +5.0%**, under the 10% minimum gain. After red x1.5 $95.7 at 4.7% (not
the development pick: 16% lost there); after red x0.5 $64.3. The sign of yesterday adds little; U48 stays.
`verification/noise_v2/g416_after_day.txt`.

## G417: size within the day by today's P/L (registered 2026-11-10, before its run)

Not tested before: `after_loss_qty_div` cut the trade after a loss; nothing pressed after a winning start ("house
money"). `day_up_mult` / `day_down_mult` in `mnqbot/noise.py` (off by default): entries while today's closed P/L is above
(below) 0 take that multiple of their contracts (at least 1). `research/g417_house_money.py`: U48 with (up, down) =
(1.5, 1), (2, 1), (1, 0.5), (1, 1.5), (1.5, 0.5), (0.5, 1). G416's measure and rule (development pick within 5% lost and
at least 10% above U48; unseen at most 5% lost and at least 10% more $ a session; then G409's fresh starts). Run once.

**G417 result (2026-11-10): rejected (no development pick).** Development (U48 $39.2 a session, 3.2% lost): day up x2
$81.5 (+108%) at 9.8% lost; up x1.5 $76.7 at 10.1%; up x1.5 / down x0.5 $76.6 at 13.3%; down x1.5 $50.2 at 13.1%; down
x0.5 $34.2 at 3.2%; up x0.5 $30.8 at 0%. None makes 10% more within 5% lost. Unseen (U48 $75.7, 3.1%): up x1.5 $107.0
(+41%) at 12.7% lost; up x2 $106.6 at 31.3%. Pressing a green day pays, but at a small cushion the bigger trades reach
the floor. `verification/noise_v2/g417_house_money.txt`.

## G418: house money only on a grown account (registered 2026-11-10, before its run)

From G417: its losses come from pressing while the cushion is small. `day_up_from` in `mnqbot/noise.py` (0 = off): day
up x`day_up_mult` only while the account's closed profit is at least that. `research/g418_house_money_grown.py`: U48 with
up x1.5 or x2 from $2,000, $4,000 or $6,000 of profit (6 variants). G416's measure and rule. Run once.

**G418 result (2026-11-10): passes development and unseen; to the fresh check.** Development (U48 $39.2 a session, 3.2%
lost): the pick **day up x2 from $2,000 of profit, $43.3 with 3.2% lost** (+10.4%); x2 from $6,000 $41.7, x1.5 from
$6,000 $41.0, x1.5 from $2,000 $39.4, from $4,000 $38.6 / $36.8. Unseen (U48 $75.7, 3.1%): the pick **$92.9 with 4.7%
lost (+22.7%)**; x2 from $4,000 $92.8 at 3.1%; x1.5 from $4,000 $86.2 at 3.1%. The pick passes G416's rule (at most 5%
lost, at least 10% more). `verification/noise_v2/g418_house_money_grown.txt`.

## G419: the fresh-start check for G418's pick (registered 2026-11-10, before its run)

`research/g419_fresh_house.py`: G418's pick and U48 on G409's 16 fresh starts (G415's runner and table). **Rule:** the
pick becomes the funded mode (built into NinjaTrader with parity and the tests) if it makes at least 10% more $ a
session than U48 there and loses at most 5% more of the starts (at most one more start of 16). Else U48 stays. Run once.

**G419 result (2026-11-10): rejected; U48 stays.** On the 16 fresh starts (12 months): U48 **$30.4 a session**, 6.2%
lost (1 start), green months 63.0%; G418's pick **$25.7 (−15%)**, 12.5% lost (2 starts), green months 58.3%. The gain on
the older starts does not reach the fresh ones, as with G400's and G410's picks (G415).
`verification/noise_v2/g419_fresh_house.txt`.

## G420: no trades against the side of the day's first winner (registered 2026-11-10, before its run)

Hourly round. Not tested before: G-rounds blocked a side after it lost (`side_lost`, cooldowns), never the other side
after a win. `win_side_only` / `win_side_target` in `mnqbot/noise.py` (off by default): after today's first winning trade
(or the first that reached its target), no new entries on the other side that session. `research/g420_win_side.py`:
U48 with the block after the first winner, after the first target, and the first plus G417's day up x1.5. G416's
measure and rule (development pick within 5% lost and at least 10% above U48; unseen at most 5% lost and at least 10%
more $ a session; then G409's fresh starts). Run once.

**G420 result (2026-11-10): rejected.** Development (U48 $39.2 a session, 3.2% lost): no entries against the first
winner $38.3 (3.2%); against the first target $39.1 (3.2%); the first plus day up x1.5 $78.2 at 13.3% lost. No pick (none
10% above U48 within 5% lost). Unseen (U48 $75.7, 3.1%): $71.9 at 4.7%; $75.7 (the same trades: after a target the bot
rarely gets a second signal the other way); $99.3 at 18.9%. Trades against the day's winner pay as well as the rest.
`verification/noise_v2/g420_win_side.txt`.

## G421: trade more often on the funded account (registered 2026-11-10, before its run)

The user: "trade more". `research/g421_trade_more.py`, cumulative: A = U48 with every check (no skipped 13:00 / 14:30);
B = A without the range-position filter; C = B without the loser limit; D = C with entry lines at 0.8 noise (U48 1.0);
E = D with entries to 15:30. Run once on G409's 16 fresh starts (trades a session, $ a session, lost, green days and
months) and once on G372's development / unseen starts. **Rule:** the variant with the most trades a session on the fresh
starts that makes at least U48's $ a session on the fresh starts and on unseen, loses at most one more fresh start than
U48 and at most 5% of the unseen starts, becomes the funded mode (built with parity and the tests). Else U48 stays.

**G421 result (2026-11-10): rejected; U48 stays.** Fresh starts (U48 1.22 trades a session, $30.4, 1 of 16 lost): A 1.21 /
$28.6 / 1; B 1.31 / $27.9 / 1; C 1.38 / $29.4 / 0; **D 1.58 / $35.1 / 0**; E 1.59 / $26.5 / 1. Development (U48 $39.2,
3.2%): A $43.5 / 0%, B $51.7 / 6.7%, C $52.8 / 0%, D $51.6 / 0%, E $44.6 / 3.2%. Unseen (U48 $75.7, 3.1%): A $73.7 / 3.1%,
B $72.0 / 3.1%, C $72.5 / 3.2%, **D $66.5 / 4.7%**, E $76.0 / 4.7%. Only D makes more on the fresh starts (+16%, 30% more
trades), and it makes 12% less on unseen; E matches U48 on unseen and makes 13% less on the fresh starts. No variant
meets the rule. `verification/noise_v2/g421_trade_more.txt`.

## G422: the narrow entry lines only in one kind of market (registered 2026-11-10, before its run)

From G421: entry lines at 0.8 noise (D) made more on the 2023-25 fresh starts and less on unseen. `entry_k_regime` /
`regime_calm` in `mnqbot/noise.py` (off by default): the entry lines at 0.8 only while the last 10 sessions' average
range is below (calm) or above (wild) the last 60's. `research/g422_regime_lines.py`: G421's C and U48, each with 0.8 when
calm and when wild. G421's measures and rule (the most trades a session on the fresh starts among variants making at
least U48's $ a session on the fresh starts and on unseen, losing at most one more fresh start and at most 5% unseen).
Run once.

**G422 first run (2026-11-10): void, a bug.** The new code named its flag `calm`, the name of calm_k's no-new-trades
flag, so every regime variant also stopped trading on many days (0.75-0.91 trades a session against U48's 1.22). Its
numbers (`verification/noise_v2/g422_regime_lines_buggy.txt`) measure the bug, not the idea. Fixed (`reg_calm`); G422 is
run again, once, with the same variants and rule.

**G422 result (2026-11-10, the fixed run): passes; U58 = G421's C with the 0.8 entry lines on calm stretches becomes the
funded mode.** Fresh starts (U48 1.22 trades a session, $30.4, 1 of 16 lost): **C with 0.8 when calm 1.54 trades, $49.2
(+62%), 0 lost, green months 68.2%**; C 1.38 / $29.4 / 0; C 0.8 when wild 1.37 / $23.9 / 2; U48 0.8 when calm 1.20 / $29.0
/ 2; U48 0.8 when wild 1.26 / $25.9 / 2. Development (U48 $39.2, 3.2%): **$42.0 (+7%), 0% lost**. Unseen (U48 $75.7, 3.1%):
**$80.5 (+6%), 1.6% lost**; U48 0.8 when calm $76.9 at 4.6%; the wild variants $65.1-70.6. Only the calm C variant makes at
least U48's money on the fresh starts and on unseen within the loss limits, so it is the pick.
**Caveats:** the fresh starts have now been looked at in G409, G415, G419, G421 and G422, and this idea came from G421's
fresh-vs-unseen split, so they are no longer fully unseen; its unseen and development gains are modest (+6-7%) and its
fewer losses are the steadier part. `verification/noise_v2/g422_regime_lines.txt`.

**U58 checks (2026-11-10):** built into `MnqNoiseV38.cs` as Funded growth on the 50K's **5-minute chart** (no range
filter, no loser limit, every entry check, `CalmEntryWidth` 0.8 on a calm stretch). On the 30-minute chart U58 made
less in NinjaTrader's growth run ($16,918 against U48's $28,191 on the window), and G422 was measured on 5-minute bars
only, so that chart keeps U48's G204 / G125 settings. The NinjaTrader tests, 50 passed (parity trade for trade). The
NinjaTrader growth run on the window: **5-minute $75,486.34** (U48 $61,047.16), 784 trades, 50.2% winners, profit factor
1.907 (1.665), closed drawdown $5,196.41 ($6,106.23), worst day −$899.38; differences from the model only at the stand-in
data's 2026-03-09 hole, as U48; 30-minute $28,191.46, identical to the model and to U48
(`verification/noise_v2/v38g_nt_u58.txt`).

## G423: wider entry lines when the market is not calm (registered 2026-11-10, before its run)

Hourly round, on U58. G422: the 0.8 lines lost money when the market was not calm. `entry_k_wild` in `mnqbot/noise.py`
(off by default): on a stretch that is not calm, the entry lines at that width. `research/g423_wide_when_wild.py`: U58
with 1.1 and 1.2 there. G421's measures; **rule:** the variant with the most $ a session on the fresh starts that makes
at least 10% more than U58 there and at least U58's $ a session on unseen, loses no more fresh starts than U58 and at
most 5% unseen, replaces U58. Run once.

**G423 result (2026-11-10): rejected; U58 stays.** Fresh starts (U58 $49.2 a session, 1.54 trades, 0 lost): 1.1 when not
calm $35.1, 1.2 $41.5 (both 0 lost). Development (U58 $42.0, 0%): $39.5 at 6.6%, $26.3 at 6.6%. Unseen (U58 $80.5, 1.6%):
$59.6 at 9.6%, $65.5 at 4.8%. Wider lines on the other days cost more than the false breakouts they skip.
`verification/noise_v2/g423_wide_when_wild.txt`.

## G424: U58 sized up faster (registered 2026-11-10, before its run)

U58 loses fewer starts than U48 (0 of 16 fresh, 0% development, 1.6% unseen), so it may carry faster steps.
`research/g424_u58_steps.py`: U58 with a contract more per $1,200 or $1,000 of profit (U58 $1,500), or the $650 fast steps
from $6,000 (U58 $9,000). G423's rule against U58 (the most $ a session on the fresh starts, at least 10% above U58 there,
at least U58's $ on unseen, no more fresh starts lost, at most 5% lost on unseen and development). Run once.

**G424 result (2026-11-10): rejected; U58 stays.** Fresh starts (U58 $49.2, 0 lost): +1 per $1,200 **$58.3 (+19%)**, 0 lost;
+1 per $1,000 $53.1 (+8%), 1 lost; fast steps from $6,000 $44.3. Development (U58 $42.0, 0%): $43.5 at 3.2%, $44.3 at 0%,
$43.0 at 0%. Unseen (U58 $80.5, 1.6%): +1 per $1,200 **$78.6 at 4.7%** (below U58), +1 per $1,000 $83.3 at 4.6%, fast
from $6,000 $78.5 at 1.6%. The $1,200 steps make more on the fresh starts and less on unseen, with three times the
losses there. `verification/noise_v2/g424_u58_steps.txt`.

## G425: a nearer take-profit on calm stretches (registered 2026-11-10, before its run)

Hourly round, on U58. U58 narrows its entry lines on a calm stretch; its take-profit stays 1.5 noise units, which smaller
moves may seldom reach. `tp_calm` in `mnqbot/noise.py` (off by default): on a calm stretch (U58's test), entries take
that take-profit. `research/g425_calm_target.py`: U58 with 1.0 and 1.25. G423's rule against U58 (the most $ a session
on the fresh starts, at least 10% above U58 there, at least U58's $ on unseen, no more fresh starts lost, at most 5% lost
on unseen and development). Run once.

**G425 result (2026-11-10): rejected; U58 stays.** Fresh starts (U58 $49.2 a session, 0 lost): target 1.0 when calm $46.6,
1.25 $46.0 (both 0 lost, a few more trades). Development (U58 $42.0, 0%): $42.4 at 9.8% lost, $41.4 at 12.7%. Unseen (U58
$80.5, 1.6%): $67.5 at 3.3%, $74.7 at 1.6%. The calm stretches' trend days still pay the full target; cutting it costs
more than the extra hits bring. `verification/noise_v2/g425_calm_target.txt`.

## G426: U58 without (or with a looser) calm-stretch filter (registered 2026-11-10, before its run)

Hourly round. U58 trades narrower lines on a calm stretch, but still skips days after a very calm one (`calm_k` 0.7, from
v2.6); the two were never tested together. `research/g426_u58_calm_filter.py`: U58 with `calm_k` 0 (off) and 0.6.
G423's rule against U58. Run once.

**G426 result (2026-11-10): rejected; U58 stays.** Fresh starts (U58 $49.2, 0 lost): calm filter off $45.2, 0.6 $44.3 (0
lost, slightly more trades). Development (U58 $42.0, 0%): off $45.7 at 0%, 0.6 $39.3 at 3.2%. Unseen (U58 $80.5, 1.6%):
off $74.4 at 1.6%, 0.6 $75.1 at 3.1%. The very calm days U58 skips lose on the recent and unseen starts; the filter
stays at 0.7. `verification/noise_v2/g426_u58_calm_filter.txt`.

## G427: does U58 still beat U48 at 2 ticks of slippage? (registered 2026-11-10, before its run)

Hourly round, a robustness check rather than a new rule. U58 replaced U48 on modest margins outside the fresh starts
(+6% unseen, +7% development) and trades about a quarter more often, so higher costs hit it harder.
`research/g427_u58_slippage.py`: U48 and U58 at the usual slippage and at 2 ticks on every market and stop fill.
**Rule:** if at 2 ticks U58 makes less $ a session than U48 on the fresh starts or on unseen, or loses more starts on
either, the funded mode goes back to U48 (a revert, built with the tests); otherwise U58 stays. Run once.

**G427 result (2026-11-10): U58 stays.** At 2 ticks of slippage on every market and stop fill: fresh starts U58 **$38.2 a
session, 0 of 16 lost** against U48 $26.5, 1 lost (at the usual slippage $49.2 / $30.4); development U58 $35.7 at 3.2%
against U48 $33.9 at 3.2%; unseen U58 **$67.6** at 3.2% against U48 $63.2 at 3.1%. The extra tick costs U58 more in
dollars (it trades more: −$11.0 a session on the fresh starts against U48's −$3.8), but it stays ahead everywhere. The
unseen loss rates (3.2% / 3.1%) are the same two starts; the measure counts a start lost partway through month 12 by the
share of the month left, so the difference is less than one start. `verification/noise_v2/g427_u58_slippage.txt`.

## The stop-placement check on MnqNoiseV38 (2026-11-10, a safety port, no rule change)

Hourly round. v3 Fix 2 (`docs/V2_STOPS.md`) added a stop-placement check to `MnqNoiseMomentum.cs`; the funded strategy,
`MnqNoiseV38.cs`, had none. Ported: every stop sent is logged ("MnqNoiseV38 stop placed: ..."), and at every bar close an
open position (bot or gap trade) must have a live stop (the platform's own report of the stop order when it gives one,
else the stop sent) and the engine's stop (`PeekStop`) may not be tighter than it by more than two ticks; a failure
prints and, live, alerts "STOP CHECK FAILED ... Put a stop in by hand now". The run's last line counts placements and
flags. **Results:** the 2025-26 window, U58 on 5-minute bars with the platform reporting stop orders: **6,295 placements,
0 flagged**; the NinjaTrader growth run unchanged ($75,486.34 on 5-minute, $28,191.46 on 30-minute: the check changes no
trade); a stop the broker cancels mid-trade is flagged (`tests/test_ninjatrader_v38.py::test_v38_stop_placement_check`).
All V38 and release tests pass (54).

## G428: U58 under the PRO account's intraday drawdown (registered 2026-11-10, before its run)

Hourly round, a measurement. G248 found U48 losing 55 of 526 starts under Take Profit Trader's PRO rule (the $2,000
drawdown trails intraday including open profit) against 21 under the Test's end-of-day rule; U58 replaced U48 on
end-of-day measures only. `research/g248_pro_intraday.py` (unchanged), 21 months from the 1st and the 15th of each month
(NQ 2015-23, the index 2011-24), run for U48 and U58 on today's code. **Rule:** if U58 loses more PRO starts than U48, the
funded mode's documentation says so and recommends U48 on a PRO account (U58 stays the default for the Test-to-funded
path under end-of-day trailing); if not, nothing changes. Run once.

**G428 result (2026-11-10): U58 stays; it loses fewer PRO starts than U48.** Under PRO's intraday drawdown, 21 months,
526 starts: **U48 55 lost** (18 + 13 on the 1st, 13 + 11 mid-month; G248's count reproduced on today's code), **U58 51
lost** (15 + 12, 15 + 9); the same in both bar orders. Median net over the 21 months: U58 a little lower on the long
horizon (index $42,241 / $42,175 against $43,865 / $44,259; NQ $50,445 / $50,246 against $51,072 / $58,720), unlike the
12-month measures where it led; the PRO risk is about one start in ten either way. Logs
`verification/noise_v2/g428_pro_u58.txt`, `g248_pro_{u48now,u58}_{MS,MID}.csv`.

## G429: the Test with no time limit, the sprint (U57) against the funded mode's sizing (U58) (registered 2026-11-10, before its run)

Hourly round. U57 was chosen to pass the Test within two weeks (G251-G321); Take Profit Trader's Test has no time limit
(Phase 0 of `docs/V2_STOPS.md`), and the v3 replay found that with no deadline smaller size passes far more often (v1.5:
87% at 1 MNQ, 53% at 2). `research/g429_test_no_deadline.py`: U57 and U58 (the NinjaTrader tests' configurations) on the
v3 replay's 116 starts (NQ 2015-24, 5-minute, 2 ticks), each run until pass or fail. **Rule:** if U58's sizing passes
more starts than U57, the docs recommend Funded growth on the Test for a trader with no deadline, and U57 only for a
deadline; no code changes either way. Run once.

**G429 result (2026-11-10): with no deadline, the funded mode's sizing passes the Test far more often than the sprint.**
116 starts, each run to the end of the data:

| | Passed | Failed | Frozen (never passes or fails) | Median trading days to pass | Passed within 10 days |
|---|---|---|---|---|---|
| U57 (Test sprint) | **56.9%** | 2.6% | 47 starts (40.5%) | 54 | 10.3% |
| U58 (Funded growth sizing) | **86.2%** | 0.0% | 16 starts (13.8%) | 124 | 0.0% |

"Frozen": the balance sits just above the floor (which stops at the start once the account has been $2,000 up), so no
trade's stop fits the room left and the bot, correctly, takes none; such a Test can never pass, so it counts as not
passed, as registered. (A first run cut each start at 760 days, against the registration's "until it passes or fails";
the rerun to the end of the data gave the same numbers: no frozen start ever moves.) **Per the rule: for a trader with no
deadline, Funded growth on the Test passes about 86% of the time (median about 6 months); the Test sprint passes about
57%, but a tenth of starts pass within two weeks.** No code changes. `verification/noise_v2/g429_test_no_deadline.csv`.

## G430: unfreezing the Test, a smaller cut-to-the-room stop (registered 2026-11-10, before its run)

From G429: with no deadline, 16 of 116 U58 Tests freeze just above the floor (no trade fits; `squeeze_min` 20 points is
the smallest stop the bot will cut a trade to). `research/g429_test_no_deadline.py` (G429's measure), U58 with
`squeeze_min` 20 (as is), 10 and 5 points. **Rule:** a smaller value is recommended for the no-deadline Test (a setting,
documented) only if it raises the pass rate and fails no more starts than U58; the funded default is not changed by this
test. Run once.

**G430 result (2026-11-10): no effect; nothing recommended.** U58 with `squeeze_min` 20 / 10 / 5 points: the same 86.2%
passed, 0 failed and 16 frozen, trade for trade. The frozen Tests sit within a few dollars of the floor (the one inspected
in G429: $9 above it), less than even a 5-point stop's risk plus fees (about $12 at 1 MNQ), so no stop setting can free
them: **a frozen Test is in practice a lost one**, and G429's 13.8% frozen for U58 (40.5% for U57) should be read as
losses. `verification/noise_v2/g430_squeeze.csv`.

## G431: the no-deadline Test at U58 starting with 2 or 3 MNQ (registered 2026-11-10, before its run)

From G429: with no deadline U58's sizing passes 86% of Tests but in a median 124 trading days. `research/g429_test_no_deadline.py`:
U58 starting at 2 and 3 MNQ (the max loss for the whole position scaled with it; the contract steps as U58). **Rule:** a
start is recommended as the faster no-deadline option if its pass rate (frozen counted as lost) is within 5 points of
U58's and its median days to pass at most 75% of U58's; otherwise 1 MNQ stays the recommendation. No code changes. Run once.

**G431 result (2026-11-10): rejected; 1 MNQ stays the no-deadline recommendation.** Passed (frozen counted as lost) /
median trading days to pass: U58 at 1 MNQ **86.2% / 124**; at 2 MNQ 58.6% / 70 (48 starts frozen); at 3 MNQ 56.9% / 57 (49
frozen, 1 failed). A bigger start reaches the target sooner when it passes, but a third more of the starts sink to the
floor first and freeze. The pass-rate cost (−28 points) is far beyond the 5 the rule allowed.
`verification/noise_v2/g431_test_start_size.csv`.

## G432: a trade may risk only part of the room above the floor, on the no-deadline Test (registered 2026-11-10, before its run)

From G429/G430: U58's no-deadline Tests that fail all freeze just above the floor (14%). `trail_frac` (U58: 1.0, a trade
may risk all the room left) at 0.5 and 0.33 makes each trade risk at most that share, so a run of losers shrinks the room
by a fraction each time instead of to nothing. `research/g429_test_no_deadline.py`, U58 with `trail_frac` 1.0 / 0.5 / 0.33.
**Rule:** recommended as a Test setting if it raises the pass rate (frozen counted as lost) by at least 3 points with
no more failures; then also measured on the funded 12-month measure before any default changes. Run once.

**G432 result (2026-11-10): rejected (no effect).** `trail_frac` 1.0 / 0.5 / 0.33: the same 86.2% passed, 0 failed and the
same 16 starts frozen (median days to pass 124 / 123 / 123). The frozen Tests are not lost to one oversized trade: they
are long losing stretches at 1 MNQ that wear the room down trade by trade, and a smaller share per trade only slows the
same slide until the 20-point minimum stop no longer fits. U58 as it is. `verification/noise_v2/g432_trail_frac.csv`.

## G433: the no-deadline Test, faster contract steps from 1 MNQ (registered 2026-11-10, before its run)

From G429/G431: U58 passes 86% of no-deadline Tests in a median 124 trading days; starting bigger cost 28 points of pass
rate. Here the start stays 1 MNQ and the size grows only out of profit, but sooner: a contract more per $1,000 or $750 of
profit (U58 $1,500). `research/g429_test_no_deadline.py`. **Rule:** recommended for the Test if its pass rate is within
2 points of U58's and its median days to pass at most 85% of U58's; no default changes. Run once.

**G433 result (2026-11-10): rejected.** Passed / median days: U58 ($1,500 steps) **86.2% / 124**; $1,000 steps 73.3% / 113
(31 frozen); $750 steps 74.1% / 110 (28 frozen, 2 failed, worst drawdown $13,011). Growing sooner gains ten days and loses
twelve points of pass rate: the bigger size arrives before the cushion is real. `verification/noise_v2/g433_test_steps.csv`.

## G434: the no-deadline Test, press only once the floor has stopped (registered 2026-11-10, before its run)

From G431/G433: bigger or faster sizing early costs pass rate. Here U58 starts and grows as it does until the account
is $2,000 (or $1,500) up, where the end-of-day floor stops at the start balance; from there, a contract more per $500 of
profit (U58: $650 steps only from $9,000). `research/g429_test_no_deadline.py`. G433's rule (pass rate within 2 points of
U58's, median days at most 85%). Run once.

**G434 result (2026-11-10): rejected.** Passed / median days: U58 **86.2% / 124**; pressing from $2,000 83.6% / 126; from
$1,500 76.7% / 130 (worst drawdown $15,248 in both). Not faster at all: the bigger late days raise the best day, and the
Test's consistency rule (best day under half the profit) then asks for more profit before it passes. On this Test,
steady size is both safer and as fast. `verification/noise_v2/g434_test_push.csv`.

## G435: the no-deadline Test with a smaller or larger early day budget (registered 2026-11-10, before its run)

Hourly round. U58 sizes each trade to fit the day's budget, $750 until the floor has stopped (`early_daily_loss`), so
that budget sets how big the Test's trades are. `research/g429_test_no_deadline.py`, U58 with $500 and $1,000. **Rule:**
recommended for the Test if it raises the pass rate (frozen counted as lost) by at least 3 points, or keeps it within 2
points with median days at most 85% of U58's; no default changes. Run once.

**G435 result (2026-11-10): rejected.** Passed / frozen / median days: U58 ($750) **86.2% / 16 / 124**; $1,000 the same to
the start; $500 87.1% / 15 / 124 (one start more, under the 3-point bar). The early budget rarely binds at the Test's
early size. `verification/noise_v2/g435_test_budget.csv`.

## G436: the no-deadline Test, U58's sizing with the sprint's signals (registered 2026-11-10, before its run)

Hourly round. The Test sprint (U57) trades an 18-session noise average and entry lines at 0.7 noise units (U58: 14
sessions, lines at 1.0, 0.8 on a calm stretch). G382 put them on the funded measure, never on the no-deadline Test with
U58's sizing. `research/g429_test_no_deadline.py`, U58 with `lookback` 18 and `entry_k` 0.7 (the calm 0.8 lines then do
not narrow further than 0.7... they replace them on a calm stretch, as coded). G435's rule. Run once.

**G436 result (2026-11-10): rejected.** Passed / frozen / median days: U58 **86.2% / 16 / 124**; with the sprint's signals
82.8% / 20 / 132 (worst drawdown $3,899). (On a calm stretch U58's 0.8 lines replace the 0.7, as the registration's
garbled parenthesis meant to say.) The sprint's wider-net signals trade more and lose more at this size.
`verification/noise_v2/g436_test_sprint_signals.csv`.

## G437: PRO, U58 with a $500 early day budget (registered 2026-11-10, before its run)

Hourly round. Under PRO's intraday drawdown U58 loses 51 of 526 starts (G428), mostly before the floor has stopped;
G435 hinted a smaller early budget saves a start on the Test. `research/g248_pro_intraday.py` (G428's measure), U58 with
`early_daily_loss` $500 (U58 $750) until the floor has stopped. **Rule:** adopted as a PRO recommendation (a setting,
documented; built into a mode only on a later pass of the full funded measure) if it loses at least 5 fewer PRO starts
than U58's 51 with the median net at least 95% of U58's on each set. Run once.

**G437 result (2026-11-10): rejected; worse.** Under PRO, 526 starts: U58 with a $500 early budget loses **85** (30 + 16
on the 1st, 26 + 13 mid-month) against U58's **51**, and the median nets fall (index $38,971 / $40,607 against $42,241 /
$42,175; NQ $48,452 / $50,927 against $50,445 / $50,246). A smaller budget cuts each early trade's max loss to fit, so
the stops sit closer and normal moves take them out more often; the early account bleeds instead of being protected.
`verification/noise_v2/g437_pro_early500.txt`, `g248_pro_u58e500_{MS,MID}.csv`.

## G438: PRO, U58 with a $1,000 early day budget (registered 2026-11-10, before its run)

The mirror of G437: a smaller early budget tightened the early stops and lost 85 PRO starts against 51. Here
`early_daily_loss` $1,000 (U58 $750), G428's measure. G437's rule (at least 5 fewer PRO losses than 51, median net at
least 95% of U58's on each set). Run once.

**G438 result (2026-11-10): rejected (no effect).** Under PRO, 526 starts: a $1,000 early budget loses **51** (16 + 11, 15 +
9) as U58 does (15 + 12, 15 + 9); median nets the same or a little higher on NQ (index $42,241 / $42,175, the same; NQ
$51,866 / $50,927 against $50,445 / $50,246). With G437: the early budget hurts when cut and does nothing when raised;
$750 stays. `verification/noise_v2/g438_pro_early1000.txt`, `g248_pro_u58e1000_{MS,MID}.csv`.

## G439: PRO, U58 with a wider max loss ($250 a contract) (registered 2026-11-10, before its run)

From G437 / G438: tighter early stops lost 34 more PRO starts; a bigger budget alone changed nothing (the stop did not
move). Here the stop itself: `max_loss_per_trade` $250 a contract (U58 $187.50), G428's measure. G437's rule (at least 5
fewer PRO losses than U58's 51, median net at least 95% of U58's on each set). Run once.

**G439 result (2026-11-10): rejected; much worse.** Under PRO, 526 starts: a $250 max loss a contract loses **103** (35 +
21, 28 + 19) against U58's 51, and the median nets fall by a fifth to two fifths (index $25,685 / $25,677 against $42,241
/ $42,175; NQ $41,923 / $42,223 against $50,445 / $50,246). A wider stop on the same budget means fewer contracts and
bigger single losses against the intraday floor. With G437: U58's $187.50 sits between a too-tight and a too-wide stop;
it stays. `verification/noise_v2/g439_pro_ml250.txt`, `g248_pro_u58ml250_{MS,MID}.csv`.

## G440: G249's PRO mode on U58 (registered 2026-11-10, before its run)

G249's PRO mode (the floor, sizing and the floor's stop from the intraday peak, `trail_intraday`; every stop tightened to
$100 above that floor, `pro_guard`) cut U48's PRO losses from 55 to 38 but cost a third of the median net, and was
rejected against its bar of 27. On U58 (51 PRO losses, G428) it has not been run. G428's measure. **Rule:** offered as a
documented PRO setting (not a default) if it loses at most 26 of 526 (half of U58's) with the median net at least 80% of
U58's on each set; else rejected. Run once.

**G440 result (2026-11-10): rejected as registered, narrowly; the best PRO result so far.** Under PRO, 526 starts: U58 with
G249's PRO mode loses **29** (5 + 8 on the 1st, 8 + 8 mid-month) against U58's **51**, 43% fewer, in both bar orders; the
bar was 26. Median nets: index $36,258 / $36,308 (86% of U58's $42,241 / $42,175), NQ $45,041 / $43,434 (89% / 86% of
$50,445 / $50,246), above the 80% bar. On U48 the same mode gave 38 lost at 70% of the net (G249); on U58 it keeps more of
both. Not adopted (the registered bar stands); it is a trade-off the user can choose: about 5.5% of funded accounts lost
instead of 9.7%, for about 12% less net over 21 months. The mode exists in the Python model only; on the funded account
it would need building into `MnqNoiseV38.cs` with parity tests first. `verification/noise_v2/g440_pro_mode_u58.txt`,
`g248_pro_u58pro_{MS,MID}.csv`.

## G441: the PRO mode's guard at $200 and $300 above the floor (registered 2026-11-10, before its run)

A follow-up to G440 (chosen after seeing it, so weigh it as such): U58 with the PRO mode lost 29 of 526 PRO starts with
the guard $100 above the floor (bar 26). Here `pro_guard` $200 and $300, G428's measure. G440's rule (at most 26 lost,
median net at least 80% of U58's on each set); if both pass, the one with fewer losses. Passing makes it a documented
PRO option only; building it into `MnqNoiseV38.cs` waits for the user. Run once.

**G441 result (2026-11-10): rejected; a bigger guard loses more.** Under PRO, 526 starts: guard $200 **39** lost (7 + 10, 12 +
10), $300 **38** (13 + 8, 9 + 8), against G440's $100 guard 29 and plain U58 51; median nets $35.4-46.0k, about the same as
$100's. A higher guard stops trades sooner whenever the account is near its floor, and the extra stop-outs bring the
floor down faster. The $100 guard of G440 stays the best PRO option found (29 lost); still a user choice, not built.
`verification/noise_v2/g441_pro_guard.txt`, `g248_pro_u58pro{200,300}_{MS,MID}.csv`.

## G442: the PRO mode's guard at $50 (registered 2026-11-10, before its run)

The other side of G441 ($200 / $300 lost 39 / 38 against $100's 29): `pro_guard` $50, G428's measure, G440's rule (at most
26 lost, median net at least 80% of U58's on each set). A follow-up to seen results. Run once.

**G442 result (2026-11-10): rejected.** Under PRO, 526 starts: guard $50 loses **31** (6 + 9, 8 + 8) at much the same nets
($36.1-46.0k). The bracket: $50 31, **$100 29**, $200 39, $300 38, no PRO mode 51. $100 is the best guard, but no setting
reaches the bar of 26; the PRO mode stays a documented user choice (G440), not built.
`verification/noise_v2/g442_pro_guard50.txt`, `g248_pro_u58pro50_{MS,MID}.csv`.

## G443: the PRO mode's cost on the recent starts (registered 2026-11-10, before its run)

A measurement for the user's choice (G440: the PRO mode loses 29 PRO starts against U58's 51 over 21 months, at 86-89% of
the net). `research/g443_pro_mode_fresh.py`: U58 and U58 + the PRO mode on G409's 16 recent 12-month starts (2023-25):
$ a session, starts lost, green months. No adoption rule; reported beside G440.

**G443 result (2026-11-10):** on the 16 recent 12-month starts, U58 **$49.2 a session**, 0 lost, green months 68.2%; U58 +
the PRO mode **$40.3** (−18%), 0 lost, green months 63.0%, worst month −$1,766 (U58 −$1,893). On recent markets the PRO
mode costs about a fifth of the money (21 months of history: about an eighth), for about 43% fewer PRO accounts lost
over 21 months (G440). Still the user's choice; not built. `verification/noise_v2/g443_pro_mode_fresh.txt`.

**Full suite (2026-11-10, after G416-G443, the v2 stops, the v3 fixes and the stop-placement checks):** 703 passed, none
failed (32 min). Every research setting added today is off by default; the NinjaTrader parity, release-package and MNQ
tests are all in it.

## G444: PRO, lock or bank winners sooner (registered 2026-11-10, before its run)

Hourly round. PRO's drawdown trails the highest balance including open profit, so open gains that fade still raise the
floor for good. U58 with the lock at 0.25 max losses (U58 0.35) and, separately, the take-profit at 1.5 noise units (U58
2.0), G428's measure. G437's rule (at least 5 fewer PRO losses than U58's 51, median net at least 95% of U58's on each
set). Run once.

**G444 result (2026-11-10): rejected, both.** Under PRO, 526 starts: lock at 0.25 loses **83** (30 + 10, 31 + 12) against U58's
51, median nets down (index $30,005 / $29,372, NQ $43,406 / $38,840); take-profit 1.5 loses **53** (17 + 11, 14 + 11), the
same as U58, with the index nets down by a third ($29,886 / $29,584; NQ $48,561 / $47,697). Banking sooner cuts the
winners that build the cushion; the floor creep from faded open profit is not where the PRO losses come from.
`verification/noise_v2/g444_pro_lock_tp.txt`, `g248_pro_{u58lock25,u58tp15}_{MS,MID}.csv`.

## G445: the narrow calm-stretch entry lines only on the trend's side (registered 2026-11-11, before its run)

Hourly round, on U58. U58 narrows both entry lines to 0.8 noise on a calm stretch (G422). A calm market drifting with
its trend may give true breakouts on the trend's side and false ones against it. `regime_trend_side` in
`mnqbot/noise.py` (off by default): on a calm stretch the 0.8 line only on the side of U58's 45-session trend (last
close above its average: the upper line; below: the lower); the other side, and both on a day with no trend, keep their
usual lines. `research/g445_calm_trend_side.py`: U58 against U58 with it. G423's rule against U58 (the variant replaces
U58 only if it makes at least 10% more $ a session on the fresh starts, at least U58's $ on unseen, loses no more fresh
starts, and loses at most 5% on unseen and on development). Run once.

**G445 result (2026-11-11): rejected; U58 stays.** Fresh starts (U58 $49.2 a session, 1.54 trades, 0 lost): trend side only
**$36.5 (−26%)**, 1.47 trades, 0 lost. Development (U58 $42.0, 0%): $44.9 (+7%), 0%. Unseen (U58 $80.5, 1.6%): $78.1,
1.6%. It fails on the fresh starts and on unseen: the narrow line against the trend earns its keep on calm stretches
too. `verification/noise_v2/g445_calm_trend_side.txt`.

## G446: U58's time stop re-checked (registered 2026-11-11, before its run)

Hourly round. U58 kept G204's 45-minute time stop (a losing trade not locked is closed after 45 minutes), chosen on U48;
U58 trades more often, on narrower lines when the market is calm, so its false breakouts may want a quicker or slower
exit. `research/g446_u58_time_stop.py`: U58 with the time stop at 30 and at 60 minutes. G423's rule against U58 (the
variant with the most $ a session on the fresh starts replaces U58 only if it makes at least 10% more there, at least
U58's $ on unseen, loses no more fresh starts, and loses at most 5% on unseen and on development). Run once.

**G446 result (2026-11-11): rejected; U58 keeps 45 minutes.** Fresh starts (U58 $49.2 a session, 0 lost): time stop 30
**$34.2 (−30%)**, 60 **$42.2 (−14%)**, both 0 lost. Development (U58 $42.0, 0%): 30 $42.7 at 3.2%, 60 $43.2 at 3.2%.
Unseen (U58 $80.5, 1.6%): 30 $76.9 at 1.6%, 60 **$85.3 (+6%) at 3.3%**. Neither beats U58 on the fresh starts; 60 makes
a little more on unseen with twice the losses. `verification/noise_v2/g446_u58_time_stop.txt`.

## G447: the calm-stretch entry lines at 0.7 or 0.9 (registered 2026-11-11, before its run)

Hourly round. U58's entry lines on a calm stretch sit at 0.8 noise, the one width G421 tried; no other width was
measured with G422's calm-only rule. `research/g447_calm_width.py`: U58 with them at 0.7 and at 0.9. G423's rule against
U58 (the variant with the most $ a session on the fresh starts replaces U58 only if it makes at least 10% more there, at
least U58's $ on unseen, loses no more fresh starts, and loses at most 5% on unseen and on development). Run once.

**G447 result (2026-11-11): rejected; U58 keeps 0.8.** Fresh starts (U58 $49.2 a session, 1.54 trades, 0 lost): 0.7
$47.5 (−3%), 1.66 trades; 0.9 **$27.9 (−43%)**; both 0 lost. Development (U58 $42.0, 0%): 0.7 $37.0, 0.9 $45.7 (both
0%). Unseen (U58 $80.5, 1.6%): 0.7 $80.6 at 1.6%, 0.9 $76.6 at 3.2%. Neither width beats 0.8 by 10% on the fresh starts;
0.7 matches it on unseen and is worse on development, 0.9 is worse on both recent sets. 0.8 sits at the top of what was
measured. `verification/noise_v2/g447_calm_width.txt`.

## G448: U58's max loss on the funded account (registered 2026-11-11, before its run)

Hourly round. G439 measured a wider max loss only under PRO's intraday drawdown (worse); on the 50K's end-of-day floor
U58's $187.50 a contract (from T.REFERENCE) was never re-checked. `research/g448_u58_max_loss.py`: U58 with
`max_loss_per_trade` $150 and $250 a contract. G423's rule against U58 (the variant with the most $ a session on the
fresh starts replaces U58 only if it makes at least 10% more there, at least U58's $ on unseen, loses no more fresh
starts, and loses at most 5% on unseen and on development). Run once.

**G448 result (2026-11-11): rejected, both; U58 keeps $187.50.** Fresh starts (U58 $49.2 a session, 0 lost): $150 **$22.1
(−55%)**, 0 lost; $250 **$25.8 (−48%)**, 1 lost. Development (U58 $42.0, 0%): $150 $48.6 at 6.6%, $250 $47.0 at 13.3%.
Unseen (U58 $80.5, 1.6%): $150 $62.8 at 3.2%, $250 $58.3 at 9.5%. As under PRO (G437 / G439), $187.50 sits between a
too-tight and a too-wide stop on the funded account too. `verification/noise_v2/g448_u58_max_loss.txt`.

## G449: U58's trade lock later (registered 2026-11-11, before its run)

Hourly round. The lock (the stop moved to entry +2.5 points once a trade is up `lock_at` x its max loss) is at 0.35. A
sooner lock was rejected on U48 (G404) and under PRO (G444); a later one alone was never measured (only inside G411's
combined pick). U58 trades narrower lines on calm stretches, whose winners may need more room before the lock.
`research/g449_u58_later_lock.py`: U58 with `lock_at` 0.45 and 0.55. G423's rule against U58 (the variant with the most $
a session on the fresh starts replaces U58 only if it makes at least 10% more there, at least U58's $ on unseen, loses
no more fresh starts, and loses at most 5% on unseen and on development). Run once.

**G449 result (2026-11-11): rejected, both; U58 keeps 0.35.** Fresh starts (U58 $49.2 a session, 0 lost): 0.45 **$32.3
(−34%)**, 0 lost; 0.55 **$24.6 (−50%)**, 2 of 16 lost. Development (U58 $42.0, 0%): 0.45 $48.3, 0.55 $56.8 (+35%), both
0%. Unseen (U58 $80.5, 1.6%): 0.45 $62.3 at 4.8%, 0.55 $69.0 at 6.3%. A later lock helped only on the 2011-18 index
years; on the recent and unseen starts it gives back trades that U58 locks. With G404 / G444: 0.35 stays.
`verification/noise_v2/g449_u58_later_lock.txt`.

## G450: U58's take-profit on the funded account (registered 2026-11-11, before its run)

Hourly round. U58's take-profit is **2.0 noise units** (T.REFERENCE; the U48 settings file sets none). G425's text above
says "1.5": a slip in the doc, not in the run (G425 compared calm-stretch targets against U58's 2.0). The target was
measured only under PRO (G444, 1.5) and on calm stretches (G425); not on the 50K's end-of-day floor.
`research/g450_u58_take_profit.py`: U58 with `take_profit` 1.5 and 2.5. G423's rule against U58 (the variant with the
most $ a session on the fresh starts replaces U58 only if it makes at least 10% more there, at least U58's $ on unseen,
loses no more fresh starts, and loses at most 5% on unseen and on development). Run once.

**G450 result (2026-11-11): rejected, both; U58 keeps 2.0.** Fresh starts (U58 $49.2 a session, 0 lost): 1.5 **$38.4
(−22%)**; 2.5 **$51.4 (+5%, short of the 10% bar)**; both 0 lost. Development (U58 $42.0, 0%): 1.5 $43.0 at 9.8%, 2.5
**$27.3 at 9.6%**. Unseen (U58 $80.5, 1.6%): 1.5 $74.0 at 4.9%, 2.5 $76.6 at 1.6%. 2.5 gains a little on the recent
starts only and loses a third on development; 2.0 stays. `verification/noise_v2/g450_u58_take_profit.txt`.

## G451: U58's trend length (registered 2026-11-11, before its run)

Hourly round. U58's trend (no shorts while the last close is above the average of the last `trend_n` closes, no longs
below; and the trend-side fill-ins) uses 45 sessions, from G241's screen on U44; it was never re-checked on U58, which
trades more often. `research/g451_u58_trend_len.py`: U58 with `trend_n` 30 and 60. G423's rule against U58 (the variant
with the most $ a session on the fresh starts replaces U58 only if it makes at least 10% more there, at least U58's $
on unseen, loses no more fresh starts, and loses at most 5% on unseen and on development). Run once.

**G451 result (2026-11-11): rejected, both; U58 keeps 45 sessions.** Fresh starts (U58 $49.2 a session, 0 lost): 30
sessions $44.6 (−9%), 1 of 16 lost; 60 sessions $39.5 (−20%), 0 lost. Development (U58 $42.0, 0%): 30 $46.6, 60 $45.1
(both 0%). Unseen (U58 $80.5, 1.6%): 30 **$65.8 at 6.1%**, 60 **$69.2 at 3.2%**. Both trend lengths help a little on
2011-18 and cost a sixth or more on the recent and unseen starts. `verification/noise_v2/g451_u58_trend_len.txt`.

## G452: U58's noise lookback (registered 2026-11-11, before its run)

Hourly round. The noise area (the average move from the open at each time of day) is taken over the last 14 sessions,
Zarattini's setting; G24 tried 10 and 20 on the growth mode of 2026-11-02, long before U58 and its calm-stretch lines
(which scale with the noise). The Test sprint uses 18. `research/g452_u58_lookback.py`: U58 with `lookback` 10 and 18.
G423's rule against U58 (the variant with the most $ a session on the fresh starts replaces U58 only if it makes at
least 10% more there, at least U58's $ on unseen, loses no more fresh starts, and loses at most 5% on unseen and on
development). Run once.

**G452 result (2026-11-11): rejected, both; U58 keeps 14 sessions.** Fresh starts (U58 $49.2 a session, 0 lost): 10
sessions $42.5 (−14%), 1 of 16 lost; 18 sessions $43.2 (−12%), 0 lost. Development (U58 $42.0, 0%): 10 **$20.1 at 3.2%**,
18 $33.8 at 9.8%. Unseen (U58 $80.5, 1.6%): 10 $73.5 at **13.4%**, 18 $75.8 at 3.2%. U58 is best on every set; 14 stays.
`verification/noise_v2/g452_u58_lookback.txt`.

## G453: U58's early day budget on the funded account (registered 2026-11-11, before its run)

Hourly round. Until the trailing floor stops, U58 sizes each trade to fit a $750 day budget (`early_daily_loss`). G435
measured $500 / $1,000 on the no-deadline Test, G437 / G438 under PRO; not on the 50K funded account's 12-month starts.
`research/g453_u58_early_budget.py`: U58 with $500 and $1,000. G423's rule against U58 (the variant with the most $ a
session on the fresh starts replaces U58 only if it makes at least 10% more there, at least U58's $ on unseen, loses no
more fresh starts, and loses at most 5% on unseen and on development). Run once.

**G453 result (2026-11-11): rejected, both; U58 keeps $750.** Fresh starts (U58 $49.2 a session, 0 lost): $1,000 $51.9
(+5%, short of 10%), $500 $49.4 (+0%); both 0 lost. Development (U58 $42.0, 0%): $1,000 $41.6 at 0%, $500 $41.3 at 6.7%.
Unseen (U58 $80.5, 1.6%): $1,000 $81.0 at 3.2%, $500 $78.5 at 1.6%. The budget barely matters on the funded account
(it binds only until the floor stops); $1,000 gains 5% recent with twice the unseen losses. Not worth a change.
`verification/noise_v2/g453_u58_early_budget.txt`.

## G454: U58's stop buffer (registered 2026-11-11, before its run)

Hourly round. The resting stop sits `stop_buffer` (0.24) x the noise area beyond the noise line, from G93 / G116 on U25
and U29; U58's calm-stretch lines are narrower, so its stops may want a different cushion. `research/g454_u58_stop_buffer.py`:
U58 with 0.18 and 0.30. G423's rule against U58 (the variant with the most $ a session on the fresh starts replaces U58
only if it makes at least 10% more there, at least U58's $ on unseen, loses no more fresh starts, and loses at most 5%
on unseen and on development). Run once.

**G454 result (2026-11-11): rejected, both; U58 keeps 0.24.** Fresh starts (U58 $49.2 a session, 0 lost): 0.18 **$37.2
(−24%)**, 0.30 **$40.4 (−18%)**; both 0 lost. Development (U58 $42.0, 0%): 0.18 $43.7 at 6.6%, 0.30 $35.2 at 0%. Unseen
(U58 $80.5, 1.6%): 0.18 $67.1 at 3.2%, 0.30 $79.0 at 4.8%. `verification/noise_v2/g454_u58_stop_buffer.txt`.

## G455: U58's breakouts only out of a fast half hour (registered 2026-11-11, before its run)

Hourly round. G361 found the bot's good breakouts come out of fast half hours; G362's filter (`thrust_k`: new entries
at a check only when the range since the previous check is at least k x the noise x the close) was measured only on
the Test sprint (U57), not on the funded account, where U58 also trades narrower lines on calm stretches.
`research/g455_u58_fast_half_hour.py`: U58 with `thrust_k` 0.5 and 0.75. G423's rule against U58 (the variant with the
most $ a session on the fresh starts replaces U58 only if it makes at least 10% more there, at least U58's $ on unseen,
loses no more fresh starts, and loses at most 5% on unseen and on development). Run once.

**G455 result (2026-11-11): rejected, both; much worse.** Fresh starts (U58 $49.2 a session, 1.54 trades, 0 lost): 0.5
**$21.1 (−57%)**, 1.17 trades; 0.75 **$14.4 (−71%)**, 0.86 trades, 1 lost. Development (U58 $42.0, 0%): $36.6 at 16.6%,
$27.3 at 6.7%. Unseen (U58 $80.5, 1.6%): $57.5 at 1.6%, $50.8 at 3.1%. Requiring a fast half hour drops a quarter to
nearly half the trades, and many of the dropped ones were winners. `verification/noise_v2/g455_u58_fast_half_hour.txt`.

## G456: U58 with no entries once the day is stretched (registered 2026-11-11, before its run)

Hourly round. G360's filter (`exhaust_k`: no new entries once the day's high-low range is already k x the last 10
sessions' average range) was measured only on the Test sprint (U57). `research/g456_u58_stretched_day.py`: U58 on the
funded account with k 1.25 and 1.5. G423's rule against U58 (the variant with the most $ a session on the fresh starts
replaces U58 only if it makes at least 10% more there, at least U58's $ on unseen, loses no more fresh starts, and loses
at most 5% on unseen and on development). Run once.

**G456 result (2026-11-11): rejected, both.** Fresh starts (U58 $49.2 a session, 0 lost): past 1.25x **$28.8 (−42%)**,
past 1.5x **$30.8 (−37%)**, each 1 of 16 lost. Development (U58 $42.0, 0%): $20.4 at 6.4%, $42.5 at 0%. Unseen (U58
$80.5, 1.6%): $41.2 at 6.3%, $61.3 at 3.1%. As on the sprint (G360): the stretched days are the trend days that pay.
`verification/noise_v2/g456_u58_stretched_day.txt`.

## G457: U58 without the gap-and-go trade (registered 2026-11-11, before its run)

Hourly round, an ablation. The gap trade (09:30-09:55 on a big opening gap, G60 on) was tested off only on the Test
sprint (G268, G315, G343); on the funded account it was never removed since U58 changed the day's other trades.
`research/g457_u58_no_gap_trade.py`: U58 with `gap_go` off. G423's rule against U58 (the variant replaces U58 only if it
makes at least 10% more $ a session on the fresh starts, at least U58's $ on unseen, loses no more fresh starts, and
loses at most 5% on unseen and on development). Run once.

**G457 result (2026-11-11): rejected; the gap trade stays, and it carries a large share of U58.** Without it: fresh starts
**$25.5 a session (−48%)**, 1.11 trades (U58 $49.2, 1.54), 0 lost; development $28.0 (−33%), 0%; unseen **$45.2 (−44%)**
at 7.9% lost (U58 1.6%). The gap-and-go trade (and the fill-ins that ride on it) is close to half of U58's profit on the
recent and unseen starts. `verification/noise_v2/g457_u58_no_gap_trade.txt`.

## G458: U58 without its first or its last entry check (registered 2026-11-11, before its run)

Hourly round. U58 takes every half-hour check from 10:00 to 15:30 (G422 dropped G125's skipped 13:00 / 14:30). The
first check follows the gap trade's half hour; the last one leaves 30 minutes to 16:00. Neither was ever removed on its
own. `research/g458_u58_first_last_check.py`: U58 with no entries at the 10:00 check (`skip_checks` "600") or at the
15:30 check ("930"), always (`skip_checks_early` off). G423's rule against U58 (the variant with the most $ a session on
the fresh starts replaces U58 only if it makes at least 10% more there, at least U58's $ on unseen, loses no more fresh
starts, and loses at most 5% on unseen and on development). Run once.

**G458 result (2026-11-11): rejected; and a registration error.** Without the 10:00 check: fresh starts **$43.6 a session
(−11%)**, 0 lost; development $38.5 at 9.5%; unseen $68.0 at 3.2% (U58 $49.2 / $42.0 at 0% / $80.5 at 1.6%). The 15:30
variant came out identical to U58 on every set because **U58's last entry check is 15:00** (`last_entry_end` 900 in the
model, `LastEntry` "15:00" in `MnqNoiseV38.cs`'s Funded growth; only the Test sprint takes 15:30). The registration's
"10:00 to 15:30" was wrong, so the 15:30 variant tested nothing; the quick start above said the same and is corrected.
`verification/noise_v2/g458_u58_first_last_check.txt`.

## G459: U58 with entries to the 15:30 check (registered 2026-11-11, before its run)

Hourly round, from G458. U58's last entry check is 15:00 (`last_entry_end` 900); the sprint uses 15:30. Close to tested
before: G8 (growth mode, 2026-10-31) and G382's "every check with entries to 15:30" on U48 (rejected); not on U58 alone,
with its calm-stretch lines. `research/g459_u58_last_1530.py`: U58 with `last_entry_end` 930. G423's rule against U58
(the variant replaces U58 only if it makes at least 10% more $ a session on the fresh starts, at least U58's $ on
unseen, loses no more fresh starts, and loses at most 5% on unseen and on development). Run once.

**G459 result (2026-11-11): rejected; U58 keeps 15:00.** Entries to 15:30: fresh starts **$34.1 a session (−31%)**, 0 lost
(U58 $49.2); development $48.9 (+17%) but **9.6% lost** (U58 0%); unseen $80.4 (U58 $80.5) at 4.9% lost (1.6%). The
15:30 entries cost the recent starts a third and triple the losses elsewhere. `verification/noise_v2/g459_u58_last_1530.txt`.

## G460: U58's calm-stretch baseline (registered 2026-11-11, before its run)

Hourly round. A calm stretch is the last 10 sessions' average range against the last `calm_long` (40) sessions'; it now
drives both the calm-day filter (`calm_k` 0.7) and U58's 0.8 entry lines (G422). G49 varied the windows on the growth
mode of 2026-11-03, before the lines used them. `research/g460_u58_calm_window.py`: U58 with `calm_long` 30 and 60.
G423's rule against U58 (the variant with the most $ a session on the fresh starts replaces U58 only if it makes at
least 10% more there, at least U58's $ on unseen, loses no more fresh starts, and loses at most 5% on unseen and on
development). Run once.

**G460 result (2026-11-11): rejected, both; U58 keeps 40.** Fresh starts (U58 $49.2 a session, 0 lost): against 30
sessions **$37.2 (−24%)**, against 60 $47.6 (−3%); both 0 lost. Development (U58 $42.0, 0%): $41.9 at 0%, $41.1 at 3.2%.
Unseen (U58 $80.5, 1.6%): $75.5 at 1.6%, **$61.2 at 6.3%**. `verification/noise_v2/g460_u58_calm_window.txt`.

## G461: U58 on a 100K account (a measurement for the user, registered 2026-11-11, before its run)

The user asked what a 100K account would make a day and how long its Test takes. G396 measured U48 (not U58) on a
100K-style account, funded only. `research/g461_100k.py`: U58 as it is, on the 50K and on a 100K-style account ($3,000
end-of-day trailing floor, $1,800 day budget, $1,500 until the floor stops; nothing else retuned). **Funded:** G396's 80
quarterly starts and 36 months: $ a session by year, months at $750+, lost. **Test:** G429's no-deadline replay (116
starts): passed, failed, median trading days to pass; the 50K at +$3,000 over $2,000, the 100K at **+$6,000 over $3,000
(the target is assumed; check the firm's)**. A measurement, not a candidate; no default changes. Run once.

**G461 result (2026-11-11), a measurement.**

| | 50K (U58) | 100K-style (U58, untuned) |
|---|---|---|
| Test, no deadline: passed / failed / still open | 86.2% / 0% / 16 of 116 | 92.2% / 0% / 9 of 116 |
| Test: median trading days to pass (middle half) | 124 (81-181) | 189 (135-277) |
| Test: passed within 60 trading days | 10.3% | 3.4% |
| Funded $ a session, years 1 / 2 / 3 | $71 / $160 / $176 | $71 / $199 / $264 |
| Funded: months at $750+ a session, year 3 | 7.3% | 15.8% |
| Funded: lost by year 3 | 2.5% | 3.8% |

U58 starts at 1 MNQ and adds a contract per $1,500 of profit on either account, so year one is the same; the 100K's
larger floor and day budget let it size up further later (year three +50%). Its Test needs twice the profit at the same
starting size, so it takes about half as long again. Not tuned for the 100K (G397's 150K-style result: starting at 2 MNQ
added 13-17%). `verification/noise_v2/g461_100k.txt`.

## G462: U58's sizing on the 100K (registered 2026-11-11, before its run)

The user: "trade more, make more, win more, on 100k". G461: U58 starts the 100K at the 50K's 1 MNQ, so year one is the
same and the Test takes 189 trading days. `research/g462_100k_sizing.py`: U58 on the 100K-style account as it is, or
starting at 2 or 3 MNQ (the max loss for the whole position, $187.50 a contract), +1 MNQ per $1,000 of profit (U58
$1,500), or 2 MNQ and +1 per $1,000 (4 variants).
**Funded rule (G397's):** development (index starts 2011-2016) the variant with the most $ a session within 5% lost and
at least 10% above the 100K as U58; it passes only if on unseen (index 2017-2023, NQ 2015-2022) it also makes at least
10% more with at most 5% lost. **Test (reported; recommended for the 100K Test only if):** the pass rate within 2 points
of the 100K as U58's 92.2% and the median trading days to pass at most 85% of its 189. A pass would be built as a 100K
mode of `MnqNoiseV38.cs` with parity tests. Run once.

**G462 result (2026-11-11): rejected, every variant; U58's sizing stays on the 100K.**

| 100K-style | Test: passed / still open of 116 | Test: median days (middle half) | Funded dev. $ a session (lost) | Funded unseen $ a session (lost) |
|---|---|---|---|---|
| **U58 as it is** | **92.2% / 9** | 189 (135-277) | **$110.7 (8.7%)** | $205.0 (1.8%) |
| start 2 MNQ | 79.3% / 24 | 129 (82-233) | $104.1 (17.4%) | $214.2 (8.8%) |
| start 3 MNQ | 62.1% / 43 (0.9% failed) | 87 (57-219) | $75.1 (30.4%) | $155.0 (22.8%) |
| +1 per $1,000 | 91.4% / 10 | 207 (130-295) | $106.0 (4.3%) | $214.8 (0%) |
| 2 MNQ, +1 per $1,000 | 75.0% / 27 (1.7% failed) | 129 (78-246) | $82.1 (13.0%) | $218.3 (7.0%) |

Funded: no variant makes 10% more on development (the best, +1 per $1,000, makes 4% less there, 5% more unseen).
Test: a bigger start passes sooner when it passes (129 / 87 days against 189), but far fewer pass (79% / 62% against
92%): the rest sit near the floor at a size the room no longer allows and never reach the target. Neither meets the
registered Test rule. `verification/noise_v2/g462_100k_sizing.txt`.

**Reading G461 / G462 with G430:** a Test still "open" at the end of the data is frozen just above the floor and in
practice lost. So the 100K as U58 loses about 7.8% of its Tests (9 of 116), starting at 2 MNQ 20.7%, at 3 MNQ 38%.

## G463: the 100K's day budget until the floor stops (registered 2026-11-11, before its run)

G461 / G462 assumed a $1,500 budget until the floor stops on the 100K (the 50K's $750 scaled; $1,800 after). It sets how
big the early trades are. `research/g462_100k_sizing.py` with `G463=1`: the 100K as U58 against an early budget of
$1,000, and of $2,000 (with the day budget at $2,000). Rules: G462's (funded: development the most $ a session within 5%
lost and 10% above the 100K as U58, then unseen at least 10% more within 5% lost; Test: pass rate within 2 points of
92.2% with the median days at most 85% of 189). Run once. (Commit 821b5f2 carried only the runner change; this text is
its registration, committed before the run.)

**G463 result (2026-11-11): rejected; the 100K keeps $1,500 (the budget barely binds).** The Test part's first run
crashed before any result (a bug in the runner: the budget passed twice to the config); fixed (`{**K100, **SIZING[tag]}`)
and run once. **Test:** identical for all three (92.2% passed, 9 frozen, median 189 days): at 1 MNQ the budget never
limits a Test trade. **Funded:** development (100K as U58 $110.7, 8.7% lost): $1,000 $110.6 at 4.3%, $2,000 **$115.0
(+4%, short of 10%)** at 8.7%; unseen ($205.0, 1.8%): $1,000 $205.0, $2,000 $218.9 (+7%) at 1.8%, year three $334 (+11%).
`verification/noise_v2/g463_100k_early_budget.txt`.

## G464: the 100K's gap-trade cap once the floor has stopped (registered 2026-11-11, before its run)

G457: the gap trade carries about half of U58's profit. Once the floor stops it takes up to `gap_go_locked_qty` 10 MNQ,
set on the 50K (G84), where 15 broke the $1,000 daily loss once (G83). The 100K has a $1,800 day budget and a $3,000
floor. `research/g462_100k_sizing.py` with `G464=1`: the 100K as U58 against the gap cap at 15 and 20 MNQ. G462's rules
(funded: development the most $ a session within 5% lost and 10% above the 100K as U58, then unseen at least 10% more
within 5% lost; Test reported). The worst funded day is also reported and must stay above −$2,000. Run once.

**G464 result (2026-11-11): rejected, both; the 100K keeps a gap cap of 10.** Test: identical (the cap applies only once
the floor has stopped). Funded development (100K as U58 $110.7 a session, 8.7% lost, worst day −$1,800): cap 15 $101.5
(−8%), cap 20 **$79.4 (−28%)**, worst day −$1,971 for both. Unseen ($205.0, 1.8%, −$1,800): cap 15 $223.0 (+9%), cap 20
$237.4 (+16%), worst day −$1,815 / −$1,952. Bigger gap trades win on 2017-2025 and lose on 2011-2016; they fail the
development half and bring the worst day near the assumed $2,000 limit. `verification/noise_v2/g464_100k_gap_cap.txt`.

## G465: fewer lost 100K starts (registered 2026-11-11, before its run)

G462 / G463: the 100K as U58 loses 8.7% of its development starts (2 of 23) and 7.8% of its Tests (frozen).
`research/g462_100k_sizing.py` with `G465=1`: the 100K as U58 against +1 MNQ per $2,000 of profit (U58 $1,500), and
against each trade risking at most half the room above the floor (`trail_frac` 0.5; U58 1.0). **Rule (survival
first):** a variant passes only if it loses fewer funded starts on development and no more on unseen, with at least
95% of the 100K as U58's $ a session on both, and passes at least as many Tests. Run once.

**G465 result (2026-11-11): rejected by its rule, both; but +1 per $2,000 is the first 100K variant better funded on
both halves.**

| 100K-style | Test passed (frozen) | Funded development $ a session (lost) | Funded unseen $ a session (lost) |
|---|---|---|---|
| U58 as it is | **92.2%** (9) | $110.7 (8.7%) | $205.0 (1.8%) |
| +1 per $2,000 | 88.8% (13) | **$122.2 (+10%), 0% lost** | **$222.9 (+9%), 0% lost** |
| at most half the room | 92.2% (9) | $110.6 (4.3%) | $205.0 (3.5%) |

+1 per $2,000 loses no funded start on either half and makes 9-10% more, but passes 4 fewer Tests (the registered rule
needs at least as many), so it fails as one setting for both. Half the room changes only a few trades: one fewer
development loss, one more unseen. A funded-only use of the $2,000 steps (the Test keeping $1,500) is a new question,
not adopted by this run; it needs its own registered test. `verification/noise_v2/g465_100k_fewer_lost.txt`.

## G466: slower contract steps on the funded account, checked on other starts (registered 2026-11-11, before its run)

From G465: +1 MNQ per $2,000 of profit (U58 $1,500) made the 100K 9-10% more on G397's starts with no start lost, but
passed fewer Tests; as a funded-only setting it needs its own test. `research/g466_slower_steps.py`: **50K:** U58 against
U58 with `profit_step` 2,000, on G415's fresh starts and G372's development / unseen starts, G423's rule (at least 10%
more $ a session on the fresh starts, at least U58's $ on unseen, no more fresh starts lost, at most 5% lost on unseen
and development). **100K-style:** the same pair on G415's fresh starts; it confirms G465 only if it makes at least 5%
more there and loses no more starts. A 100K funded mode would then step by $2,000 and its Test by $1,500. Run once.
(Commit e5690d8 carried only the runner; this is its registration, committed before the run.)

**G466 result (2026-11-11): the 50K rejected; the 100K confirmed.**
- **50K:** +1 per $2,000 fresh starts **$33.9 a session (−31%)** (U58 $49.2), both 0 lost; development $43.2 (+3%), 0%;
  unseen **$68.8 (−14%)** at 1.6%. U58's $1,500 steps stay on the 50K.
- **100K-style, G415's fresh starts:** U58 $26.7 a session, 0 of 16 lost, worst month −$2,313; +1 per $2,000 **$32.7
  (+22%)**, 0 lost, green months 69.3% (64.1%), worst month −$1,749. With G465 (G397's starts: +10% development, +9%
  unseen, no start lost on either) it passes on all three 100K start sets, so a 100K funded mode steps by $2,000; its
  Test keeps $1,500 (G465: 92.2% against 88.8%).
Note: on the fresh starts the 100K as U58 makes less than the 50K ($26.7 against $49.2): its floor stops only after
+$3,000, so the gap trade stays at 1 MNQ (`gap_go_max_qty` until the floor stops) for longer.
`verification/noise_v2/g466_slower_steps.txt`.

## G467: the 100K with 2 gap contracts before the floor stops (registered 2026-11-11, before its run)

G466: on the 100K the floor stops only after +$3,000, so the gap trade (about half of U58's profit, G457) stays at 1 MNQ
for longer than on the 50K. 2 early gap contracts were rejected on the 50K (G61, G173), never tried with the 100K's
$3,000 floor. `research/g462_100k_sizing.py` with `G467=1` (the Test: 100K U58 against it with `gap_go_max_qty` 2; the
funded measure: the 100K funded mode, $2,000 steps, against it with 2) and `research/g467_100k_gap_early_fresh.py`
(G415's fresh starts, the funded pair). **Funded rule:** at least 10% more $ a session than the 100K funded mode on
G397's development and unseen starts and at least 5% more on the fresh starts, with no more starts lost on any.
**Test rule:** the pass rate within 2 points of 92.2% with the median days at most 85% of 189. Each part passes or fails
on its own. Run once.

**G467 result (2026-11-11): rejected, both parts.** Test: 100K U58 92.2% passed / 9 frozen / median 189; with 2 early gap
contracts 92.2% / 8 frozen / 1 failed / 188 (no faster). Funded (100K funded mode, $2,000 steps): development $122.2 →
$116.9 (−4%), unseen $222.9 → $221.3 (−1%, one start lost), fresh starts $32.7 → **$27.6 (−15%)**. A second early gap
contract does not pay on the 100K either. `verification/noise_v2/g467_100k_gap_early.txt`.

## G468: the 100K funded mode's contract step around $2,000 (registered 2026-11-11, before its run)

G466 confirmed +1 MNQ per $2,000 for the 100K funded mode (against $1,500); is $2,000 the best? `research/g462_100k_sizing.py`
with `G468=1` (G397's development / unseen starts) and `research/g468_100k_step_fresh.py` (G415's fresh starts): the
100K funded mode with steps of $2,000 (as G466), $1,750 and $2,500. **Rule:** a step replaces $2,000 only if it makes at
least 5% more $ a session on all three start sets with no more starts lost on any. (The Test part prints too; the Test
keeps $1,500, G465.) Run once.

**G468 result (2026-11-11): rejected, both; the 100K funded mode keeps $2,000.** Development ($2,000 $122.2, 0% lost):
$1,750 $126.0 (+3%), $2,500 $115.2 (−6%); unseen ($222.9, 0%): $221.1 (−1%), $197.0 (−12%, 1.8% lost); fresh starts
($32.7): $31.5 (−4%), $27.9 (−15%). $2,000 is the best of the three on two sets of three and close on the third. (The
Test part of the runner was not run: the Test keeps $1,500, G465.) `verification/noise_v2/g468_100k_step.txt`.

## G469: the giveback brake on the 100K funded mode (registered 2026-11-11, before its run)

Once the floor has stopped, while the profit is under `giveback_brake` (0.45) x the best end-of-day profit, every trade
is 1 MNQ (G99, tuned on the 50K's $2,000 floor). `research/g462_100k_sizing.py` with `G469=1` (G397's development /
unseen starts) and `research/g469_100k_brake_fresh.py` (G415's fresh starts): the 100K funded mode ($2,000 steps) with
the brake at 0.35 and 0.55. G468's rule (a brake replaces 0.45 only with at least 5% more $ a session on all three start
sets and no more starts lost on any). Run once.

**G469 result (2026-11-11): passes; the 100K funded mode takes the giveback brake at 0.35.**

| 100K funded ($2,000 steps) | development $ a session (lost) | unseen | fresh starts (worst month) |
|---|---|---|---|
| brake 0.45 (U58) | $122.2 (0%) | $222.9 (0%) | $32.7 (−$1,749) |
| **brake 0.35** | **$146.8 (+20%)** (0%) | **$239.4 (+7%)** (0%) | **$34.9 (+7%)** (−$2,086) |
| brake 0.55 | $86.1 (−30%) (0%) | $186.7 (−16%) (0%) | $27.0 (−17%) (−$1,577) |

0.35 makes at least 5% more on all three start sets with no start lost on any, so it meets G468's rule; its worst month
on the fresh starts is $337 deeper. The 100K funded mode is now: U58 on the 100K's limits, +1 MNQ per $2,000 (G466),
brake 0.35 (G469). The brake applies only once the floor has stopped, so the Test is unchanged. Not yet built into
`MnqNoiseV38.cs` (it waits for the user's 100K rules). `verification/noise_v2/g469_100k_brake.txt`.

## G470: the giveback brake on the 50K (registered 2026-11-12, before its run)

G469: on the 100K a later brake (0.35, U58 0.45) made 7-20% more with no start lost. On the 50K the brake (G99, 0.45 from
G174's checks on U38) was not re-checked on U58. `research/g470_u58_brake.py`: U58 with `giveback_brake` 0.35 and 0.25.
G423's rule against U58 (the variant with the most $ a session on the fresh starts replaces U58 only if it makes at
least 10% more there, at least U58's $ on unseen, loses no more fresh starts, and loses at most 5% on unseen and on
development). Run once.

**G470 result (2026-11-12): rejected by G423's rule; U58 keeps 0.45 on the 50K.** Fresh starts (U58 $49.2 a session, 0
lost): brake 0.35 $50.5 (+3%), 0.25 $50.4 (+2%), both 0 lost, worst month −$1,945 / −$2,019 (U58 −$1,893). Development
(U58 $42.0, 0%): $47.7 (+14%), **$49.9 (+19%)**, both 0%. Unseen (U58 $80.5, 1.6%): $82.1 (+2%), $84.9 (+5%), both 1.6%.
A later brake is a little better on every set with no more starts lost, but on the fresh starts it is 2-3% better, far
from the rule's 10%. Not adopted on the 50K. `verification/noise_v2/g470_u58_brake.txt`.

## G471: the 100K funded mode's brake below 0.35 (registered 2026-11-12, before its run)

G469: on the 100K the brake ran 0.55 < 0.45 < 0.35 in $ a session; G470 on the 50K had 0.25 close to 0.35. Is 0.35 the
end of the trend? `research/g462_100k_sizing.py` with `G471=1` (G397's starts) and `research/g471_100k_brake_fresh.py`
(G415's fresh starts): the 100K funded mode ($2,000 steps, brake 0.35) against the brake at 0.25 and off (0; G155 found
the brake saves accounts on U34). G468's rule (replaces 0.35 only with at least 5% more $ a session on all three start
sets and no more starts lost on any). Run once.

**G471 result (2026-11-12): rejected by G468's rule; the 100K funded mode keeps brake 0.35.** Development (0.35 $146.8,
0% lost): 0.25 $152.4 (+4%), off $161.5 (+10%); unseen ($239.4, 0%): $256.3 (+7%), $257.7 (+8%); fresh starts ($34.9,
worst month −$2,086): $35.3 (+1%, −$2,123), $36.2 (+4%, −$2,066). No start lost by any. The brake costs a little on the
100K at every level, but the fresh-start gain of having none (+4%) is short of the 5% the rule asks on all three sets.
`verification/noise_v2/g471_100k_brake_low.txt`.

## G472: the 100K funded mode's contract cap (registered 2026-11-12, before its run)

U58 caps a trade at `size_up_to` 60 MNQ (G247: the 50K firm's). The 100K funded mode ($2,000 steps, brake 0.35) grows to
$250-350 a session in year three, where the cap may bind; a 100K account usually allows more contracts (to be checked
against the user's firm). `research/g462_100k_sizing.py` with `G472=1` (G397's starts) and
`research/g472_100k_cap_fresh.py` (G415's fresh starts): the cap at 60, 90 and 120. G468's rule (a cap replaces 60 only
with at least 5% more $ a session on all three start sets and no more starts lost on any). Run once.

**G472 result (2026-11-12): rejected, both; the 100K funded mode keeps the cap at 60.** Development (cap 60 $146.8, 0%
lost): cap 90 $139.4 (−5%), 120 $134.1 (−9%); unseen ($239.4): $231.6 (−3%), $224.5 (−6%); fresh starts (12 months):
identical ($34.9; the cap never binds in the first year). Where the cap binds (years two and three) the bigger
positions give back more than they add. `verification/noise_v2/g472_100k_cap.txt`.

## G473: a balanced adoption rule, applied to the changes already measured (registered 2026-11-12, before its run)

The user: "the strategy is too strict. make it more balanced." G423's rule (at least 10% more on the fresh starts) has
rejected changes that were better on every set with no more starts lost (G470's later brake on the 50K, G471's brake
off on the 100K). **The balanced rule, from now on:** a change is adopted when, against the current setting, it makes
at least as much $ a session on each of the three start sets (G415's fresh starts, G372's or G397's development and
unseen), at least 5% more on their average, loses no more starts on any set, and its worst month on the fresh starts is
at most $250 deeper. **Applied to the measured candidates** (their numbers were seen, so each pick must also be confirmed
on a measure not used to pick it): NinjaTrader's own growth run on the 2025-26 window (`research/v38_ninjatrader_run.py
grow`, `GIVEBACK=`), which must make at least the current setting's net with a worst day no deeper than −$1,000.
Candidates that meet the balanced rule on the numbers already recorded: on the 50K, the brake at 0.25 (+2.5% / +19.0% /
+5.5%, average +9.0%, worst month $127 deeper) and 0.35 (+2.7% / +13.6% / +2.0%, average +6.1%, $52 deeper); the pick
is the higher average, 0.25. On the 100K funded mode, no brake (+3.7% / +10.0% / +7.6%, average +7.1%, worst month $20
less deep). Every other recorded candidate since G423 falls short (at least one set lower, or more starts lost).
The 50K pick is confirmed (or not) by the NinjaTrader run below; the 100K mode is not yet built. Run once.

**G473 result (2026-11-12): the 50K takes the brake at 0.25 (U58 on the 5-minute chart); the 100K funded mode's brake
goes off.**
- **NinjaTrader confirmation (as registered):** the growth run on the 2025-26 window is identical at 0.45, 0.35 and
  0.25 ($75,486.34 on 5-minute bars, 784 trades, worst day −$899.38; 30-minute $28,191.46): the brake never engages
  on that window, so the check meets the rule (no less net, worst day above −$1,000) but cannot tell the settings
  apart. The adoption rests on the three replay sets.
- **The Test (a safety check added before building, reported here):** G429's no-deadline replay, 50K: 0.45 86.2%
  passed / 16 frozen / median 124 days; 0.25 **87.1% / 15 / 122**; none failed.
- **Built:** `MnqNoiseV38.cs` sets `GivebackBrake` 0.25 for Funded growth on the 5-minute chart (U58); the Test sprint,
  the bigger accounts, Custom and the 30-minute chart keep 0.45. The NinjaTrader tests (55) pass, parity trade for
  trade (the 50K model config `GROW` carries 0.25; the sprint, bigger-account and Custom configs 0.45).
- **The 100K funded mode** (not built yet): U58 on the 100K's limits, +1 MNQ per $2,000 (G466), no brake (G473).
`verification/noise_v2/g473_balanced_nt.txt`.

## G474: the 50K with no giveback brake (registered 2026-11-12, before its run)

G470 / G473: on the 50K a later brake was better (0.25 adopted); on the 100K none at all was (G471 / G473). G155 found
the brake saved accounts on U34. `research/g474_u58_no_brake.py`: U58 with the brake at 0.25 against `giveback_brake` 0
(off). The balanced rule (G473): at least as much $ a session on each of G415's fresh and G372's development / unseen
starts, at least 5% more on their average, no more starts lost on any, the fresh starts' worst month at most $250
deeper; then NinjaTrader's growth run on the window at least as good. Run once.

**G474 result (2026-11-12): rejected by the balanced rule; the 50K keeps the brake at 0.25.** No brake against 0.25:
fresh starts $52.2 (+3.5%; worst month −$1,919, $100 shallower), development $49.94 (equal), unseen $88.2 (+3.9%), no
start lost on any. Average +2.5%, short of the 5%. Between 0.25 and off the brake barely acts on the 50K.
`verification/noise_v2/g474_u58_no_brake.txt`.

## G475: aggressive 50K variants (a measurement for the user, registered 2026-11-12, before its results)

The user: "loosen up, need it to make a lot more". Every lever tried one at a time added at most a few percent; this
stacks the ones that leaned up, to show the user the trade-off. `research/g475_aggressive.py`: U58 (brake 0.25) against
A1 = no brake + a contract per $1,000 + a $1,000 day budget until the floor stops; A2 = A1 + take-profit 2.5; A3 = A1 +
a 2-MNQ start. Measures: $ a session and starts lost on G415's fresh and G372's development / unseen starts, the fresh
starts' worst month. **Not a default change:** a variant would be offered as an opt-in Mode only if the user picks it
knowing its loss rate; the balanced rule (G473) decides whether it could replace U58. Run once. (This text was meant
for commit c110c9e, which carried only the runner; it is committed here after the run started and before any result.)

**G475 result (2026-11-12), a measurement: more money only with many more lost accounts; none meets the balanced rule.**

| 50K funded | fresh $ a session (lost of 16, worst month) | development (lost) | unseen (lost) |
|---|---|---|---|
| **U58 (brake 0.25)** | **$50.4** (0, −$2,019) | $49.9 (0%) | $84.9 (1.6%) |
| A1: no brake, +1 per $1,000, $1,000 early budget | $63.6, +26% (2, −$2,115) | $56.3, +13% (6.6%) | $100.7, +19% (9.4%) |
| A2: A1 + take-profit 2.5 | $75.2, +49% (3, −$2,620) | $46.4, −7% (6.4%) | $101.0, +19% (9.4%) |
| A3: A1 + start 2 MNQ | $79.0, +57% (3, −$2,592) | $67.5, +35% (15.7%) | $81.6, −4% (28.2%) |

(A lost start counts $0 a session from its loss on.) A1 makes 13-26% more on every set but loses about 1 account in 8
on the recent starts and 1 in 11 unseen, against U58's 0 and 1 in 64. Offered to the user as an opt-in mode, not adopted.
`verification/noise_v2/g475_aggressive.txt`.

## G476: more trades on the 50K (registered 2026-11-12, before its run)

The user: "i need it to enter more trades." U58 takes about 1.6 trades a session. `research/g476_more_trades.py`: U58
(brake 0.25) against T1 = entry checks every 15 minutes (`check_step` 15; tried on U44, k317 and U57, not on U58),
T2 = the 0.8 entry lines every day (`entry_k` 0.8; U58 uses them only on calm stretches), T3 = both. Trades a session
are reported with the $ and losses. **Rule:** the balanced rule (G473); a variant that passes is built into
`MnqNoiseV38.cs` (T1 needs the 15-minute grid there). Otherwise the one with the most trades is offered as an opt-in
with its cost. Run once.

**G476 result (2026-11-12): rejected, all three; extra entries cost money and accounts.**

| 50K funded | trades a session (fresh) | fresh $ a session (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| **U58 (brake 0.25)** | 1.58 | **$50.4** (0) | $49.9 (0%) | **$84.9** (1.6%) |
| T1 checks every 15 min | **1.78 (+13%)** | $42.7, −15% (0) | $53.9, +8% (10.1%) | $55.4, −35% (14.4%) |
| T2 0.8 lines every day | 1.61 (+2%) | $40.0, −21% (0) | $52.8, +6% (3.2%) | $78.8, −7% (4.7%) |
| T3 both | 1.81 (+14%) | $24.0, −52% (1) | $50.2, 0% (10.1%) | $40.8, −52% (12.6%) |

The added 15-minute entries are mostly false breakouts; with them the account loses 1 in 7 unseen starts. None meets
the balanced rule, and none is offered: the cheapest extra trades (T1) cost a third of the unseen money.
`verification/noise_v2/g476_more_trades.txt`.

## G477: twice the trades (a measurement for the user, registered 2026-11-12, before its run)

The user: "i need 100% more trades" (U58: about 1.6 a session). `research/g477_double_trades.py`: U58 (brake 0.25)
against D1 = entry lines at 0.6 noise every day, no calm-day skip, no trend filter; D2 = D1 + 15-minute checks; D3 =
D1 + 10-minute checks. Reported: trades a session, $ a session and starts lost on G415's fresh and G372's development /
unseen starts. The balanced rule (G473) decides adoption; a variant at about twice the trades is offered as an opt-in
only with its measured cost. Run once.

**G477 result (2026-11-12), a measurement: twice the trades costs most of the money and a quarter of the accounts.**

| 50K funded | trades a session (fresh) | fresh $ a session (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| **U58 (brake 0.25)** | 1.58 | **$50.4** (0) | **$49.9** (0%) | **$84.9** (1.6%) |
| D1 loose entries | 2.19 (+39%) | $17.6, −65% (1) | $22.6, −55% (29.4%) | $49.9, −41% (9.4%) |
| D2 = D1 + 15-min checks | **3.20 (+102%)** | $8.3, −84% (3) | $32.7, −34% (23.0%) | $18.5, −78% (28.3%) |
| D3 = D1 + 10-min checks | 2.76 (+74%) | $25.1, −50% (6) | $8.4, −83% (42.4%) | $27.0, −68% (26.7%) |

Only D2 doubles the trades, and it keeps about a sixth of the money and loses 1 account in 4 on the older and unseen
starts. The bot's edge is its selectivity; its extra breakouts lose. Nothing adopted; nothing worth offering.
`verification/noise_v2/g477_double_trades.txt`.

## The opt-in modes built (2026-11-12)

The user: "just keep implementing things". `MnqNoiseV38.cs` gains two opt-in Modes, both run as Funded growth's U58 on
5-minute bars with overrides (a setup warning on any other chart): **Funded aggressive** (G475's A1: `GivebackBrake` 0,
`ProfitStep` 1,000, `EarlyDayBudget` 1,000) and **Funded growth 100K U58** (G461's assumed 100K limits: `DailyLoss`
1,800, `TrailDD` 3,000, `LossGuard` 1,900, `EarlyDayBudget` 1,500; G466's `ProfitStep` 2,000; G473's no brake). The
default stays Test sprint / Funded growth, unchanged. Tests: `test_v38_opt_in_modes` (both modes agree with the model
trade for trade, change the trades, name themselves on the dashboard, warn off a 30-minute chart); the NinjaTrader and
release tests, 57 passed.

## G478: a contract per $1,250 on the 50K (registered 2026-11-12, before its run)

Hourly round. G424 (old rule, brake 0.45): +1 per $1,200 made 19% more on the fresh starts and 2% less unseen. On the
current U58 (brake 0.25): `research/g478_step_1250.py`, `profit_step` 1,250 against 1,500. The balanced rule (G473):
at least as much $ a session on each of the three start sets, at least 5% more on their average, no more starts lost,
the fresh starts' worst month at most $250 deeper; then NinjaTrader's growth run on the window at least as good. Run once.

**G478 result (2026-11-12): rejected by the balanced rule (one more start lost on two sets); +14% more money.** +1 per
$1,250 against U58 (brake 0.25): fresh starts **$57.6 (+14.3%)**, 0 lost, worst month −$2,223 ($204 deeper);
development **$55.7 (+11.5%)** at 3.2% lost (U58 0%); unseen **$98.5 (+16.0%)** at 3.2% (1.6%). Average +14%, but one
more start lost on each of development (1 of 31) and unseen (1 of 63), so it fails "no more starts lost". A middle
ground between Funded growth and Funded aggressive. `verification/noise_v2/g478_step_1250.txt`.

**Funded growth plus built (2026-11-12):** a third opt-in Mode, Funded growth's U58 with `ProfitStep` 1,250 (G478).
`test_v38_opt_in_modes` covers it (trade for trade with the model); the NinjaTrader and release tests, 58 passed.

**Daily tracking (2026-11-12):** the user wants the bot tracked every day, trading or not. Live, `MnqNoiseV38.cs` now
writes `Documents\NinjaTrader 8\MnqNoiseV38_daily_<account>.csv`, one row a session after the 16:00 close (the model's
16:00 exit counted): the mode, whether orders were placed, the account's balance / net liquidation / realized P/L, the
strategy's real P/L and trades that day, the model's P/L and trades that day and its total, the prop floor and room,
tomorrow's contracts. Rows append across restarts. With **Place orders off** the dashboard says TRACKING ONLY and the
model's trades are what the bot would have taken; a "Model today" line shows the model's day in every state.
`test_v38_daily_tracking_log` (live in the simulator, Place orders off: no real trade, one row a session, the model's
trades per day matching the model's, each day's P/L the change in the running total, a second run appending); the
NinjaTrader and release tests, 59 passed. NinjaTrader must be open for anything to be written.

**The MNQ Bot Dashboard refreshed (2026-11-12):** its journal is now the current bot's (U58 with the 0.25 brake,
Funded growth, the NinjaTrader simulator on the 2025-26 stand-in window: 783 trades, +$75,486.34, 50.2% winners, the
journal NinjaTrader writes), replacing U48's of 2026-11-03; the page's fixed text matches (up to 60 contracts, the
45-minute time stop, tested win rate 50.2%, profit factor 1.91). The page's own check passed. The hourly round now
refreshes it whenever the file the user runs changes, and attaches the user's live or daily journal once they send it.
The full suite (before the daily log change): 706 passed; the NinjaTrader and release tests after it: 59 passed.

## G479: the gap slot, the source of the red days (registered 2026-11-12, before its run)

The user: "if that much red exists, something is wrong with the strategy, find out what it is and fix it". On the
current bot's journal (U58, brake 0.25, 2025-26 window, 783 trades; looked at before this registration): **170 of the
201 red days start with a 09:40 entry and 106 have only 09:40 entries.** Those entries (the gap trade and its
small-gap and opening-drive fill-ins) reach the 09:55 exit 117 times (80% winners, +$42,855) and are stopped 154
times (all losers, −$33,711): +$9,144 in all against +$66,342 for the rest. `research/g479_gap_slot.py`: U58 against
V1 no small-gap fill-in (`gap_go_small_k` −1; U58 0, any gap), V2 no opening-drive fill-in (`gap_go_drive_k` 0; U58
0.6), V3 the gap trigger at 0.8 noise (U58 0.65), V4 = V1 + V2. **Rule:** the balanced rule (G473) adopts one into
Funded growth; green days (G415's fresh starts) are reported, and a variant that adds at least 5 points of green days
at no more than 10% of U58's $ on each set and no more starts lost is offered as an opt-in. Run once.

**G479 result (2026-11-12): rejected; the gap slot is where the red shows, not why.** Fresh starts (U58 $50.4 a session,
green days 41.9%): V1 no small-gap fill-in $54.1 (+7%), green 42.9%; V2 no drive fill-in $35.8, 41.9%; V3 trigger 0.8
$46.9, 41.8%; V4 no fill-ins $41.7, 43.2%. Development (U58 $49.94, 0%): V1 $49.69 (−0.5%), V2 $45.5, V3 $45.8 at 9.8%
lost, V4 $44.0. Unseen (U58 $84.9, 1.6%): V1 $87.1 (+2.7%), V2 $82.3, V3 $75.3 at 8.1%, V4 $84.9. V1 is a little better
on two sets but not on development, and short of the balanced rule's 5%; none moves the green days more than 1.3 points
(G457, no gap trade at all: +3.7 points at half the money). The red days are the breakout's ordinary losers.
`verification/noise_v2/g479_gap_slot.txt`.

## G480: exits for green days (registered 2026-11-12, before its run)

The user wants most days green. U58 ends 41.9% of its traded days green on the fresh starts; its money comes from a
few trend days with a 2.0-noise take-profit. `research/g480_green_exits.py`: U58 against E1-E3 take-profit 0.5 / 0.75
/ 1.0 noise units, E4 0.5 with the lock at 0.15, E5 no new entries once the day is green (`day_stop_profit` $1), E6
0.75 + E5, E7 E4 + E5. **Rule:** the balanced rule (G473) decides a default change. Otherwise, among the variants with
green days at least 50% of traded days on the fresh starts and a positive $ a session on every set, the one with the
most $ a session on unseen is built as an opt-in "Funded green days" mode, with its cost stated; if none reaches 50%,
nothing is built and the closest is reported. Run once.

**G480 result (2026-11-12): most days green costs about two thirds of the money; built as the opt-in "Funded green
days".**

| | green traded days (fresh) | fresh $ a session (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| **U58 (brake 0.25)** | 41.9% | **$50.4** (0) | **$49.9** (0%) | **$84.9** (1.6%) |
| E1 target 0.5 | 44.3% | $23.4 (1) | $31.4 (0%) | $38.4 (7.9%) |
| E2 target 0.75 | 42.3% | $38.3 (0) | $39.3 (3.4%) | $56.0 (6.3%) |
| E3 target 1.0 | 41.3% | $50.0 (0) | $39.1 (0%) | $64.7 (3.2%) |
| E4 target 0.5, lock 0.15 | 44.6% | $29.4 (0) | $19.8 (3.2%) | $26.5 (5.8%) |
| **E5 stop once green** | **55.0%** | $11.7 (1) | $13.7 (0%) | $31.1 (2.9%) |
| E6 0.75 + stop once green | 58.5% | $15.0 (0) | $7.5 (6.7%) | $18.5 (0%) |
| E7 E4 + stop once green | 60.2% | $14.6 (0) | $4.3 (3.4%) | $12.8 (3.2%) |

A nearer target alone barely moves the green days (breakouts that reach 0.5 noise mostly reach 2.0 as well); only
stopping for the day once it is green does. Of the three variants above 50% that make money on every set, E5 makes the
most unseen, so per the rule it is built: **Funded green days** = Funded growth with `DayProfitStop` $1 (no new entries
once today's closed P/L is above $0). It keeps 23-37% of U58's money. `test_v38_opt_in_modes` covers it (trade for
trade with the model); the NinjaTrader and release tests, 60 passed. `verification/noise_v2/g480_green_exits.txt`.

## G481: stop once green, from a time of day (registered 2026-11-12, before its run)

Hourly round, from G480: stopping once the day is green made 55% of traded days green but cut the money to a third,
because the trend days that pay start green and keep going. A middle ground: the morning trades as usual, and from
11:00, 12:00 or 13:00 no new entries once today's P/L is above $0 (`day_stop_late_from` / `day_stop_late` $1; G310 tried
13:00 at $500 on the sprint). `research/g481_late_green_stop.py`. **Rule:** the balanced rule (G473) for a default
change; else G480's opt-in rule (green days at least 50% on the fresh starts, positive on every set, the most $ unseen),
which would replace E5 in "Funded green days" only if it makes more on all three sets. Run once.

**G481 result (2026-11-12): "Funded green days" now stops once green from 11:00 (replaces G480's E5).**

| | green traded days (fresh) | fresh $ a session (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| U58 (brake 0.25) | 41.9% | $50.4 (0) | $49.9 (0%) | $84.9 (1.6%) |
| G480 E5, stop once green all day | 55.0% | $11.7 (1) | $13.7 (0%) | $31.1 (2.9%) |
| **stop once green from 11:00** | **50.5%** | **$24.8** (1) | **$24.7** (0%) | **$56.6** (4.7%) |
| from 12:00 | 48.0% | $33.4 (1) | $33.6 (9.9%) | $60.5 (1.5%) |
| from 13:00 | 46.2% | $36.1 (1) | $32.1 (3.2%) | $58.8 (3.1%) |

From 11:00 is the only one at 50% or more; it makes about twice E5 on every set, so per the registered rule it replaces
E5 (unseen losses 4.7% against E5's 2.9%). It keeps half to two thirds of U58's money. Built: `V38Settings.DayStopLateFrom`
/ `DayStopLate` in `MnqNoiseV38.cs` (the model's G310 rule), "Funded green days" = 11:00 and $1;
`test_v38_opt_in_modes` (trade for trade with `day_stop_late_from` 660, `day_stop_late` 1); the NinjaTrader and release
tests pass. `verification/noise_v2/g481_late_green_stop.txt`.

**G481 in NinjaTrader's simulator (2026-11-12), the 2025-26 window:** Funded green days 393 trades, **216 traded days:
109 green, 107 red (50.5%)**, net **+$4,232** (Funded growth on the same window: 783 trades, 330 traded days 39.1%
green, +$75,486). The green days hold up; on this window the money falls far more (−94%) than on the replay sets
(−34% to −51%): the window's money came mostly from afternoon trend legs on days already green by 11:00 (the
+$33,412 day of 2026-09-21 among them). Note: the simulator binary in `ninjatrader/tests/Sim/bin` was stale (built
before the opt-in modes) and ran the mode as Custom until rebuilt; the tests always build their own copy and were not
affected; the Funded growth journal on the dashboard is identical after the rebuild. The MNQ Bot Dashboard now shows
this mode's journal (as the user asked), with the comparison in its subtitle.
`verification/noise_v2/g481_nt_window_green_days.csv`.

## G482: lock the green instead of stopping (registered 2026-11-12, before its run)

The user: make green days significantly more profitable, with fewer red days. G481 stops new entries once the day is
green (from 11:00) and so misses the afternoon trend legs (the simulator window: +$4,232 against +$75,486). The other
way: keep trading, but once the day is up `day_lock_at`, every open trade's stop goes no lower than where today's P/L
is `day_lock_keep`, so a green day cannot close red (G294's day lock; G380 tried it only at $800+ for money).
`research/g482_green_lock.py`: U58 and G481's Funded green days against L1 lock at +$150 keeping $1, L2 +$300 keeping
$1, L3 +$300 keeping $100, L4 L2 without the small-gap fill-in, L5 L2 + G481's stop once green from 13:00.
**Rule:** a variant replaces G481 in Funded green days if its green traded days on the fresh starts are at least G481's
50.5% and it makes at least 25% more $ a session than G481 on each of the three sets, with no more starts lost on any;
of several, the most $ unseen. Then NinjaTrader's simulator on the window must show it at least 50% green traded days.
The balanced rule (G473) separately decides a Funded growth change. Run once.

**G482 result (2026-11-12): no lock makes most days green; L4 improves Funded growth (pending NinjaTrader's check).**

| | green traded days (fresh) | fresh $ a session (lost of 16, worst month) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| U58 (brake 0.25) | 41.9% | $50.4 (0, −$2,019) | $49.94 (0%) | $84.87 (1.6%) |
| Funded green days (G481) | 50.5% | $24.8 (1, −$1,329) | $24.7 (0%) | $56.6 (4.7%) |
| L1 lock +$150 keep $1 | 43.4% | $52.2 (1) | $43.4 (0%) | $82.3 (3.1%) |
| L2 lock +$300 keep $1 | 42.8% | $60.4 (0) | $50.47 (0%) | $83.55 (1.6%) |
| L3 lock +$300 keep $100 | 43.5% | $55.6 (0) | $49.0 (3.4%) | $76.8 (4.8%) |
| **L4 = L2, no small-gap fill-in** | 43.6% | **$61.9 (0, −$1,977)** | **$50.35 (0%)** | **$85.65 (1.6%)** |
| L5 L2 + stop once green from 13:00 | 47.4% | $47.1 (2) | $37.6 (0%) | $55.9 (6.2%) |

Green days: no variant reaches G481's 50.5%, so Funded green days is unchanged. A green-day lock keeps the trend days
(more money) but barely changes how many days are green: the red days are days that never turn green. **L4 meets the
balanced rule for Funded growth** (+22.8% / +0.8% / +0.9%, average +8.2%, no more starts lost, worst month $42
shallower). Its NinjaTrader build (a +$300 day lock keeping $1 and no small-gap fill-in, in plain Funded growth on
5-minute bars, plus a guard so a negative `FillSmallK` turns the fill-in off as in the model) is saved as
`verification/noise_v2/g482_l4_pending.patch`: the simulator run that must confirm it on the 2025-26 window waits on an
approval in this session, so the file the user runs is unchanged until that run passes. `verification/noise_v2/g482_green_lock.txt`.

**G482 L4 in NinjaTrader's simulator (2026-11-12): rejected.** On the 2025-26 window Funded growth with L4 makes
**+$57,186.35** (744 trades, 312 traded days, 124 green / 188 red, 39.7%) against Funded growth's **+$75,486.34** (783
trades, 39.1% green): −24%, so it fails the balanced rule's NinjaTrader check. The +$300 lock closes trend trades on
the window's biggest days early (the replay sets' gain was mostly on the fresh starts). The file the user runs stays
as it is; the patch stays in `verification/noise_v2/g482_l4_pending.patch` for the record; the simulator binary is
rebuilt from the unchanged file.

## G483: scratch instead of lose (registered 2026-11-12, before its run)

The user wants about 50 red of ~216 traded days. G482: the red days are days that never turn green; some of them had a
trade that went a little the right way first and then hit its stop. Here the lock (stop to entry + `lock_plus` once a
trade is up `lock_at` x its max loss) arms sooner with a cushion that just covers the fees, so such a trade ends about
flat-to-green: `research/g483_scratch.py`, U58 and Funded green days (G481) against S1 `lock_at` 0.15 / `lock_plus` 1
point (U58 0.35 / 2.5), S2 0.10 / 1, S3 S1 inside Funded green days. (G404 tried sooner locks with the +2.5 cushion on
U48; G480 E4 with a 0.5 target.) **Rule:** the balanced rule (G473) for Funded growth; for Funded green days, at least
G481's 50.5% green traded days and at least 25% more $ than G481 on each set with no more starts lost; then the
simulator on the window. Run once.

**G483 result (2026-11-12): rejected, all three; scratching makes fewer green days, not more.** Fresh starts (green
traded days / $ a session / lost of 16): U58 41.9% / $50.4 / 0; Funded green days 50.5% / $24.8 / 1; S1 lock 0.15 +1
41.1% / $34.8 / 1; S2 0.10 +1 40.3% / $37.2 / 1; S3 46.1% / $18.0 / 3. Development (U58 $49.9, 0%): S1 $41.7 at 13.3%
lost, S2 $32.3 at 16.6%, S3 $23.3. Unseen (U58 $84.9, 1.6%): S1 $63.2 at 6.1%, S2 $58.7 at 9.5%, S3 $52.3 at 9.4%. A
scratched trade frees the bot to take the next signal (1.69-1.72 trades a session against 1.58), and those extra trades
lose: the days stay red and the trend days lose their winners. `verification/noise_v2/g483_scratch.txt`.

## G484: Funded green days with more money (registered 2026-11-12, before its run)

Hourly round. Funded green days (G481: from 11:00 no new entries once the day is green) keeps its green rule; its size
and its gap slot change: `research/g484_green_days_more_money.py`, P1 +1 MNQ per $1,250 (G478: +14% on U58), P2 no
small-gap fill-in (G479 V1), P3 both. **Rule:** replaces G481's settings in Funded green days if its green traded days
on the fresh starts are at least 50% and it makes at least 10% more $ a session than G481 on each of the three sets with
no more starts lost on any; then NinjaTrader's simulator on the window must show at least 50% green traded days and
more net than G481's +$4,232. Run once.

**G484 result (2026-11-12): rejected by its rule (more starts lost); P3 is +21-31% money at 51% green.**

| | green traded days (fresh) | fresh $ (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| Funded green days (G481) | 50.5% | $24.8 (1) | $24.7 (0%) | $56.6 (4.7%) |
| P1 +1 per $1,250 | 50.3% | $33.2, +34% (2) | $31.9, +29% (3.4%) | $66.1, +17% (7.9%) |
| P2 no small-gap fill-in | 50.9% | $25.5, +3% (1) | $25.3, +3% (0%) | $57.9, +2% (3.1%) |
| P3 both | 51.2% | $32.0, +29% (2) | $32.4, +31% (3.4%) | $68.7, +21% (6.3%) |

P3 keeps most traded days green and makes 21-31% more on every set, but loses one more start on each set, so it fails
"no more starts lost"; P2 alone is too small (+2-3%). Funded green days unchanged. Offered to the user as a choice.
`verification/noise_v2/g484_green_days_more_money.txt`.

## G485: skip the days that end red (registered 2026-11-12, before its run)

Hourly round. G482-G484: the red days are days that never turn green, and no exit, lock or sizing change moved Funded
green days much past 51%. The other way is not to trade those days: a day filter inside Funded green days (G481).
`research/g485_green_day_filters.py`: D1 `calm_k` 0.8 and D2 0.9 (no entries after a calmer stretch; U58 has 0.7),
D3 `gap_block` 0.005 (no entries against a 0.5%+ opening gap), D4 `drive_filter_k` 0.25 (no entries against the
09:30-10:00 drive; G318 tested it for passes only). **Rule:** a variant replaces G481's settings in Funded green days
if its green traded days on the fresh starts are at least 53%, its $ a session is at least 90% of G481's on each of
the three sets, and it loses no more starts on any; of several, the most green days. Then NinjaTrader's simulator on
the 2025-26 window must show more than 50.5% green traded days, fewer than 107 red days and a net of at least +$4,232
(a D3/D4 win is built in the C# file first). The balanced rule (G473) does not apply (no Funded growth variant). Run once.

**G485 result (2026-11-12): rejected, all four; no day filter moves the green days (49-51%).**

| | green traded days (fresh) | fresh $ (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| Funded green days (G481) | 50.5% | $24.8 (1) | $24.7 (0%) | $56.6 (4.7%) |
| D1 calm 0.8 | 50.7% | $26.2 (0) | $28.8 (3.2%) | $58.0 (1.6%) |
| D2 calm 0.9 | 49.3% | $26.8 (0) | $30.9 (0%) | $47.6 (1.6%) |
| D3 not against a 0.5% gap | 50.1% | $24.3 (1) | $25.3 (0%) | $52.9 (4.7%) |
| D4 not against the drive | 50.1% | $23.8 (2) | $25.2 (0%) | $56.6 (7.7%) |

None reaches 53% green traded days, so Funded green days is unchanged and the simulator check does not run. The days
these filters skip end red about as often as the days they keep: a day's chance of ending green is not visible in its
calm stretch, its gap or its opening drive. (D1 makes 2-17% more with fewer starts lost on two sets, one more on
development; not this rule's aim.) `verification/noise_v2/g485_green_day_filters.txt`.

## G486: stop once green from 10:30 or 10:00; and U58 with calm 0.8 (registered 2026-11-12, before its run)

Hourly round. Stopping once green all day (G480 E5) made 55% of traded days green at a third of the money; from 11:00
(G481) 50.5% at half to two thirds; the times between were never run. `research/g486_green_from_1030.py`: inside Funded
green days, G1 from 10:30 (`day_stop_late_from` 630) and G2 from 10:00 (600); and, for Funded growth, C1 U58 with
`calm_k` 0.8 (G485's D1 made more with fewer starts lost on two sets inside Funded green days; G426 ran U58 only at 0
and 0.6). **Rule, green days:** G1 or G2 replaces 11:00 in Funded green days if its green traded days on the fresh
starts are at least 52.5%, its $ a session at least 80% of G481's on each set, with no more starts lost on any; of
both, the more green days; then the simulator on the 2025-26 window must show more green traded days than 50.5% and
fewer red days than 107. **Rule, Funded growth:** the balanced rule (G473) for C1 against U58, then NinjaTrader's
growth run on the window at least +$75,486 with a worst day no deeper than −$1,000. Run once.

**G486 result (2026-11-12): rejected, all three.**

| | green traded days (fresh) | fresh $ (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| U58 (Funded growth) | 41.9% | $50.4 (0) | $49.9 (0%) | $84.9 (1.6%) |
| C1 U58 calm 0.8 | 42.5% | $48.9 (0) | $57.9 (3.0%) | $74.4 (1.6%) |
| Funded green days (G481, from 11:00) | 50.5% | $24.8 (1) | $24.7 (0%) | $56.6 (4.7%) |
| G1 green stop from 10:30 | 53.6% | $13.4, −46% (1) | $19.3, −22% (0%) | $44.8, −21% (3.1%) |
| G2 green stop from 10:00 | 55.0% | $11.7, −53% (1) | $13.7, −44% (0%) | $31.1, −45% (2.9%) |

Each half hour earlier adds about 2-3 points of green days and costs a fifth to a half of the money (G2 is G480's E5:
the first check is 10:00), so neither keeps 80%. C1 makes less on the fresh and unseen sets and loses more starts on
development: it fails the balanced rule (U58 keeps 0.7). Nothing changes; no simulator run.
`verification/noise_v2/g486_green_from_1030.txt`.

## G487: Funded green days with the day lock (registered 2026-11-12, before its run)

Hourly round. G482 tried the day lock on U58 and with the green stop from 13:00 (L5), never with Funded green days'
11:00 stop. Before 11:00 Funded green days trades as U58 does, and a morning that is up can still close red; the lock
keeps it green while a trend trade runs. `research/g487_green_days_lock.py`: Funded green days (G481) with K1
`day_lock_at` $300 / `day_lock_keep` $1, K2 $150 / $1 (`DayLockAt` / `DayLockKeep` exist in the C# file).
**Rule:** a variant replaces G481's settings in Funded green days if its green traded days on the fresh starts are at
least 50.5%, its $ a session at least 10% more than G481's on each set, with no more starts lost on any; of both, the
most $ unseen. Then NinjaTrader's simulator on the 2025-26 window (rebuilt) must show at least 50.5% green traded days
and a net above +$4,232. Run once.

**G487 result (2026-11-12): rejected, both.**

| | green traded days (fresh) | fresh $ (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| Funded green days (G481) | 50.5% | $24.8 (1) | $24.7 (0%) | $56.6 (4.7%) |
| K1 + lock +$300 keep $1 | 51.9% | $30.6, +24% (3) | $20.9, −15% (0%) | $52.9, −7% (6.0%) |
| K2 + lock +$150 keep $1 | 52.9% | $35.5, +43% (1) | $19.4, −21% (3.2%) | $53.4, −6% (3.1%) |

The lock adds 1-2 points of green days and helps on the fresh starts, but makes less on development and unseen (it
closes trend trades on days that would have gone on), as G482's lock did in the simulator. Funded green days is
unchanged; no simulator run. `verification/noise_v2/g487_green_days_lock.txt`.

## G488: a recovery trade after a loser (registered 2026-11-12, before its run)

Hourly round. The red days are days whose losses are never made back. In Funded green days (G481) the trade after a
losing trade today takes a nearer take-profit, so it more often wins and turns the day: `research/g488_recovery_trade.py`,
R1 `after_loss_tp` 0.75, R2 1.0 noise units (U58 2.0), R3 R1 with twice the contracts (`after_loss_qty_div` 0.5,
still sized within the day's budget and the trailing floor). (v2.3 tested `after_loss_tp` on the old fixed-size bot
for money; never with growth sizing or for green days.) **Rule:** a variant replaces G481's settings in Funded green
days if its green traded days on the fresh starts are at least 53%, its $ a session at least 90% of G481's on each
set, with no more starts lost on any; of several, the most green days. Then it is built in the C# file (the after-loss
take-profit and contracts are not there yet) with a parity test, and NinjaTrader's simulator on the 2025-26 window must
show more than 50.5% green traded days and fewer than 107 red days, net at least +$4,232. Run once.

**G488 result (2026-11-12): rejected, all three.**

| | green traded days (fresh) | fresh $ (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| Funded green days (G481) | 50.5% | $24.8 (1) | $24.7 (0%) | $56.6 (4.7%) |
| R1 after a loser target 0.75 | 52.9% | $33.4 (0) | $17.7, −28% (0%) | $47.0, −17% (6.5%) |
| R2 after a loser target 1.0 | 52.8% | $33.0 (0) | $17.8, −28% (6.7%) | $52.6, −7% (3.2%) |
| R3 R1, twice the contracts | 51.7% | $41.7 (0) | $13.6, −45% (22.4%) | $51.1, −10% (3.2%) |

None reaches 53% green traded days; all make less on development and unseen (the trade after a loser is often the
day's trend trade, and the nearer target cuts it). Doubling after a loser loses 22% of the development starts.
Funded green days is unchanged; no simulator run. `verification/noise_v2/g488_recovery_trade.txt`.

## G489: what the red days are made of, a measurement (registered 2026-11-12, before its run)

Hourly round. G482-G488 changed exits, locks, filters, sizing and the trade after a loser; none moved Funded green days
past about 53% green traded days at its money. Before the next idea, a measurement of its red days on G415's fresh
starts (`research/g489_red_day_anatomy.py`): for each traded day, the trade count, whether the first trade lost and was
in the 09:35 gap slot, whether the day's closed P/L was above $0 before it closed red, and the most points any trade was
its way (its best excursion); for red and green days and by trade count. No setting changes: it only picks the next
test's target. Run once.

**G489 result (2026-11-12), a measurement.** Fresh starts, Funded green days: 2,131 traded days, 50.9% green. Of the
1,047 red days: **94.5% start with a losing first trade, 68.9% with the 09:35 gap trade, 59.7% with the gap trade
stopped** (on green days the gap trade is stopped first on 11.2%); 53.6% have one trade only; only 5.6% were green on
closed trades before closing red (so day locks and stop-once-green can't fix many); in 41.2% a trade was 40+ points its
way at some point. Green share by the day's trade count: 1 trade 51%, 2 59%, 3 57%, 4 34%, 5+ 0-25%. **The target:**
the gap trade's stop sits at the 09:30 open (a wide risk), and it goes to break-even only once a bar closes 1.5x that
risk its way, so gap trades that run and come back end at the full stop. `verification/noise_v2/g489_red_day_anatomy.txt`.

## G490: protect the gap trade sooner, with a cushion (registered 2026-11-12, before its run)

From G489. New in `mnqbot/noise.py` (off by default): `gap_go_be_plus`, the gap trade's break-even stop at the entry
plus this many points instead of one tick. `research/g490_gap_green.py`: inside Funded green days (G481), B1 the gap
stop to entry + 2.5 points once a bar closes 0.5x its risk its way (`gap_go_be` 0.5, now 1.5), B2 0.75x + 2.5, B3 0.5x +
a tick; and U58 + B1 for Funded growth (G275 tested 0.75 / 1.0 on the sprint for passes only). Note: G489 measured the
fresh starts, which pick the target here; development and unseen are untouched. **Rule, green days:** a variant replaces
G481's settings if its green traded days on the fresh starts are at least 53%, its $ a session at least 90% of G481's
on each set, with no more starts lost on any; of several, the most green days. **Rule, Funded growth:** the balanced
rule (G473) for U58 + B1. Either is then built in the C# file (`GapGoBe` exists; the cushion is new) with a parity test
and checked in NinjaTrader's simulator on the 2025-26 window (green days: more than 50.5% green, fewer than 107 red,
net at least +$4,232; growth: at least +$75,486, worst day no deeper than −$1,000). Run once.

**G490 result (2026-11-12): rejected, all four; B2 comes closest.**

| | green traded days (fresh) | fresh $ (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| U58 (Funded growth) | 41.9% | $50.4 (0) | $49.9 (0%) | $84.9 (1.6%) |
| U58 + B1 | 44.8% | $42.0 (0) | $50.1 (6.4%) | $83.4 (1.6%) |
| Funded green days (G481) | 50.5% | $24.8 (1) | $24.7 (0%) | $56.6 (4.7%) |
| B1 gap to +2.5 at 0.5x risk | 53.6% | $21.3, −14% (2) | $22.3, −10% (0%) | $54.7, −3% (6.2%) |
| B2 gap to +2.5 at 0.75x | 52.4% | $24.5, −1% (1) | $24.6, −0% (0%) | $59.0, +4% (4.7%) |
| B3 gap to +1 tick at 0.5x | 50.1% | $20.1 (2) | $26.2 (0%) | $55.4 (4.6%) |

Protecting the gap trade sooner does turn some red days green (B1 +3.1 points, B2 +1.9) but cuts gap trades that would
have run, and a stop a tick past the entry (B3) ends red after fees. B1 makes too little and loses more starts; B2
keeps the money but misses the 53% bar; U58 + B1 makes less on two sets and loses 6.4% of development starts.
Nothing changes; no simulator run. `gap_go_be_plus` stays in the model, off. `verification/noise_v2/g490_gap_green.txt`.

## G491: the gap trade out sooner (registered 2026-11-12, before its run)

From G489 / G490: most red days start with a stopped gap trade, and gap trades that reach their 09:55 exit win about
80% of the time (G479). A shorter hold leaves less time for the stop. `research/g491_gap_exit_green.py`: inside Funded
green days (G481), X1 the gap trade out at the 09:45 bar's open (`gap_go_exit` 585; now 595), X2 09:50 (590); and U58
+ X2 for Funded growth (G276 tested 09:45 on the old sprint for passes only; `GapGoExit` exists in the C# file).
**Rule, green days:** as G490's (at least 53% green traded days on the fresh starts, at least 90% of G481's $ on each
set, no more starts lost on any; the most green days). **Rule, Funded growth:** the balanced rule (G473). Then
NinjaTrader's simulator on the 2025-26 window as in G490. Run once.

**G491 result (2026-11-12): rejected, all three; the gap trade's last minutes carry its money.**

| | green traded days (fresh) | fresh $ (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| U58 (Funded growth) | 41.9% | $50.4 (0) | $49.9 (0%) | $84.9 (1.6%) |
| U58 + X2 out 09:50 | 42.8% | $38.0 (0) | $44.9 (6.6%) | $74.7 (3.2%) |
| Funded green days (G481) | 50.5% | $24.8 (1) | $24.7 (0%) | $56.6 (4.7%) |
| X1 gap out 09:45 | 51.2% | $13.8 (1) | $25.1 (0%) | $45.0 (4.7%) |
| X2 gap out 09:50 | 51.3% | $20.9 (1) | $18.1 (0%) | $49.6 (3.1%) |

A sooner exit adds under 1 point of green days and costs 10-45% of the money: the gap trades that reach 09:55 make
most of their move in its last minutes. Nothing changes; no simulator run. `verification/noise_v2/g491_gap_exit_green.txt`.

## G492: the small green-day gains together (registered 2026-11-12, before its run)

Hourly round. Each of G485 D1 (`calm_k` 0.8: +0.2 points, more $), G487 K2 (day lock +$150 / $1: +2.4 points, more $
fresh, less elsewhere) and G490 B2 (gap stop to entry + 2.5 points at 0.75x risk: +1.9 points, the same $) moved
Funded green days a little; together they may add up. `research/g492_green_combo.py`: C1 B2 + D1, C2 C1 + K2. These
were picked on the same three sets, so NinjaTrader's 2025-26 window is the check that was not used to pick them.
**Rule:** a variant replaces G481's settings in Funded green days if its green traded days on the fresh starts are at
least 53%, its $ a session at least G481's on each set, with no more starts lost on any; of both, the most green days.
Then it is built in the C# file (the gap cushion is new) and the simulator on the window must show more than 50.5% green
traded days, fewer than 107 red days and a net of at least +$4,232. Run once.

**G492 result (2026-11-12): rejected by its rule, narrowly; C1 is the best Funded green days variant so far.**

| | green traded days (fresh) | fresh $ (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| Funded green days (G481) | 50.5% | $24.8 (1) | $24.7 (0%) | $56.6 (4.7%) |
| **C1 gap +2.5 at 0.75x + calm 0.8** | **53.2%** | **$27.5, +11% (0)** | **$28.7, +16% (3.2%)** | **$58.1, +3% (1.6%)** |
| C2 C1 + day lock $150 | 55.3% | $33.3, +35% (0) | $21.1, −15% (0%) | $52.1, −8% (1.6%) |

C1 meets every part of the rule but one: it loses one development start (3.2%) where G481 loses none, while it loses
fewer on the fresh (0 against 1) and unseen (1.6% against 4.7%) sets. As registered, "no more starts lost on any" fails,
so Funded green days is unchanged and the simulator check does not run. C2 has the most green days of any variant that
makes money on every set, but makes less on development and unseen. Offered to the user as a choice.
`verification/noise_v2/g492_green_combo.txt`.

**Final check (2026-11-12, the user: "finalize and make sure it's all right with 0 errors").** On the file as it is
(default Funded growth = U58, brake 0.25, 5-minute chart): the full suite **709 passed, 0 failed**; the NinjaTrader and
release tests 60 passed (the strategy compiled as C# 5 with warnings as errors, as NinjaTrader 8 does, and run trade for
trade against the model); the simulator rebuilt with 0 warnings, 0 errors; the lint clean. Nothing in the strategy file
changed since G481 (G482-G492 left every mode as it was).

## G493: a loser limit in Funded green days (registered 2026-11-12, before its run)

Hourly round. G489: days with 4 or more trades end green 0-34% of the time, so their later trades mostly deepen the
loss. U58 has no loser limit (G421); in Funded green days a limit may keep the money those days lose.
`research/g493_green_days_losers.py`: M1 no new entries after 2 losing trades today (`max_losers` 2), M2 after 3
(`MaxLosers` exists in the C# file). **Rule:** a variant replaces G481's settings in Funded green days if its green
traded days on the fresh starts are at least G481's 50.5%, its $ a session at least 10% more than G481's on each set,
with no more starts lost on any; of both, the most $ unseen. Then the simulator on the 2025-26 window: at least 50.5%
green traded days and a net above +$4,232. Run once.

**G493 result (2026-11-12): rejected, both; no effect.**

| | green traded days (fresh) | fresh $ (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| Funded green days (G481) | 50.5% | $24.8 (1) | $24.7 (0%) | $56.6 (4.7%) |
| M1 2 losers a day | 50.3% | $23.5 (1) | $26.4 (3.4%) | $52.8 (6.5%) |
| M2 3 losers a day | 50.4% | $25.0 (1) | $26.0 (3.4%) | $55.0 (6.2%) |

Within a few % either way, with more starts lost on two sets: the 11:00 green stop and the day budget already end most
long losing days. Funded green days unchanged; no simulator run. `verification/noise_v2/g493_green_days_losers.txt`.

## G494: the gap trade's stop nearer (registered 2026-11-12, before its run)

Hourly round, from G489-G491: the gap trade's stop at the 09:30 open is where most red days start. A nearer stop loses
less when hit (a smaller red day, or one a later trade can make back) at the cost of being hit more often.
`research/g494_gap_stop_nearer.py`: inside Funded green days (G481), the gap stop `gap_go_stop_frac` of the way from
the 09:30 open toward the 09:30 bar's close: S1 0.25, S2 0.5 (G111 tested it on an early bot for money; not in the C#
file). **Rule:** as G490's (at least 53% green traded days on the fresh starts, at least 90% of G481's $ on each set,
no more starts lost on any; the most green days); then built in the C# file with a parity test and checked in the
simulator on the 2025-26 window (more than 50.5% green, fewer than 107 red, net at least +$4,232). Run once.

**G494 result (2026-11-12): rejected, both; fewer green days.**

| | green traded days (fresh) | fresh $ (lost of 16) | development (lost) | unseen (lost) |
|---|---|---|---|---|
| Funded green days (G481) | 50.5% | $24.8 (1) | $24.7 (0%) | $56.6 (4.7%) |
| S1 gap stop 0.25 nearer | 48.5% | $19.4 (2) | $27.1 (0%) | $61.5 (4.6%) |
| S2 gap stop 0.5 nearer | 46.8% | $15.1 (1) | $25.0 (3.2%) | $73.1, +29% (3.1%) |

A nearer gap stop is hit more often, so more days start red (as expected, the opposite of the aim). S2 makes much more
on unseen (+29%) and a little more on development, but less on the fresh starts; not this rule's aim, noted for a
Funded growth test. Nothing changes; no simulator run. `verification/noise_v2/g494_gap_stop_nearer.txt`.

**Go-live (2026-11-13): the user starts the bot.** The strategy file is unchanged since the final check (709 tests
passed; sha256 of `ninjatrader/Strategies/MnqNoiseV38.cs` begins `ac3165b930f992fd`). The hourly rounds go on, and the
file changes only when a test passes its registered rule; the user is told before any change.

## G495: how often a fresh 50K reaches +$25,000 in a year, a measurement (registered 2026-11-13, before its run)

The user ran NinjaTrader's Strategy Analyzer on 2026-01-01 to 11-11 and got +$5,581, and wants +$25,000. Two findings
before this test: (1) their backtest had "Trailing drawdown and contract steps from date" at 2026-11-12, after its end,
so it never added a contract (the simulator reproduces it: +$5,241 to 2026-10-16); (2) with that date at 2026-01-02 the
same file makes +$9,847 on the simulator (Funded growth plus +$8,698, Funded aggressive +$9,698, Funded green days
+$2,729), and a 50K started 2025-01-02 made +$69,975 in 2026 alone (already sized up). The user's goal, stated as a
measure: **the share of fresh 50K starts at +$25,000 net within their first 12 months.** `research/g495_reach_25k.py`
on G415's fresh and G372's development / unseen starts: U58, P (+1 per $1,250), A1 (Funded aggressive), A1 + a $1,500
day budget once the floor stops, A1 + a contract per $750, A1 + faster steps (+1 per $400 from $5,000). Reported: that
share, the 12-month median and lower quartile, the best, and the share lost. A measurement: it picks what the next
round builds and confirms; no setting changes here. Run once.

**G495 result (2026-11-13), a measurement: a fresh 50K reaches +$25,000 in a year on 13-52% of starts; Funded growth
plus is the best balance.**

| 50K, first 12 months | fresh (16): reach $25K / median / lost | development (31) | unseen (64) |
|---|---|---|---|
| U58 (Funded growth) | 12.5% / $7,306 / 0% | 16.1% / $10,150 / 0% | 39.1% / $16,099 / 1.6% |
| **P +1 per $1,250 (Funded growth plus)** | **18.8% / $14,067 / 0%** | **25.8% / $13,880 / 3.2%** | **48.4% / $23,279 / 3.1%** |
| A1 (Funded aggressive) | 25.0% / $11,023 / 12.5% | 22.6% / $12,187 / 6.5% | 48.4% / $24,745 / 9.4% |
| A1 + $1,500 day once locked | 12.5% / $9,508 / 6.2% | 22.6% / $7,459 / 12.9% | 51.6% / $32,463 / 6.2% |
| A1 + 1 per $750 | 37.5% / $12,416 / 12.5% | 22.6% / $4,864 / 19.4% | 46.9% / $21,134 / 17.2% |
| A1 + 1 per $400 from $5,000 | 31.2% / $8,642 / 12.5% | 19.4% / $13,812 / 6.5% | 48.4% / $22,034 / 9.4% |

Funded growth plus has the highest median on the fresh and development starts, about as often reaches $25K as the
aggressive variants, and loses the fewest accounts after U58 (0-3.2%). The recent starts (fresh, 2023-25) are the
hardest: a single account reaches $25K in a year on 1 in 5 of them. **Two accounts** trade the same signals, so their
combined net is twice one's: with Funded growth plus on both, the median combined first year is about $28,000 (fresh
and development) to $46,000 (unseen). `verification/noise_v2/g495_reach_25k.txt`.

## G496: Funded growth plus toward +$25,000 a year (registered 2026-11-13, before its run)

From G495. `research/g496_plus_to_25k.py`: Funded growth plus (U58, brake 0.25, +1 MNQ per $1,250) against Q1 + a
$1,500 day budget once the floor stops (now $900), Q2 + $1,250, Q3 + faster steps (+1 per $400 from $5,000; now $650
from $9,000), Q4 no giveback brake. G495's measure. **Rule:** a variant replaces Funded growth plus's settings if, on
each of the three sets, its share of starts at +$25,000 in 12 months and its 12-month median are at least plus's and it
loses no more starts; of several, the highest share on unseen. Then NinjaTrader's simulator, a fresh start on
2026-01-02 (to 2026-10-16), must make at least plus's +$8,698. Run once.

**G496 result (2026-11-13): rejected, all four; Funded growth plus stays as it is.**

| first 12 months | fresh: reach $25K / median / lost | development | unseen |
|---|---|---|---|
| **Funded growth plus** | **18.8% / $14,067 / 0%** | **25.8% / $13,880 / 3.2%** | 48.4% / $23,279 / 3.1% |
| Q1 + $1,500 day once locked | 12.5% / $8,750 / 0% | 25.8% / $8,923 / 3.2% | 46.9% / $13,626 / 3.1% |
| Q2 + $1,250 day once locked | 12.5% / $12,346 / 0% | 22.6% / $11,067 / 3.2% | 50.0% / $25,925 / 4.7% |
| Q3 + 1 per $400 from $5,000 | 12.5% / $8,743 / 0% | 22.6% / $10,782 / 3.2% | 45.3% / $23,299 / 3.1% |
| Q4 no brake | 12.5% / $14,067 / 0% | 25.8% / $13,880 / 6.5% | 46.9% / $23,279 / 3.1% |

A bigger day budget or faster steps add bigger losing days as well as bigger winning ones; on the recent starts they
reach $25K less often. Nothing changes; no simulator run. `verification/noise_v2/g496_plus_to_25k.txt`.

## G497: Funded growth plus with the gap stop halfway and calm 0.8 (registered 2026-11-13, before its run)

Hourly round toward the user's +$25,000 (G495's measure). Two changes made more money in the green-days rounds: the
gap trade's stop halfway from the 09:30 open toward the 09:30 bar's close (G494 S2: +29% unseen inside Funded green
days) and `calm_k` 0.8 (G485 D1, G492 C1). `research/g497_plus_gap_stop.py`: Funded growth plus against R1 the gap
stop halfway (`gap_go_stop_frac` 0.5), R2 `calm_k` 0.8, R3 both. **Rule:** as G496's (on each set the share at
+$25,000 in 12 months and the median at least plus's, no more starts lost; the highest unseen share), then built (the
gap stop fraction is new in the C# file) and NinjaTrader's simulator on a fresh 2026-01-02 start must make at least
plus's +$8,698. Run once.

**G497 result (2026-11-13): rejected, all three; Funded growth plus stays.**

| first 12 months | fresh: reach $25K / median / lost | development | unseen |
|---|---|---|---|
| **Funded growth plus** | **18.8% / $14,067 / 0%** | **25.8% / $13,880 / 3.2%** | **48.4% / $23,279 / 3.1%** |
| R1 gap stop halfway | 6.2% / $7,205 / 6.2% | 16.1% / $6,964 / 9.7% | 42.2% / $20,282 / 6.2% |
| R2 calm 0.8 | 25.0% / $11,782 / 0% | 22.6% / $12,579 / 9.7% | 40.6% / $15,090 / 6.2% |
| R3 both | 0% / $3,924 / 6.2% | 29.0% / $10,454 / 3.2% | 39.1% / $13,368 / 4.7% |

Neither change carries over to plus's sizing: each reaches $25K less often on at least two sets and loses more
accounts. Nothing changes; no simulator run. `verification/noise_v2/g497_plus_gap_stop.txt`.

## G498: Funded growth plus with a sprint start (registered 2026-11-13, before its run)

Hourly round toward the user's +$25,000 (G495's measure). A fresh 50K grows slowly until its trailing floor stops
(+$2,000), because every trade is sized to the room above it. The Test sprint's rule (`sprint_qty` contracts for the
first `sprint_days` sessions until +$3,000, cut to the day's budget and the room above the floor) was tested for passing
Tests (G250-G290), never on a funded account's first year. `research/g498_plus_sprint_start.py`: Funded growth plus
against K1 3 MNQ for 10 sessions, K2 4 MNQ for 10, K3 3 MNQ for 20. **Rule:** as G496's (on each set the share at
+$25,000 in 12 months and the median at least plus's, no more starts lost; the highest unseen share), then NinjaTrader's
simulator on a fresh 2026-01-02 start must make at least plus's +$8,698 (the sprint exists in the C# file). Run once.

**G498 result (2026-11-13): rejected by its rule (more accounts lost, less on unseen); a sprint start reaches $25K
more often on the recent and development starts.**

| first 12 months | fresh: reach $25K / median / lost | development | unseen |
|---|---|---|---|
| **Funded growth plus** | 18.8% / $14,067 / 0% | 25.8% / $13,880 / 3.2% | **48.4% / $23,279 / 3.1%** |
| K1 3 MNQ x 10 sessions | 31.2% / $13,465 / 12.5% | 35.5% / $9,937 / 12.9% | 40.6% / $15,394 / 7.8% |
| K2 4 MNQ x 10 sessions | 37.5% / $11,630 / 12.5% | 38.7% / $10,207 / 9.7% | 45.3% / $20,523 / 10.9% |
| K3 3 MNQ x 20 sessions | 31.2% / $14,905 / 6.2% | 29.0% / $9,921 / 9.7% | 45.3% / $19,338 / 12.5% |

The sprint trades the first weeks at 3-4 MNQ against a $2,000 floor: when they go well the account is sized up months
sooner (more starts reach $25K on the fresh and development sets), when they go badly the account is gone (1 in 8 to
1 in 10 lost, against plus's 0-3%). It makes less on unseen. Nothing changes; no simulator run. Reported to the user
as a trade-off. `verification/noise_v2/g498_plus_sprint_start.txt`.

## G499: a sprint start with a defence (registered 2026-11-13, before its run)

From G498: a sprint start reaches $25K more often on the recent and development starts but loses 1 in 8-10 accounts.
Here the sprint is smaller, or drops to 1 MNQ while the room above the trailing floor is under $1,500 (G284's
`sprint_low_room` / `sprint_low_qty`). `research/g499_plus_safe_sprint.py`: Funded growth plus against L1 2 MNQ for 20
sessions, L2 3 MNQ for 20 with 1 MNQ under $1,500 of room, L3 4 MNQ for 10 with the same. **Rule:** as G496's (on each
set the share at +$25,000 in 12 months and the median at least plus's, no more starts lost; the highest unseen share),
then NinjaTrader's simulator on a fresh 2026-01-02 start at least plus's +$8,698. Run once.

**G499 result (2026-11-13): rejected by its rule (more accounts lost, lower medians on development / unseen); L3 is
the best result yet on the recent starts.**

| first 12 months | fresh: reach $25K / median / lost | development | unseen |
|---|---|---|---|
| **Funded growth plus** | 18.8% / $14,067 / 0% | 25.8% / $13,880 / 3.2% | 48.4% / $23,279 / 3.1% |
| L1 2 MNQ x 20 | 37.5% / $14,445 / 6.2% | 25.8% / $10,577 / 12.9% | 46.9% / $20,200 / 4.7% |
| L2 3 MNQ x 20, 1 under $1,500 | 37.5% / $14,443 / 0% | 29.0% / $10,216 / 9.7% | 46.9% / $19,243 / 6.2% |
| **L3 4 MNQ x 10, 1 under $1,500** | **50.0% / $22,679 / 6.2%** | 32.3% / $10,217 / 12.9% | 48.4% / $19,945 / 4.7% |

The defence cuts the losses on the recent and unseen starts (L3: 1 of 16 and 4.7%, against G498 K2's 12.5% and 10.9%)
and L3 reaches $25K on half of the recent starts (plus: 1 in 5), but on development it still loses 1 in 8 and every
variant's median is below plus's on development and unseen. Nothing changes; no simulator run. Reported to the user
as the trade-off. `verification/noise_v2/g499_plus_safe_sprint.txt`.

## G500: G499's sprint with a stronger defence (registered 2026-11-13, before its run)

From G499: L3 (4 MNQ for the first 10 sessions, 1 MNQ while under $1,500 above the floor) reaches $25K on half the
recent starts but loses 1 in 8 development starts. `research/g500_sprint_defence.py`: plus and L3 against M1 L3 with
the gap trade at 1 MNQ during the sprint (`sprint_gap_qty` 1; a gap trade's stop is the widest), M2 L3 at 1 MNQ under
$1,800 of room, M3 both. **Rule:** as G496's against plus (on each set the share at +$25,000 in 12 months and the
median at least plus's, no more starts lost; the highest unseen share); then built (the low-room defence is new in the
C# file) and NinjaTrader's simulator on a fresh 2026-01-02 start at least plus's +$8,698. Run once.

**G500 result (2026-11-13): rejected, all three.**

| first 12 months | fresh: reach $25K / median / lost | development | unseen |
|---|---|---|---|
| Funded growth plus | 18.8% / $14,067 / 0% | 25.8% / $13,880 / 3.2% | 48.4% / $23,279 / 3.1% |
| L3 (G499) | 50.0% / $22,679 / 6.2% | 32.3% / $10,217 / 12.9% | 48.4% / $19,945 / 4.7% |
| M1 L3 + gap 1 MNQ in the sprint | 37.5% / $16,886 / 6.2% | 32.3% / $9,476 / 9.7% | 45.3% / $19,408 / 4.7% |
| M2 L3, 1 MNQ under $1,800 | 43.8% / $13,663 / 0% | 29.0% / $9,370 / 9.7% | 48.4% / $19,716 / 6.2% |
| M3 both | 25.0% / $7,073 / 6.2% | 25.8% / $10,200 / 3.2% | 42.2% / $16,858 / 4.7% |

A stronger defence takes back most of the sprint's gain before it takes back its losses; none keeps plus's loss rate
and median on all three sets. Nothing changes; no simulator run. `verification/noise_v2/g500_sprint_defence.txt`.

## G501: careful steps until the floor stops, faster after (registered 2026-11-13, before its run)

Hourly round toward +$25,000 (G495's measure). G496-G500: more size early loses accounts; once the trailing floor has
stopped (+$2,000) the account has a cushion. `research/g501_locked_steps.py`: Funded growth plus ($1,250 a contract
throughout) against a contract per `profit_step` until the floor stops, then per `profit_step_locked` (G104, tested on
U28 only): N1 $1,500 then $1,000, N2 $1,500 then $750, N3 $1,250 then $750. **Rule:** as G496's (on each set the share
at +$25,000 in 12 months and the median at least plus's, no more starts lost; the highest unseen share); then built
(`profit_step_locked` is not in the C# file) and NinjaTrader's simulator on a fresh 2026-01-02 start at least plus's
+$8,698. Run once.

**G501 result (2026-11-13): rejected, all three; worse.**

| first 12 months | fresh: reach $25K / median / lost | development | unseen |
|---|---|---|---|
| **Funded growth plus** | 18.8% / $14,067 / 0% | **25.8% / $13,880 / 3.2%** | **48.4% / $23,279 / 3.1%** |
| N1 $1,500 then $1,000 | 25.0% / $9,243 / 6.2% | 16.1% / $7,436 / 12.9% | 45.3% / $18,812 / 4.7% |
| N2 $1,500 then $750 | 18.8% / $7,461 / 12.5% | 16.1% / $4,073 / 19.4% | 35.9% / $9,255 / 12.5% |
| N3 $1,250 then $750 | 25.0% / $7,538 / 12.5% | 19.4% / $8,352 / 9.7% | 40.6% / $12,263 / 15.6% |

Once the floor stops, the cushion is only the profit above it: faster steps put bigger sizes on that cushion, and a
losing stretch at those sizes takes the account back down to the stopped floor. Nothing changes; no simulator run.
`verification/noise_v2/g501_locked_steps.txt`.

## G502: two accounts toward +$25,000 together, a measurement (registered 2026-11-13, before its run)

The user runs two 50K accounts on the same signals, started together; their combined net is twice one account's, so
the pair reaches +$25,000 when one account reaches +$12,500. `research/g502_two_accounts.py`: G495's table with that
goal (the column "reach_25k" there means one account at +$12,500) for U58, Funded growth plus and Funded aggressive.
A measurement: it states the pair's odds; no setting changes. Run once.

**G502 result (2026-11-13), a measurement: with two accounts, Funded growth plus reaches +$25,000 together within the
first year on 50-63% of starts.**

| two 50K accounts, first 12 months | fresh: pair at $25K / one account's median / lost | development | unseen |
|---|---|---|---|
| U58 (Funded growth, what the user runs) | 37.5% / $7,306 / 0% | 45.2% / $10,150 / 0% | 57.8% / $16,099 / 1.6% |
| **Funded growth plus** | **50.0% / $14,067 / 0%** | **51.6% / $13,880 / 3.2%** | **62.5% / $23,279 / 3.1%** |
| Funded aggressive | 37.5% / $11,023 / 12.5% | 48.4% / $12,187 / 6.5% | 60.9% / $24,745 / 9.4% |

Plus is the best on every set for the pair: about half the recent and development starts, and 5 in 8 unseen, reach
+$25,000 combined within 12 months (U58: 3 in 8 to 6 in 10). A lost start loses both accounts (the same trades).
Recommended to the user: Funded growth plus on both accounts. `verification/noise_v2/g502_two_accounts.txt`.

## G503: bigger trades with the trend (registered 2026-11-13, before its run)

Hourly round toward +$25,000 (G495's measure). U58 already keeps shorts out while the price is above its 45-session
average (`trend_n` 45); a trade on the trend's side never takes more size. `trend_with_mult` (in mnqbot/noise.py, never
run in a recorded test): a trade with the trend takes that many times the contracts, the same stop in points, still cut
to the day's budget and the room above the floor. `research/g503_trend_with_size.py`: Funded growth plus against W1
1.5x, W2 2x. **Rule:** as G496's (on each set the share at +$25,000 in 12 months and the median at least plus's, no more
starts lost; the highest unseen share); then built (not in the C# file) and NinjaTrader's simulator on a fresh
2026-01-02 start at least plus's +$8,698. Run once.

**G503 result (2026-11-13): rejected, both; far more accounts lost.**

| first 12 months | fresh: reach $25K / median / lost | development | unseen |
|---|---|---|---|
| **Funded growth plus** | 18.8% / $14,067 / 0% | 25.8% / $13,880 / 3.2% | **48.4% / $23,279 / 3.1%** |
| W1 1.5x with the trend | 31.2% / $9,305 / 18.8% | 32.3% / $15,996 / 16.1% | 42.2% / $17,603 / 18.8% |
| W2 2x with the trend | 25.0% / $3,523 / 37.5% | 25.8% / $1,189 / 22.6% | 39.1% / $5,235 / 28.1% |

The trend's side is not a safer side for size: the bigger trades lose 1 account in 5 or worse. Nothing changes.
`verification/noise_v2/g503_trend_with_size.txt`.
