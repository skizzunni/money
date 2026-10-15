# Does the bot have an edge? A multi-year test

**Verdict: the original sweep/breakout bot has no edge.** On 3¾ years of Nasdaq-100 data, none of its seven pre-declared variants shows an edge that survives costs, and the variant picked on the tuning years lost money on the unseen years. **Don't pay for a prop evaluation to trade those rules.**

**One published strategy does have an edge over 16 years: noise-area momentum** ([third round](#third-round-16-years-2010-2026)). It holds at today's costs as a share of price, but it carries real caveats, and on a $25K / $1,500 evaluation it failed more often than it passed (about 4 in 10 historical starts passed). It's now in TradingView as [`pine/mnq_noise_momentum.pine`](../pine/mnq_noise_momentum.pine), with its rules in [NOISE.md](NOISE.md).

---

## Data

| | |
|---|---|
| Source | HistData.com, free, `NSXUSD` 1-minute bars: a CFD on the Nasdaq-100 cash index, bid prices |
| Period | Jan 2, 2023 → Sep 30, 2026 (1,235,902 one-minute bars → 247,381 five-minute bars) |
| Clock | New York time with daylight saving. Checked: the 09:30 open spike and the 08:30 and 10:00 data spikes sit at the same clock time in winter and summer. |
| Difference from MNQ | Same index, nearly identical intraday moves. Price level differs by the futures basis, and the data has no futures volume (the rules don't use volume). |
| Holes | 282 stretches of missing minutes inside 09:30–16:00, on 157 days, mostly in 2023. See [Holes in the free data](#holes-in-the-free-data). |

## Method (fixed before looking at results)

- **Tuning period:** 2023–2024. **Unseen period:** 2025 → Sep 2026, run once.
- **Seven variants**, listed in [`research/nsx_study.py`](../research/nsx_study.py):
  - A: defaults (both setups)
  - B: sweep only
  - C: breakout with retest entry, 5-minute range
  - D: breakout with retest entry, 15-minute range
  - E: breakout with retest entry, far-side stop
  - F: breakout entering at the next open after the breakout close, 5-minute range
  - G: same as F with a 15-minute range
- **Selection rule:** among variants with ≥ 100 tuning-period trades, take the highest tuning-period expectancy in R. That variant is judged on the unseen period only.
- **Fills and costs:** the repo's standard, deliberately cautious ones: $0.62 per contract per side, 1 tick of slippage on stops and market orders, limits fill only one tick through, stop wins ties. $150 risk per trade and the daily rails as in [RULES.md](RULES.md).

## Results

**Tuning period, 2023–2024**

| Variant | Trades | Win % | PF | Avg R | Net $ | Max DD $ | Evals passed/failed |
|---|---:|---:|---:|---:|---:|---:|---:|
| A both (defaults) | 316 | 26.9% | 0.92 | −0.048 | −1,574 | 3,555 | 2 / 4 |
| B sweep only | 28 | 32.1% | 0.95 | +0.030 | −89 | 875 | 0 / 0 |
| C breakout retest, 5m | 298 | 27.2% | 0.95 | −0.043 | −991 | 3,510 | 2 / 4 |
| D breakout retest, 15m | 291 | 23.7% | 0.80 | −0.101 | −3,615 | 4,485 | 1 / 6 |
| E breakout retest, far stop | 282 | 24.5% | 0.81 | −0.093 | −3,098 | 5,383 | 0 / 4 |
| **F breakout close entry, 5m** | 399 | 28.8% | 0.98 | **+0.001** | −523 | 4,758 | 2 / 5 |
| G breakout close entry, 15m | 314 | 24.2% | 0.79 | −0.108 | −3,812 | 6,545 | 1 / 6 |

B has too few trades to qualify, so the rule picks **F**, with an expectancy of essentially zero.

**Unseen period, 2025 → Sep 2026**

| Variant | Trades | Win % | PF | Avg R | Net $ | Max DD $ | Evals passed/failed |
|---|---:|---:|---:|---:|---:|---:|---:|
| A both (defaults) | 239 | 21.8% | 0.74 | −0.166 | −4,026 | 5,098 | 0 / 5 |
| B sweep only | 10 | 20.0% | 0.55 | −0.217 | −332 | 735 | 0 / 0 |
| C breakout retest, 5m | 238 | 23.1% | 0.78 | −0.130 | −3,364 | 4,252 | 0 / 4 |
| D breakout retest, 15m | 195 | 25.6% | 1.02 | +0.002 | +158 | 1,638 | 0 / 1 |
| E breakout retest, far stop | 119 | 27.7% | 0.91 | −0.053 | −627 | 2,305 | 0 / 2 |
| **F breakout close entry, 5m (picked)** | 238 | 25.2% | 0.94 | **−0.056** | **−788** | 3,855 | 1 / 4 |
| G breakout close entry, 15m | 165 | 27.9% | 1.06 | +0.027 | +525 | 1,809 | 1 / 1 |

- **The picked variant lost on unseen data:** −$788 over 238 trades.
- **Its odds on a $25K / $1,500-drawdown evaluation within 60 sessions** (Monte Carlo on its unseen-period days): pass 4%, fail 9%, still trying after 60 days 87%.
- **D and G are the only positives, and they don't count.** They were among the worst in the tuning period, so this is noise flipping sign, not an edge.

**Best case, all costs removed.** Full period, no fees, no slippage, limits fill on a touch:

| Variant | Avg R, best case | Avg R, best case, holes removed | By year, holes removed (2023 / 2024 / 2025 / 2026) |
|---|---:|---:|---|
| A both (defaults) | −0.043 | −0.026 | −0.14 / +0.15 / −0.07 / −0.13 |
| B sweep only (37–38 trades) | −0.016 | −0.016 | −0.29 / +0.42 / +0.00 / −0.67 |
| C breakout retest, 5m | −0.036 | −0.017 | −0.13 / +0.16 / −0.05 / −0.14 |
| D breakout retest, 15m | −0.035 | −0.013 | −0.21 / +0.08 / +0.02 / +0.05 |
| E breakout retest, far stop | −0.062 | −0.056 | −0.28 / +0.05 / +0.08 / −0.30 |
| F breakout close entry, 5m | +0.021 | +0.045 | −0.08 / +0.16 / +0.06 / −0.08 |
| G breakout close entry, 15m | −0.029 | −0.013 | −0.32 / +0.14 / +0.04 / +0.03 |

- **Even with free trading, the best variant barely makes anything.** F makes +0.045R a trade, under $7 even at the full $150 of risk. Fees and slippage eat that: with realistic costs and the holes removed, F makes +0.003R a trade.
- **The results swing with the year.** Every variant made money in 2024 and lost in 2023, and 2025–2026 are mixed. That is market regime, not skill in the rules.

## Holes in the free data

The free HistData files are missing minutes: 282 stretches inside 09:30–16:00, on 157 days (2023: 235, 2024: 9, 2025: 10, 2026: 28). Some are long. On 2023-03-07 the data jumps from 09:59 to 11:00, and price is 115 points lower when it comes back.

If price crosses a stop inside a hole, the backtest can't see it. It fills the stop at the first price after the hole, which can be far past the stop. A real stop order would have filled near the stop. In the tables above, every trade that lost more than 1.01R (up to −5.8R) and every day worse than the $300 daily limit (down to −$789) came from a hole.

The tables above are as run, holes included. Here they are again with the trades that were open across a hole removed:

| Variant | Hole trades, tuning / unseen | Avg R tuning: as run → holes removed | Avg R unseen: as run → holes removed |
|---|---:|---:|---:|
| A both (defaults) | 11 / 1 | −0.048 → −0.033 | −0.166 → −0.156 |
| B sweep only | 1 / 0 | +0.030 → +0.032 | −0.217 → −0.217 |
| C breakout retest, 5m | 11 / 1 | −0.043 → −0.017 | −0.130 → −0.119 |
| D breakout retest, 15m | 18 / 2 | −0.101 → −0.069 | +0.002 → +0.007 |
| E breakout retest, far stop | 26 / 1 | −0.093 → −0.090 | −0.053 → −0.045 |
| **F breakout close entry, 5m** | 26 / 0 | +0.001 → **+0.040** | **−0.056 → −0.056** |
| G breakout close entry, 15m | 21 / 0 | −0.108 → −0.083 | +0.027 → +0.027 |

- **The answer doesn't change.** F is still the tuning-period pick. None of its unseen-period trades crossed a hole, so its −0.056R, −$788 and evaluation odds stand exactly.
- **With the holes removed, the risk rails held.** No trade in any variant lost more than 1.01R, and no day lost more than $263.
- **This is an approximation.** Removing trades after the fact isn't the same as a re-run: later trades on the same day could have sized or fired differently.

## Second round: published strategies

Three intraday strategies with published evidence on US index ETFs, each run with its authors' settings and no tuning, on the same data. The rules and the pass bar were fixed before running and are written out in [`research/published_lab.py`](../research/published_lab.py).

- **S1, 5-minute opening range** (Zarattini & Aziz, 2023). Trade in the direction of the 09:30–09:35 candle at the 09:35 open. The stop goes at that candle's far end, the target at 10R, and otherwise the trade exits at the close.
- **S2, noise-area momentum** (Zarattini, Aziz & Barbon, 2024). Every half hour, go long above or short below the day's usual range, exit when price comes back inside it, and be out by the close. S2b adds the paper's VWAP trailing stop, using a time-weighted average because the data has no volume.
- **S3, last-half-hour momentum** (Gao, Han, Li & Zhou, 2018). At 15:30, trade in the direction of the move from the previous close to 10:00, and exit at the close.
- **Pass bar.** After costs, a t-stat of at least 2.5 on daily P&L, positive in both 2023–2024 and 2025–2026, and positive in at least 3 of the 4 years.
- **Fills and costs.** Same as above, on 1-minute bars.

| Strategy | Trades | Win % | Avg per trade | Net | t | 2023–24 | 2025–26 | Years up | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| S1, every signal, in R | 769 | 24.3% | +0.053R | +40.6R | 0.64 | −5.6R | +46.2R | 2 of 4 | fail |
| S1, $150 risk | 618 | 22.3% | +$10.65 | +$6,579 | 0.89 | −$1,072 | +$7,651 | 3 of 4 | fail |
| S2a, 1 contract | 591 | 39.6% | +$5.45 | +$3,221 | 0.57 | +$3,895 | −$674 | 3 of 4 | fail |
| S2b, 1 contract | 628 | 39.0% | +$4.16 | +$2,615 | 0.46 | +$4,024 | −$1,408 | 3 of 4 | fail |
| S3, 1 contract | 798 | 49.7% | +$0.90 | +$721 | 0.24 | −$37 | +$758 | 2 of 4 | fail |

- **None passes.** All are slightly positive overall, but not by more than luck produces. The best t-stat is 0.89, against a bar of 2.5.
- **S1 comes closest, and its edge is too thin for an evaluation.** At +0.053R per trade it still had a losing stretch 38R deep. Keeping that inside a $1,500 drawdown means risking under $40 a trade. That earns about $2 a trade, so reaching a $1,500 target would take roughly three years.
- **3¾ years can't settle edges this small.** Day-to-day results swing so much that telling a +0.05R edge from luck takes far more history than this. The papers used much longer periods.
- **What the S1 rows cover.** The $150-risk row skips the roughly 150 days whose first candle is too wide to trade with $150 of risk. The R row takes every signal, as the paper does.
- **Days left out.** Only full sessions count. Holidays, half days, and the weeks when the US and European clock changes differ are dropped (this data's session ends at 15:15 New York time in those weeks). Days with a trade open across missing minutes are left out too.

## Third round: 16 years, 2010-2026

You downloaded `NSXUSD` back to November 2010, about 16 years in all. The 2010–2022 data was new to every strategy. The clock was checked the same way as before: the 09:30 open spike sits at 09:30 in both winter and summer, every year.

**Pass bar, set before running.** It extends the second round's bar to three eras:

- After costs, a t-stat of at least 2.5 over the whole period.
- Positive in each era: 2010–2016, 2017–2022 and 2023–2026.
- Positive in at least 75% of the years with 100+ sessions.

**Units.** The index went from about 2,100 to 30,000, so S1 is scored in R, and S2 and S3 in % of price per trade (summed, at a constant contract value). That way the early years count as much as the recent ones.

**As declared, with today's MNQ costs in index points at every price level:**

| Strategy | Trades | Avg per trade | t | 2010–16 | 2017–22 | 2023–26 | Years up | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| S1 opening range, every signal | 3,576 | −0.03R | −0.87 | −276.3R | +123.2R | +40.7R | 8 of 16 | fail |
| S1 opening range, $150 risk | 3,372 | −$3.23 | −0.67 | −$31,371 | +$13,913 | +$6,579 | 9 of 16 | fail |
| S2a noise area | 2,915 | +0.020% | 1.91 | −22.0% | +65.8% | +13.1% | 7 of 16 | fail |
| S2b noise area + TWAP stop | 3,047 | +0.020% | 2.04 | −21.1% | +68.7% | +12.0% | 8 of 16 | fail |
| S3 last half hour | 3,687 | −0.021% | −4.39 | −39.8% | −37.2% | +0.3% | 3 of 16 | fail |

**The cost question.** Charging today's costs in points at 2011 prices charges about ten times today's cost as a share of price, because 1 tick was a much bigger slice of a 2,300 index. To decide whether to trade these rules *now*, the right charge is today's costs as a share of price. Here is the same set of trades under three cost models:

| Strategy | Costs | Avg per trade | t | 2010–16 | 2017–22 | 2023–26 | Years up | Result |
|---|---|---:|---:|---:|---:|---:|---:|---|
| S1 opening range | today's, as share of price | +0.069R | 1.72 | −4.8R | +205.4R | +47.0R | 10 of 16 | fail |
| S1 opening range | none | +0.096R | 2.32 | +38.8R | +240.6R | +64.2R | 10 of 16 | fail |
| **S2a noise area** | **today's, as share of price** | **+0.036%** | **3.50** | **+12.8%** | **+76.7%** | **+14.3%** | **14 of 16** | **pass** |
| S2a noise area | none | +0.039% | 3.86 | +17.0% | +81.0% | +16.5% | 15 of 16 | pass |
| S2b noise area + TWAP stop | today's, as share of price | +0.036% | 3.72 | +15.4% | +79.9% | +13.2% | 14 of 16 | pass |
| S2b noise area + TWAP stop | none | +0.039% | 4.11 | +19.7% | +84.4% | +15.6% | 15 of 16 | pass |
| S3 last half hour | today's, as share of price | −0.004% | −0.91 | +6.0% | −23.8% | +1.9% | 8 of 16 | fail |
| S3 last half hour | none | −0.001% | −0.14 | +11.4% | −18.6% | +4.9% | 10 of 16 | fail |

- **Noise-area momentum passes once costs are scaled to today, and nothing else does.** Before costs it made money in 15 of 16 years.
- **Weigh that carefully.** The share-of-price cost model was chosen after seeing the declared result, so it counts for less than a pre-set test. In its favor: this is a published strategy run with its authors' settings, nothing was tuned, and the change is to costs, not to the rules.
- **The edge is uneven.** More than half of it came from 2018 and 2022, two volatile years.

**On a $25K evaluation.** This is S2a, the version in the TradingView script ([`research/noise_eval.py`](../research/noise_eval.py)), on 1 MNQ at the last price in the data (30,661) with today's costs. The evaluation rules are Take Profit Trader-style: $1,500 target, $1,500 end-of-day trailing drawdown, a breach intraday fails, best day under 50% of profit, and at least 5 trading days. Each evaluation starts on a historical day and runs forward through real history, once for every possible start day.

| | As published (the script) | With the bot's $300 daily loss limit |
|---|---:|---:|
| Average per session | +$17.73 | +$14.87 |
| Daily swing (standard deviation) | $304 | $265 |
| t-stat | 3.50 | 3.37 |
| Worst intraday dip | −$2,465 | −$307 |
| Worst losing stretch | −$8,168 | −$10,474 |
| 2023–2026 total | +$8,755 | −$14 |
| Pass / fail within 60 sessions | 30% / 49% | 30% / 43% |
| Pass / fail within 125 sessions | 38% / 57% | 41% / 53% |
| Pass / fail within 250 sessions | 43% / 57% | 46% / 53% |
| Pass / fail within 125 sessions, 2023–2026 starts | 39% / 59% | 34% / 66% |

- **An evaluation is more likely to fail than pass, even with a real edge.** The edge is about $18 a session, against swings of about $300 a day and a $1,500 trailing drawdown. That's thin for passing.
- **The $300 daily limit isn't used.** It helps a little over 16 years but erases 2023–2026, the period closest to now.
- **2026 is a losing year so far:** −$3,155 through September on 1 MNQ.
- **The bot matches the research.** Its 5-minute reference (`mnqbot/noise.py`) makes the same trades as the 1-minute research version on 1,979 of 1,999 clean sessions. The other 20 are holidays and other irregular sessions.

## Fourth round: can it trade more often?

Nine versions of noise-area momentum, fixed before running ([`research/noise_tuning.py`](../research/noise_tuning.py)):

- **Variants:** check every 30, 15 or 5 minutes (first check at 10:00), with the noise band at 0.8×, 1.0× or 1.2×.
- **Selection:** pick the best on 2010–2019, then judge it on 2020 to September 2026, which the choice never saw. Switch only if the pick also beats the current version on 2020–2026.
- **Terms:** 1 MNQ at today's price and costs, over 3,331 complete sessions with no missing minutes.

| Version | Trades a day | Win % | 2010–19 $/day (t) | 2020–26 $/day (t) | Worst intraday dip | Worst losing stretch | Evaluation pass / fail, 2020–26 starts |
|---|---:|---:|---:|---:|---:|---:|---:|
| 30 min × 0.8 | 0.99 | 37% | +14.26 (2.04) | +24.96 (2.41) | −$2,465 | $9,876 | 42% / 56% |
| **30 min × 1.0 (current)** | **0.84** | **39%** | **+18.51 (2.83)** | **+24.11 (2.65)** | **−$2,465** | **$9,211** | **41% / 56%** |
| 30 min × 1.2 | 0.72 | 40% | +15.69 (2.59) | +21.76 (2.51) | −$2,465 | $5,913 | 35% / 61% |
| 15 min × 0.8 | 1.28 | 32% | +18.14 (2.55) | +26.72 (2.52) | −$3,703 | $10,563 | 42% / 57% |
| 15 min × 1.0 | 1.11 | 33% | +18.09 (2.73) | +17.43 (1.86) | −$2,297 | $9,108 | 39% / 61% |
| 15 min × 1.2 | 0.97 | 33% | +15.12 (2.48) | +20.67 (2.34) | −$2,577 | $5,063 | 34% / 63% |
| 5 min × 0.8 | 2.04 | 25% | +15.42 (2.14) | +21.26 (1.96) | −$3,609 | $7,579 | 40% / 60% |
| 5 min × 1.0 | 1.77 | 26% | +14.07 (2.13) | +16.63 (1.67) | −$3,526 | $6,958 | 36% / 64% |
| 5 min × 1.2 | 1.57 | 28% | +12.74 (2.11) | +17.43 (1.93) | −$3,290 | $5,772 | 38% / 59% |

- **The current version was the best on 2010–2019, so it stays.**
- **Checking more often adds trades, not edge.** At 5 minutes it trades about twice as often, but only about a quarter of trades win, the t-stat drops, and the worst dip deepens to about −$3,600.
- **Two versions earned a little more per day in 2020–2026,** 15 min × 0.8 and 30 min × 0.8. Neither was best on 2010–2019, so switching to one because of 2020–2026 would be fitting to the test. Their evaluation odds are no better either.

## Fifth round: can it trade on most days?

The same set-up as the fourth round, with narrower noise bands (0.5×, 0.25×, 0.0×) so that most days trade ([`research/noise_daily.py`](../research/noise_daily.py)).

The bar was set before running:

- a trade on at least 80% of days
- t ≥ 2 in both 2010–2019 and 2020–2026
- evaluation odds from 2020–2026 starts no worse than the current version's

| Band | Days with a trade | Trades a day | Win % | 2010–19 $/day (t) | 2020–26 $/day (t) | Evaluation pass / fail, 2020–26 starts | Bar |
|---|---:|---:|---:|---:|---:|---:|---|
| **1.0× (current)** | **60%** | **0.84** | **39%** | **+18.51 (2.83)** | **+24.11 (2.65)** | **41% / 56%** | — |
| 0.5× | 83% | 1.27 | 35% | +18.48 (2.34) | +26.59 (2.21) | 46% / 54% | met |
| 0.25× | 92% | 1.52 | 35% | +10.33 (1.18) | +23.27 (1.73) | 32% / 68% | missed |
| 0.0× | 97% | 1.75 | 35% | +11.91 (1.27) | +22.23 (1.50) | 28% / 72% | missed |

0.5× met that bar, but the bar didn't cover everything. Over the full 16 years:

| Band | $/day | Losing years | Worst losing stretch | 2025–2026 total | Evaluation pass / fail, all starts |
|---|---:|---:|---:|---:|---:|
| **1.0× (current)** | **+20.89** | **1 of 16** | **$9,211** | **−$89** | **41% / 55%** |
| 0.5× | +21.93 | 4 of 16 | $20,316 | −$14,902 | 43% / 57% |
| 0.25× | +15.83 | 5 of 16 | $16,377 | −$13,140 | 34% / 66% |
| 0.0× | +16.30 | 5 of 16 | $14,018 | −$10,519 | 30% / 70% |

- **The current version stays.** Trading on 83% of days instead of 60% adds about $1 a day. In exchange, the worst losing stretch doubles, losing years go from 1 to 4, and it lost about $15,000 over 2025–2026. The evaluation odds are a wash.
- **Narrower still is clearly worse:** weaker in both periods and lower evaluation odds.
- **The full-period table was added after seeing the first one.** It was used only to reject a change, never to adopt one.

## What this does and doesn't say

- **It says** that the original sweep/breakout rules have no edge after realistic costs on 2023–2026 Nasdaq-100 data, and would very likely not pass a $25K evaluation. Of three published strategies, only noise-area momentum held up over 16 years, and even it fails most $25K evaluations.
- **It doesn't say** that sweeps or breakouts can never work. Only the rules above were tested, on 3¾ years.
- **Testing more variants on the same data would be data-mining.** Anything found that way would need fresh unseen data to be believed.
- **Risk control can't create an edge that isn't there.** Once the data holes are removed, the rails kept every loss within 1.01R and every day under the $300 limit, and the rules still lost money.

## Reproduce

Download the `NSXUSD` ASCII 1-minute files from HistData.com, then run:

```bash
python research/nsx_study.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"   # the study
python research/nsx_holes.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"   # the data-hole check and best case
python research/published_lab.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"   # the published strategies + cost check
python research/noise_eval.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"      # noise momentum on a $25K evaluation
python research/noise_tuning.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"    # can it trade more often? (no)
python research/noise_daily.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"     # can it trade on most days? (not safely)
```

The raw data isn't stored in this repo.
