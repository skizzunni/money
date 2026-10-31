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
