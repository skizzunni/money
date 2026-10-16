# Does the bot have an edge? A multi-year test

**Verdict: the original sweep/breakout bot has no edge.** On 3¾ years of Nasdaq-100 data, none of its seven pre-declared variants shows an edge that survives costs, and the variant picked on the tuning years lost money on the unseen years. **Don't pay for a prop evaluation to trade those rules.**

**One published strategy does have an edge over 16 years: noise-area momentum** ([third round](#third-round-16-years-2010-2026)). It holds at today's costs as a share of price, but it carries real caveats, and as first traded it failed more $25K evaluations than it passed. The [ninth round](#ninth-round-the-account-and-the-exit) changed that: with a resting-stop exit it passes about 6 in 10 historical $25K evaluations on 1 MNQ. The [tenth round](#tenth-round-why-the-trades-lose) then studied why its trades lose and moved the stop 0.24 noise units past the line, which raised profit per day by 43% on years the analysis never saw. It's now in TradingView as [`pine/mnq_noise_momentum.pine`](../pine/mnq_noise_momentum.pine), with its rules in [NOISE.md](NOISE.md).

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

## Sixth round: searching the data for new patterns

Instead of testing known strategies, this round searched the 16 years for patterns of its own, with guards against finding luck.

**Measurements.** 30 measurements, all taken at each half hour from 10:00 to 15:30 ([`research/discovery.py`](../research/discovery.py)):

- the move from the open, the last 30 and 5 minutes, and the first 30 minutes
- position in the day's range, distance from the average price, and the share of up-minutes
- volatility and range versus normal, and the move in noise units
- the overnight range and where the open sits in it, and the gap
- yesterday's move, range and close position, and price versus yesterday's high and low
- the last week's and month's move, 20-day volatility, and whether the gap has filled
- day of week, month turn, and options expiry

Each one was tested against the next 30 minutes, the next 60 minutes, and the move to the close. A test for a time-of-day drift was included too.

**Periods:**

- **Discovery:** 2011–2018, 1,922 sessions.
- **Confirmation:** 2019–2022, 929 sessions.
- **Final test:** 2023 to September 2026, 748 sessions, run once.

**The luck filter.** Testing thousands of things finds "patterns" by chance alone, so discoveries had to pass a 5% false discovery rate before going to confirmation.

| Search | Tests | Passed the luck filter, 2011–18 | Repeated, 2019–22 | Final test, 2023–26 |
|---|---:|---|---|---|
| Each measurement on its own | 1,085 | 2 (both "last month's move → the last half hour") | 0 (t fell from 4.7 to 1.3) | not reached |
| Extremes only: top vs bottom 10% ([`discovery2.py`](../research/discovery2.py)) | 735 | 0 | 0 | not reached |
| All 30 combined in a model, four trading rules (up to 12 trades a day) | 4 | t 3.7–10.4 on the years it learned from | best t 1.62, needed 2 | not reached |
| Afternoon trend: at 13:30, trade toward the side of the average price, hold to the close ([`afternoon.py`](../research/afternoon.py)) | 3 | t 3.46 on 2011–2022 | — | **−$8.08 a day, t −0.71: failed** |

- **Nothing new held up.** No measurement, alone or in combination, predicted the next 30 minutes, the next hour, or the close on years it hadn't seen.
- **The combined model shows how backtests fool people.** t = 9–10 on the years it learned from fell to 0.5–1.6 on new years.
- **The afternoon trend looked solid for twelve years** (+$22.53 a day), then lost money in 2023–2026, including −$7,411 in 2026.
- **The one edge that survives all of this** is noise-area momentum, the strategy already in TradingView. It trades only on the bigger, rarer moves that these all-days tests can't see.

## Seventh round: the overnight session, regimes, and a nonlinear walk-forward model

Three things the sixth round didn't try ([`research/discovery3.py`](../research/discovery3.py)), with the same luck filter and periods:

| Search | Tests | Passed the luck filter, 2011–18 | Repeated, 2019–22 |
|---|---:|---|---|
| 13 new overnight and cross-day measurements (Asia and Europe moves, 08:30–09:30 move, overnight volatility and trend consistency, overnight extremes vs yesterday's, yesterday's afternoon) | 385 | 0 | 0 |
| Regime-conditional: 13 measurements × 6 regimes (volatility, last month, overnight range) | 1,872 | 33 | **20** |

**The 20 survivors are one family:** after a wide overnight range, or when the last month is down, price on the far side of its daily average at 11:30–13:30 keeps going into the close. That's the afternoon-trend idea that failed the sixth round, plus a regime filter.

**Walk-forward gradient boosting.** A nonlinear model on all 43 measurements, pooled across half hours. For each year from 2015 to 2026 it is trained on 2011 up to the year before and predicts that year, so every prediction is out of sample. The primary rule (fixed in advance) trades only when the predicted move is more than twice the round-trip cost.

| Target | Rule | Trades a day | $/day, 2015–26 | t | Years up |
|---|---|---:|---:|---:|---:|
| Next 30 min | always in | 12.0 | +1.15 | 0.11 | 6 of 12 |
| Next 30 min | > 1× cost | 4.8 | +9.16 | 1.08 | 8 of 12 |
| Next 30 min | **> 2× cost (primary)** | 2.3 | +8.51 | **1.22** | 9 of 12 |
| To the close | always in | 12.0 | −16.38 | −1.45 | 4 of 12 |
| To the close | > 1× cost | 11.6 | −16.34 | −1.46 | 5 of 12 |
| To the close | > 2× cost (primary) | 11.2 | −17.80 | −1.61 | 4 of 12 |

Nothing near the bar of t ≥ 2.5. Flexible models find nothing a simple rule can't.

**Final test of the regime family** ([`research/regime_trend.py`](../research/regime_trend.py)). Six candidates were fixed before running: enter at 13:30 or 11:30 on the side of the daily average, hold to the close, only in the regime (overnight range wide, last month down, or either). On 2011–2022, the years that found the idea:

| Candidate | Days traded | $/day | t |
|---|---:|---:|---:|
| 13:30, overnight range wide | 59% | +21.18 | 3.51 |
| **13:30, last month down (picked)** | 47% | +22.66 | **4.17** |
| 13:30, either | 72% | +24.89 | 3.98 |
| 13:30, no filter (reference) | 100% | +22.53 | 3.46 |
| 11:30, any regime | 47–72% | +13.64 to +17.23 | 1.96–2.15 |

**Run once on 2023 to September 2026:** 748 sessions, traded 44% of days, **−$5.10 a day, t −0.58**, 47% of trades won, by year 2023 +$954, 2024 −$2,170, 2025 +$3,509, 2026 −$6,111. **Failed.** On a $25K evaluation starting from every 2023–2026 day: 13% pass, 78% fail.

- **The regime filter didn't fix the afternoon trend.** Over 2011–2022 it looks strong (t 4.17) because 2011–2022 is where it was found. On the untouched years it loses.
- **Across all 16 years it still shows t 3.6 and 14 winning years.** That's the trap: a backtest over the years that found the rule proves nothing. Only the final test counts.
- **Noise-area momentum remains the only survivor** of seven rounds.

## Eighth round: what's actually wrong

Passing a $25K / $1,500 evaluation with a strategy that averages *m* dollars a day against a swing of *s* dollars a day is close to a gambler's-ruin problem: the odds rise with *m ÷ s²*, not with the number of trades. Noise-area momentum on 1 MNQ has *m* ≈ $18 and *s* ≈ $300, so the whole $1,500 cushion is five ordinary days. More price-only edge has been searched for (rounds six and seven) and not found. What's left is the ratio. Two fixes with evidence behind them, fixed before running ([`research/round8.py`](../research/round8.py)):

| Fix | Result |
|---|---|
| **Size by volatility**, as the paper does (0–2 contracts by the last 20 sessions' volatility) | Worse: +$17.73 → +$10.93 a day, evaluation pass 38% → 35%. The edge lives on the wild days, so cutting them cuts the profit. |
| **An overnight return stream.** The 24-hour clock in 44 half-hour bins, 2011–2018 | Two bins passed the luck filter. The 02:00 bin (the European open, where the academic "overnight drift" sits) had t = 5.0 on 2011–2018 and **−0.18 on 2019–2022**. Dead. Nothing to test further. |

## Ninth round: the account, and the exit

Two more levers on the same ratio ([`research/round9.py`](../research/round9.py)):

**A. A continuous exit.** Once in a trade, a stop order rests at the current noise line and moves with it at every half hour, instead of a check at the half hour. No new parameters. The 30-minute check is where the −$2,465 days came from.

| | 2011–2022, half-hour check | 2011–2022, resting stop | 2023–2026, half-hour check | 2023–2026, resting stop |
|---|---:|---:|---:|---:|
| $/day | +23.21 | +22.35 | +12.53 | +14.13 |
| t | 3.80 | 4.20 | 1.08 | 1.28 |
| Worst intraday dip | −$2,465 | **−$1,412** | −$1,252 | **−$976** |
| Worst losing stretch | $5,156 | $4,744 | $9,211 | $6,208 |
| Trades a day | 0.60 | 1.21 | 0.60 | 1.21 |
| $25K evaluation pass / fail, 125 sessions | 42% / 54% | **53% / 37%** | 40% / 57% | 40% / 56% |

The rule set in advance was: a candidate if the pass rate rises 3 points on 2011–2022 (it rose 11), confirmed if it rises 3 points on 2023–2026 too. It didn't rise there, so by that bar it's not confirmed. It was equal or better on every other measure in both periods and worse on none, and it attacks the thing that fails evaluations, so it is now the script's default, with the half-hour check kept as a setting.

**B. The account tier.** The same 1-contract sessions through the evaluation rules of larger accounts, from every start day in 2011–2026, 500 sessions:

| Account (target / drawdown) | Half-hour check: pass / fail | Resting stop: pass / fail / still running | Median days to pass (stop) |
|---|---:|---:|---:|
| $25K (1,500 / 1,500) | 47% / 53% | 61% / 39% / 0% | 45 |
| $50K (3,000 / 2,000) | 52% / 48% | 64% / 36% / 0% | 85 |
| **$100K (6,000 / 3,000)** | 72% / 22% | **84% / 7% / 9%** | 203 |
| $150K (9,000 / 4,500) | 68% / 3% | 68% / 3% / 29% | 298 |

With 2 or 3 contracts the odds fall back toward the $25K numbers: more contracts shrink the cushion in exactly the same way a smaller account does.

- **The $25K account is the wrong instrument for a 1-contract edge.** The same strategy and size pass 84% of the time on a $100K evaluation, because the $3,000 drawdown is ten ordinary days instead of five.
- **The price is time.** About a year of trading days to reach the $100K target, and an evaluation fee for each month of it.
- **Tiers as I understand Take Profit Trader's** (their site is unreachable from here): verify the targets, drawdowns, fees and the rule on holding through the night before paying.

## Tenth round: why the trades lose

A trade-level post-mortem of the strategy (resting stop on the line) on 1-minute data ([`research/postmortem.py`](../research/postmortem.py)). Study period 2011–2018, 2,084 trades:

- **77% of trades lose**, average loss $69 against an average win of $308. 98% of losses are stop-outs.
- **77% of the losers are premature:** stopped on the line, after which price went on at least one full risk in our direction. $69,000 of the $110,000 lost.
- **Losers die in 10 minutes (median); winners last 209.** The stop on the line catches the first wobble after entry.
- **Half of all trades are re-entries** after a stop-out (21% win rate, net positive).
- Winners rarely go far against us first (80th percentile of their adverse excursion: 0.62 of the initial risk). Losers often go our way first (42% reached one full risk).
- 10:00 entries made 44% of all profit; entries after 14:00 lost.
- Premature stop-outs overshot the line by 0.09 σ (median) and 0.24 σ (75th percentile) before resuming.

**Overlays**, each with one number taken from 2011–2018, confirmed on 2019–2022 (at least +10% per day and no lower t), then the confirmed set run once on 2023–2026:

| Overlay | 2011–18 $/day (t) | 2019–22 $/day (t) | Confirmed | 2023–26 $/day (t), win % |
|---|---:|---:|---|---:|
| Base: stop on the line | +21.62 (3.38) | +23.70 (2.49) | — | +14.13 (1.28), 25% |
| O1 tighter stop at 0.62 × risk | +23.03 (3.75) | +24.27 (2.67) | no (+2%) | +15.98 (1.44), 21% |
| O2 breakeven after 1 risk | +19.93 (3.20) | +28.44 (3.12) | yes | **+9.06 (1.04)**, 19%: failed its final test in the first run |
| O3 no entries from 14:00 | +22.73 (3.74) | +18.30 (2.11) | no | +13.22 (1.24), 26% |
| O6 continuation entry (stop order at the signal close) | +21.65 (3.40) | +24.02 (2.51) | no | +14.46 (1.30), 26% |
| **O7 stop 0.24 σ past the line** | **+24.44 (3.57)** | **+34.10 (3.26)** | **yes** | **+20.14 (1.75), 34%** |
| O6 + O7 | +24.49 (3.59) | +33.91 (3.24) | yes | +20.82 (1.81), 35% |
| O8 trend filter (trailing 20-day trendiness ≥ 1) | +16.92 (2.99) | +14.48 (1.78) | no | +12.00 (1.21), 26% |
| O7 + O8 | +20.27 (3.33) | +25.66 (2.85) | no | +15.06 (1.46), 34% |

O4 (no re-entry) and O5 (minimum push) were switched off by their own rule: re-entries and weak pushes make money in 2011–2018.

**What happened with the final test, exactly.** In the first run O2 was the only confirmed overlay, and it failed its final test (+$9.06 against +$14.13). O6 and O7 were added after that. In the second run my script combined everything confirmed, O2 + O7, and the combination failed (+$13.02), because O2 drags it down. **O7 on its own clears the final-test bar in every period**, including 2023–2026: +43% per day, t 1.28 → 1.75, win rate 25% → 34%, 30% fewer trades, drawdown $6,208 → $5,785. It is adopted on that basis, and this paragraph is the caveat.

**Robustness of the number.** 0.12, 0.24 and 0.36 all beat the base on both the study and confirmation periods (2019–2022: +$27.70, +$34.10, +$35.01 per day against +$23.70), so 0.24 is not a lucky value.

**The strategy with the buffered stop, all 16 years, 1 MNQ:** **+$26.02 a day, t 5.04, 15 of 16 years positive, worst intraday dip −$1,552, worst losing stretch $5,666.** 2026 through September: −$1,527. Evaluation odds from every start day, 500 sessions: $25K 62% / 38%, $50K 74% / 26%, $100K 78% / 22%, $150K 74% / 3% (23% still running, median 253 days).

**Why it is losing now.** Trendiness = |open-to-close move| ÷ the day's noise. Good years: 1.12–1.25 (2018: 1.25, +$80 a day on the on-line stop). 2019: 1.05, −$3. 2025: 1.01, +$10. 2026: 0.99, −$12. Days have stopped moving more than their own noise, so breakouts don't follow through. The trailing trend filter (O8) didn't help: by the time 20 days of low trendiness switch it off, the bad patch is mostly over.

## Eleventh round: the worst days, and a cap per trade

Where the worst intraday dips and the worst losing stretch come from, and what caps them ([`research/dips.py`](../research/dips.py)). The strategy with the buffered stop, 1 MNQ, 2011–2018.

**The ten worst intraday dips** are the famous crash days: the August 2011 US-downgrade week (the 5th and 10th), December 2018 (the 19th and 27th), the February 2018 "Volmageddon" (the 6th and 9th), September 2015. Each had 3–4 trades and a risk at entry of $470–$910 against a median of $120, because the noise lines were far from the price on those days. Gaps through the stop played almost no part (one day in ten).

**The worst losing stretch** ran from 29 August 2011 to 3 April 2012: 118 sessions, $5,041, with 56 losing days against 22 winning and no single day worse than −$842. It is the chop after a crash, not one bad day.

**Protections**, each with one number from 2011–2018, confirmed on 2019–2022 only if both the worst dip and the max drawdown fell by at least 15% while keeping at least 90% of the profit per day:

| Protection | 2011–18 $/day, dip, DD | 2019–22 $/day, dip, DD | 2023–26 $/day, dip, DD |
|---|---|---|---|
| Base | +24.34, −1,381, 5,041 | +33.73, −1,552, 3,667 | +20.15, −861, 5,666 |
| P1 at most 2 trades a day | +25.99, −1,118, 4,088 | +31.91, −1,376, 3,538 | +6.53, −861, 8,303 |
| P2 stop for the day after a $361 loss | +25.04, −875, 4,584 | +32.71, −1,376, 3,297 | +9.06, −829, 7,631 |
| P3 skip entries riskier than $285 | +23.26, −834, 3,085 | +13.35, −827, 2,401 | +10.30, −643, 3,926 |
| P4 cap the loss per trade at $285 | +25.24, −1,125, 5,061 | +35.77, −1,376, 3,208 | +20.68, −931, 5,590 |

- **Nothing met the bar.** The riskiest entries are the big winners in volatile years (the riskiest 10%: 41% win rate, +$5,006 net), so skipping them (P3) halves the profit. Limiting trades or stopping for the day (P1, P2) blocks the re-entries that made 2023–2026's money.
- **The worst days can't be removed without removing the edge.** They are the days the market moved 3–5%; a trend strategy that is in the market on those days gets hit on the way in.

**A cap per trade, swept** (added after the above, chosen looking at all periods; the cap starts the minute after the fill, as the script must do it):

| Cap per contract | 2011–18 $/day (t), DD | 2019–22 $/day (t), DD | 2023–26 $/day (t), DD |
|---|---|---|---|
| none | +24.34 (3.55), 5,041 | +33.73 (3.22), 3,667 | +20.15 (1.75), 5,666 |
| $35 | +17.50 (3.25), 4,942 | +21.20 (2.65), 2,533 | +12.95 (1.19), 4,541 |
| **$100** | **+27.00 (4.24), 3,984** | +30.63 (3.26), 3,555 | **+24.96 (2.24), 2,564** |
| $200 | +25.83 (3.87), 4,961 | +30.93 (3.02), 3,685 | +24.02 (2.12), 4,498 |
| $350 | +24.23 (3.54), 5,057 | +33.77 (3.21), 3,296 | +20.10 (1.80), 6,051 |

- **$100–$200 per contract improves nearly everything**, with 2019–2022 giving back about 9% of its profit; **$35 wrecks it; $350 changes nothing.** The script now has *Max loss per trade* = $350 for the whole position and 3 contracts as the default, $117 per contract. With 10 contracts the same $350 would be $35 each.
- This was chosen with all periods in view, so it is a weaker result than the pre-registered rounds. Two of the three levels tested beat the base everywhere, so it is not a knife-edge.

## Twelfth round: does the chart's bar length matter?

A 30-minute chart in TradingView showed better 2026 results than the bot had shown before, so the same rules were run on 5, 15 and 30-minute bars. Each month's prices were rescaled to today's level, so the $350 max loss is the same distance in points as it is now. 3 MNQ, all costs included, 2011 to September 2026.

Without the max loss, the bar length makes no difference: the script only acts at the half hours, and the line stop doesn't move between them. With it, the bar length matters. The max-loss stop needs the entry fill, so it starts on the bar after the fill. On a 30-minute chart, every trade goes its first half hour with no $350 cap.

| 3 MNQ, $350 max loss | 5 min | 15 min | 30 min |
|---|---|---|---|
| Net, 2011–2026 | $287,609 | $291,564 | $280,178 |
| Net, 2023–2026 | $66,332 | $64,114 | $58,029 |
| Net, 2026 to September | $4,974 | $7,247 | $5,164 |
| Worst losing stretch | $11,808 | $15,688 | $16,170 |
| Trades that lost more than $400 | 146 | 335 | 473 |

**The 5-minute chart is the one that keeps the $350 promise.** It made about the same money as the others over 16 years, with the smallest losing stretch and a third as many trades past $400 as on 30 minutes. In 2026 the three are close, and 15 minutes happened to be best. That is one year, and no bar length is better across the periods. The trades that still lose more than $400 on 5 minutes are fast markets: price jumps past the stop between one minute and the next, as in March 2020.

The script now says so: the dashboard's *Chart* row turns orange on a chart longer than 5 minutes while the max loss is on.

## Thirteenth round: the $50K evaluation, 1 to 10 contracts

Take Profit Trader's $50K Test as reviews describe it: a $3,000 target, a $2,000 end-of-day trailing drawdown (only the closing balance counts), the best day under half the profit, at least 5 trading days, up to 60 MNQ. Check the firm's own page before buying. The bot on a 5-minute chart with the $350 max loss per trade, prices at today's level, every start day from 2011. Each attempt gets 125 sessions, about six months.

| Contracts ($350 max loss per trade) | Pass, 2011–2022 | Fail, 2011–2022 | Pass, 2023–2026 | Fail, 2023–2026 | Median sessions to pass |
|---|---|---|---|---|---|
| 1 | 42% | 25% | 46% | 23% | 63–85 |
| 2 | 48% | 47% | 60% | 35% | 40–57 |
| 3 | 38% | 60% | 39% | 53% | 27–34 |
| 5 | 32% | 67% | 32% | 65% | 22–31 |
| 10 | 20% | 79% | 17% | 82% | 21–45 |

The rest of the attempts were still open after 125 sessions. **2 contracts gave the best odds**: about half the attempts passed, in two to three months. 10 contracts passed fastest when it passed, but failed about 4 attempts in 5. Two things work against it. A losing stretch of 5 or 6 stopped trades at $350 each uses up the $2,000 drawdown. And $350 over 10 contracts is a $35 stop per contract, so normal wiggles stop trades out: it made about $13–16 a day per contract against about $22 at 1–3 contracts.

So the bot is as ready for a $50K evaluation as it will get from this data. At 2 contracts, expect to pay for about two attempts per pass.

## Fourteenth round: more trades a day

Round five tested checking more often and narrowing the band, but with the paper's half-hour exit. The bot now exits on a resting stop and a max loss, so it was tested again. Variants: entry checks every 30, 15, 10 or 5 minutes, and a noise band 1.0, 0.8 or 0.6 times as wide. Twelve variants on 5-minute bars, 1 MNQ, $117 max loss, prices at today's level. The rules were fixed before running. A variant had to make at least 25% more trades a day, at least as much per day, and a t-stat no more than 0.3 lower. It had to do that in 2011–2018, then again in 2019–2022, and once more in 2023–2026 with a worst losing stretch no more than 20% larger.

| Per contract, 2023–2026 | Trades a day | $ a day | t | Worst losing stretch |
|---|---|---|---|---|
| **Every 30 min, band 1.0 (the bot)** | **0.89** | **$23.32** | **2.48** | **$2,222** |
| Every 30 min, band 0.8 | 1.12 | $18.00 | 1.79 | $3,145 |
| Every 15 min, band 1.0 | 1.03 | $19.76 | 2.07 | $2,799 |
| Every 10 min, band 1.0 | 1.12 | $14.69 | 1.64 | $5,450 |
| Every 5 min, band 1.0 | 1.25 | $17.64 | 1.77 | $3,738 |
| Every 5 min, band 0.6 | 2.13 | $4.67 | 0.39 | $10,755 |

Only checks every 10 minutes passed 2011–2018. It failed 2019–2022: less per day, and a t-stat 0.35 lower. **Nothing replaces the bot.** Every extra entry is a weaker breakout than the half-hour ones, and in 2023–2026 every variant made less per day with a bigger losing stretch. The narrower bands looked good in 2019–2022 and fell apart after, which is the pattern of a lucky fit. The full table is in `research/more_trades.py`'s output.

## Fifteenth round: a trade every day

The bot trades on 57% of days. The other 43% are days when price never closes outside the noise area. Two ideas were tested for those days, with rules and a pass bar written before running ([`research/fill_in.py`](../research/fill_in.py)).

- **A fade inside the noise area.** If a breakout of the usual range means trend, a move toward the edge that doesn't break out might come back. At a half-hour check, with the bot flat and price in the outer half (or outer quarter) of the noise area: sell near the upper line or buy near the lower one. The stop is the line itself, where the bot takes over in the other direction. The target is the middle of the area, or halfway to it. Four variants.
- **A gap fade before 10:00.** The bot never trades 09:30–10:00. If the overnight gap is more than 0.5 or 1.0 times the 10:00 noise, fade it at the 09:30 open, target yesterday's close, out at 10:00. Two variants.

The bar to pass: the side trades alone at t ≥ 2.64 on 2011–2018, and the bot plus them must trade on more days, make at least as much a day, keep the t-stat within 0.3, and keep the worst losing stretch within 20%. Then t ≥ 1.65 and the same four tests on 2019–2022, then on 2023–2026 once. 1 MNQ, $117 max loss, prices at today's level.

| Per contract | Days traded, 2011–18 | $/day 2011–18 | $/day 2019–22 | $/day 2023–26 | Worst stretch 2023–26 | Side trades' t, by period |
|---|---|---|---|---|---|---|
| **The bot alone** | **59%** | **$22.70** | **$23.05** | **$23.32** | **$2,222** | |
| + fade, outer half, target the middle | 91% | $28.46 | $15.67 | $36.53 | $4,202 | 1.51 / −1.06 / 1.90 |
| + fade, outer half, target halfway | 91% | $22.25 | $17.85 | $28.67 | $4,124 | −0.16 / −1.00 / 1.08 |
| + fade, outer quarter, target the middle | 77% | $25.89 | $8.66 | $33.48 | $2,222 | 1.13 / −3.03 / 1.98 |
| + fade, outer quarter, target halfway | 77% | $21.18 | $7.23 | $24.52 | $2,835 | −0.73 / −4.30 / 0.33 |
| + gap fade, gap > 0.5 noise | 90% | $32.03 | $29.39 | $32.17 | $3,292 | 2.90 / 1.07 / 1.59 |
| + gap fade, gap > 1.0 noise | 83% | $32.34 | $25.58 | $28.62 | $3,347 | 3.22 / 0.46 / 1.03 |

- **The fade inside the noise area failed.** It lost money in 2019–2022 in every version. The days the bot can't trade aren't reliably two-way.
- **The gap fade over 1.0 noise units** passed 2011–2018 and failed 2019–2022 (t 0.46). Nothing passed the rules, so the bot is unchanged.
- **The gap fade over 0.5 noise units is the near miss.** It made money in all three periods, and with it the bot made about $9 a day more per contract, with a higher t-stat each time and a trade on 90% of days. It failed one test: its worst losing stretch was 32% larger on 2011–2018 (and 48% larger on 2023–2026). On a $50K evaluation it passed more often at 1 MNQ (66% vs 41% on 2011–2022, 59% vs 38% on 2023–2026), and at 2 MNQ it passed slightly more often and faster. But at 1 MNQ on 2023–2026 it also failed more: 26% vs 7%.
- **A disclosure.** Before the full run, a check of the code's mechanics on June 2023 to May 2024 showed each variant's side P&L for that year. That year is inside the final test. Nothing was changed after it; the rules above were already written.

## Sixteenth round: more profit from the same trades

The profit comes from a few trend days; about two thirds of trades lose. Two levers act on that from opposite ends ([`research/profit_levers.py`](../research/profit_levers.py)), with the pass bar written before running:

- **Add to winners.** At a later half-hour check, if the trade is up 1 (or 0.5) noise units and still outside the line, add a unit, up to 2 or 3. The whole position keeps one $117-per-contract max loss, measured from the average entry.
- **Protect winners.** Once a trade is up 1 noise unit, trail a stop 1 or 2 noise units behind the best close, or move it to the entry.

To pass on 2011–2018 a variant needed at least 10% more a day, a t-stat within 0.3, and at least as much a day per dollar of worst losing stretch. Then better than the bot on 2019–2022 and 2023–2026. 1 base contract, prices at today's level.

| Per contract | $/day 2011–18 | $/day 2019–22 | $/day 2023–26 | t 2023–26 | Worst stretch 2023–26 |
|---|---|---|---|---|---|
| **The bot** | **$22.70** | **$23.05** | **$23.32** | **2.48** | **$2,222** |
| Add to 2 units at +1 | $30.16 | $24.77 | $21.38 | 1.62 | $3,891 |
| Add to 3 units at +1 | $32.98 | $16.09 | $23.86 | 1.55 | $3,894 |
| Add to 2 units at +0.5 | $33.12 | $26.46 | $21.97 | 1.57 | $4,362 |
| Trail 1.0 behind | $22.79 | $31.52 | $17.85 | 2.59 | $3,132 |
| Trail 2.0 behind | $23.14 | $25.41 | $24.35 | 2.61 | $2,222 |
| Stop to the entry | $23.03 | $25.15 | $17.93 | 2.37 | $2,896 |

- **Nothing passed.** Adding to winners made more on 2011–2018 but with a much bigger losing stretch, so less per dollar of risk; on 2023–2026 it made less. The trailing stops and the breakeven stop didn't reach +10% on 2011–2018.
- **The 2-unit trailing stop is slightly better in every period**, by $0.44 to $2.36 a day, with the same or a slightly higher t-stat. It's too small to clear the bar, and too small to be worth a second stop to manage by hand.
- **More profit, for now, comes from size.** The bot makes about $23 a day per contract; profit scales with contracts and so do the losing stretches. The account's drawdown limit sets how many it can carry (round thirteen).

## Seventeenth round: the win rate

A TradingView run with 10 contracts showed 2 wins in 5 trades. Over 16 years the bot wins about 30% of trades and makes its money because an average win is about 3.4 times an average loss. Two questions, measured on 1 contract, prices at today's level ([`research/profit_levers.py`](../research/profit_levers.py) with its `target` and `cap_pts` options). These were run after every period had been seen, so they describe; they are not a test.

**What the max loss per contract does to the win rate:**

| Per contract | Win %, 2011–26 | Avg win | Avg loss | $/day 2011–26 | $/day 2023–26 |
|---|---|---|---|---|---|
| No max loss | 33.5% | $343 | −$128 | $23.30 | $21.00 |
| **$117 (that's $350 on 3 MNQ)** | **28.3%** | **$342** | **−$100** | **$22.90** | **$23.30** |
| $35 (that's $350 on 10 MNQ) | 15.4% | $352 | −$51 | $15.20 | $12.30 |

$350 spread over 10 contracts is a 17.5-point stop, inside normal 5-minute noise: it halves the win rate and about halves the profit.

**What a take-profit does.** A limit this many noise units from the entry, with the line stop and the $117 max loss as before:

| Take profit at | Win % 2011–26 | $/day 2011–18 | $/day 2019–22 | $/day 2023–26 | t 2023–26 | $50K pass at 2 MNQ, 2023–26 |
|---|---|---|---|---|---|---|
| none (the bot) | 28.3% | $22.70 | $23.05 | $23.32 | 2.5 | 42% |
| 0.5 noise units | 48.9% | — | — | $15.30 | 2.5 | — |
| 1.0 | 36.9% | $21.10 | $25.30 | $21.70 | 3.1 | 66% |
| 1.5 | 32% | $22.50 | $34.80 | $22.60 | 2.9 | 68% |
| 2.0 | 30.3% | $24.40 | $31.10 | $23.50 | 2.9 | 51% |
| 2.5 | 29% | $23.40 | $30.40 | $24.70 | 2.9 | 50% |
| 3.0 | 29% | $22.80 | $27.20 | $24.10 | 2.8 | 47% |

- **A high win rate costs money.** Taking profit at half a noise unit wins about half the trades and makes a third less, because it cuts the big trend days the profit comes from.
- **A take-profit at 1.5–2.5 noise units is a lead, not a result.** It is smooth across settings, has a higher t-stat in every period and better $50K odds in 2023–2026, and barely moves the win rate. But most of its extra money is in 2019–2022, and it was found after all 16 years were seen, so there is no untouched data left to confirm it. It needs a forward test: paper trading from October 2026 on.

## Eighteenth round: can the losing trades be spotted at entry?

Every earlier round looked for new places to trade. This one keeps the bot's trades and asks whether facts known at the moment of each signal separate the losers from the winners, so the bot could skip them ([`research/meta_label.py`](../research/meta_label.py)). Ten facts, each a two-way split, rules fixed before running: the trade goes the way of the overnight gap, of yesterday's move, of the last 20 sessions; the market is wilder than its 1-year normal; the signal is at or before 11:30; how far the close is past the line; the day's range so far; first trade of the day; distance from the day's average price; long or short. 3,457 trades, 1 contract, $117 max loss.

| Fact | $ per trade, yes / no, 2011–18 | t | $ per trade, yes / no, 2019–22 | t |
|---|---|---|---|---|
| With the overnight gap | 30.68 / 12.98 | 1.36 | 29.70 / 20.91 | 0.39 |
| With yesterday's move | 28.12 / 21.45 | 0.54 | 17.55 / 35.41 | −0.89 |
| With the last 20 sessions | 32.33 / 17.78 | 1.18 | 30.70 / 23.05 | 0.38 |
| Wilder market than normal | 30.63 / 17.95 | 1.05 | 35.93 / 14.68 | 1.12 |
| Signal by 11:30 | 29.26 / 17.71 | 0.96 | 25.56 / 28.51 | −0.14 |
| Closed well past the line | 32.91 / 16.39 | 1.35 | 34.01 / 19.39 | 0.73 |
| Big range so far | 29.13 / 20.17 | 0.73 | 35.51 / 18.51 | 0.84 |
| First trade of the day | 25.84 / 22.76 | 0.24 | 32.51 / 19.84 | 0.62 |
| Far from the day's average price | 29.02 / 20.28 | 0.71 | 27.06 / 26.61 | 0.02 |
| Long | 24.95 / 24.36 | 0.05 | 34.76 / 19.83 | 0.76 |

- **No fact passed the luck filter** (5% false discovery rate on 2011–2018); the largest t was 1.36.
- **Stage two, added after seeing 2011–2022 only:** the five facts that pointed the same way in both periods, scored 0–5, trading only above a cutoff. Every cutoff kept the win rate at 28% and gave up profit (score ≥ 3: $18.50 a day against $21.64), so nothing went to the final test. 2023–2026 was not looked at for any of this.
- **The losers can't be told apart at entry.** These facts move the size of the wins a little, not the odds of winning. A breakout that will fail looks like one that will run, until it fails; that is what the stop is for.

## Nineteenth round: three ways at the losing trades

Rules and pass bar fixed before running ([`research/losers.py`](../research/losers.py)), 1 contract, $117 max loss, prices at today's level. To pass on 2011–2018: $ per day no lower than the bot's, a t-stat within 0.3, and more $ per day per dollar of worst losing stretch; the flip trades also had to stand alone at t ≥ 2.73. Then the same on 2019–2022, then 2023–2026 once.

- **Time stop.** Breakouts that work tend to work fast, so a trade still losing 15, 30 or 60 minutes after the fill is closed there.
- **Two-check confirmation.** Enter only when two half-hour checks in a row close outside the same line.
- **Flip the failed breakout.** When the bot is stopped out within 30 or 60 minutes, trade the other way: stop at the failed trade's extreme, target the middle of the noise area or the far line.

| Per contract | Win % 2011–18 | Avg loss 2011–18 | $/day 2011–18 | $/day 2019–22 | Flip trades' t, 2011–18 / 2019–22 |
|---|---|---|---|---|---|
| **The bot** | **28.1%** | **−$91** | **$22.70** | **$23.05** | |
| Time stop 15 min | 21.5% | −$70 | $18.48 | $19.61 | |
| Time stop 30 min | 24.8% | −$78 | $22.04 | $22.85 | |
| Time stop 60 min | 26.6% | −$85 | $22.64 | $22.33 | |
| Two checks in a row | 30.1% | −$100 | $15.32 | $15.71 | |
| Flip within 30 min, target the middle | 30.0% | −$91 | $28.93 | $17.88 | 2.57 / −1.09 |
| Flip within 30 min, target the far line | 28.1% | −$91 | $30.33 | $19.35 | 2.44 / −0.67 |
| Flip within 60 min, target the middle | 30.5% | −$91 | $29.46 | $14.42 | 2.53 / −1.69 |
| Flip within 60 min, target the far line | 28.4% | −$91 | $30.42 | $15.90 | 2.30 / −1.21 |

- **Nothing passed, so 2023–2026 was not looked at.**
- **Flipping failed breakouts** made $6–8 a day more on 2011–2018, just short of the bar, then lost money on its own on 2019–2022. The trapped-traders move was real in the older years and has not been since.
- **A 30-minute time stop makes losses about 14% smaller at about the same profit.** It trades a smaller average loss for fewer winners (some slow starters are cut), so the money comes out even. It isn't better, only different.
- **Waiting for a second check** raises the win rate a little and costs a third of the profit: the entry is half an hour later on the trades that work.

## Twentieth round: let the noise area adapt to today's market

Volatility clusters, so today's normal range might be better predicted by recent and current conditions than by a flat 14-session average ([`research/adaptive.py`](../research/adaptive.py)). Rules and pass bar as in round nineteen, fixed before running. A fifth angle, Fed announcement days, was dropped: this environment's network policy blocks the Federal Reserve's and Wikipedia's sites, and the dates were not going to be typed from memory.

| Per contract | Trades/day 2011–18 | $/day 2011–18 | $/day 2019–22 | Worst stretch 2011–18 | Worst stretch 2019–22 |
|---|---|---|---|---|---|
| **The bot** | **0.98** | **$22.70** | **$23.05** | **$3,223** | **$5,178** |
| Band scaled by the overnight range, strength 0.5 | 1.10 | $16.42 | $25.67 | $4,846 | $5,688 |
| Band scaled by the overnight range, strength 1.0 | 1.23 | $13.97 | $26.03 | $5,641 | $4,474 |
| Faster-adapting average (half-life 7 sessions) | 0.95 | $23.47 | $21.10 | $2,842 | $5,199 |
| An extra check at 09:45 | 1.08 | $22.90 | $25.81 | $4,060 | $5,330 |
| Only breakouts past yesterday's high or low | 0.70 | $16.64 | $12.82 | $2,813 | $4,426 |

- **The faster-adapting average passed 2011–2018 and failed 2019–2022**, so 2023–2026 was not looked at.
- **The overnight scaling points opposite ways in the two periods**: worse on 2011–2018, better on 2019–2022. That is noise, not an edge.

## Twenty-first round: contracts that follow the account

A prop account is passed or lost on its path, not its average, so this round changes only how many contracts the bot trades each day, from the account's profit so far ([`research/sizing.py`](../research/sizing.py)). Every size stays within $350 a trade: at most 3 contracts with a $117-per-contract max loss. The $50K Test as reviews describe it, every start day, 125 sessions. To pass: a higher pass rate than a fixed 2 contracts, and a fail rate no higher.

| Size rule | Pass 2011–18 | Fail 2011–18 | Pass 2019–22 | Fail 2019–22 |
|---|---|---|---|---|
| **Fixed 2** | **50.6%** | **43.3%** | **47.9%** | **50.9%** |
| Fixed 3 | 33.4% | 62.6% | 40.9% | 59.1% |
| Build up: 2, then 3 once up $750, 1 if down $750 | 42.7% | 50.5% | 40.6% | 57.5% |
| Earn the size: 1, then 2 once up $500, 3 once up $1,500 | 42.0% | 34.9% | 42.1% | 40.8% |
| Back off: 3, then 2 if down $500, 1 if down $1,000 | 37.1% | 59.7% | 40.2% | 59.2% |

- **Nothing passed.** Fixed 2 contracts stays the best simple choice.
- **"Earn the size" fails about 8–10 points less often** but passes less too: more attempts are still open after six months. It's the safer way to run an evaluation if a slower pass is acceptable, not a better one.

## Twenty-second round: spread the contracts over copies of the bot

Instead of a better signal, the same signal split across copies that differ only in when they check (:00/:30 or :15/:45) or how many sessions the noise area averages (10, 14 or 20). No copy is picked for its own backtest; the average should keep the profit and shrink the losing stretches ([`research/ensemble.py`](../research/ensemble.py)). To pass on 2011–2018: at least 95% of the bot's $ per day, a t-stat at least as high, a smaller worst losing stretch; then the same on 2019–2022 and 2023–2026.

| Per contract | $/day 2011–18 | t | Worst stretch | $/day 2019–22 | t | Worst stretch |
|---|---|---|---|---|---|---|
| **The bot** | **$22.70** | **4.11** | **$3,223** | **$23.05** | **2.44** | **$5,178** |
| Half at :00/:30, half at :15/:45 | $20.62 | 3.87 | $4,514 | $18.23 | 2.09 | $4,802 |
| Thirds on 10, 14 and 20 sessions | $22.86 | 4.19 | $3,154 | $22.54 | 2.43 | $4,716 |
| All six | $20.82 | 3.95 | $4,296 | $18.20 | 2.11 | $5,052 |

- **The mixed windows passed 2011–2018 and missed 2019–2022 by 0.01 on the t-stat.** It's a tie with the bot, not an improvement: the copies' daily P&L is 94–96% correlated, so splitting barely smooths anything.
- **Checking at :15/:45 is worse than :00/:30**, so mixing it in costs profit.

## Twenty-third round: the bot's edge in the overnight sessions

Nasdaq futures trade about 23 hours a day; the bot works 10:00–16:00. The same logic, a move past the usual range for the time since the session opened, was run inside the European session (03:00–09:25, checks 03:30–09:00) and the Asian one (20:00–02:55, checks 20:30–02:30), with the noise area built around each session's open, the bot's stops, and 2 ticks of slippage for the thinner market ([`research/overnight_noise.py`](../research/overnight_noise.py)). To pass: t ≥ 2.24 on 2011–2018, then t ≥ 1.65 on 2019–2022 and 2023–2026.

| Per contract, 2011–2018 | Trades a day | Win % | $/day | t | Worst stretch |
|---|---|---|---|---|---|
| Europe | 1.50 | 23.0% | −$4.16 | −1.20 | $11,159 |
| Asia | 1.29 | 25.5% | +$3.70 | 1.41 | $3,233 |

- **Neither passed.** Overnight moves past the usual range don't keep going the way the day session's do. The edge belongs to the regular session, when the most traders and the most hedging flow are in the market.

## Twenty-fourth round: Fed announcement days

The scheduled FOMC announcement days 2011–2026 ([`research/fomc_dates.csv`](../research/fomc_dates.csv), 127 days) come from the Federal Reserve's meeting calendars; unscheduled meetings, conference calls and notation votes are left out. The statement is at 14:00 New York time (in 2011–2012 some came at 12:30 or 14:15). Four variants, fixed before running, with the pass bar of rounds nineteen and twenty ([`research/fomc.py`](../research/fomc.py)): step aside (flat at 13:55, no entries at 13:30 or 14:00), skip the day, 2 contracts on entries from 14:30, and no shorts before 14:00 (stocks have tended to drift up into the announcement: Lucca and Moench, 2015).

| Per contract | $/day 2011–18 | t | $/day 2019–22 | t | $/day 2023–26 | t | Worst stretch 2023–26 |
|---|---|---|---|---|---|---|---|
| **The bot** | **$22.70** | **4.11** | **$23.05** | **2.44** | **$23.32** | **2.48** | **$2,222** |
| Step aside | $22.56 | 4.08 | $23.06 | 2.45 | | | |
| Skip the day | $23.08 | 4.21 | $22.23 | 2.38 | | | |
| 2 contracts after 14:30 | $22.79 | 4.09 | $23.83 | 2.46 | | | |
| **No shorts before 14:00** | **$22.96** | **4.16** | **$23.22** | **2.46** | **$24.07** | **2.55** | **$2,222** |

- **No shorts before 14:00 passed all three periods**, including the final test on 2023–2026, run once. The pre-announcement shorts it skips lost money in every period: 21 trades in all, 9 + 5 + 7.
- **It's small.** About $0.20–0.75 a day per contract (1–3%), from 1–3 trades a year, so the evidence rests on few trades; the independent academic finding behind it is part of why it was adopted. The worst losing stretch is unchanged.
- **It's in the bot** as *Fed days: no shorts before 14:00*, on by default, with the 2026–2027 dates pre-filled.

## Twenty-fifth round: take half off at a profit, let the rest run

A full take-profit (round seventeen) raised the share of winners but cut the trend days. Scaling out keeps half the position on them: half is closed at a limit 0.5 or 1.0 noise units in profit, the other half runs to the line stop, the max loss or 16:00, with its stop moved to the entry once the first half is banked, or left as before ([`research/scale_out.py`](../research/scale_out.py)). To pass on 2011–2018: winners up at least 10 points, at least 90% of the bot's $ per day, a t-stat within 0.3, a worst losing stretch at most 10% larger.

| Per contract | Win % 2011–18 | Avg win | Avg loss | $/day 2011–18 | t | Worst stretch | $/day 2019–22 | t | Worst stretch |
|---|---|---|---|---|---|---|---|---|---|
| **The bot** | **28.1%** | **$316** | **−$91** | **$22.70** | **4.11** | **$3,223** | **$23.05** | **2.44** | **$5,178** |
| Half at +0.5, rest to breakeven | 50.0% | $119 | −$96 | $13.72 | 3.77 | $2,698 | $14.70 | 2.20 | $4,317 |
| Half at +0.5, rest as before | 40.4% | $155 | −$82 | $13.33 | 3.78 | $2,629 | $12.23 | 1.86 | $4,619 |
| Half at +1.0, rest to breakeven | 38.3% | $196 | −$94 | $17.98 | 4.34 | $2,675 | $21.32 | 2.79 | $4,502 |
| Half at +1.0, rest as before | 37.2% | $203 | −$91 | $17.90 | 4.44 | $2,743 | $20.02 | 2.66 | $4,768 |

- **Nothing passed.** Half off at +0.5 with the rest moved to breakeven wins half the trades, and makes about 40% less: the average win falls from $316 to $119 while the average loss stays about $95.
- **Half off at +1.0 with a breakeven stop is the smoothest version**: a higher t-stat, a smaller losing stretch and more winning months in both periods. But it makes 8–21% less a day, so it isn't more profit, only a calmer ride.
- **The losers stay the same size whatever the exit**, because they are breakouts that fail before the trade is ever in profit. Exits can only reshape the winners.

## Twenty-sixth round: the take-profit, judged walk-forward

Round seventeen found a take-profit about 1.5–2.5 noise units from the entry better in every period, but after all 16 years had been seen. Walk-forward is the standard way to judge a parameter then ([`research/walkforward_tp.py`](../research/walkforward_tp.py)): each year from 2015, pick the setting with the highest daily-P&L t-stat over 2011 up to the year before, from none (the bot) and 1.0, 1.5, 2.0, 2.5 and 3.0 noise units, and trade that year with it. The choice never sees the year it trades. The limit works from the bar after the fill, as the Pine script places it (stricter than round seventeen, where 44 of 798 targets filled on the entry bar). Pass bar, fixed before running: the stitched 2015–2026 record beats the bot on $ per day and t-stat with no larger worst losing stretch.

The procedure picked 2.0 in 2015–2016 and 2019–2021, and 1.5 in 2017–2018 and every year from 2022. It never picked "none".

| Per contract, 2015 – Sep 2026 | $/day | t | Worst losing stretch | Years up |
|---|---|---|---|---|
| The bot | $24.66 | 4.71 | $5,178 | 12 of 12 |
| **Walk-forward take-profit** | **$25.77** | **5.39** | **$4,185** | **12 of 12** |

**It passed, and a 1.5-noise-unit take-profit is now in the bot** (*Take profit*, 0 turns it off). The fixed 1.5 setting by period, with the $50K Test odds at 2 MNQ (as in round thirteen):

| Per contract | Win % | $/day | t | Worst stretch | Months up | $50K pass / fail at 2 MNQ |
|---|---|---|---|---|---|---|
| Bot, 2011–2018 | 28.1% | $22.70 | 4.11 | $3,223 | 62% | 51% / 43% |
| **Take-profit, 2011–2018** | **33.5%** | **$22.10** | **4.41** | **$3,086** | **61%** | **52% / 44%** |
| Bot, 2019–2022 | 27.2% | $23.05 | 2.44 | $5,178 | 65% | 48% / 51% |
| **Take-profit, 2019–2022** | **30.1%** | **$33.21** | **3.54** | **$3,181** | **75%** | **47% / 53%** |
| Bot, 2023–2026 | 30.1% | $23.32 | 2.48 | $2,222 | 58% | 42% / 43% |
| **Take-profit, 2023–2026** | **33.1%** | **$22.43** | **2.92** | **$2,672** | **60%** | **68% / 25%** |

- **The t-stat is higher in every period**: the same money with smaller swings, or more money (2019–2022).
- **The $50K odds in 2023–2026 rose from 42% to 68%, and the fail rate fell from 43% to 25%.** Banking the big days at the target smooths the path, and the evaluation is judged on the path.
- **The win rate rises 3–6 points**, to about a third.
- **Caveats.** The idea came from looking at all the years (round seventeen); walk-forward removes the look-ahead in the setting, not in the idea. In 2023–2026 alone it made about $0.90 a day less per contract and its worst stretch was about 20% larger; the gain there is the steadier path.

## Twenty-seventh round: the max loss is live from the fill

A TradingView run at 10 contracts showed a −$867 trade under a $350 max loss. The cap needs the fill price, so the script had started it on the bar after the fill: a short filled at 15:30, price ran up through the cap during that 5-minute bar, and the next bar opened past it. A trader who places the stop with the entry, as a bracket order, has it live from the fill. The backtest now does the same: on the fill bar the cap is measured from the expected fill (the signal close plus a tick), then from the real fill. This is a correction to match how the bot is traded, not a variant chosen by its results. What it does, with the 1.5-noise-unit take-profit ([`research/profit_levers.py`](../research/profit_levers.py), `cap_on_fill_bar`):

| Per contract | $/day 2011–18 | $/day 2019–22 | $/day 2023–26 | t 2023–26 | Worst trade 2019–22 |
|---|---|---|---|---|---|
| $117 a contract ($350 on 3), cap from the bar after the fill | $22.10 | $33.21 | $22.43 | 2.92 | −$1,042 |
| **$117 a contract, cap live from the fill** | **$23.66** | **$32.83** | **$19.60** | **2.71** | **−$338** |
| $35 a contract ($350 on 10), cap from the bar after the fill | $12.52 | $21.07 | $11.59 | 1.62 | −$1,042 |
| **$35 a contract, cap live from the fill** | **$14.17** | **$14.31** | **$5.83** | **1.10** | **−$257** |

- **At $117 a contract it's about even**: a little better on 2011–2018, the same on 2019–2022, a little worse on 2023–2026, and the losses past the cap shrink (worst trade −$1,042 to −$338 on 2019–2022).
- **At $35 a contract the backtest had been flattering.** A $35-per-contract stop sits inside normal 5-minute moves; once it is live from the fill, as it would be in real trading, 2023–2026 falls to about $6 a day per contract and the win rate to about 13%. $350 on 10 contracts is the setting that holds the bot back, not the signal.

## Twenty-eighth round: size each trade from the $350

The rules "up to 10 MNQ" and "at most $350 per trade" squeeze the stop to $35 a contract at a fixed 10. Risk-based sizing keeps both: at each signal, n = floor($350 / (distance from the expected fill to the bot's line stop × $2)), between 1 and 10, with the $350 max loss for the whole position live from the fill ([`research/risk_size.py`](../research/risk_size.py)). The bot otherwise as it trades now (take-profit, fill-bar cap). Pass bar, fixed before running: against fixed 10, more $ a day in total, a higher t-stat, a worst losing stretch no larger, on 2011–2018, then 2019–2022, then 2023–2026.

| Total, $350 max loss | Avg contracts | Win % 2011–18 | $/day 2011–18 | t | Worst stretch | $/day 2019–22 | t | Worst stretch |
|---|---|---|---|---|---|---|---|---|
| Fixed 10 | 10 | 15.4% | $141.74 | 3.51 | $28,423 | $143.12 | 2.18 | $47,457 |
| Fixed 3 | 3 | 33.3% | $70.98 | 4.73 | $9,165 | $98.50 | 3.62 | $10,077 |
| Risk-sized up to 10 | 1.8–2.7 | 39.4% | $30.98 | 2.88 | $9,629 | $52.31 | 3.74 | $5,466 |

- **Risk sizing failed.** The bot's line stop is usually far enough from the entry that only 1–3 contracts fit in $350, so it wins the most trades (about 40%) and has the smallest swings, but makes the least.
- **Fixed 10 at $350 made about twice what fixed 3 did on 2011–2022**, with a losing stretch 3–5 times as deep and a lower t-stat; on 2023–2026 the two made about the same (round twenty-seven). Fixed 10 is a choice for a large account, not for a $2,000 evaluation drawdown.

## Twenty-ninth round: busier days, from daily NQ futures volume

Yahoo Finance has NQ futures daily bars with volume back to 2000 ([`research/volume_days.py`](../research/volume_days.py) has the download). Its 5-minute bars go back only 60 days, too short for an intraday volume test, so this round asks whether the bot does better on busier days. Three facts known before the open, rules fixed before running: yesterday's volume above its 20-day average; the last 5 days' average above the 60-day average; the 5-day average above the 20-day average. Contract-roll weeks (10 days before to 3 after each quarterly expiry) are left out, because volume moves between contracts there. The same bar as round eighteen: a false-discovery filter on 2011–2018, confirmation on 2019–2022, then a final test.

| Fact | $ per trade, yes / no, 2011–18 | t | $ per trade, yes / no, 2019–22 | t |
|---|---|---|---|---|
| Heavy yesterday | 24.34 / 11.33 | 1.55 | 21.64 / 38.99 | −1.11 |
| Active week | 23.35 / 14.16 | 1.11 | 26.19 / 30.11 | −0.26 |
| Volume rising | 20.56 / 17.76 | 0.33 | 25.63 / 31.20 | −0.37 |

**Nothing passed**; each fact flipped sign between the periods. Daily volume doesn't tell the bot's good days from its bad ones. Intraday volume at the signal is still untested: it needs years of 1-minute futures bars with volume.

## Thirtieth round: market mood and hourly volume at the signal

More of Yahoo Finance's data ([`research/fear_volume.py`](../research/fear_volume.py)): the VIX, VIX3M and VIX9D fear indexes, S&P 500 futures (ES) daily, and NQ futures hourly bars with volume for about two years. Rules fixed before running.

**Part A, market mood**, facts known before the open, with round eighteen's bar:

| Fact | $ per trade, yes / no, 2011–18 | t | $ per trade, yes / no, 2019–22 | t |
|---|---|---|---|---|
| Fearful: VIX above its 1-year median | 27.77 / 8.62 | 2.55 | 25.90 / 19.19 | 0.53 |
| Inverted: VIX at or above VIX3M | 40.45 / 14.61 | 1.73 | 4.71 / 26.80 | −1.07 |
| Short-term stress: VIX9D at or above VIX | 28.68 / 11.77 | 2.04 | 12.64 / 29.43 | −1.19 |
| Fear rising: VIX up the day before | 19.96 / 15.93 | 0.54 | 3.06 / 41.60 | −2.94 |
| Nasdaq leading the S&P over 20 days | 14.54 / 23.05 | −1.10 | 17.16 / 30.84 | −1.02 |

None passed the luck filter (5% false discovery rate over five; "fearful" came closest at p = 0.011).

**Part B, hourly volume at the signal**, June 2024 to September 2026, 553 trades: the last full hour before the signal busier than the same hour over the previous 20 sessions, or not. First half: busy −$10.74 a trade, quiet +$66.29 (t −2.15). Second half: busy +$24.94, quiet +$12.32 (t +0.52). The sign flips: **failed**.

## Thirty-first round: trade more when the market is scared

"Fearful" pointed the same way in both periods, and so did "wilder than normal" in round eighteen, while round eight found that cutting size on wild days hurt. The rule that follows, picked after seeing 2011–2022 and tested once on 2023–2026 ([`research/fear_size.py`](../research/fear_size.py)): 2 units when the previous VIX close is above its 1-year median, 1 otherwise. Pass bar: a higher t-stat and more $ a day per dollar of worst losing stretch than flat sizing (both ratios are the same for flat sizing at any size).

| Per unit | t 2011–18 | $ per $1k stretch | t 2019–22 | $ per $1k stretch | t 2023–26 | $ per $1k stretch | Worst stretch 2023–26 |
|---|---|---|---|---|---|---|---|
| Flat | 4.73 | 7.75 | 3.62 | 9.77 | 2.71 | 5.42 | $3,618 |
| 2 units when scared | 4.85 | 6.82 | 3.46 | 8.26 | 2.16 | 3.51 | $7,237 |

**Failed.** The scared periods hold the losing streaks too, so trading bigger in them doubles the worst stretch and adds less than it risks. The bot earning more per trade on fearful days is real enough to show in three rounds, but it doesn't make a better sizing rule.

## Thirty-second round: volume at the signal, on real NQ futures 1-minute bars

A public dataset on Hugging Face ([mdelcristo/NQ-F_1min_OHLCV_Parquet](https://huggingface.co/datasets/mdelcristo/NQ-F_1min_OHLCV_Parquet), MIT licence) has NQ futures 1-minute bars with volume from January 2015 to July 2025: 3.67 million bars, real exchange prices including the contract rolls (the 09:30 open shows the expected jump, from about 500 contracts a minute to 2,800). [`research/nq_volume.py`](../research/nq_volume.py).

**The bot on this independent data**, as it trades now, 1 contract, $117 max loss: 3,463 trades, 31.0% winners, **$27.94 a day, t = 5.72**, positive in 10 of 11 years (2015 +$6,250, 2016 +$3,299, 2017 +$1,827, 2018 +$15,226, 2019 −$1,337, 2020 +$6,008, 2021 +$9,141, 2022 +$17,439, 2023 +$7,634, 2024 +$2,471, 2025 to July +$3,423). The edge isn't an artefact of the index CFD data the rounds above used. At a $35 stop per contract ($350 over 10 MNQ) the same years give a third as much per contract and three losing years (2017, 2019, 2025).

**Volume at the signal**, four facts against the same time of day over the previous 20 sessions, rules fixed before running (discovery 2015–2019, confirmation 2020–2022, final 2023–2025, roll weeks left out):

| Fact | $ per trade, yes / no, 2015–19 | t | $ per trade, yes / no, 2020–22 | t |
|---|---|---|---|---|
| Busy half hour before the signal | 19.15 / 15.84 | 0.29 | 37.11 / 22.56 | 0.82 |
| Volume surge in the last 5 minutes | 20.51 / 12.85 | 0.71 | 27.85 / 43.79 | −0.84 |
| Busy day so far | 17.24 / 20.93 | −0.32 | 28.91 / 42.33 | −0.72 |
| Busy overnight | 23.15 / 12.02 | 1.05 | 30.82 / 35.11 | −0.25 |

**Nothing passed.** Breakouts on heavy volume did no better than breakouts on light volume, so volume confirmation, a staple of breakout trading, adds nothing to this bot.

## Stress tests of version 1.0

The bot as it trades now, per contract with $117 of room (the $350 max loss on 3 MNQ), on both datasets: the index data 2011–2026 and the NQ futures 2015–2025 ([`research/stress.py`](../research/stress.py), simulated with `mnqbot.noise`, the reference the Pine script is tested against). Pass bars fixed before running: profitable with t ≥ 2 under double slippage, doubled fees, and every setting nudged both ways; profitable with every entry filled one bar late.

| Per contract | Index 2011–26 $/day | t | NQ futures 2015–25 $/day | t |
|---|---|---|---|---|
| **As it trades** | **$25.11** | **6.53** | **$27.94** | **5.72** |
| Slippage 2 ticks a side (double) | $23.94 | 6.22 | $26.42 | 5.42 |
| Slippage 3 ticks a side | $22.88 | 5.96 | $25.45 | 5.22 |
| Fees doubled | $23.50 | 6.12 | $26.26 | 5.38 |
| Stop buffer 0.12 / 0.36 | $22.01 / $24.26 | 5.85 / 6.16 | $24.03 / $27.29 | 5.08 / 5.47 |
| Take-profit off / 1.0 / 2.0 | $23.50 / $21.45 / $25.84 | 5.50 / 5.95 / 6.37 | $29.54 / $24.80 / $30.36 | 5.27 / 5.37 / 5.91 |
| Lookback 10 / 20 sessions | $23.74 / $23.73 | 6.04 / 6.09 | $25.92 / $25.39 | 5.16 / 5.13 |
| Max loss $80 / $160 a contract | $19.51 / $24.63 | 5.48 / 6.24 | $19.35 / $29.91 | 4.36 / 5.89 |
| Every entry 5 minutes late | $13.20 | 3.63 | $16.60 | 3.52 |

**Every case passed on both datasets.** No setting sits on a cliff: every neighbour of every setting is profitable with t above 4. Costs matter little. Speed matters most: an entry 5 minutes late roughly halves the profit, because the trades that work move fast.

**10,000 reshuffled years** (20-session blocks of the real daily P&L, 252 sessions each), per contract: a losing year 3.6% of the time on the index data and 2.8% on the futures; the 5th-percentile year +$481 and +$971; the 95th-percentile deepest drawdown within a year $3,764 and $4,222. Multiply by the contracts.

**Pine tests for version 1.0**: besides the hand-built cases, 40 randomised cases run the script against the reference on a harsher synthetic market (price gaps between bars, missing bars, half days, trend and quiet days, a daylight-saving change) with random settings (exit mode, 1–10 contracts, max loss off to $1,170, stop buffer, take-profit, lookback 5 or 14, 5/10/15-minute charts, extended hours on or off, random Fed and holiday dates). They agree on every trade, every alert and every trade-log row, across about 1,000 line stops, 500 max-loss stops, 400 take-profits, 500 fill-bar exits and 500 stops filled at a gapped open. A mutation check confirms the tests catch each of 20 planted bugs.

**One difference to know about**: when a single bar touches both the stop and the take-profit, the tests and the Python reference count the stop (the worst case); TradingView's broker emulator guesses the path inside the bar and sometimes counts the target. So TradingView can show slightly better results than the tests on such bars.

## Thirty-third round: sell the bounce instead of the breakdown

On 16 October 2026 (real MNQ bars from Yahoo, 10 MNQ at $350) the bot shorted five breakdowns by 12:00: four bounced about 17 points inside the first 5 minutes and hit the $35-per-contract stop (−$342 to −$367 each), one ran to the take-profit (+$3,278), +$1,853 on the morning. The idea that day suggests: rest a limit entry a little better than the signal price, so the bounce becomes the entry. Rules fixed before running ([`research/pullback.py`](../research/pullback.py)): a limit 0.1 or 0.25 noise units better than the signal close, filled a tick through, cancelled at the next check; the stop counted on the fill bar if the bar reached it (worst case); everything else as the bot trades.

| Per contract | $/day 2011–18 | t | $/day 2019–22 | t |
|---|---|---|---|---|
| **$117 max loss, market entry (the bot)** | **$23.66** | **4.73** | **$32.83** | **3.62** |
| $117, limit 0.1 better | $15.58 | 3.39 | $20.01 | 2.49 |
| $117, limit 0.25 better | $8.31 | 2.14 | $5.16 | 0.81 |
| $35 max loss, market entry | $14.17 | 3.51 | $14.31 | 2.18 |
| $35, limit 0.1 better | $6.91 | 1.96 | $9.48 | 1.62 |
| $35, limit 0.25 better | $3.63 | 1.30 | $3.88 | 0.86 |

**Failed, clearly.** The limit fills on the breakouts that come back, which are the ones failing, and misses the ones that run without looking back, which are the ones that pay. The market entry stays.

## Thirty-fourth round: are the first and last checks worth trading?

A 15:30 entry has 25 minutes to pay before the 16:00 exit; a 10:00 entry is judged against a noise area built from the noisiest half hour of the day. Four variants, fixed before running ([`research/check_times.py`](../research/check_times.py)): no entries at 15:30; at 15:00 or 15:30; at 10:00; at 10:00 or 15:30. The pass bar was the usual one on the index data, plus a replication on the NQ futures data.

| Per contract | $/day 2011–18 | t | $/day 2019–22 | t |
|---|---|---|---|---|
| **The bot** | **$23.66** | **4.73** | **$32.83** | **3.62** |
| No 15:30 | $21.70 | 4.54 | $31.64 | 3.53 |
| No 15:00 or 15:30 | $19.88 | 4.23 | $33.46 | 3.74 |
| No 10:00 | $20.23 | 4.18 | $26.83 | 3.12 |
| No 10:00 or 15:30 | $18.34 | 3.98 | $25.25 | 2.99 |

**Nothing passed; the idea was wrong.** By entry time, 2011–2022, the 10:00 entries are the bot's best (722 trades, $30.98 each, the largest total of any check) and the 15:30 entries pay $23.48 each. The weak ones are midday: 13:00 (198 trades, −$10.93 each) and 14:00 ($1.37). With twelve check times, one or two looking bad is what chance produces, and none of these differences is large next to the spread of single trades, so the midday checks stay too.

## Thirty-fifth round: what each minute of delay costs

The stress tests found a 5-minute-late entry roughly halves the profit. This round measures it minute by minute, on 1-minute bars of both datasets ([`research/delay.py`](../research/delay.py)). Entries fill at the open of the first minute after the check (what an automated order gets), or 1, 2, 3 or 5 minutes later, with the max loss then measured from the real fill. Everything else is the bot as it trades. The 1-minute simulation matches the reference engine trade for trade (306 of 306 trades on NQ 2019, same P/L to the cent). The rule, fixed before running: build automation if 1–3 minutes of delay cost 15% or more.

| $ per day per contract, % of on time | Index 2011–26, $117 | Index, $35 | NQ futures 2015–25, $117 | NQ futures, $35 |
|---|---|---|---|---|
| On time (automated) | $26.31 (100%) | $12.82 (100%) | $29.02 (100%) | $11.96 (100%) |
| 1 minute late | $20.27 (77%) | $11.21 (87%) | $24.79 (85%) | $9.06 (76%) |
| 2 minutes late | $17.96 (68%) | $8.46 (66%) | $20.83 (72%) | $7.85 (66%) |
| 3 minutes late | $15.91 (60%) | $8.84 (69%) | $15.54 (54%) | $4.49 (38%) |
| 5 minutes late | $14.03 (53%) | $3.99 (31%) | $17.10 (59%) | $2.55 (21%) |
| *5-minute bars, on time (the TradingView backtest)* | *$25.11 (95%)* | *$12.30 (96%)* | *$27.94 (96%)* | *$11.82 (99%)* |

- **Each minute late costs about 15–25% of the profit.** The breakout pays most in the minutes right after the check, and a late entry also starts further from the line, so its stop is closer and fills more often. At $35 a contract (the $350 over 10 MNQ) three minutes late leaves about 40–70%.
- **The 5-minute backtest is not flattered by its bar length.** On 1-minute bars, where stops and targets are resolved minute by minute, the same rules make 1–5% more than on 5-minute bars.
- **So automation passes the bar.** But the firm decides: Take Profit Trader's Universal Trading Policies (help center, updated 9 October 2026) say *"Automated trading systems, bots, or algorithmic execution tools are not permitted."* By a 28-firm review of official help pages (prop-memo.com, 21 September 2026), Apex now bans automation too, while Lucid Trading, MyFundedFutures, FundedNext Futures and FTMO Futures allow it in writing, and Tradeify, Bulenox and Topstep allow self-built bots with conditions. Check the firm's own rules before buying.
- **Webhook mode (v1.1).** For a firm that allows it, the script can now send each order as a TradersPost message with the bracket attached. The broker holds the stop placed with the entry and the strategy can't move it, so in this mode the stop only ever tightens, and an exit message closes the trade when the chart's tighter stop fills. Tested against the moving stop before building it: NQ futures 2015–2025 at $117, $27.10 a day against $27.94, t-stat 5.61 against 5.72, worst losing stretch $4,174 against $4,222; index 2011–2026, $25.07 against $25.11. At $35: $11.74 against $11.82 and $12.31 against $12.30. On real MNQ 5-minute bars from Yahoo, 21 September to midday 16 October 2026, the same trades and winners and slightly more money: +$12,555 against +$12,313 at 10 MNQ and $350, +$6,731 against +$6,662 at 3 MNQ. The same money.

## Thirty-sixth round: more winners at 10 MNQ and $350

The user's TradingView account showed about 5 winners in 15 trades and asked for a much higher win rate without changing sizes. Every exit setting so far was tuned at $117 a contract; at the user's setting, $350 over 10 MNQ, the stop is $35 a contract (17.5 points). There the bot wins about 14% of trades and trades twice a day, because ordinary 5-minute noise hits the stop and the bot re-enters at the next check. Rules fixed before running ([`research/win_rate35.py`](../research/win_rate35.py)), per contract at $35 (×10 for the account), pass bar against the bot: win rate 10 points higher, $ per day no lower, t-stat within 0.3, $ per day per dollar of worst losing stretch no lower.

| 2011–2018, per contract at $35 | Trades/day | Win % | $/day | t |
|---|---|---|---|---|
| **The bot** | **2.03** | **15.4%** | **$14.17** | **3.51** |
| Take-profit 0.5 / 0.75 / 1.0 noise units | 2.3–2.8 | 18–25% | $1.48 / $8.25 / $11.94 | 0.5–3.2 |
| Lock: once a bar closes 17.5 pts up, stop to entry + 2.5 | 2.32 | 36.7% | $14.38 | 3.83 |
| Lock at 35 pts up | 2.17 | 27.8% | $13.90 | 3.59 |
| No entries after 1 / 2 losers today | 0.66 / 1.12 | 17% / 16% | $4.80 / $9.77 | 2.3 / 3.4 |
| No second entry on a side that lost today | 0.69 | 17.4% | $5.29 | 2.47 |

The lock passed discovery and failed confirmation: on 2019–2022 it won 31% against 12% but made $11.84 a day against $14.31. **The repeat entries the bot takes after a stop-out are where its money is**: limiting them cut the profit by a third to two thirds.

## Thirty-seventh round: the lock with room, and skipping the signals a $35 stop can't survive

Rules fixed before running ([`research/win_rate35b.py`](../research/win_rate35b.py)): five locks with more room ((trigger, lock) of (17.5, 5), (17.5, 8.75), (26.25, 8.75), (26.25, 13.125), (35, 17.5) points), no entry when 17.5 points is under 0.1–0.3 noise units, and every pair. Same pass bar. 2019–2022 had been seen once for one lock.

- **Nothing passed.** The best, the (17.5, 5) lock, won 36.7% against 15.4% at $14.14 a day against $14.17 (t 3.79 against 3.51): it missed the bar by three cents.
- **Skipping the high-noise signals costs most of the money** ($7.32 a day at 0.1, $1.25 at 0.2): the days the noise is wide are the trend days.

**Descriptive, after both rounds: the lock is a fast exit, and on 5-minute bars it is too slow.** On 5-minute bars the lock can only act at the next bar after the trigger; a broker's auto-breakeven acts on the tick. So the same rule on 1-minute bars of both datasets, armed when price *touches* the trigger and moved from the next minute, as Tradovate's Auto Breakeven would do it (trigger 70 ticks, offset +10 ticks):

| Per contract at $35 (×10 for 10 MNQ at $350) | Win % | $/day | t | Worst losing stretch | Months up |
|---|---|---|---|---|---|
| Index 2011 – Sep 2026, the bot | 14.1% | $12.82 | 4.34 | $3,800 | 57% |
| **Index 2011 – Sep 2026, with the lock** | **48.7%** | **$13.01** | **5.18** | $4,553 | 63% |
| NQ futures 2015 – Jul 2025, the bot | 13.3% | $11.96 | 3.22 | $3,920 | 58% |
| **NQ futures 2015 – Jul 2025, with the lock** | **48.0%** | **$11.65** | **3.66** | **$2,655** | 58% |
| Index 2011–18 / 2019–22 / 2023–26, the bot | 15.5 / 12.1 / 13.4% | $14.63 / $15.60 / $5.60 | | | |
| Index, with the lock | 50.3 / 46.7 / 47.3% | $14.80 / $16.91 / $4.59 | | | |
| 5-minute bars (what the TradingView chart shows), index / NQ, the bot | 14.1 / 13.2% | $12.30 / $11.82 | 4.18 / 3.19 | | |
| 5-minute bars, with the lock | 39.7 / 37.9% | $11.57 / $9.53 | 4.39 / 2.88 | | |

- **About half the trades win instead of one in seven, for about the same money**, with a higher t-stat on both datasets. A locked trade closes at the entry + 2.5 points less a tick, +$3.26 a contract after fees: many of the new winners are small. The average winner is smaller and there are three times as many.
- **On real MNQ bars from Yahoo, 21 September to midday 16 October 2026** (never used to choose anything here), at 10 MNQ and $350 on 5-minute bars: 50 trades, 23 winners (46%), +$13,474, worst day −$1,382, against 44 trades, 11 winners (25%), +$12,313, worst day −$1,862 without it. Winning days fell from 7 of 10 to 5 of 10.
- **The $50K evaluation at 10 MNQ and $350** (125-day window, 1-minute bars): passes 28% against 21% on the index 2011–2026, 25% against 13% on 2023–2026, 22% against 22% on NQ futures. At this size most attempts still fail either way.
- **Caveats.** The lock was found by looking at 2011–2022, and the 1-minute version after every period had been seen; only the Yahoo weeks are new. It is in the bot (v1.2) because the user asked for the win rate at fixed sizes and it keeps the money on both datasets; set *Lock a small win* to 0 to turn it off. On the 5-minute chart it costs 6–19% of the profit; the broker's Auto Breakeven, set as above, is what gets the 1-minute numbers.

## Thirty-eighth round: on top of the lock

Three ideas at 10 MNQ and $350 with the lock on, on 1-minute bars, fixed before running ([`research/lock_more.py`](../research/lock_more.py)): a second lock step (35 points up → stop to entry + 17.5, or 52.5 → + 35); no new entries after a take-profit fills; no new entries after 3 or 4 losing trades in a day. Pass bar against the bot with the lock: $ per day no lower, t-stat within 0.3, $ per day per dollar of worst losing stretch no lower, win rate no more than 2 points lower, on 2011–2018, then 2019–2022, then 2023 – Sep 2026 once, then NQ futures.

| 2011–2018, per contract at $35 | Trades/day | Win % | $/day | t | Worst stretch |
|---|---|---|---|---|---|
| **The bot with the lock (v1.2)** | **2.47** | **50.3%** | **$14.80** | **4.36** | **$2,643** |
| Second step 35 → +17.5 | 2.74 | 50.4% | $12.92 | 4.32 | $2,235 |
| Second step 52.5 → +35 | 2.82 | 50.4% | $11.50 | 4.04 | $2,370 |
| Done after a take-profit | 2.07 | 49.5% | $11.19 | 3.77 | $2,705 |
| Stop after 3 losers | 2.04 | 50.7% | $13.19 | 4.29 | $3,125 |
| **Stop after 4 losers** | **2.27** | **50.6%** | **$15.19** | **4.67** | **$2,569** |

**Stop after 4 losers passed every stage**, and is in the bot (v1.3, *Max losing trades a day*, 0 = no limit):

| Per contract at $35 | Win % | $/day | t | Worst losing stretch | $50K pass / fail at 10 MNQ |
|---|---|---|---|---|---|
| v1.2, 2019–2022 | 46.7% | $16.91 | 3.00 | $2,771 | |
| **v1.3, 2019–2022** | **47.0%** | **$17.04** | **3.24** | **$2,453** | |
| v1.2, 2023–2026 | 47.3% | $4.59 | 0.98 | $4,553 | 25% / 75% |
| **v1.3, 2023–2026** | **47.8%** | **$6.64** | **1.49** | **$3,497** | **23% / 76%** |
| v1.2, NQ futures 2015–2025 | 48.0% | $11.65 | 3.66 | $2,655 | 22% / 76% |
| **v1.3, NQ futures 2015–2025** | **48.8%** | **$12.90** | **4.33** | **$1,835** | **25% / 74%** |

- **Four losers in a day is about −$1,400 at 10 MNQ**, most of the $2,000 drawdown; past that, the day's later signals lost on balance. At three the bot gives up too many days that come back.
- **The second lock step and stopping after a target both cost money.** Locked trades that keep running are the big winners, and so are the re-entries after a target.
- **On the real MNQ weeks from Yahoo** (21 September – 16 October 2026, 5-minute bars), v1.3 made +$13,068 on 44 trades, 19 winners (43%), against +$13,474 for v1.2 and +$12,313 for v1.1. Four weeks is small next to the tests above.
- **The evaluation odds at 10 MNQ and $350 barely move** (about a quarter pass). The size, not the rules, is what holds them down.

## Rounds thirty-nine to forty-two: more winners at 10 MNQ and $350, again

A TradingView screenshot of v1.3 on 16 October 2026 showed 7 winners in 17 trades (41%). On 2011–2018 1-minute data at this setting, half the losing trades are stopped within 2 minutes of the fill and three quarters within 5, mostly by the bounce just after the breakout; only a tenth of the winners close within 2 minutes. Each idea below was fixed before its test; the baseline is v1.3 on 1-minute bars.

| Per contract at $35 (×10 for 10 MNQ at $350) | Win % | $/day | t | Worst stretch | Result |
|---|---|---|---|---|---|
| **v1.3, 2011–2018** | **50.6%** | **$15.19** | **4.67** | **$2,569** | |
| Ghost trade: skip the signal if a trade from the first minute would have been stopped within 1 / 2 / 3 / 5 minutes, else enter then (39) | 47–49% | $4.34–$9.81 | 1.6–3.4 | | failed |
| Lock at 12.5 points instead of 17.5 (39) | 56.3% | $16.31 | 5.29 | $2,189 | see below |
| Lock as a trailing stop, activate 12.5 / trail 10 (40, 41) | 57.2% | $9.55 | 5.67 | $1,086 | failed |
| Skip spikes: no entry when the 5-minute check bar closed in the top fifth of its range toward the signal (42) | 52.1% | $16.08 | 5.32 | $1,501 | failed |

- **The ghost trade fails badly.** Many trades that bounce in the first minutes go on to win, and the ones that survive are entered later, at worse prices.
- **The lock at 12.5 points** passed 2011–2018 and improved every money measure on 2019–2022 (winners 47.0% → 51.0%, $17.04 → $17.63, t 3.24 → 3.48), but its win rate rose 4 points against the 5 required, so it failed. Looked at afterwards: all of 2011–2026 53.8% against 49.0% and $14.33 against $13.71; NQ futures 52.8% against 48.8% and $13.33 against $12.90; but 2023–2026 $6.14 against $6.64. Not adopted.
- **The trailing lock** (round forty-one asked the evaluation question directly: pass rate at least 5 points higher, fewer fails, t within 0.3) raised the $50K passes at 10 MNQ from 32% to 43% on 2019–2022, then nearly erased the profit on 2023–2026 ($0.91 a day against $6.64, t 0.39). Failed.
- **Skipping spikes** came from looking at 2011–2018 (spikes into the close won 44.8% and lost $17 a contract on average), passed 2019–2022 (48.8% against 47.0%, $18.66 against $17.04, worst stretch 41% smaller), then failed 2023–2026 ($5.37 against $6.64, win rate +0.2 points).

**What the TradingView chart shows, and why.** v1.3 at 10 MNQ and $350 over 16 years: **40% winners on 5-minute bars (38.5% on NQ futures), 49% on 1-minute bars (48.7%)**. The lock has to act within seconds; on a 5-minute chart the script moves it a bar late. Letting the lock fill inside the bar along TradingView's own bar path (open, nearer extreme, farther extreme, close) only gets to 40.7%: inside 5 minutes price crosses the trigger and back more often than four prices can show. So the chart will show about 40%, and an account using Tradovate's Auto Breakeven about 49%. **A 17-trade stretch swings between about 24% and 59% winners** (10th to 90th percentile) by chance alone.

**More backtest on the chart.** With 24-hour bars, the 14 sessions of history use up most of what TradingView loads (about 18 days of 5-minute bars on a 5,000-bar plan), leaving 3 days of trades. The bot needs only regular-hours bars: on the Yahoo weeks, an RTH chart (09:30–16:15) gives the same 44 trades to the cent with 4,012 bars instead of 13,538, so the same plan shows about 45 days of trades. The dashboard now says so on an extended-hours chart.

## A check on real MNQ futures data, September 21 to October 15, 2026

Yahoo's last 60 days of MNQ 5-minute bars (from 7 August 2026) let the Python reference run on real futures prices ([`research/yahoo_forward.py`](../research/yahoo_forward.py)). From 21 September, the first day with 14 sessions of history, it reproduces the TradingView trade log a user sent for 12 and 14 October: the same trades, entries within a tick or two, the take-profits at +$3,067 and +$3,771 against TradingView's +$3,067.60 and +$3,767.60. Most of October is newer than any data used in the rounds above.

The same weeks at four settings (the bot as it is now, take-profit and fill-bar cap included):

| Setting | Trades | Winners | Total | Winning days | Worst day |
|---|---|---|---|---|---|
| 10 MNQ, $350 max loss | 39 | 10 (26%) | +$10,460 | 6 of 9 | −$1,862 |
| 3 MNQ, $350 max loss | 20 | 14 (70%) | +$6,390 | 8 of 9 | −$366 |
| 2 MNQ, $350 max loss | 18 | 13 (72%) | +$3,543 | 8 of 9 | −$244 |
| 10 MNQ, $1,170 max loss | 20 | 14 (70%) | +$21,285 | 8 of 9 | −$1,218 |

- **The $35-per-contract stop is visible trade by trade.** At 10 MNQ and $350 the bot was stopped 29 times, 7 times in a row on 22 September and 5 on 30 September, re-entering at each check because price was still outside the line. With $117 a contract the same signals gave 20 trades, 14 of them winners.
- **Four weeks is a small sample.** Over 16 years the bot wins about a third of its trades at $117 a contract; 70% here is a good month, not the new normal. What carries over is the comparison between settings on the same days.

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
python research/discovery.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"      # search for new patterns, one at a time
python research/discovery2.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"     # extremes, and all of them combined
python research/afternoon.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"      # the afternoon-trend idea, final test
python research/discovery3.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"     # overnight, regimes, walk-forward boosting
python research/regime_trend.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"   # the regime-trend family, final test
python research/round8.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"         # volatility sizing, the 24-hour clock
python research/round9.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"         # the resting-stop exit, account tiers
python research/postmortem.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"     # why the trades lose; the buffered stop
python research/dips.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"           # the worst days; protections; the cap sweep
python research/timeframes.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"     # 5 vs 15 vs 30-minute charts
python research/eval50k.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"        # the $50K evaluation, 1 to 10 MNQ
python research/more_trades.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"    # more trades a day? (no)
python research/fill_in.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"        # a trade every day? (not by the rules)
python research/profit_levers.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"  # add to winners, trailing stops (no)
python research/meta_label.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"     # spot the losers at entry? (no)
python research/losers.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"         # time stops, confirmation, flips (no)
python research/adaptive.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"       # a noise area that adapts (no)
python research/sizing.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"         # contracts that follow the account (no)
python research/ensemble.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"       # copies of the bot (a tie, no)
python research/overnight_noise.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv" # the edge overnight (no)
python research/fomc.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"            # Fed days: no shorts before 14:00 (adopted)
python research/scale_out.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"       # half off at a profit (no)
python research/walkforward_tp.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"  # the take-profit, walk-forward (adopted)
python research/risk_size.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"       # size each trade from the $350 (no)
python research/volume_days.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv" nq_1d.json  # busier days (no)
python research/yahoo_forward.py mnq_5m.json 10 350                    # real MNQ bars, the last 60 days
python research/fear_volume.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv" yahoo_dir   # market mood, hourly volume (no)
python research/fear_size.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv" yahoo_dir     # bigger when scared (no)
python research/nq_volume.py path/to/nq_parquet_dir                    # real NQ futures; volume at the signal (no)
python research/stress.py nsx_5m_scaled.pkl nq_5m_scaled.pkl           # stress tests of version 1.0
python research/pullback.py nsx_5m_scaled.pkl                          # limit entry on the bounce (no)
python research/check_times.py nsx_5m_scaled.pkl nq_5m_scaled.pkl      # skip the first or last checks (no)
python research/delay.py nsx_1m_scaled.pkl nq_1m_scaled.pkl            # each minute of entry delay, 1-minute bars
python research/win_rate35.py nsx_5m_scaled.pkl nq_5m_scaled.pkl       # more winners at $35 a contract (lock, no pass)
python research/win_rate35b.py nsx_5m_scaled.pkl nq_5m_scaled.pkl      # the lock with room, skip wide noise (no pass)
python research/lock_more.py nsx_1m_scaled.pkl nq_1m_scaled.pkl       # on top of the lock: 4 losers a day (adopted)
python research/ghost.py nsx_1m_scaled.pkl nq_1m_scaled.pkl           # ghost trade, lower lock (no pass)
python research/trail_lock.py nsx_1m_scaled.pkl nq_1m_scaled.pkl      # the lock as a trailing stop (no pass)
python research/eval_trail.py nsx_1m_scaled.pkl nq_1m_scaled.pkl      # the trailing lock for the evaluation (no pass)
python research/spike.py nsx_1m_scaled.pkl nq_1m_scaled.pkl           # skip spikes into the close (no pass)
```

The raw data isn't stored in this repo.
