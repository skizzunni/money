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

## Forty-third round: a better entry price, and a second chance

On 16 October 2026 the bot's four losing shorts were each stopped by a ~17.5-point bounce, then price went the signals' way. Fixed before running ([`research/better_entry.py`](../research/better_entry.py)): a limit 4.25 or 8.75 points better than the signal close for 2 minutes, then a market order if unfilled (so the runners still get in); or, after a max-loss stop, a stop order to re-enter at the stopped trade's price until the next check. Pass bar: win rate 3 points higher at no less money, t within 0.3, as before.

| 2011–2018, per contract at $35 | Win % | $/day | t |
|---|---|---|---|
| **v1.3** | **50.6%** | **$15.19** | **4.67** |
| Limit 4.25 better, then market | 43.8% | $2.01 | 0.66 |
| Limit 8.75 better, then market | 43.8% | $4.57 | 1.45 |
| Second chance | 48.2% | $8.54 | 2.53 |

**Failed, clearly.** The limit fills on the bounces that keep going, which are the losers; the re-entries after a stop-out lose again more often than not.

**Two facts for choosing settings, measured afterwards on 1-minute bars with v1.3's rules:**

- **With the lock, every size wins about half its trades.** Same $350 max loss: 10 MNQ 49%, 5 MNQ 52%, 3 MNQ 51% (index 2011–2026); fewer contracts buy evaluation odds (30% → 38% → 45% passes) and smaller losing stretches, not winners.
- **The lock trigger is the win-rate dial.** At 10 MNQ and $350:

| Lock trigger (×17.5 points) | Win % 2011–18 / 2019–22 / 2023–26 / NQ | $/day ×10 2011–18 / 2019–22 / 2023–26 / NQ |
|---|---|---|
| 1.0 (17.5 pts, the default) | 50.6 / 47.0 / 47.8 / 48.8 | $152 / $170 / $66 / $129 |
| 0.75 (13.1 pts) | 55.3 / 50.5 / 50.5 / 52.3 | $166 / $181 / $57 / $134 |
| 0.5 (8.75 pts) | 58.8 / 51.9 / 53.3 / 54.8 | $147 / $173 / $45 / $127 |

  0.75 wins 3–5 points more often in every period, makes more on three of four and has a smaller worst losing stretch on all four, but made 14% less on 2023–2026; 0.5 wins more still and made a third less on 2023–2026. The default stays at 1.0 (the lower trigger failed its pre-registered test in round thirty-nine); *Lock a small win* set to 0.75 is the choice for more winners.

## Why the win rate sits near half: the first minutes are a coin flip

**The S&P 500 at the signal** (HistData SPXUSD 1-minute, 2010 – Sep 2026, its own noise area computed the same way). v1.3's trades at 10 MNQ and $350, 2011–2018: when the S&P was also beyond its line in the same direction, 2,620 trades won 51.5% and made $79 each; when it was still inside its noise area, 1,736 trades won 48.6% and made $40 each. The unconfirmed trades still pay, so skipping them would cost about $69,000 over those eight years for one point of win rate. Not used.

**The geometry.** If price after the entry moved at random, a trade with a 17.5-point stop would reach +a points first with probability 17.5 / (17.5 + a). The lock dial (round forty-three) against that, 2011–2018:

| Lock trigger | Random walk | Measured |
|---|---|---|
| +17.5 points (v1.3) | 50.0% | 50.6% |
| +13.1 points | 57.1% | 55.3% |
| +8.75 points | 66.7% | 58.8% (fees and slippage cost the tiny wins) |

Over the first minutes after the bot's entry, price is indistinguishable from a coin flip; none of the facts tested at the signal (the S&P, a spike into the close, volume, time of day, waiting minutes, better limit prices) changes that. The win rate is set by where the lock sits against the stop; the profit comes from the half-hour trends the bot is built on, which show only over 30 minutes and more. More winners at the same money would need something that predicts the next few minutes; nothing measured here does.

## Forty-fourth round: drop the trades that lose on average

Dropping trades that lose on average raises winners and money together. Fixed before running ([`research/drop_losers.py`](../research/drop_losers.py)): no entries on monthly options-expiration Fridays (dealer hedging tends to pin the index); or, walk-forward, each year no entries at the half-hour checks that lost on average over all earlier years. Pass bar against v1.3 (1-minute bars, 10 MNQ, $350): win rate higher, $ per day no lower, t within 0.3, $ per day per dollar of worst stretch no lower.

| 2013–2018, per contract at $35 | Win % | $/day | t | Worst stretch |
|---|---|---|---|---|
| **v1.3** | **51.35%** | **$15.28** | **4.15** | **$1,548** |
| No options-expiry Fridays | 51.51% | $15.11 | 4.15 | $1,517 |
| Walk-forward checks | 51.49% | $15.95 | 4.54 | $1,704 |

**Neither passed**: both moved the win rate by about a sixth of a point, the first for less money, the second with a larger worst stretch. No day or check time stands out as a reliable loser either.

## Rounds forty-five and forty-six, and a second setup: more of the same coin flip

- **Time exits** ([`research/time_exits.py`](../research/time_exits.py), fixed before running): lock a trade that is 5+ points up after 10, 15 or 30 minutes, or close a trade that hasn't reached the lock after 10, 15 or 30 minutes. On 2011–2018 every variant landed within about a point of v1.3's win rate and $0.50 of its $ per day; none met the bar (win rate higher at no less money, t within 0.3, no worse stretch per dollar).
- **10:00 releases** ([`research/release_days.py`](../research/release_days.py)): v1.3's 10:00 entries on ISM days won 37–40% and lost money on 2011–2018 (39 trades), against 48.5% and +$94 on other days. But skipping the 10:00 entry on ISM days (and on consumer-confidence days) left the totals unchanged or lower even on 2011–2018: the bot then enters at 10:30, and those trades do no better.
- **A second setup in the bot's idle half hour: fade the opening gap** (enter against the gap at 09:31 with the 17.5-point stop, exit by 10:00; 2011–2018, every gap size): with a +8.75 target it wins 54–60% and loses 2–4 points a trade after fees; with +17.5, 47–51% and −0.5 to −1.8 points; with +26.25, 40–44% and about break-even. The same geometry as the bot's own entries: the first half hour gives no short-term edge either.

## Rounds forty-seven and forty-eight: the S&P

- **The same bot on MES** ([`research/mes.py`](../research/mes.py)), 10 contracts and $350: $35 a contract is 7 S&P points, about twice as wide against the noise as 17.5 Nasdaq points. On HistData SPXUSD 1-minute bars the bot has no edge on the S&P at this size: $4.84 a day on 2011–2018, $12.35 on 2019–2022 and −$80 on 2023–2026, against $152, $170 and $66 on MNQ. The edge is the Nasdaq's.
- **Lock the breakouts the S&P doesn't confirm earlier** ([`research/confirm_lock.py`](../research/confirm_lock.py)): every trade taken, but a signal the S&P did not confirm locks at 13.1 points instead of 17.5. Win rate +2.0 / +1.2 / +0.9 points on 2011–2018 / 2019–2022 / 2023–2026 and a smaller worst losing stretch in each, $ per day +6% / +7% / −1% (the last is $0.07 a day per contract, so it missed the bar); on NQ futures 2015–2025, +1.4 points and −2% $ per day. About a point of win rate for about the same money: not adopted.
- **Re-enter after a lock exit** (a stop order at the trade's lock trigger price, until the next check; a quick look at 2011–2018, simulator option `relock`): 47.2% winners and $7.31 a day against 50.6% and $15.19, worst stretch twice as large. The shake-outs are not followed by continuation more often than chance.

## Rounds forty-nine and fifty: the take-profit at $35, and a heads-up before the check

- **The take-profit, re-chosen walk-forward at 10 MNQ and $350 with the lock** ([`research/walkforward_tp35.py`](../research/walkforward_tp35.py)): each year the level with the best t-stat over all earlier years, from none and 1.0–3.0 noise units. The index picked 1.25 every year, NQ futures 1.5 in most; the stitched records tie fixed 1.5 ($135 and $125 a day ×10 against the same). 1.5 stays.
- **The heads-up (v1.4).** Each check's lines are known from the open, so five minutes before a check the script can see whether price is already past the line. On 2011–2018 (5-minute bars), when it was, a signal followed at the check 93–94% of the time; when it was inside, 3%; and 92% of all signals were already past the line five minutes earlier. With the position, the daily limit and the Fed rule taken into account (2017–2018), 89% of heads-ups were followed by that signal and 85% of signals had one. Placing orders by hand, each minute between the check and the fill cost 15–25% of the profit (round thirty-five); with the order prepared, the fill is seconds after the check. The heads-up is an alert and a dashboard note only, so the trades and the backtest don't change. On the real MNQ weeks from Yahoo (21 September – 16 October 2026, never used to build it): 45 heads-ups, 41 followed by that signal (91%), and 41 of the 45 signals had one; on 16 October all six shorts were flagged five minutes ahead.
- **Three more settings, walk-forward at 10 MNQ and $350** ([`research/walkforward_more.py`](../research/walkforward_more.py)): sessions in the noise average (10/14/20/30), the lock offset (1.25/2.5/5) and the daily loser limit (3/4/5/6). Each either picked v1.3's value nearly every year or did worse when it moved away (a 10-session lookback: +$9 a day on the index, −$15 on NQ futures and a far larger worst stretch). v1.3's settings are where the walk-forward lands.
- **The moving line stop at this size.** With $35 a contract the max loss is nearly always the closer stop: over 2011–2026 the line closed 51 of 8,315 trades (0.6%), and a bracket left alone all trade made $136 a day ×10 against $137 (NQ futures $127 against $129). The entry alert now says to leave the stop where it is when the max loss is the closer stop: one bracket, nothing to move.
- **Why evaluations fail at 10 MNQ and $350** (125-day window, 1-minute bars, v1.3): index 2011–2026 30% pass, 56% hit the $2,000 drawdown first, 13% reached $3,000 but were blocked by the 50% consistency rule (one take-profit day is $3,000–4,300 at this size) and then hit the drawdown, 1% time out; NQ futures 25% / 57% / 17% / 2%. (The index data's worst day, −$3,537 on 20 October 2011, is a 150-point jump inside one minute in the CFD data; the NQ futures' worst is −$1,532, in line with the 4-loser limit.)
- **A closer take-profit for the evaluation.** At 10 MNQ and $350, take-profit 1.25 against 1.5: $50K passes 34% / 36% / 27% against 32% / 32% / 23% on the index 2011–2018 / 2019–2022 / 2023–2026 and 28% against 25% on NQ futures, with smaller worst stretches on three of the four; but $ per day ×10 of 152 / 166 / 79 / 116 against 152 / 170 / 66 / 129, so 10% less on NQ futures. A trade-off, so 1.5 stays; *Take profit* 1.25 is the setting for someone who cares only about passing.
- **The Fed rule at this size** still helps: $138.5 against $137.1 a day ×10 on the index, $132.2 against $129.0 on NQ futures, with a higher t-stat and no larger worst stretch.

## Fifty-second round: a lock trigger scaled to the day's noise

The lock trigger as k × the check's noise (σ × price), kept between 8.75 and 17.5 points ([`research/lock_sigma.py`](../research/lock_sigma.py)): sooner on quiet days, the full 17.5 on volatile ones. On 2011–2018 every k met the bar (k = 0.15: 53.7% against 50.6% winners, $16.60 against $15.19 a day, t 5.19 against 4.67, $50K passes 36% against 32%). On 2019–2022, a volatile stretch where the trigger mostly sat at 17.5, it tied v1.3 ($17.03 against $17.04 a day, 47.6% against 47.0% winners) and so missed the bar; 2023–2026 was not looked at. Not adopted.

## Most trades profitable: the lock at 0.75

The user's aim, more than half the trades profitable without fewer trades. Descriptive, after rounds thirty-nine and forty-three (where the 13.1-point lock missed the pre-registered bars), at 10 MNQ and $350 on 1-minute bars (the broker's auto-breakeven):

| | Win % | $/day ×10 | t | Worst stretch ×10 | Trades/day | $50K pass |
|---|---|---|---|---|---|---|
| Index 2011–2026, lock at 17.5 (v1.5) | 49.0% | $137 | 5.76 | $34,973 | 2.19 | 30% |
| Index 2011–2026, lock at 13.1 | **53.0%** | **$145** | 6.33 | $31,513 | 2.28 | 31% |
| NQ futures 2015–2025, lock at 17.5 | 48.8% | $129 | 4.33 | $18,347 | 2.26 | 25% |
| NQ futures 2015–2025, lock at 13.1 | **52.3%** | **$134** | 4.63 | $16,454 | 2.37 | 28% |
| Index 2023–2026, 17.5 / 13.1 | 47.8% / 50.5% | $66 / $57 | 1.49 / 1.34 | $34,973 / $31,513 | | 23% / 20% |
| NQ futures 2023–2025, 17.5 / 13.1 | 48.5% / 50.9% | $66 / $63 | 1.26 / 1.25 | $16,682 / $16,454 | | 19% / 24% |

Over the whole histories the 13.1-point lock wins more than half its trades, makes more money with smaller losing stretches, and takes slightly more trades; over the last three years it still wins about half, for 5–14% less money. On the real MNQ weeks (5-minute bars, the chart's view): 48 trades, 46% winners, +$11,084, against 44, 43% and +$13,068. *Lock a small win* = 0.75 is the setting; the default stays at 1.0 because the recent years pay less.

Why the recent years pay less: where the two locks part ways, the 13.1-point lock saves about six stopped-out losers for every runner it cuts short, in 2011–2018 and in 2023–2026 alike (266 against 40; 76 against 12), but a cut runner is now worth more (a 2023–2026 target about $4,900 at 10 MNQ against about $3,400 before): +$96,490 against −$79,581 then, +$25,420 against −$35,693 now. A trigger between 13.1 and 17.5 set by the day's noise (13.1 on quiet days, 17.5 on volatile ones) slides along the same line: k = 0.15 gives 50.5% / 50.0% winners on the index / NQ futures with $142 / $130 a day ×10, k = 0.2 gives 49.6% / 49.3% with $139 / $129. More winners and more recent money trade against each other along one curve, and the lock trigger picks the point on it.

## Fifty-third round: the earlier lock only in the first minutes

On 2011–2018 the losers a 13.1-point lock saves hit it fast (77% within 5 minutes of the fill, median 3) and the runners it cuts later (55%, median 5). Rule, fixed before the tests ([`research/lock_early.py`](../research/lock_early.py)): for the first 5 (or 10) minutes the lock arms at 13.1 points, after that at 17.5. It passed 2011–2018 (54.2% against 50.6% winners, $16.43 against $15.19 a day) and 2019–2022 (49.8% against 47.0%, $17.63 against $17.04), then failed 2023 – Sep 2026 (49.8% against 47.8% winners but $5.53 against $6.64 a day). Every earlier lock tested so far gives up money on 2023–2026, where the trend days it cuts short are bigger.

## Fifty-fourth round: the noise from a median or a trimmed mean

The noise as the median of the 14 sessions, or their mean without the largest and smallest ([`research/noise_median.py`](../research/noise_median.py)), so one extreme day doesn't widen the lines for 14 sessions. The median made less on 2011–2018. The trimmed mean passed 2011–2018 and 2019–2022 and on 2023 – Sep 2026 made more ($7.29 against $6.64 a day) with more trades, but its worst losing stretch grew from $3,497 to $4,053, so it failed; on NQ futures 2015–2025 it made less ($11.73 against $12.90, and $2.56 against $6.65 on 2023–2025). The mean stays.

## Fifty-fifth round: a check every 15 minutes

Checks at every quarter hour, each with its own noise ([`research/checks15.py`](../research/checks15.py)), at 10 MNQ and $350 with the lock: on 2011–2018 2.80 trades a day against 2.27 and $16.47 against $15.19, but 49.8% winners against 50.6%, a t-stat of 4.51 against 4.67 and a worst losing stretch of $3,983 against $2,569. Failed: the extra quarter-hour trades add more swings than money.

## The lock dial, finely, and volume at the signal

- **Volume into the signal** (NQ futures 2015–2018, the last five minutes' volume against the same minutes' median over the previous 20 sessions, by fifths): winners 48.6% / 48.0% / 53.4% / 47.7% / 52.7%, with no order to it. No lead from volume either.
- **The lock trigger between 14 and 17.5 points** (descriptive, chosen after all the data was seen): at 14.9 points (*Lock a small win* 0.85) NQ futures 2015–2025 win 51.1% against 48.8% with $132 against $129 a day ×10 and a worst stretch of $16,377 against $18,347, and 2023–2025 50.1% against 48.5% with $67 against $66; the index 2011–2026 51.2% against 49.0% and $138 against $137; but the index 2023–2026 $49 against $66 (at 14.0 points $56, at 15.75 $48: noisy). On the real MNQ weeks from Yahoo (5-minute bars) 47 trades, 47% winners, +$11,452 against 44, 43%, +$13,068. The input now takes steps of 0.05; the default stays 1.0.

## Rounds fifty-six and fifty-seven: the clock

- **Checks off the half hour** ([`research/offset_checks.py`](../research/offset_checks.py)), each with its own noise: at :05/:35 $7.34 a day and 49.1% winners on 2011–2018, at :10/:40 $11.03 and 48.9%, against $15.19 and 50.6% at :00/:30. The half hours themselves matter.
- **By check, 2011–2018** (v1.3 at 10 MNQ and $350): entries from the hourly checks made about $95 a trade, those from the half-hour checks about $28. **Locking the half-hour entries at 13.1 points** and keeping 17.5 for the hourly ones ([`research/lock_half.py`](../research/lock_half.py)) passed 2011–2018 (52.7% against 50.6% winners, $15.70 against $15.19) and on 2019–2022 won 49.2% against 47.0% with a better t-stat and a smaller worst stretch, but made $16.98 against $17.04 a day, so it failed.

## Fifty-eighth round: lock the weak-trend breakouts earlier

One rule from rounds forty-eight and fifty-seven ([`research/weak_trend_lock.py`](../research/weak_trend_lock.py)): a trade from a half-hour check, or one the S&P did not confirm, locks at 13.1 points; an hourly, confirmed trade keeps 17.5; every trade taken. The best near-miss so far:

| Per contract at $35 | Win % | $/day | t | Worst stretch |
|---|---|---|---|---|
| Index 2011–2018, v1.5 / weak-trend lock | 50.6% / 53.9% | $15.19 / $16.16 | 4.67 / 5.08 | $2,569 / $2,491 |
| Index 2019–2022 | 47.0% / 49.6% | $17.04 / $18.15 | 3.24 / 3.54 | $2,453 / $2,246 |
| Index 2023 – Sep 2026 (final) | 47.8% / 49.6% | $6.64 / $7.00 | 1.49 / 1.62 | $3,497 / $3,232 |
| NQ futures 2015–2025 | 48.8% / 51.3% | $12.90 / $12.68 | 4.33 / 4.38 | $1,835 / $1,929 |
| NQ futures 2015–2018 / 2019–2022 / 2023–2025 | 50.1→53.9 / 47.7→49.6 / 48.5→50.3% | $13.69→14.26 / $16.13→15.38 / $6.65→6.09 | | |

It passed every index period, the final test included, then failed the NQ futures replication: more winners in every period, but 5–8% less money on 2019–2025 there. On the real MNQ weeks it tied ($13,101 against $13,068, 44% against 43% winners). Not adopted: on the real futures the recent years still pay a little less, the same trade as every earlier lock.

## Round fifty-nine: an Apex 25K evaluation

`research/apex25k.py`. The question: is $350 a trade too much on a 25K evaluation, where the trailing drawdown is
$1,000? Modelled on 1-minute bars with the bot itself (v1.6 rules, take-profit from the fill as the NinjaTrader
bracket places it, $1.24 fees and a tick of slippage): $1,500 target, $1,000 trailing drawdown, 30 calendar days,
up to 40 MNQ. Two plans: intraday trail (the threshold follows the highest equity, open profit included) and
end-of-day trail (set from the closing balance, plus a $500 daily loss limit that ends the day, not the
evaluation). Apex's rules as its help center is quoted in search results; the site refuses this machine. An
evaluation starts on every session. Pass bar, fixed before running: the best 30-day pass rate on 2011-2018 must beat
the current evaluation setting (3 MNQ, $350, 4 losers) by 5 points, with no more busts, on 2019 - Sep 2026 and on NQ
futures 2015-2025.

Pass / bust % within 30 days; the last three columns are for the bot alone, without the evaluation's limits.

| Setting | Data | End-of-day plan: pass / bust | Intraday plan: pass / bust | Days at -$500 | Days at -$1,000 | $ a day |
|---|---|---|---|---|---|---|
| 3 MNQ, $350, 4 losers (was the evaluation setting) | 2011-18 | 37.2 / 60.5 | 21.5 / 78.3 | 14.2% | 3.0% | 60 |
| | 2019-26 | 32.1 / 63.6 | 15.9 / 83.6 | 15.6% | 4.0% | 77 |
| | NQ futures | 36.2 / 61.3 | 19.3 / 80.7 | 15.7% | 3.9% | 67 |
| 3 MNQ, $250, 3 losers (end-of-day pick) | 2011-18 | 39.8 / 57.1 | 22.9 / 76.7 | 11.5% | 0.1% | 58 |
| | 2019-26 | 35.2 / 59.9 | 16.5 / 82.3 | 14.3% | 0.1% | 60 |
| | NQ futures | 37.6 / 58.7 | 19.1 / 80.8 | 14.2% | 0.0% | 54 |
| **3 MNQ, $200, 2 losers (now the evaluation setting)** | 2011-18 | 39.0 / 55.3 | 24.8 / 73.5 | 0.0% | 0.0% | 54 |
| | 2019-26 | 40.6 / 52.4 | 18.3 / 79.3 | 0.2% | 0.0% | 45 |
| | NQ futures | 38.0 / 57.0 | 21.4 / 78.0 | 0.0% | 0.0% | 43 |
| 2 MNQ, $100, 3 losers (intraday pick) | 2011-18 | 31.9 / 39.9 | 27.6 / 57.2 | 0.0% | 0.0% | 28 |
| | 2019-26 | 32.2 / 37.3 | 24.0 / 59.8 | 0.1% | 0.0% | 29 |
| | NQ futures | 31.3 / 42.7 | 24.2 / 65.2 | 0.0% | 0.0% | 23 |
| 10 MNQ, $350, 4 losers | 2011-18 | 36.4 / 63.6 | 7.8 / 92.2 | 29.5% | 14.5% | 149 |
| | 2019-26 | 27.3 / 71.0 | 3.8 / 95.7 | 29.0% | 15.2% | 130 |
| | NQ futures | 31.0 / 68.7 | 4.4 / 95.6 | 30.0% | 16.0% | 122 |

The rest of the time an evaluation times out (2 MNQ at $100 times out 26-31% of the time: too slow for 30 days).

Verdict: **no setting passed the bar.** The end-of-day pick beat the old setting by 3.1 and 1.4 points (5 needed); the
intraday pick passed 2019-26 (+8.1) and missed on NQ futures (+4.9). What the table does show, as description:

1. **$350 and 4 losers is too much for a $1,000 drawdown.** 3-4% of days would lose the whole drawdown in one day,
   and 14-16% would hit the end-of-day plan's $500 daily limit. At $200 and 2 losers no day reached -$1,000 and
   almost none -$500, and the pass rate is as good or slightly better on all three data sets, with fewer busts. The
   cost: it makes less a day (about $45-54 against $60-77 at 3 MNQ), which a 30-day evaluation absorbs. For a 25K account the evaluation side should be 3 MNQ, $200, 2 losers: a judgement call on risk (it
   wasn't the 2011-18 pick), not a test result. (The user then went back to 50K evaluations: round sixty.)
2. **Buy the end-of-day plan.** On the intraday plan open profit drags the threshold up, and every setting busts
   57-96% of attempts.
3. **10 MNQ doesn't fit a 25K account**: 4-8% pass on the intraday plan, 27-36% end-of-day, 15-16% of days at
   -$1,000. On a funded 25K account (same $1,000 drawdown) the funded setting carries that risk too.
4. Even the best setting passes about 4 attempts in 10 within 30 days. Plan for several attempts.

## Round sixty: an Apex 50K evaluation

`research/apex50k.py`: the user went back to 50K evaluations. Same simulation as round fifty-nine, with Apex's 50K
rules as 2026 reviews quote them: $3,000 target, $2,000 trailing drawdown, 30 calendar days with no resets (a
timeout is as lost as a bust), up to 60 MNQ; the end-of-day plan has a $1,000 daily loss limit, the intraday plan
none. Pass bar, fixed before running: the best 30-day pass rate on 2011-2018 must beat 3 MNQ, $350, 4 losers by 5
points, with no more busts, on 2019 - Sep 2026 and NQ futures 2015-2025.

| Setting (end-of-day plan) | Data | Pass / bust / timeout % | Days at -$1,000 | $ a day |
|---|---|---|---|---|
| 3 MNQ, $350, 4 losers | 2011-18 | 29.4 / 48.5 / 22.2 | 3.0% | 60 |
| | 2019-26 | 34.3 / 42.1 / 23.5 | 4.0% | 77 |
| | NQ futures | 32.2 / 46.6 / 21.2 | 3.9% | 67 |
| **6 MNQ, $300, 3 losers (now the evaluation setting)** | 2011-18 | 36.9 / 57.1 / 6.1 | 0.2% | 84 |
| | 2019-26 | 39.1 / 52.3 / 8.6 | 0.3% | 88 |
| | NQ futures | 38.2 / 57.8 / 4.1 | 0.0% | 68 |
| 8 MNQ, $280, 3 losers (the 2011-18 pick) | 2011-18 | 40.2 / 54.4 / 5.5 | 0.3% | 106 |
| | 2019-26 | 35.6 / 58.8 / 5.6 | 0.1% | 87 |
| | NQ futures | 36.2 / 60.8 / 3.1 | 0.0% | 81 |
| 10 MNQ, $350, 4 losers | 2011-18 | 39.1 / 59.6 / 1.3 | 14.5% | 149 |
| | 2019-26 | 36.3 / 60.7 / 3.0 | 15.2% | 130 |
| | NQ futures | 36.0 / 63.0 / 1.1 | 16.0% | 122 |

On the intraday plan every setting passes 12-28% and busts 57-96%. The best, 4 MNQ, $200, 3 losers (27.6% on
2011-18), failed the bar (2019-26: 24.0% against 25.0%).

Verdict: **no setting passed the bar.** The end-of-day pick (8 MNQ, $280, 3 losers) did worse than the old setting
on 2019-26 (+1.3 points) and NQ futures (+4.0), with more busts. Description, not a test result:

1. **Buy the end-of-day plan.** It passes 30-40% of attempts against 12-28% on the intraday plan.
2. **3 MNQ is too slow for a 30-day, $3,000 evaluation.** A fifth of its attempts run out of time, and with no
   resets a timeout costs the fee like a bust. 6 MNQ at $300 with 3 losers passed 4.8-7.5 points more often on all
   three data sets, almost never had a -$1,000 day, and 3 losers x $300 = $900 stays under the $1,000 daily limit.
   It busts more (52-58% against 42-48%) because it takes the risk the old setting left on the table as timeouts.
   It is now the evaluation setting: a judgement call, not a test result.
3. Every setting passes about 4 attempts in 10 at best. A 25K evaluation (round fifty-nine) passes about as often;
   the 50K is worth more once funded.
4. **The user had already bought the intraday plan.** There, every setting passes about a quarter of attempts. The
   best on average, 4 MNQ, $200, 3 losers (27.6 / 24.0 / 24.2% pass, 57-65% bust, no -$1,000 days), ties the old
   3 MNQ, $350, 4 losers (25.1 / 25.0 / 23.9%, 61-65% bust, 3-4% of days at -$1,000) on passing and has fewer
   blow-up days, so it is the intraday evaluation setting. 6 MNQ at $300 is worse there (20-24% pass, 74-77% bust).

| Setting (intraday plan) | Pass / bust / timeout %: 2011-18 | 2019-26 | NQ futures |
|---|---|---|---|
| **4 MNQ, $200, 3 losers (intraday evaluation setting)** | 27.6 / 57.2 / 15.2 | 24.0 / 59.8 / 16.2 | 24.2 / 65.2 / 10.6 |
| 3 MNQ, $350, 4 losers | 25.1 / 61.3 / 13.6 | 25.0 / 61.5 / 13.5 | 23.9 / 64.8 / 11.3 |
| 5 MNQ, $175, 4 losers | 27.0 / 62.8 / 10.2 | 22.7 / 65.5 / 11.7 | 22.7 / 71.3 / 6.0 |
| 6 MNQ, $300, 3 losers | 24.1 / 74.1 / 1.8 | 20.2 / 76.6 / 3.2 | 22.1 / 77.4 / 0.4 |
| 10 MNQ, $350, 4 losers | 17.7 / 82.3 / 0.0 | 14.0 / 84.4 / 1.6 | 14.2 / 85.8 / 0.0 |

## Round sixty-one: what a 50K account pays out

`research/apex_payouts.py` simulates the whole path with the bot on 1-minute bars: the 50K intraday-trail evaluation
at 4 MNQ, $200, 3 losers, then the funded Performance Account under Apex 4.0's payout rules as 2026 reviews quote
them ($2,000 drawdown trailing open profit until it locks at +$100, tiered daily loss limit, a payout after 5 days of
$200+, a balance of $52,600, no day over 50% of the profit, caps $1,500-$3,000, at most 6 payouts). Every session is a
start. Pass bar, fixed before running: the 2011-18 best must beat the funded setting then in use (10 MNQ, $350,
4 losers) by 10% on 2019-25 and NQ futures under all three payout-cap assumptions.

Expected payouts per evaluation bought (base caps; the evaluation passes 23-28% of the time):

| Funded setting | 2011-18 | 2019-25 | NQ futures 2015-24 | Funded accounts that bust | Payout per funded account per month alive |
|---|---|---|---|---|---|
| **4 MNQ, $200, 2 losers (now the funded setting)** | $862 | $552 | $550 | 79-83% | $306-356 |
| 4 MNQ, $140, 2 losers (the 2011-18 pick) | $1,054 | $673 | $355 | 72-88% | $241-350 |
| 3 MNQ, $350, 2 losers | $612 | $562 | $495 | 82-84% | $390-664 |
| 10 MNQ, $350, 4 losers (was the funded setting) | $672 | $172 | $337 | 81-94% | $341-407 |

Verdict: the 2011-18 pick (4 MNQ, $140, 2 losers) beat 10 MNQ by far on 2019-25 but only by 5% on NQ futures: **FAIL**.
Description: 10 MNQ paid the least per evaluation on 2019-25 because it busts the $2,000 drawdown before most payouts.
4 MNQ, $200, 2 losers had the best worst case of all 39 settings ($550 per evaluation, $397 under the low caps) and is
now the funded setting: a judgement call, not a test result. Most funded accounts end in a bust after one or two
payouts; what one pays in total averages about $1,750-3,100.

## Round sixty-two: more trades on quiet days (a fade inside the noise area)

`research/quiet_fade.py`. The user asked for more trades a week on one account. The bot trades on about 57% of days;
on the rest price stays inside the noise area. Idea: on those days fade a check that closes in the outer part of the
noise area (more than 0.5 or 0.75 noise units past the anchor, still inside the line), target the anchor or halfway,
stop where the bot itself would go in the other direction (the line + 0.24 sigma) or $200, 4 MNQ, flat at 16:00; ten
variants (bot not traded today / bot flat at the moment, one or two fades a day). Pass bar, fixed before running:
alone t >= 2, and bot + fade better than the bot alone in $ a day and in $ a day per $1k of worst losing stretch, on
2011-18, then 2019-26 and NQ futures.

| Bot alone → bot + the best fade (0.75, anchor, up to 2 a day) | Trades a week | Days with a trade | $ a day | 50K intraday evaluation pass / bust % |
|---|---|---|---|---|
| 2011-18 | 9.0 → 12.3 | 59% → 70% | 54.55 → 56.85 | 24.5 / 58.7 → 25.7 / 67.7 |
| 2019-26 | 8.3 → 11.4 | 55% → 65% | 49.57 → 37.48 | 23.0 / 59.3 → 21.5 / 70.8 |
| NQ futures 2015-25 | 8.8 → 12.1 | 57% → 68% | 40.58 → 24.71 | 22.4 / 63.4 → 19.4 / 76.3 |

**FAIL at every stage.** No variant made money on its own in any period (best on 2011-18: +$2.29 a day, t 0.30; all
lose on 2019-26 and NQ futures), they win 15-37% of the time: the outer part of the noise area doesn't revert. The
extra 3 trades a week cost money and add 9-13 points of busts to the evaluation. More trades only help when each one
has an edge.

## Rounds sixty-three to sixty-five: more money from the winners, on one 50K account

The user wants more per week from one account. The bot's profit comes from trend days, so three ways to press the
trades that are already winning, each with its pass bar fixed before running: the best 2011-18 variant must beat the
bot by 10% in expected payouts per 50K evaluation (round sixty-one's simulation, base caps) with no lower evaluation
pass rate, on 2019-26 and on NQ futures. 4 MNQ, $200 max loss, 1-minute bars, open profit counted minute by minute.

| Study | Best on 2011-18 | Payouts per evaluation, 2019-26 / NQ (bot: $439 / $317) | Evaluation pass %, 2019-26 / NQ (bot: 22.9 / 25.3) | Verdict |
|---|---|---|---|---|
| Pyramid: add contracts when the lock arms ([`pyramid.py`](../research/pyramid.py)) | add 2, stop at the lock | $300 / $333 | 22.0 / 22.3 | FAIL |
| Runner: half off at the take-profit, trail the rest ([`runner.py`](../research/runner.py)) | trail 1.0 noise unit | $473 / $295 | 21.1 / 24.5 | FAIL |
| Size ladder on profit and cushion ([`size_ladder.py`](../research/size_ladder.py)) | 6 MNQ from +$1,000 in the evaluation | $463 / $544 (flat 4: $553 / $550) | 18.9 / 20.6 | FAIL |

- **Pyramid:** most trades that reach the lock come back to it, so an add bought 25 points higher loses on most of
  them; winners fall from about 50% to 10-12% and evaluation busts rise 9-30 points.
- **Runner:** the half taken off at the take-profit gives up more than the runner earns; a 3.5-unit target for all
  contracts busts 71-79% of evaluations.
- **Ladder:** sizing up reaches the target sooner but busts more; in the funded account payouts are capped, so the
  extra size adds risk and no money. A funded 50K pays about $70-86 a week while it lasts, ladder or not.
- **The payout rules cap one Apex account**, whatever the strategy: at most 6 payouts of $1,500-$3,000 (about
  $13,000 in all), with at least 5 qualifying days between them.

## Round sixty-six: playing the Apex payout rules (one account, all 6 payouts)

`research/payout_policy.py`. The user's goal for one 50K account: all six payouts, as reliably and fast as possible.
The bot earns on a few big days, which collides with the 50% consistency rule and the five $200 days a payout needs.
Policies (24 combinations): a daily profit stop in the funded account (none, $400, $600, $900), a protect mode
(2 MNQ while the balance is at or above $52,600 and the next payout isn't taken yet), 3, 4 or 6 MNQ at a 25-point
cap; and a $1,000 daily profit stop in the evaluation. Pass bar, fixed before running: the best 2011-18 policy by the
chance an evaluation leads to all six payouts must beat the current setup by 25% (relative) on 2019-25 and NQ futures,
with no less paid per evaluation.

| Policy | Paid per evaluation, 2011-18 / 2019-25 / NQ | All six payouts, % of evaluations | At least one payout, % | Weeks from funded to the 6th payout |
|---|---|---|---|---|
| Current (4 MNQ, no stop) | $862 / $553 / $550 | 5.7 / 3.4 / 3.7 | 10.9 / 5.3 / 7.1 | 152 / 124 / 153 |
| 4 MNQ, protect mode (2011-18 best) | $1,034 / $573 / $631 | 7.1 / 3.6 / 4.3 | 12.4 / 6.0 / 7.1 | 156 / 143 / 159 |
| 3 MNQ, $900 daily profit stop, protect | — / $752 / $625 | — / 3.4 / 2.6 | — / 11.5 / 12.8 | — / 51-83 |

**FAIL**: protect mode raised the six-payout chance by 6% (2019-25) and 18% (NQ futures) against the 25% needed; the
evaluation profit stop lowered the pass rate. Description: under every policy only 3-7% of evaluations reach all six
payouts, and those take about 2½-3 years, because a funded account makes about $65-160 a week and the six payouts
add up to about $13,000. A $900 daily profit stop roughly doubles the chance of at least one payout; protect mode was
slightly better in all three periods.

## Round sixty-seven: the TradingView size on Apex (description)

`research/pine_size.py`. The user's TradingView run (10 MNQ, $1,170 max loss) made $6,000+ in a day in October 2026,
while the NinjaTrader settings (4 MNQ, $200) make about $270 a week. The same bot at each size, over 16 years, and on
the 50K intraday-trail evaluation and funded account (round sixty-one's simulation, base caps):

| Setting | $ a week, bot alone (2011-18 / 2019-25 / NQ) | Weeks at $1,500+ | Days at -$2,000 or worse | Worst week | 50K evaluation pass % | Paid per evaluation |
|---|---|---|---|---|---|---|
| 4 MNQ, $200 (NinjaTrader now) | $272 / $270 / $245 | 16-17% | 0% | -$2,782 | 23-28% | $550-862 |
| 10 MNQ, $1,170, 4 losers (TradingView) | $968 / $1,250 / $1,125 | 37-41% | 8-9% | -$28,467 | 12-16% | $74-223 |
| 10 MNQ, $1,170, 1 loser | $739 / $877 / $822 | 33-35% | 0-0.1% | -$25,668 | 13-16% | $104-256 |
| 10 MNQ, $350, 4 losers | $727 / $666 / $626 | 31-34% | 0% | -$5,413 | 15-18% | $32-398 |

The big size does what the user saw: it averages about $1,000-1,250 a week and makes $6,000+ on 2-3.5% of days. It
also loses $2,000 or more, a 50K account's whole drawdown, on about one day in twelve, and its worst weeks lose
$13,000-28,000. On Apex it passes the evaluation in a median of 2 sessions when it passes (12-16% of attempts), and
then the funded account almost always busts before a payout: 1-2% of evaluations are ever paid. The average week is
not the problem; the drawdown is.

## Round sixty-eight: the bot on gold, silver, crude oil and the euro

`research/other_markets.py`: the same v1.6 rules on other markets Apex trades on the same account, each in its own
regular hours (gold and silver 08:20-13:30, crude 09:00-14:30, euro 08:20-15:00 New York), $200 max loss, contracts
set before looking at P/L so the stop sits as far from price in noise units as the Nasdaq bot's (8 MGC, 3 SIL, 17 MCL,
20 M6E). HistData 1-minute data (crude has no files for January 2024 - May 2026). Pass bar, strict because four
markets were tried: t >= 2.5 on 2011-18 alone, then t >= 1.5 on 2019-26, then a better 50K account combined.

| Market | $ a day 2011-18 / 2019-26 | t | Trades a week | Winners |
|---|---|---|---|---|
| Nasdaq, 4 MNQ (for reference) | 55.75 / 56.05 | 4.02 / 3.76 | 9.4 / 8.9 | 51% / 50% |
| Gold | 19.71 / 2.27 | 1.74 / 0.20 | 6.0 / 6.2 | 10% |
| Silver | 10.14 / -41.21 | 0.78 / -3.68 | 7.8 / 7.7 | 43-47% |
| Crude | -54.51 / -37.44 | -5.14 / -2.78 | 7.2 / 6.5 | 7-9% |
| Euro | -134.11 / -117.79 | -19.2 / -16.9 | 7.9 / 7.4 | 38-40% |

**FAIL**: no market passed the first stage. At a $200 stop these markets need many contracts, and fees plus a tick of
slippage cost $26 (gold) to $75 (euro) a trade against about $7 on 4 MNQ. The edge is the Nasdaq's.

## Round sixty-nine: other markets as cues for the Nasdaq (lead-lag scan)

`research/leadlag.py`. Trading the Nasdaq only, with other markets as cues: at every half-hour check 10:00-15:30, the
last 5, 15, 30, 60 minutes' and the since-09:30 move of gold, silver, crude oil, the euro, the yen, the dollar index,
the DAX, the Nikkei and the S&P, and the Nasdaq-minus-S&P move (50 features), each traded with or against its move,
held 30 minutes or to the close, when the move is in its own top 30% of the past year: 200 rules, $1.24 and a tick a
side on MNQ. Protocol fixed before running: Benjamini-Hochberg at q = 0.05 on 2011-18, then one look at 2019-26, then
NQ futures. **0 of 200 survived the first stage**; the best (the Nasdaq-minus-S&P 30-minute move, to the close) had
p = 0.043, where about 10 of 200 would by chance. Other markets' recent moves don't predict the Nasdaq's next half
hour beyond chance.

## Round seventy: new price-action cues at the signal

`research/cues.py`. 34 cues from the Nasdaq's own price at the moment of each of the bot's signals, none of them in
round eighteen: distance to yesterday's high, low and close, the prior week's and the overnight high and low, round
100- and 250-point levels, gap filled or not (11 level cues); the signal bar's body, close position, size and the bars
before it (8); repeat breakouts, time since the day's extreme, the opposite line already hit, the previous trade's
result (9); month turn, Monday/Friday, the day after a big day, the opening range agreeing (6). The bot's own trades at
4 MNQ, $200 (3,662 on 2011-18). Protocol fixed before running: Benjamini-Hochberg at q = 0.05 on 2011-18, then one
look at 2019-26, then NQ futures.

One cue survived 2011-18: trades whose 5-minute signal bar closed in its far quarter made -$1.98 against +$46.95
(t -3.48). On 2019-26 the difference was gone ($29.82 against $31.92, t -0.12). **No survivor.** What is visible at the
moment of the signal doesn't tell the winners from the losers, as in round eighteen.

## Round seventy-one: classic intraday setups on MNQ

`research/setups.py`. 24 rules in 9 families none of the earlier rounds tested: Crabel NR7/NR4, inside day,
initial-balance breakout, opening drive, gap and go, prior-day high/low breakout, three-day trend, lunch reversal, VWAP
band fade; $1.24 and a tick a side, stop first when a bar reaches both. Protocol fixed before running:
Benjamini-Hochberg at q = 0.05 on 2011-18 (best p needed <= 0.0021), then 2019-26, then NQ futures.

**0 survivors** at the first stage; the best was gap and go (gap at least 1.0x its 14-day average, first 5 minutes
continuing it, in at 09:35, stop at the open, out at 10:29): t 2.78, p 0.005. Description, not a pass: gap and go was the
only family positive in all three data sets in all four variants (gap at least 0.5x, held to the close: t 2.0 / 3.4 /
3.5 on 2011-18 / 2019-26 / NQ futures, $54 and $42 a trade on the last two, 18-23% winners, about 1.3 trades a week).
VWAP band fades lose everywhere (t -2.1 to -2.5). Gap and go gets its own confirmation test (round seventy-two).

## Round seventy-two: gap and go, confirmed on other indexes?

`research/gap_go_confirm.py`. Round seventy-one's gap and go (gap at least 0.5x its 14-session average, the first 5
minutes continuing it, in at the 6th minute, stop at the open, out at the close) was picked from 24 rules, so the
Nasdaq's own years were used up. The same rule, unchanged, on markets it was never tuned on, 2011 - Sep 2026, costs
as a share of price equal to MNQ's. Pass bar fixed before running: t >= 2.0 in at least 2 of 3 markets, none at
t <= -2.0.

| Market | Trades a year | $ a trade (one MNQ-sized position) | t | t 2011-18 / 2019-26 | Winners |
|---|---|---|---|---|---|
| S&P 500 | 56 | +$14.32 | 1.81 | 0.41 / 2.08 | 15% |
| DAX | 74 | +$20.19 | 2.36 | 2.68 / 0.40 | 15% |
| Nikkei 225 | 48 | +$23.21 | 1.76 | -0.58 / 2.19 | 18% |

**FAIL** (1 of 3 at t >= 2). All three are positive, none consistent across both halves: a weak momentum tilt at the
open, not strong enough to trade. Not added.

## Round seventy-three: jobs-report days

`research/macro_days.py`, dates in [`nfp_dates.csv`](../research/nfp_dates.csv) (derived from BLS's published rule, the
third Friday after the week with the 12th, checked against the 15 dates that could be confirmed; bls.gov and FRED
refuse this machine; CPI dropped for want of a source). The bot at 4 MNQ, $200 on jobs-report days and other days:

| Period | Report days: $ a day (days) | Other days | Winners, report / other |
|---|---|---|---|
| 2011-18 | $167.67 (84) | $49.22 | 47.9% / 46.6% |
| 2019-26 | $119.64 (79) | $43.41 | 41.0% / 43.5% |
| NQ futures 2015-25 | $108.60 (112) | $39.14 | 45.0% / 44.1% |

Four rules, protocol fixed before running (Benjamini-Hochberg on 2011-18, then 2019-26, then NQ futures): 2x size on
report days (t 1.84 / 1.30 / 1.71), skip them (the mirror), a 1.25x wider noise area (t -1.69 / -0.72 / -0.98), a
10:00 trade in the direction of the 08:30-10:00 move (t 1.28 / -0.80 / -0.08). **No survivor.** Description: the bot
makes about 2.5-3.4 times its usual $ a day on jobs-report days, in the same direction in all three data sets; with
about 12 such days a year the evidence stays under the bar. A replication on other scheduled releases follows.

## Round seventy-four: do other scheduled releases replicate the jobs-report days?

`research/news_days.py`, dates in [`ism_dates.csv`](../research/ism_dates.csv) (ISM manufacturing, the first business day
of the month; January excluded, its release day varies) and `fomc_dates.csv`; jobs-report days left out of every group.
Pass bar fixed before running: the bot earns more on ISM days and on FOMC days than on days without news in all three
periods, and a pooled one-sided t >= 2.0 for at least one.

| Period | ISM days | FOMC days | Jobs-report days | No news |
|---|---|---|---|---|
| 2011-18 | $124.01 (79) | $36.57 (64) | $149.71 (93) | $50.51 |
| 2019-26 | $64.04 (76) | -$33.50 (59) | $99.49 (87) | $44.46 |
| NQ futures 2015-25 | $94.01 (107) | -$10.77 (82) | $103.44 (120) | $40.37 |

**FAIL**: ISM days lean the jobs-report way (t 0.83 pooled), FOMC days go the other way. "News days make trend days" is
not a rule to size on.

## Round seventy-five: the near-misses of round seventy, on data they hadn't seen

`research/cue_replicate.py`. Round seventy's three near-misses, definitions unchanged, pass bar fixed before running
(Bonferroni for 3: the predicted sign with t >= 2.4 on index 2019-26 and t >= 1.5 on NQ futures 2019-25), as the daily
P/L difference against the bot alone:

| Rule | t 2011-18 | t 2019-26 | t NQ 2015-25 | t NQ 2019-25 | Verdict |
|---|---|---|---|---|---|
| B8: 2x size when the signal bar's wick against the trade is over half its range | 4.46 | 3.40 | 3.85 | 2.42 | **PASS** |
| B3: skip oversized signal bars | 1.42 | -1.94 | -0.75 | -1.23 | FAIL |
| C3: skip the last trading day of the month | 1.29 | -0.10 | 0.53 | -0.48 | FAIL |

**The first cue in these rounds to hold on data it hadn't seen.** For a long, the 5-minute bar that closes above the
line has closed in the lower half below its high (the mirror for a short); it is known when the bar closes, before the
entry fills. Checked independently on the 5-minute bars the NinjaTrader strategy trades (4 MNQ, $200):

| Data | Wick trades | Other trades | Wick trades' share of the profit |
|---|---|---|---|
| Index 2011-18 | 42% of trades, $49 a trade, 49% winners | $15, 45% | 70% |
| Index 2019-26 | 39%, $53, 46% | $14, 42% | 70% |
| NQ 2015-18 | 42%, $52, 48% | $7, 44% | 84% |
| NQ 2019-25 | 40%, $31, 46% (t 0.91 on this slice) | $15, 41% | 58% |

## Round seventy-six: sizing the wick trades on a 50K Apex account

`research/wick_size.py`. Only the contracts change (wick / other trades, the same 25-point cap), on the 50K
intraday-trail evaluation and funded account. Adoption bar fixed before running: more paid per evaluation than 4 / 4 in
all three periods, with no lower pass rate.

| Split (wick / other) | Paid per evaluation, 2011-18 / 2019-25 / NQ | Evaluation pass % | $ a week, bot alone |
|---|---|---|---|
| 4 / 4 (now) | $862 / $553 / $550 | 27.5 / 22.9 / 25.3 | $272 / $270 / $245 |
| 6 / 2 | $1,113 / $315 / $713 | 27.9 / 15.5 / 19.6 | $338 / $302 / $267 |
| 8 / 2 | $1,078 / $101 / $324 | 24.4 / 13.9 / 18.4 | $438 / $386 / $339 |
| 6 / 0 | $649 / $172 / $494 | 24.3 / 14.3 / 15.6 | $302 / $251 / $217 |
| 10 / 2 | $851 / $103 / $299 | 22.8 / 12.2 / 15.7 | $539 / $470 / $412 |

**None adopted.** Size on the wick trades raises the bot's weekly $ (up to $412-539 a week at 10 / 2), but fewer,
bigger trades make the path rougher, and on a $2,000 trailing drawdown the evaluation busts more: on 2019-25 every split
passes less often and pays less than 4 / 4. The cue is real; turning it into size doesn't fit this drawdown.

## Round seventy-seven: managing wick trades and the rest differently

`research/wick_manage.py`. 4 MNQ, $200 for every trade; only the management changes with the wick cue (round
seventy-five). Adoption bar as round seventy-six. Pass % / paid per evaluation:

| Variant | 2011-18 | 2019-25 | NQ 2015-24 |
|---|---|---|---|
| E0 the bot | 27.5 / $862 | 22.9 / $553 | 25.3 / $550 |
| E1 wick trades take-profit 2.5 | 24.0 / $604 | 20.0 / $369 | 20.6 / $277 |
| E2 other trades take-profit 0.75 | 24.9 / $965 | 21.7 / $487 | 22.6 / $462 |
| E3 E1 + E2 | 21.9 / $715 | 17.1 / $293 | 17.7 / $387 |
| E4 other trades lock at +0.5 | 27.8 / $817 | 21.9 / $638 | 21.3 / $342 |
| E5 other trades by a limit at mid-bar | 23.7 / $509 | 17.6 / $416 | 23.4 / $437 |

**None adopted.** E4 raises winners to 54-57% but pays less on two of three periods.

## Round seventy-eight: trade only when the bot's own recent results are good

`research/regime_filter.py`. The bot runs virtually all the time; the account trades live only when its virtual
results over past sessions are good. Adoption bar as round seventy-six. Pass % / paid per evaluation / $ a week:

| Variant | 2011-18 | 2019-25 | NQ 2015-24 |
|---|---|---|---|
| R0 the bot | 27.5 / $862 / $272 | 22.9 / $553 / $270 | 25.3 / $550 / $245 |
| R1 last 10 sessions > 0 | 21.5 / $848 / $194 | 15.2 / $173 / $63 | 17.2 / $199 / $130 |
| R2 last 20 > 0 | 19.7 / $726 / $171 | 16.6 / $375 / $154 | 18.2 / $280 / $119 |
| R3 last 5 > 0 | 20.9 / $313 / $166 | 11.2 / $128 / $53 | 13.4 / $27 / $50 |
| R4 4 MNQ when last 10 > 0, else 2 | 22.5 / $979 / $233 | 17.7 / $321 / $166 | 22.3 / $423 / $188 |
| R5 sit out after 3 losing days | 25.1 / $827 / $221 | 20.1 / $731 / $191 | 22.3 / $356 / $156 |

**None adopted.** The filters cut busts but sit out the trend days that pay; the bot's streaks don't predict its next
days.

## Round seventy-nine: all 34 cues in one walk-forward model

`research/trade_model.py`. Logistic (C 0.1) and ridge (alpha 10) on round seventy's 34 cues per trade, trained on
earlier years only and scored year by year (index 2015-26, NQ futures 2015-25); trades sized 6 / 4 / 2 MNQ by the
predicted tercile (cut-offs from the training years). Adoption bar fixed before running: top tercile beats bottom with
t >= 2 out of sample on both, and more paid per evaluation with no lower pass rate.

Out of sample: AUC 0.523-0.528; winners 52.9% / 52.2% / 48.0% (index) and 52.9% / 52.1% / 48.3% (NQ) by tercile;
top vs bottom t 0.91 (index), 0.38 (NQ). Sizing by tercile: evaluation pass 25.0% -> 18.2% (index), 23.5% -> 19.9%
(NQ). **FAIL**: the cues tilt the odds by 4-5 points, too little to size on a $2,000 trailing drawdown.

## Round eighty: the session after mega-cap earnings

`research/earnings_days.py`, dates in [`megacap_earnings.csv`](../research/megacap_earnings.csv) (SEC EDGAR 8-K item 2.02
filings of Apple, Microsoft, Nvidia, Amazon, Alphabet, Meta, Tesla and Broadcom, 2011-2026; the reaction session is
the filing day if accepted before 09:30 New York, else the next session). Jobs-report days left out. Pass bar fixed
before running: higher on reaction sessions in all three periods and t >= 2.0 on 2019-26.

| Period | Reaction sessions | $ a day after earnings | Other days | t |
|---|---|---|---|---|
| 2011-18 | 204 | $95.07 | $43.56 | 1.05 |
| 2019-26 | 161 | $114.89 | $36.27 | 1.23 |
| NQ futures 2015-25 | 243 | $67.80 | $35.52 | 0.72 |

**FAIL** on t. The same pattern as jobs-report days (round seventy-three): the bot makes about 2-3 times its usual $ a
day after mega-cap earnings in every period, too noisy to prove with this many days.

## Round eighty-one: the NinjaTrader strategy on a 1-minute chart

`research/chart_minutes.py` (description). The strategy acts on bar closes: on a 5-minute chart the lock arms only when
the 5-minute bar closes; on a 1-minute chart, within the minute (the engine is the same; its 1-minute parity with the
Python bot is in tests/test_ninjatrader.py). At the account's settings (4 MNQ, $200, 3 losers), 5-minute bars built
from the same 1-minute data, evaluation as round sixty:

| Data | Chart | Winners | $ a week | Worst losing stretch | 50K evaluation pass / bust % |
|---|---|---|---|---|---|
| 2011-18 | 5-minute | 46.5% | $258 | $11,118 | 24.1 / 64.5 |
| | **1-minute** | **51.3%** | **$272** | **$10,957** | **26.2 / 59.0** |
| 2019-26 | 5-minute | 43.4% | $240 | $17,058 | 20.1 / 68.1 |
| | **1-minute** | **49.9%** | **$269** | **$13,357** | **21.6 / 63.6** |
| NQ futures 2015-25 | 5-minute | 44.1% | $194 | $15,275 | 21.5 / 70.2 |
| | **1-minute** | **50.6%** | **$224** | **$11,890** | **22.7 / 67.0** |

The 1-minute chart is better on every measure in every period: 5-7 points more winning trades, 5-16% more a week,
smaller losing stretches, more passes and fewer busts. The guide and the strategy now say to use it. (All the Apex
simulations of rounds fifty-nine to eighty already used the 1-minute engine.)

## Rounds eighty-two and eighty-three: the lock, tuned for the Apex account

`research/lock_apex.py`: twelve locks (arm at 0.5, 0.75, 1.0, 1.25 max loss; stop to entry + 2.5, 6.25, 12.5 points),
4 MNQ, $200, 1-minute bars, the same lock in the evaluation and funded account. Adoption bar fixed before running: the
2011-18 best by payouts per evaluation beats the current (1.0, +2.5) by 10% on 2019-25 and NQ futures with no lower
pass rate. The 2011-18 best (0.5, +6.25) paid 20% and 30% more but passed fewer evaluations (19.2% vs 22.9%, 20.5% vs
25.3%): **FAIL**. Arming at 0.5 raised winners to 57-63% and cut evaluation busts by 6-12 points, but fewer
evaluations reached $3,000 within 30 days.

`research/lock_split.py` (description: chosen after seeing round eighty-two): the current lock in the evaluation, an
earlier one on the funded account only, so the pass rate is unchanged.

| Funded lock | Paid per evaluation, 2011-18 / 2019-25 / NQ | Funded winners | Funded accounts that bust | Weeks to the 1st payout |
|---|---|---|---|---|
| 1.0, +2.5 (was) | $862 / $553 / $550 | 50-52% | 79-83% | 5-8 |
| **0.5, +6.25 (now)** | **$1,135 / $585 / $628** | **58-63%** | **69-80%** | 8-11 |
| 0.5, +2.5 | $1,322 / $520 / $474 | 58-63% | 64-85% | 8-10 |
| 0.75, +2.5 | $809 / $681 / $348 | 54-57% | 80-89% | 7-9 |

(0.5, +6.25) is better than the old funded lock in all three periods on payouts per evaluation, winners and busts; the
first payout comes 2-3 weeks later. The NinjaTrader strategy's funded side now uses it: a judgement call, not a test.

## Round eighty-four: the evaluation's lock and size together

`research/eval_lock_size.py`. The earlier lock cut evaluation busts but ran out of time; more size makes the target
faster. 4, 5 or 6 MNQ (25-point cap) x lock (1.0, +2.5), (0.5, +2.5), (0.5, +6.25), in the evaluation only; the funded
account as the strategy trades it now. Adoption bar fixed before running: the 2011-18 best by pass rate beats the
current one by 2 points on 2019-25 and NQ futures with no lower payouts.

| Evaluation | Pass / bust / timeout %, 2011-18 | 2019-25 | NQ 2015-24 | Paid per evaluation |
|---|---|---|---|---|
| 4 MNQ, 1.0 / +2.5 (now) | 27.5 / 57.3 / 15.2 | 22.9 / 59.1 / 18.0 | 25.3 / 64.4 / 10.2 | $1,135 / $585 / $628 |
| 5 MNQ, 0.5 / +6.25 (2011-18 best) | 29.0 / 55.1 / 15.9 | 22.3 / 64.8 / 12.9 | 23.8 / 64.9 / 11.3 | $1,721 / $695 / $835 |
| 4 MNQ, 0.5 / +6.25 | 26.6 / 42.9 / 30.5 | 19.2 / 50.6 / 30.1 | 20.5 / 50.3 / 29.2 | $1,406 / $667 / $715 |

**FAIL**: the pick passes 0.6 and 1.5 points less often on 2019-25 and NQ. It pays more per evaluation in all three
periods, but with the funded account unchanged that difference comes from which days the passes land on, not from the
evaluation itself; the pass rate is the clean measure, and it doesn't improve. The evaluation stays as it is.

## Round eighty-five: a trailing stop instead of the lock, for the intraday-trail evaluation

`research/trail_intraday.py`. On an intraday trailing drawdown the threshold follows open-profit peaks, so the lock's
giveback costs cushion. Five trailing stops (activate at A points, trail B behind the best price) against the fixed
lock in the evaluation, 4 MNQ, $200; the funded account as the strategy trades it. Bar fixed before running (pass rate
+2 points on 2019-25 and NQ, payouts no lower). Pass / timeout % / paid per evaluation:

| Evaluation exit | 2011-18 | 2019-25 | NQ 2015-24 |
|---|---|---|---|
| Fixed lock (now) | 27.5 / 15 / $1,135 | 22.9 / 18 / $585 | 25.3 / 10 / $628 |
| Trail 25 / 22.5 | 19.2 / 47 / $594 | 18.8 / 46 / $390 | 16.7 / 45 / $426 |
| Trail 37.5 / 25 | 22.5 / 36 / $900 | 23.3 / 38 / $689 | 16.8 / 34 / $498 |
| Trail 12.5 / 10 | 11.3 / 72 / $347 | 9.1 / 72 / $276 | 4.7 / 77 / $105 |

**FAIL**: the fixed lock had the best 2011-18 pass rate of all six. Trailing halves the busts but cuts the trend days
that reach $3,000; a third to three quarters of evaluations then run out of time.

## Round eighty-six: more checks on news days

`research/news_checks.py`. On jobs-report days and the sessions after mega-cap earnings (rounds seventy-three and
eighty), V1 checks every 15 minutes, each quarter hour with its own noise; V2 allows one more loser. Every other day as
now. Bar fixed before running: pass rate no lower and payouts per evaluation higher in all three periods.

| Variant | Evaluation pass % (2011-18 / 2019-25 / NQ) | Paid per evaluation | $ a week |
|---|---|---|---|
| Now | 27.5 / 22.9 / 25.3 | $1,135 / $585 / $628 | $272 / $270 / $245 |
| V1 15-minute checks on news days | 28.4 / 25.1 / 27.3 | $1,141 / $577 / $579 | $295 / $283 / $263 |
| V2 one more loser on news days | 26.9 / 23.1 / 24.8 | $1,123 / $446 / $490 | $269 / $259 / $242 |

**FAIL** for both. V1 passes more evaluations (+0.9 to +2.2 points) and makes more a week in all three periods, but paid
1.5% and 8% less per evaluation on 2019-25 and NQ. Not adopted: it needs the coming earnings dates entered by hand, and
the gain is small.

## Round eighty-seven: the first payout within two weeks of being funded

`research/fast_payout.py`. A funded 50K intraday-trail account from every session, up to 10 sessions: 360 policies
(4-10 MNQ at a 25-point cap, a daily profit stop of $400-$1,000 or none, a daily loss stop of $500, $800 or none, 1-3
losers, two locks). Apex's first payout needs 5 days of $200+, +$2,600 and no day above half the profit. Pick and bar
fixed before running.

| Policy | Paid within 10 sessions, 2011-18 / 2019-25 / NQ | Busted within 10 | Paid within 20 |
|---|---|---|---|
| 10 MNQ, stop the day at +$800 or -$800, 3 losers, lock 0.5 / +6.25 (the 2011-18 pick) | 8.1% / 6.5% / 5.5% | 33-36% | 22-28% |
| 10 MNQ, stop at +$800, 3 losers, lock 1.0 / +2.5 (best on 2019-25 and NQ) | 7.7% / 9.8% / 7.0% | 43-49% | 22-26% |
| 4 MNQ, no stops (the funded setting now) | 0.0% / 0.2% / 0.0% | 11-16% | 2-6% |

**NOT ADOPTED**: no policy pays within two weeks more often than it busts; the best pays within two weeks in fewer than
one start in ten. The binding rule is the five $200 days: the bot trades on about 57% of days, ends 22% of days up
and 34-35% down, and only 11-16% of days $200 or more up (4 to 10 MNQ), so five such days rarely come inside ten
sessions, whatever the size: its profit comes from a few big days, not from many green ones. The fastest policies are a
coin flip with the account within four weeks, and two weeks is out of reach for this strategy under these rules.

## Round eighty-eight: more $200 days

`research/green_days.py`. The bot bent toward many +$200 days (Apex's qualifying days): 6, 8 or 10 MNQ at a 25-point
cap, take-profit 0.25, 0.5 or 1.5 noise units, a +$250 daily profit stop or none, 2 or 3 losers (36 variants).

- A closer take-profit raises the share of $200 days only to about 20% (from 11-16%) and costs money; the best for the
  two-week payout race (10 MNQ, take-profit 0.25, 3 losers) paid within 10 sessions 2.0-2.6% of starts and busted
  about 60%: worse than round eighty-seven.
- A +$250 daily profit stop makes green days (36-46%) outnumber red days (13-20%), but every variant loses money
  (-$1 to -$27 a day): it caps the big days that pay for the losers. (Ten such days can't reach +$2,600 either.)

**FAIL**: a winning-streak shape at the day level costs this strategy its edge.

## Round eighty-nine: tight daily loss stops for the two-week payout

`research/tight_day_stops.py`. 6-10 MNQ, a daily loss stop of $250 or $350, a profit stop of $500-$800, 2 or 3 losers,
both locks (72 policies), as round eighty-seven. The pick (10 MNQ, +$800 / -$350, lock 0.5 / +6.25) paid within 10
sessions 3.3% / 2.9% / 1.4% of starts (2011-18 / 2019-25 / NQ), busting 13-16% within 10 and about 36-49% within 20:
**FAIL** (round eighty-seven's pick paid 6.5% / 5.5%). Tight loss stops keep the account alive longer but cut the
days that reach the payout.

## Round ninety: profit uncapped, only losses capped

`research/loss_only.py` (description). The user's rule: no daily profit stop, only a daily loss stop ($250, $350,
$500, $800 or none), 4-10 MNQ, 2 or 3 losers, both locks. The funded account's first payout:

| Best by "paid within 20 sessions" | Paid within 10 | within 20 | within 40 | Busted within 40 |
|---|---|---|---|---|
| 4 MNQ, no loss stop (or $800), 3 losers, lock 1.0 / +2.5 (2011-18 / 2019-25 / NQ) | 0.8 / 0.8 / 0.5% | 11.1 / 6.9 / 7.0% | 25.6 / 21.8 / 22.1% | 63-67% |

With profit uncapped, a payout within two weeks almost never happens (under 1% of starts at any size or loss stop):
the bot's profit comes in big days, and Apex's 50% consistency rule then blocks the request until enough smaller green
days dilute the big one. Bigger size only adds busts. A daily loss stop changes little.

## Round ninety-one: a dynamic daily profit cap for the 50% consistency rule

`research/dynamic_cap.py`. A day's profit is at most half the cycle's when it is at most the cycle's profit before it.
So on the funded account the bot may make up to max(floor, profit since the last payout) a day, then stops; big days
stay allowed once the cycle can absorb them. Floors $400, $600, $900 or no cap, 4 or 6 MNQ; evaluation unchanged. Bar
fixed before running (the 2011-18 best by payouts per evaluation beats no cap by 10% in payouts and in payouts within
40 sessions on 2019-25 and NQ).

| Funded | Paid per evaluation, 2011-18 / 2019-25 / NQ | First payout within 20 sessions | within 40 | Busted within 40 |
|---|---|---|---|---|
| 4 MNQ, no cap (now) | $1,135 / $585 / $628 | 5.5 / 2.2 / 1.7% | 23.3 / 14.7 / 12.2% | 47 / 54 / 53% |
| 4 MNQ, floor $900 | $678 / $867 / $499 | 6.2 / 6.7 / 4.0% | 25.6 / 29.6 / 23.8% | 42 / 40 / 45% |
| 6 MNQ, floor $600 | $427 / $348 / $318 | 11.9 / 16.5 / 11.2% | 29.3 / 35.0 / 30.0% | 60 / 51 / 56% |

**NOT ADOPTED** (the 2011-18 pick was no cap). Description: the dynamic cap roughly doubles the chance of a first
payout within 40 sessions (8 weeks) and, at 4 MNQ with a $900 floor, lowers busts in all three periods, but pays less
over the account's life in two of three; at 6 MNQ it pays sooner still and much less in total. A faster first payout
and more total payouts pull against each other.

## Round ninety-two: a different strategy, intraday trend pullbacks

`research/trend_pullback.py`. 24 rules: a trend-day qualifier at 10:30 or 11:00 (80% of minutes above the day's average
price and a fresh high, or a strong first hour), then buy pullbacks to the 5-minute 9- or 20-period EMA (the mirror for
downtrends), stop beyond the pullback or 25 points, 2R or a trailing exit, $300 risk a trade up to 10 MNQ. Protocol
fixed before running: Benjamini-Hochberg on 2011-18, then 2019-26, then NQ futures.

**0 survivors** (best p 0.004, needed 0.0021): the 9-EMA pullback with a swing stop and trailing exit made $15-25 a day
(t 2.2-2.9) at 40% winners, 21% green days and 27% red; 10 of 24 rules lose. Like the bot, it makes its money from a
few trend days, and it is no stronger than the bot.

## Round ninety-three: trade with the multi-day trend

`research/trend_filter.py`. Trend from completed sessions only: the previous close vs its 20- or 50-session average,
both agreeing, or the 20-session average's 5-session slope. Rules: with the trend only, or 6 MNQ with it and 2
against. Bar fixed before running (the 2011-18 best by payouts per evaluation beats the bot by 10% on 2019-25 and NQ
with no lower pass rate).

Trading only with the trend keeps 39-48% of the trades and **doesn't raise the share of winners** (49-52% either way):
the multi-day trend doesn't tell this bot's winners from its losers. It halves busts but most evaluations then run out
of time (45-65% timeouts) and payouts per evaluation collapse. The best on 2011-18, 6 / 2 MNQ by the 20-session
average's slope, paid $184 against $585 (2019-25) and $601 against $628 (NQ) per evaluation: **FAIL**.

## Round ninety-four: reverse a failed breakout

`research/trap_reversal.py`. When a bot trade is stopped out (line stop or max loss) within 3 or 10 minutes of its fill
or any time, enter the other way at the next minute: stop beyond the failed trade's best price or 25 points, target
1R or 2R, once a day, 4 MNQ (12 rules). Protocol fixed before running.

**It reliably loses**: every rule loses on 2011-18 ($-11 to $-37 a trade, 30-45% winners; ten of twelve significant,
all negative), and the fixed-stop versions lose in every period (2019-26 t -2.2 to -3.7, NQ futures t -3.2 to -4.8).
Added to the bot it cuts $ a week and payouts. A quickly failed breakout doesn't run back the other way; trading
against it is a losing trade. (Re-entering the original direction gets its own test, round ninety-five.)

## Round ninety-five: re-enter after a quick stop-out

`research/reentry.py`. The mirror of round ninety-four, chosen after seeing it, so the bar was strict (t >= 3.0 on
2011-18, 2.5 on 2019-26, 2.0 on NQ): after a quick line or max-loss stop, re-enter the same way at the next minute,
25-point stop, 1R or 2R target, once a day, 4 MNQ. The 2R re-entries are positive in every period ($5-23 a trade,
35-38% winners, $2-11 a day) but weak (t 1.1-1.6 / 0.5-1.0 / 2.1-2.8); the 1R ones break even. **No rule counts.**

## Round ninety-six: Market Profile

`research/market_profile.py`. Yesterday's time-at-price profile (point of control, 70% value area) and 14 rules: the
80% rule (open outside the value area, back inside for one or two half hours, trade to the far edge or the point of
control), a fade to the point of control after the first 15 or 30 minutes, acceptance breakouts out of the value area,
and a point-of-control magnet at 11:00; $300 risk, up to 10 MNQ. Protocol fixed before running.

**0 survivors** on 2011-18 (best |t| 1.64, a losing rule). The classic 80% rule wins 28-31% of the time here and turns
negative after 2018; acceptance breakouts are positive in all three periods but weak (t 0.3-1.5, about one trade every
three weeks). Yesterday's profile levels don't give an MNQ edge.

## Round ninety-seven: classic named daytrade systems

`research/classic_systems.py`. 18 rules: Larry Williams' volatility breakout (stop orders at the open +/- 0.3, 0.5 or
0.7 of yesterday's range, first side only, out at the close; stop at the open, at the opposite level, or 25 points),
Turtle Soup, Raschke's 80-20, and the Holy Grail. Protocol fixed before running.

**0 survivors** at discovery (best p 0.006, needed 0.0028). Description: the Williams breakout with wide stops is
positive in all three data sets at every k; k 0.5 with the stop at the opposite level made $31 / $47 / $38 a trade at
1 MNQ (t 2.75 / 2.97 / 2.99 on 2011-18 / 2019-26 / NQ futures, 52-55% winners, about 3 trades a week), but risks
$200-900 a contract. With a 25-point stop it loses everywhere. Turtle Soup, 80-20 and the Holy Grail are rare and
inconsistent. What the Williams breakout adds to the bot on the Apex account is round ninety-eight.

## Round ninety-eight: the Williams breakout added to the bot

`research/williams_combo.py` (description; every period had been seen). The bot as the strategy trades it plus
Williams k 0.5 (stop at the opposite level, W5, or at the open, W2) at 1 or 2 MNQ, overlapping positions summed minute
by minute.

| Bot + | $ a week, 2011-18 / 2019-25 / NQ | Evaluation pass % | Paid per evaluation | First payout within 20 sessions |
|---|---|---|---|---|
| nothing | 272 / 270 / 245 | 24.6 / 19.5 / 22.8 | $962 / $559 / $599 | 5.5 / 2.2 / 1.7% |
| W2 x1 | 357 / 378 / 351 | 24.1 / 19.6 / 21.3 | $1,040 / $475 / $517 | 10.9 / 7.6 / 9.1% |
| W5 x1 | 374 / 402 / 364 | 21.4 / 17.8 / 19.5 | $841 / $350 / $395 | 13.8 / 6.6 / 9.9% |
| W5 x2 | 475 / 534 / 484 | 18.2 / 11.5 / 14.8 | $319 / $151 / $144 | 13.9 / 7.7 / 11.7% |

It adds $85-130 a week at 1 MNQ and brings the first payout sooner, but its stops are wide (W5: 95th percentile
$1,300-1,800 a trade at 1 MNQ), red days rise to 43-50%, and on a $2,000 trailing drawdown evaluations bust more and
pay less per evaluation in 2019-25 and on NQ. **Not added.** (Correlation of daily P/L with the bot: 0.4.)

## Rounds ninety-nine and one hundred: the Williams breakout sized to a fixed risk, and as it can run on one account

`research/williams_sized.py` (description; the Williams family's periods had all been seen): stops scaled to
yesterday's range and contracts to a fixed $ risk. Six of twelve variants are positive with t >= 2 in all three data
sets; the strongest, k 0.5 with the stop a quarter of yesterday's range from the fill and $200 of risk a trade (mostly
1 MNQ), out at the close: t 4.14 / 2.96 / 4.64, $36-46 a trade, 34-36% winners, about 3 trades a week, never more than
$300 at risk; up in all 11 NQ futures years and 14 of 16 index years. Added to the bot as a separate position it raised
the evaluation pass rate slightly in all three periods and $ a week by $100-130, with payouts per evaluation up in two
periods and down in one.

`research/combo_live.py`: on one Apex account the two can't hold opposite positions (hedging is banned) and positions
net, so the version that can run is one position at a time (whichever setup enters first owns the account until flat),
with the Williams entry a market order the minute after a level is touched. Bar fixed before running: higher pass rate
and $ a week in all three periods, payouts per evaluation at least 90% of the bot's.

| | $ a week, 2011-18 / 2019-25 / NQ | Evaluation pass % | Paid per evaluation | Paid within 20 sessions |
|---|---|---|---|---|
| Bot | 272 / 270 / 245 | 27.5 / 22.9 / 25.3 | $1,135 / $585 / $628 | 5.5 / 2.2 / 1.7% |
| Bot + Williams, one position at a time | 201 / 293 / 235 | 22.8 / 23.7 / 19.1 | $1,040 / $644 / $445 | 8.9 / 6.8 / 4.9% |

**NOT ADOPTED** (passes 2019-25 only): taking turns blocks some of the bot's trend days, which pay for everything.

## Round one hundred and one: the bot first, the Williams breakout only in its gaps

`research/combo_priority.py` (chosen after round one hundred, so round one hundred's bar, unchanged): the bot keeps
every trade; a Williams trade is taken only while the bot is flat, and when the bot enters while a Williams trade is
open, the Williams trade is closed at that minute's open first. Same machinery as round one hundred.

| | $ a week, 2011-18 / 2019-25 / NQ | Evaluation pass % | Paid per evaluation | Paid within 20 sessions | Red days |
|---|---|---|---|---|---|
| Bot | 272 / 270 / 245 | 27.5 / 22.9 / 25.3 | $1,135 / $585 / $628 | 5.5 / 2.2 / 1.7% | 34-36% |
| Bot first, Williams in the gaps | 316 / 311 / 288 | 28.5 / 23.9 / 25.3 | $1,453 / $730 / $741 | 9.9 / 4.4 / 4.0% | 49-50% |

By the bar: **passes 2011-18 and 2019-25; on NQ the pass rate ties (25.3 / 25.3) instead of rising, so formally not
adopted.** Everything else is better in all three periods: $41-44 more a week, payouts per evaluation up 18-28%, a
first payout within 20 sessions about twice as often; winners stay at 49-50%. The cost: red days rise from about a
third to about half (many small breakout losers, at most about $200 + fees each).

Neighbors (a scratch check, same machinery): k 0.5 with the stop at half the range and $400; k 0.3, 0.5 and 0.7
with a quarter of the range and $200, $300, $200. All four pay out within 20 sessions more often than the bot in all
three periods; three of four make more $ a week in all three (k 0.7: $265 against $270 in 2019-25); every one pays
less per evaluation than the bot in at least one period. So the extra trades and the sooner first payout hold up
around k 0.5 / 0.25 / $200; the gain in payouts per evaluation is the fragile part.

**Built into the NinjaTrader strategy anyway, as a switch, on by default** ("Breakout in the bot's gaps"): the
miss is a tie, not a loss, and the user asked for more trades a week, more money and the first payout sooner.
Switch it off for the bot alone. The strategy's trades with it on are `combo_priority.py`'s, trade for trade
(`tests/test_ninjatrader.py`). It still doesn't make $1,500 a week at this size.

## Round one hundred and two: the breakout together with the bot, and stop-and-reverse

`research/combo_more.py` (bar fixed before running, against round 101 on all three periods: more $ a week, pass
rate, payouts per evaluation and first payouts within 20 sessions no lower). From here on overlapping positions are
summed minute by minute (`trap_reversal.leg_paths`) for every setup, round 101's included, which is a little stricter
than round 101's own measure (its pass rates here: 26.4 / 21.7 / 22.7%).

| | $ a week, 2011-18 / 2019-25 / NQ | Pass % | Bust % | Paid per evaluation |
|---|---|---|---|---|
| Round 101 (the strategy now) | 316 / 311 / 288 | 26.4 / 21.7 / 22.7 | 60 / 61 / 67 | $1,268 / $727 / $690 |
| Together (a same-direction breakout taken while the bot is in, at most 10 MNQ in all) | 395 / 390 / 384 | 24.6 / 17.9 / 22.0 | 73 / 76 / 75 | $1,281 / $495 / $578 |
| Stop-and-reverse | 311 / 316 / 292 | 26.2 / 21.1 / 23.5 | 61 / 64 / 69 | $1,179 / $640 / $657 |
| Both | 379 / 401 / 385 | 24.3 / 16.3 / 21.8 | 74 / 78 / 76 | $1,071 / $449 / $584 |

**None adopted.** Together adds $80-95 a week, but the bigger positions bust 8-14 points more evaluations.

## Round one hundred and three: a lock and take-profit for the breakout trade

`research/w_manage.py` (pick on 2011-18 by payouts per evaluation among variants making at least as much a week;
adopted if, on 2019-25 and NQ, payouts and pass rate no lower, $ a week at least 95%, fewer red days). Locks at 0.5R,
1R, 1.5R (R = the breakout's stop), the stop then to entry + 0.1R; take-profits at 2R, 4R, none. The lock does what
it says: the breakout wins 53-68% of its trades instead of 45-46%, all trades 51-54% instead of 49-50%, red days
42-46% instead of 49-50%. But payouts per evaluation fall on the later sets (pick, lock 1R: $486 against $727 in
2019-25, $482 against $690 on NQ). **Not adopted.**

## Round one hundred and four: the overnight drift

`research/overnight_drift.py`. Boyarchenko, Larsen and Whelan ("The Overnight Drift", 2023) find index futures'
returns concentrated overnight, around the European open. Long 1 MNQ from a time in the night to a later one, $2.24
costs a trade; 5 windows x every night / after a down session / after an up session; bar: Benjamini-Hochberg at 10%
on 2011-18, then t >= 2 on 2019-26 and NQ futures 2015-25.

| 18:00 to the 09:30 open, every night | $ a night | Up nights | t |
|---|---|---|---|
| 2011-18 | +26.2 | 56.5% | 3.50 |
| 2019-26 | +22.2 | 54.0% | 1.75 |
| NQ 2015-25 | +15.0 | 54.5% | 1.62 |

Positive on every data set (18:00-02:00 too: t 1.99 / 2.23 / 1.92), but no rule clears t 2 on both later sets.
The 02:00-03:00 hour the paper points to is the strongest on 2011-18 (t 3.64) and fades later (0.35 / 1.20).
**Nothing counts** by the bar.

## Round one hundred and five: the overnight long on the account

`research/overnight_combo.py`. Apex's day runs from 18:00 to 16:59, so a night belongs to the next session's Apex
day and comes first in it. Long 1 or 2 MNQ at 18:00, stop 75 or 150 points, out at the 09:30 open, added to the
strategy as it is now. The pre-registered pick (most payouts per evaluation on 2011-18: 1 MNQ, stop 150) **failed**
(payouts per evaluation $564 against $727 in 2019-25). A check afterwards, of neighbouring stops and of the 13 months
from July 2025 no combination round had used:

| 1 MNQ, stop 100 points | $ a week, 2011-18 / 2019-25 / Jul 2025-Aug 2026 / NQ | Pass % | Paid per evaluation | First payout within 20 sessions |
|---|---|---|---|---|
| Now | 316 / 311 / 242 / 288 | 26.4 / 21.7 / 24.5 / 22.7 | $1,268 / $727 / $31 / $690 | 9.9 / 4.4 / 3.1 / 4.0% |
| Entered at 18:00 | 392 / 351 / 370 / 329 | 29.4 / 21.8 / 23.4 / 23.4 | $1,510 / $769 / $73 / $773 | 17.1 / 13.2 / 14.1 / 11.2% |
| Entered at 18:01 (as NinjaTrader can) | 396 / 341 / 334 / 325 | 29.3 / 21.6 / 22.1 / 24.3 | $1,455 / $595 / $41 / $877 | 16.8 / 13.0 / 10.3 / 11.5% |
| At 18:01, funded account only | 316 / 311 / 242 / 288 | as now | $1,168 / $625 / $114 / $743 | 16.8 / 13.0 / 10.3 / 11.5% |

(The July 2025 window's payouts are small because few funded accounts can finish in it.) It reliably brings the
first payout two to three times as often within 20 sessions and adds $30-90 a week, but busts rise 6-8 points and
the total paid per evaluation is not reliably higher: the first payout comes sooner, and later busts give it back.
On real MNQ bars from Yahoo (37 nights, August-October 2026) the 100-point stop made +$894 at 1 MNQ, 40% of nights
up. **Not built in.**

## Round one hundred and six: the overnight long until the first payout

`research/overnight_first.py` (description, chosen after round 105): the overnight long on the funded account only
until its first payout, then off. It pays even less in total than leaving it on ($1,150 / $605 / $88 / $604 per
evaluation against $1,268 / $727 / $31 / $690 now). It also measures the two-week goal directly: a first payout
within 10 sessions of being funded happens 0.2-0.6% of the time now and 1.5-3.3% with the overnight long. Apex's first
payout needs +$2,600 and five $200 days; in two weeks that is about $1,300 a week, four times what the strategy
makes on average. **Not adopted.**

## Round one hundred and seven: the strategy now on Apex's 50K EOD-trail evaluation

A check, not a search: the strategy as it is now (bot + breakout) on the EOD-trail evaluation ($3,000 target,
$2,000 drawdown set from end-of-day balances, $1,000 daily loss limit, 30 days) with the evaluation side at round
sixty's EOD setting, 6 MNQ / $300 / 3 losers, against the intraday trail the user trades now. The funded account is
modelled as before (drawdown trailing open profit until +$100), so if an EOD evaluation leads to an EOD funded
account this understates it.

| | Pass %, 2011-18 / 2019-25 / NQ | Bust % | Median sessions to pass | Paid per evaluation |
|---|---|---|---|---|
| Intraday trail, bot 4 MNQ (now) | 26.4 / 21.7 / 22.7 | 60 / 61 / 67 | 10 / 10 / 10 | $1,268 / $727 / $690 |
| EOD trail, bot 4 MNQ | 33.0 / 32.9 / 30.5 | 43 / 34 / 42 | 11 / 12 / 11 | $1,500 / $875 / $908 |
| EOD trail, bot 6 MNQ, $300 | 39.6 / 40.0 / 36.9 | 53 / 48 / 58 | 7 / 8 / 7 | $1,864 / $1,369 / $1,117 |
| EOD trail, bot 8 MNQ, $400 | 39.4 / 37.9 / 38.8 | 58 / 57 / 59 | 6 / 5 / 5 | $2,052 / $1,364 / $1,230 |
| EOD trail, 6 MNQ + the overnight long | 40.8 / 38.4 / 35.3 | 52 / 56 / 62 | 7 / 7 / 6 | $2,094 / $1,012 / $1,179 |

The plan is the largest lever found: 1.6-1.8 times the passes and 1.5-1.9 times the money per evaluation, in every
period. 6 and 8 MNQ are close; 6 stays (round sixty's choice, not refitted here). The overnight long is mixed again.
For reference only: the user trades the intraday trail, which the strategy's defaults are set for.

## Round one hundred and eight: the EOD route end to end (for reference)

`research/eod_full.py`: an EOD evaluation, then an EOD funded account (threshold under the highest close, locking at
+$100; $250 qualifying days), with round 102's "together", round 105's overnight long and a 6-MNQ funded side
re-tested on it. Base pays $2,196 / $1,748 / $1,536 per evaluation; "together" passes its bar ($2,276 / $1,749 /
$1,691, pass rate up 0.8-2.1 points); the overnight long and 6 MNQ funded fail. Not built in: the user trades the
intraday trail, where "together" failed (round 102).

## Round one hundred and nine: if the intraday evaluation's threshold stops trailing

`research/eval_lock.py`. Every intraday evaluation result so far let the threshold trail the peak all the way to the
target. Third-party summaries of Apex's 2026 rules say it stops: in evaluations possibly at the starting balance once
the peak reaches +$2,000 (funded: at +$100). Not confirmed on Apex's own site from here. The user's evaluation (the
strategy now):

| Threshold | Pass %, 2011-18 / 2019-25 / NQ | Bust % | Paid per evaluation |
|---|---|---|---|
| Never stops (every result so far) | 26.4 / 21.7 / 22.7 | 60 / 61 / 67 | $1,268 / $727 / $690 |
| Stops at the start | 30.2 / 27.5 / 28.5 | 52 / 50 / 56 | $1,416 / $865 / $838 |
| Stops at the start, then 1.5x size | 30.0 / 28.9 / 28.9 | 57 / 55 / 61 | $1,480 / $1,024 / $872 |
| Stops at the start, then 2x size | 29.2 / 27.4 / 28.3 | 60 / 59 / 65 | $1,474 / $1,002 / $872 |

If the threshold does stop, the earlier pass rates are 4-6 points too low. Sizing up once it has stopped pays more
per evaluation, but x1.5 passes fewer on 2011-18 (30.0 against 30.2), so by the bar (more passes and at least as
much paid in all three) **not adopted**. The +$100 lock gives the same picture.

## Round one hundred and ten: intraday momentum into the close

`research/last_half_hour.py`. Gao, Han, Li and Zhou (2018): the return from the previous close to 10:00 predicts the
last half hour. 12 rules (three signals, 15:30 or 15:00 to the close, all days or the larger half); bar:
Benjamini-Hochberg at 10% on 2011-18, then t >= 2 on both later sets. The paper's own signal is negative from 2019
(t -2.03) and on NQ futures (-1.20). The open-to-15:00 and close-to-15:00 signals traded into the close are positive
on all three sets (t 0.88 / 1.92 / 2.10 and 1.93 / 1.35 / 2.36) but clear neither stage; they overlap the bot's own
15:00 and 15:30 checks anyway. **Nothing counts.**

## Round one hundred and eleven: breakout trades lost to the bot's timing

`research/combo_late.py` (bar as round 102). Only 8.5% of the breakout's first touches (130 of 1,526 on NQ) come while
the bot is in a trade, nearly all in the bot's direction. Re-arming the breakout once the bot is flat ("late": 84
trades on NQ, -$12 each on average) changes almost nothing; round 102's "together" at 6 MNQ in all instead of 10
still busts 7-14 points more evaluations ($539 against $727 per evaluation in 2019-25). **None adopted.**

## Round one hundred and twelve: the evaluation's lock again, with the breakout

`research/eval_lock_w.py` (adopted if more passes and at least as much paid in all three periods). Arming the lock at
0.5 max loss in the evaluation helps a lot on 2011-18 (29.6% passed against 26.4%, $1,612 against $1,268 per
evaluation) and hurts later (17.5% against 21.7% in 2019-25). (0.5, +6.25) and (0.75, +4) the same. **(1.0, +2.5)
stays.** Read with the threshold stopping at the start (round 109), the picture is the same.

## How the strategy's risk is split

The strategy's two parts, as it trades the evaluation (daily P/L, all sessions):

| | Bot (4 MNQ): $ a day / swing | Breakout: $ a day / swing | Correlation |
|---|---|---|---|
| 2011-18 | 55.8 / 626 | 8.9 / 178 | 0.00 |
| 2019-25 | 51.8 / 648 | 7.9 / 194 | 0.00 |
| NQ 2015-24 | 49.0 / 627 | 8.3 / 179 | 0.02 |

Uncorrelated in every period. By mean-variance the breakout should carry 1.7-2.0 times its risk ($350-400 a trade),
stable across periods, but that would raise the whole strategy's return-to-swing ratio by only about 3% (0.099 to
0.102 a day), and round 101's neighbours at $400 were mixed: not worth changing. That ratio, about 0.1 a day, is
what sets the pass rate on a $2,000 trailing drawdown with 30 days; rule changes move it by a few percent, and only a
new edge uncorrelated with both would move it much.

## Round one hundred and thirteen: a daily give-back stop for the intraday trail

`research/day_giveback.py` (adopted if more passes and at least as much paid in all three periods): once the day's
equity (bot + breakout, closed + open) has been up $P, close everything and stop for the day if it falls $G below
the day's best (P $300 / $600 x G $200 / $400; evaluation only, or both). (A first run compared each minute's low with
a best that included the same minute's high, triggering stops a real fill wouldn't; the run reported here compares
with the best before the minute.) It does what it is meant to do (green days up to 42%, red days down to a third,
evaluation busts down by as much as 44 points) but it cuts the trend days that pay for everything: $ a week falls by a
third to two thirds and so many evaluations run out of time that passes fall to 7-20%. **None adopted.**

## Round one hundred and fourteen: the overnight long, 18:00 to 02:00

`research/overnight_early.py`. Round 104's most consistent window (t 1.99 / 2.23 / 1.92), 1 MNQ from 18:01 to the
02:00 open, stop 50 or 100 points, in the evaluation and funded (or funded only); bar as round 105.

| | $ a week, 2011-18 / 2019-25 / NQ | Pass % | Bust % | Paid per evaluation | First payout within 20 sessions |
|---|---|---|---|---|---|
| Now | 316 / 311 / 288 | 26.4 / 21.7 / 22.7 | 60 / 61 / 67 | $1,268 / $727 / $690 | 9.9 / 4.4 / 4.0% |
| Stop 50 | 355 / 344 / 321 | 28.5 / 22.4 / 23.4 | 58 / 60 / 67 | $1,421 / $821 / $799 | 15.0 / 10.2 / 8.4% |
| Stop 100 | 372 / 349 / 336 | 28.5 / 23.6 / 24.3 | 60 / 61 / 67 | $1,600 / $957 / $720 | 15.0 / 11.1 / 10.8% |

Both pass the bar in all three periods (funded only: fail). But the two newest checks go the other way: on the 13
months from July 2025 (no round chose anything on them) the pass rate falls (21.0% and 19.3% against 24.5%) and $ a
week dips, and on real MNQ bars from Yahoo (37 nights, August-October 2026) it lost $1,114 (stop 50) and $999 (stop
100) at 1 MNQ. A published effect that held to 2025 and has been losing since: **not built in.** Worth re-checking as
more nights come in.

## Round one hundred and fifteen: smaller size when the evaluation's cushion runs low

How the user's intraday-trail evaluations bust (the strategy now; 2019-25 / NQ): over a median of 9 sessions, not in
one day; before the bust day about $1,750 of the $2,000 cushion is already gone and the bust day only has to lose
another $230-250. `research/cushion_size.py`: half size below $1,000 or $700 of cushion, or half below $1,000 and a
quarter below $500 (evaluation only; adopted if more passes and at least as much paid in all three periods).

| | Pass %, 2011-18 / 2019-25 / NQ | Bust % | Out of time % |
|---|---|---|---|
| Now | 26.4 / 21.7 / 22.7 | 60 / 61 / 67 | 13 / 17 / 10 |
| Half under $1,000 | 21.3 / 16.4 / 17.5 | 41 / 43 / 47 | 38 / 41 / 36 |
| Half under $700 | 25.0 / 19.2 / 19.2 | 50 / 50 / 56 | 25 / 31 / 25 |
| Half under $1,000, a quarter under $500 | 21.6 / 13.9 / 17.0 | 24 / 27 / 24 | 55 / 59 / 59 |

Busts fall a lot; the evaluations then run out of their 30 days instead, and fewer pass. **None adopted.** With rounds
63 and 84 (more size busts more) this brackets the evaluation from both sides: the $2,000 trail and the 30-day clock
together, and the current size sits near the best balance between them for this edge. Third-party summaries of the
2026 rules agree the 30 days are fixed (from the purchase date, no renewal or reset; legacy accounts auto-renew), so
start the strategy on the day the evaluation is bought. With 60 or 90 days instead (a scratch check), the cushion rules
are still mixed: better on 2011-18, worse in 2019-25.

## Round one hundred and sixteen: the source paper's VWAP trailing stop, on the bot as it trades now

How the two parts have done year by year first ($ a week at the evaluation's settings, index data): the bot from
-$41 (2013) to +$668 (2022), weak in 2013, 2017 and 2025 (+$17; NQ -$99), strong in 2026 so far (+$474); the breakout
-$94 to +$147, no trend. No sign of decay, but lumpy years: an evaluation started in a bad year mostly fails.

`research/vwap_stop.py`, with `mnqbot.noise`'s research-only `vwap_stop` (off by default; not in the Pine script or
NinjaTrader): the bot's stop is also never looser than the day's VWAP (volume-weighted on NQ, time-weighted on the
index data, which has no volume), as of the last half-hour check or the last bar. Only tested before on the bot's
first version over 3 3/4 years (the second round, S2b). Bar: more $ a week, pass rate and payouts no lower, all three.

| | $ a week, 2011-18 / 2019-25 / Jul 2025-Aug 2026 / NQ | Pass % | Bust % | Paid per evaluation |
|---|---|---|---|---|
| Now | 316 / 311 / 242 / 288 | 26.4 / 21.7 / 24.5 / 22.7 | 60 / 61 / 69 / 67 | $1,268 / $727 / $31 / $690 |
| VWAP at the checks | 315 / 283 / 268 / 292 | 27.5 / 22.1 / 23.1 / 24.4 | 57 / 60 / 68 / 64 | $1,320 / $706 / $31 / $785 |
| VWAP every bar | 312 / 284 / 269 / 292 | 27.3 / 22.5 / 23.1 / 24.2 | 58 / 59 / 68 / 64 | $1,322 / $700 / $31 / $785 |

A little safer (more passes and fewer busts on the three main sets), but $28 a week less in 2019-25 and less paid per
evaluation there, and fewer passes in the newest 13 months. **Not adopted.**

## Round one hundred and seventeen: the breakout's shorts

Longs against shorts, $ a trade as the strategy trades them: the breakout +24.1 / +8.5 (2011-18), +16.6 / +15.1
(2019-25), +14.2 / -4.1 (July 2025-2026), +28.7 / +5.3 (NQ); the bot +28.9 / +30.5, +42.2 / +19.1, +26.8 / +33.5,
+39.6 / +14.2. Only the breakout's gap shows in 2011-18, so only the breakout is changed (`research/w_long.py`;
adopted if pass rate and payouts no lower and one higher on 2019-25 and NQ):

| | Pass %, 2019-25 / NQ | Paid per evaluation | Red days |
|---|---|---|---|
| Now | 21.7 / 22.7 | $727 / $690 | 49% / 50% |
| Breakout shorts at half risk | 20.7 / 22.8 | $663 / $656 | 49% / 50% |
| No breakout shorts | 20.9 / 22.7 | $609 / $576 | 41% / 41% |

Dropping the shorts cuts red days by eight points but pays less. (Half risk barely changes anything: most breakout
trades are 1 MNQ already.) **Not adopted.**

## The wick cue on the bot as it trades now

Round 75's wick cue (the signal bar closes in its half away from the trade) was found on 5-minute bars, before the
1-minute chart, the take-profit and the lock. Measured on the bot now (the five 1-minute bars up to the check as the
signal bar; 4 MNQ, $200): wick trades $52.0 / $44.7 / $38.5 / $38.4 a trade against $13.7 / $20.6 / $25.4 / $17.8 for
the others (2011-18 / 2019-25 / July 2025-2026 / NQ), the difference t 2.72 / 1.36 / 0.33 / 1.54. The other trades
make money too and the gap has shrunk to noise in the newest data: cutting them would mostly give up profit. No round.

## Round one hundred and eighteen: smaller bot trades before the day's breakout has touched

The bot's trades by the day's breakout ($ a trade, 4 MNQ): after a touch in the same direction +49.2 (t 5.40, 62% of
trades) / +29.4 / +22.3 / +37.8 (2011-18 / 2019-25 / July 2025-2026 / NQ); before any touch +2.1 (t 0.18, 34%) /
+26.9 / +56.0 / +8.6; against a touch (3-4%) noise. `research/touch_size.py`: the before-a-touch trades at 2 or 1
MNQ (adopted if pass rate and payouts no lower and one higher on 2019-25 and NQ). The worst losing stretch and the
busts fall a lot (NQ: $9,550 to $6,084 and 67% to 56% at 2 MNQ), but so do the money and the passes where those trades
earned (2019-25: 21.7% to 16.9% passed; the newest 13 months: $242 to $166 a week). **Not adopted.**

## Round one hundred and nineteen: the hours next to the session

`research/edge_hours.py`. 16:00-16:30 and 16:00-16:59 (still inside Apex's day) and 08:30 or 09:00 to 09:30, each with
the move before it, against it, or long; 12 rules at 1 MNQ, $2.24 a trade; bar: Benjamini-Hochberg at 10% on 2011-18,
then t >= 2 on 2019-26 and NQ, positive in the newest 13 months. **Nothing counts.** The 16:00-16:59 long is positive
where there are bars for it (2011-18 t 2.07, $6.78 a trade; NQ t 2.53, $7.76) but misses the first stage, and the index
data has no post-16:00 bars from 2019, so its main later test can't be run. Fading the overnight move from 09:00 is
positive in 2019-26 (t 1.69) and the newest months (t 2.58) but not before (t -2.13 in 2011-18 for the long side, 0.68
on NQ): not stable.

## Round one hundred and twenty: a breakout of the overnight range

`research/overnight_range.py`: the strategy's breakout with the overnight session's high and low (18:00-09:29) as its
levels instead of the open +/- half of yesterday's range (only when the open is inside the overnight range); stop,
size and exit unchanged. One test; bar: t >= 2 on 2011-18, 2019-26 and NQ, positive in the newest 13 months.

| | Trades a year | $ a trade | Winners | t | Correlation with the breakout (days both trade) |
|---|---|---|---|---|---|
| 2011-18 | 201 | +22.5 | 32% | 2.56 | 0.63 |
| 2019-26 | 167 | +22.3 | 31% | 2.08 | 0.54 |
| July 2025-Sep 2026 | 191 | -9.3 | 28% | -0.43 | 0.35 |
| NQ 2015-25 | 180 | +30.7 | 32% | 3.42 | 0.64 |

Clears the three main stages but loses in the newest 13 months, and it is largely the same trade as the breakout
already in the strategy (correlation 0.54-0.64): not the independent source the account needs. **Does not count.**

## Round one hundred and twenty-one: the breakout's risk on the funded account alone

`research/funded_w.py` (the evaluation as now; adopted if more paid per evaluation and a first payout within 20
sessions at least as often, all three periods):

| Funded side | Paid per evaluation, 2011-18 / 2019-25 / NQ | First payout within 20 sessions |
|---|---|---|
| No breakout | $1,152 / $561 / $536 | 5.5 / 2.2 / 1.7% |
| $100 a trade | $1,188 / $635 / $457 | 7.4 / 2.8 / 2.4% |
| $200 (now) | $1,268 / $727 / $690 | 9.9 / 4.4 / 4.0% |
| $300 a trade | $976 / $494 / $591 | 13.0 / 8.0 / 7.2% |

$200 pays the most in all three periods; $300 brings the first payout sooner but busts more funded accounts later.
**The setting stays.**

## Round one hundred and twenty-two: the bot's funded settings with the breakout on the account

`research/funded_bot.py`: funded contracts 3 / 4 / 5 x losers 2 / 3 x lock (0.5, +6.25) or (1.0, +2.5), the breakout
and the evaluation as now; pick the most paid per evaluation on 2011-18, adopted if it pays more and brings a first
payout within 20 sessions at least as often on 2019-25 and NQ. The pick (3 MNQ, 3 losers, lock 0.5 / +6.25: $1,472)
pays $739 / $652 against $727 / $690 and pays out within 20 sessions less often: **not adopted.** For the record, 3 MNQ
with the rest as now pays the most on the two later sets ($839 / $818, 2011-18 $1,238 against $1,268) with fewer funded
busts, but the first payout comes later (3.3 / 3.5% within 20 sessions against 4.4 / 4.0%), against the user's
two-week goal. **The funded setting stays.**

## Round one hundred and twenty-three: the bot's evaluation settings with the breakout on the account

`research/eval_bot.py`: contracts 3 / 4 / 5 x losers 2 / 3 / 4 (pick the highest pass rate on 2011-18; adopted if it
passes more and pays at least as much on 2019-25 and NQ). The pick, 4 MNQ / 4 losers (27.0% on 2011-18), passes 19.2%
against 21.7% in 2019-25. **Not adopted.**

## Round one hundred and twenty-four: close everything the moment the evaluation reaches its target

Challenging the method rather than the strategy: every evaluation result so far (apex25k.attempt) counted a pass only
when a trade CLOSED with the balance at +$3,000. A trade that carried the account past +$3,000 in open profit and
then fell back didn't pass, where a trader closes everything at that moment. `research/pass_lock.py`: passed the
minute the merged minute equity reaches +$3,025 (the threshold checked first, up to and including that minute); a
take-profit at that price does it (the NinjaTrader strategy now does). Bar: more passes and at least as much paid,
all three periods.

| The user's intraday-trail evaluation | Pass %, 2011-18 / 2019-25 / NQ / July 2025-Aug 2026 | Bust % | Sessions to pass | Paid per evaluation |
|---|---|---|---|---|
| Now (pass only at a trade's close) | 26.4 / 21.7 / 22.7 / 24.5 | 60 / 61 / 67 / 69 | 10 / 10 / 10 / 8 | $1,268 / $727 / $690 |
| **Close everything at the target** | **35.4 / 37.1 / 34.5 / 27.9** | 54 / 49 / 58 / 68 | 9 / 8 / 8 / 7 | **$1,835 / $1,349 / $1,163** |
| Threshold stopping at the start (round 109), now | 30.2 / 27.5 / 28.5 / 26.6 | 52 / 50 / 56 / 67 | | $1,416 / $865 / $838 |
| Threshold stopping at the start, close at the target | 36.7 / 39.3 / 37.1 / 29.0 | 51 / 46 / 53 / 67 | | $1,862 / $1,441 / $1,233 |

**Adopted**, the largest gain since the breakout: 1.3-1.7 times the passes and 1.45-1.9 times the money per
evaluation, in every period and under both readings of the threshold. In the NinjaTrader strategy as "Evaluation:
close everything at this profit" ($3,000): the take-profit of the trade in progress at the price that gets there
($25 past it, for the fees) when that is closer than its own; at market if a bar closes $25 past it; no new trades
after. Every earlier evaluation result above was measured without it and is too low.

## Round one hundred and twenty-five: the evaluation's size and loser limit, with close-at-target

`research/pass_lock_size.py`: contracts 3 / 4 / 5 / 6 x losers 2 / 3 / 4 with close-at-target (pick the highest pass
rate on 2011-18; adopted if it passes more and pays at least as much on 2019-25 and NQ). The pick, 5 MNQ / 2 losers
(36.2% on 2011-18), passes 37.3% / 35.4% against 37.1% / 34.5% but pays $1,089 against $1,163 on NQ. **4 MNQ / 3
losers stays.** Bigger sizes pass about as often, faster (5-7 sessions) and bust more.

## Round one hundred and twenty-six: the near-misses again, with close-at-target

`research/retest_lock.py`. The variants rejected on the old pass rule that came closest, against the strategy now
with close-at-target; adopted if more passes and at least as much paid in all three periods and no fewer passes in
the newest 13 months.

| | Pass %, 2011-18 / 2019-25 / NQ / July 2025-Aug 2026 | Paid per evaluation | First payout within 20 sessions |
|---|---|---|---|
| Now | 35.4 / 37.1 / 34.5 / 27.9 | $1,835 / $1,349 / $1,163 | 9.9 / 4.4 / 4.0% |
| Breakout together with the bot, 6 MNQ in all | 34.8 / 33.6 / 35.5 / 22.8 | $1,816 / $1,007 / $1,187 | 11.3 / 5.0 / 6.5% |
| Evaluation lock 0.5 / +2.5 | 38.1 / 30.9 / 30.2 / 19.3 | $1,978 / $1,108 / $1,031 | 9.9 / 4.4 / 4.0% |
| Breakout $300 in the evaluation | 37.1 / 35.9 / 35.4 / 27.9 | $1,864 / $1,282 / $1,191 | 9.9 / 4.4 / 4.0% |
| VWAP stop | 35.8 / 35.3 / 34.8 / 25.9 | $1,872 / $1,171 / $1,169 | 10.5 / 4.5 / 3.8% |
| Overnight long 18:01-02:00 | 36.3 / 37.1 / 33.3 / 21.0 | $2,171 / $1,523 / $1,206 | 15.0 / 11.1 / 10.8% |

**None adopted.** The overnight long pays more in all three periods and brings the first payout two to three times as
often, but passes fewer evaluations on NQ and in the newest months (and lost on the real MNQ nights of round 114).

## Round one hundred and twenty-seven: when to ask for a payout

`research/payout_buffer.py`: a payout only when the balance after it stays $500 / $1,000 / $2,000 above the minimum.
Paid per evaluation moves by about +/-2% ($1,822-1,864 against $1,835 on 2011-18; $1,305-1,338 against $1,349 in
2019-25) and the first payout comes later. **Ask as soon as it's allowed (as now).**

## Round one hundred and twenty-eight: stop for the day the moment closing makes the funded account payout-eligible

`research/payout_lock.py`: the funded counterpart of round 124 (closing at the minute's worst equity less $10, when
that leaves the day meeting every payout condition). Bar: more paid per evaluation in all three periods and a first
payout within 20 sessions at least as often.

| | Paid per evaluation, 2011-18 / 2019-25 / NQ / July 2025-Aug 2026 | First payout within 20 sessions |
|---|---|---|
| Now | $1,835 / $1,349 / $1,163 / $36 | 9.9 / 4.4 / 4.0 / 3.1% |
| Close when payout-eligible | $1,506 / $1,389 / $1,174 / $76 | 13.8 / 8.8 / 8.2 / 7.2% |

The first payout comes twice as often within 20 sessions everywhere, and the total is up on the three later sets but
down 18% on 2011-18: **not adopted.** It would also need the strategy to know Apex's payout state (qualifying days,
the cycle's profit), which it can't read from the account.

## Round one hundred and twenty-nine: an evaluation that runs out of time has failed, so play bolder near the end

`research/bold_finish.py`. A timeout and a bust are the same outcome for the user, so late in the 30 days an
evaluation that hasn't passed gives up nothing by taking more risk (bold play against a deadline). With close-at-
target; adopted if more passes in all three periods and the newest 13 months and at least as much paid.

| | Pass %, 2011-18 / 2019-25 / NQ / newest | Out of time % | Paid per evaluation |
|---|---|---|---|
| Now | 35.4 / 37.1 / 34.5 / 27.9 | 11 / 14 / 8 / 4 | $1,835 / $1,349 / $1,163 |
| From day 20, 2x | 38.8 / 39.9 / 36.1 / 25.2 | 2 / 2 / 1 / 1 | $1,933 / $1,479 / $1,253 |
| From day 20, 2.5x (10 MNQ) | 38.7 / 39.3 / 35.9 / 27.6 | 1 / 1 / 0 / 1 | $1,946 / $1,435 / $1,252 |
| From day 24, 2x | 38.0 / 40.0 / 36.2 / 25.2 | 4 / 5 / 2 / 2 | $1,892 / $1,484 / $1,252 |
| From day 24, 2.5x | 38.7 / 40.6 / 36.4 / 26.2 | 2 / 3 / 1 / 1 | $1,917 / $1,509 / $1,265 |
| 2x within $1,000 of the target | 35.8 / 37.4 / 33.8 / 27.2 | 10 / 13 / 7 / 3 | $1,889 / $1,387 / $1,196 |

Every late rule passes 1.4-3.5 points more and pays 4-12% more on the three long periods, as the argument predicts,
but none passes more in the newest 13 months (few timeouts there to convert: 4%). **Not adopted by the bar; built in
as an option, off by default** ("Evaluation: from day 20, 2.5x size"), for the user to switch on.

## Round one hundred and thirty: a take-profit for the breakout, and the manual mode verified

Apex bans automation (third-party summaries checked October 2026), so trading this on Apex means Place orders off and
clicking the alerts; several 2026 summaries also say every order needs a stop AND a take-profit. `research/w_bracket.py`:
the breakout's take-profit at 4, 6 or 8 times its stop (pick the nearest within 0.5 points of pass rate and 97% of the
payouts of none in all three periods, else 8 as the compliance minimum):

| Breakout take-profit | Pass %, 2011-18 / 2019-25 / NQ / newest | Paid per evaluation |
|---|---|---|
| None | 35.4 / 37.1 / 34.5 / 27.9 | $1,835 / $1,349 / $1,163 |
| 4 stops | 34.7 / 36.8 / 34.4 / 27.6 | $1,630 / $1,301 / $1,126 |
| 6 stops | 35.7 / 36.5 / 34.6 / 27.9 | $1,841 / $1,373 / $1,177 |
| 8 stops | 35.2 / 36.5 / 34.4 / 27.9 | $1,810 / $1,414 / $1,138 |

6 and 8 miss the 0.5-point rule by 0.1 in 2019-25, so **8 stops** (2x yesterday's range), as the rule says: results
essentially unchanged, and every trade carries a full bracket. In the strategy as "Breakout: take-profit" (8).

The alerts-only mode was audited by following it: a test trader who does only what the alert lines say ends up with
exactly the strategy's own trades. It found three gaps, now fixed: the bot's stop and take-profit moves weren't
announced (now MOVE STOP / MOVE TAKE-PROFIT), the breakout's alert gave its stop in points and no exit alerts (now
prices, its exits and "first close the breakout"), and close-at-target had no manual form (now from the account's
net liquidation: the take-profit moved to the target's price, then "close everything now"). It also found a rounding
bug: take-profits placed by price were rounded toward the price (up to a tick less than tested); now away from it.

## Round one hundred and thirty-one: the breakout's lock again, for more winning trades

`research/w_lock_target.py`, with close-at-target and the 8R take-profit (adopted if more winners and pass rate within
0.5 points and 97% of the payouts in all three periods): a lock at 0.5R makes 53-55% of trades winners (49-50% now) and
red days 42-48% (49-55%), but pays $1,568 / $1,377 / $770 per evaluation against $1,810 / $1,414 / $1,138; at 1R the
same, weaker. **Not adopted**: more winning trades cost payouts on this account.

The funded payout stop of round 128 is now in the NinjaTrader strategy as an option (on by default since round 132) ("Funded: stop for
the day once closing makes it payout-eligible"), verified against an independent replica of the cycle's rules.

## Round one hundred and thirty-two: money a week from one account slot, and the payout stop on

`research/accounts_needed.py`. Every result before counted money per evaluation bought. The goal is money a week, and
an account is run as a slot: an evaluation; when it fails or times out, the next one the next session; once passed, the
funded account until it busts or pays its sixth payout, then a new evaluation. From every start session, the strategy
as it trades now (bot + breakout, close-at-target, funded settings), payouts only, before fees:

| Period | $ a week per slot, 26 weeks (stop off / on) | 52 weeks (off / on) | evaluations a slot, 52 weeks | break-even evaluation price, 52 weeks (off / on) |
|---|---|---|---|---|
| 2011-2018 | $45 / $52 | $70 / $77 | 7-7.4 | $498 / $513 |
| 2019-2025 | $36 / $43 | $47 / $63 | 10.1 | $217 / $301 |
| Jul 2025-Aug 2026 | $24 / $29 | $29 / $29 (63 starts) | 13-14 | $88 / $101 |
| NQ 2015-2024 | $31 / $35 | $40 / $48 | 8.8-9.1 | $210 / $243 |

(break-even price: the evaluation price at which the payouts just pay for the evaluations and a $79 activation per
funded account; 26 weeks: $191 / $219, $117 / $146, $65 / $88, $100 / $118.)

- **The payout stop pays more a week in every period, at both horizons** (equal in the newest window over 52 weeks,
  where only 63 starts fit). Per evaluation (round 128) it paid 18% less on 2011-18; per week of a running slot it
  pays more, because the payouts come sooner and the next evaluation starts sooner. **Adopted: on by default.**
- **$1,500 a week would be 20-64 slots (not an option: the user trades one account).** Copy trading between one's own Apex accounts is allowed (third-party summaries of
  Apex's help center; Tradovate's group copier is on Apex's help center), up to 20 funded accounts. Accounts copied
  from the same trades pay N times one slot on average but do not spread the risk: a bad stretch is bad on all of them.
- **One account's bound.** The funded strategy makes $41-49 a day with a spread of about $513 (2011-25), $10 a day in
  the newest 13 months. A day's mean m at spread s against a $2,000 drawdown fails with probability about
  exp(-2 m 2000 / s^2): about half at these numbers, as measured. $300 a day (the $1,500 a week) with only a 20% chance
  of failing needs a spread of $863 or less: four times the strategy's return for its risk (0.35 a day against 0.09). No rule tested in 131
  rounds came near that; it is the size of the gap, not a tuning problem.
- **Fees decide the newest window.** At $65-101 a slot's payouts only just cover a promotional evaluation price; at
  Apex's quoted list prices for the intraday 50K ($118-249, third-party) the newest 13 months lose money.

## Round one hundred and thirty-three: the evaluation's and the funded account's size, judged as money a week

`research/slot_size.py`. The sizes were chosen per evaluation; per week, passing faster matters. 52 weeks from every
start, the payout stop on, net $ a week per slot after $100 an evaluation and $79 an activation (pick: the best on
2011-18; adopted if more on 2019-25 and NQ and no less in the newest 13 months):

| Evaluation / funded | 2011-18 | 2019-25 | Jul 2025-Aug 2026 (63 starts) | NQ 2015-24 |
|---|---|---|---|---|
| 4 MNQ, 3 losers / 4 MNQ (now) | $59 | $39 | $0 | $25 |
| 5 MNQ, 3 losers / 4 MNQ | $65 | $52 | $2 | $32 |
| 6 MNQ, 2 losers / 4 MNQ | $70 | $62 | -$1 | $31 |
| 6 MNQ, 3 losers / 4 MNQ | $67 | $58 | $15 | $31 |
| 8 MNQ, 3 losers / 4 MNQ (pick) | $75 | $51 | -$12 | $33 |
| 4 MNQ, 3 losers / 3 MNQ | $70 | $35 | -$6 | $38 |
| 4 MNQ, 3 losers / 5 or 6 MNQ | $59 / $47 | $27 / $19 | -$4 | $9 / -$4 |

**Not adopted** by the bar fixed before running: the pick, 8 MNQ, loses in the newest 13 months. But every bigger
evaluation (5, 6 and 8 MNQ, either loser limit) nets more than 4 MNQ in all three long periods, and 6 MNQ / 3 losers
nets more in all four; it was not the pick, so it is not made the default after the fact. It is one setting away:
**Contracts in an evaluation** 6 and **Evaluation: max loss per trade** $300 (the research keeps the 25-point cap a
contract; at $200 and 6 MNQ the cap would be 16.7 points, which was not tested). Bigger on the funded account nets
less everywhere but NQ: 4 MNQ stays. The newest window has only 63 starts that fit 52 weeks, so its numbers move a lot
with one outcome (most setups there show the same $28.8 a week paid: one funded account's payouts).

## Round one hundred and thirty-four: the breakout's risk in the evaluation, and the bold finish, judged per week

`research/slot_eval.py`, as round 133 (52 weeks, payout stop on, net of $100 an evaluation and $79 an activation;
pick on 2011-18, adopted if more on 2019-25 and NQ and no less in the newest 13 months):

| Evaluation side | 2011-18 | 2019-25 | Jul 2025-Aug 2026 | NQ 2015-24 |
|---|---|---|---|---|
| now (breakout $200) | $58.9 | $39.2 | $0.3 | $25.0 |
| breakout $300 | $60.7 | $41.6 | $4.1 | $29.4 |
| **breakout $400 (pick)** | **$69.6** | **$42.4** | **$3.6** | **$31.5** |
| bold finish, day 20, 2.5x | $62.7 | $46.3 | $0.1 | $31.0 |
| bold finish, day 24, 2x | $57.0 | $46.1 | $0.2 | $26.1 |

**Adopted: the breakout risks $400 a trade in the evaluation** (1-10 MNQ; funded stays $200, round 121). Built into
the NinjaTrader strategy as its own setting ("Risk a trade in the evaluation"), verified trade for trade against the
research reference at $400 (evaluation) and $200 (funded). The bold finish nets more in three periods but not in the
newest 13 months and was not the pick: it stays an option, off.

## Round one hundred and thirty-five: the funded account's settings, judged per week

`research/slot_funded.py`, as rounds 133-134 (the evaluation now with the breakout at $400; net $ a week at $100 an
evaluation):

| Funded side | 2011-18 | 2019-25 | Jul 2025-Aug 2026 | NQ 2015-24 |
|---|---|---|---|---|
| now (breakout $200, 2 losers, lock 0.5 / +6.25) | $69.6 | $42.4 | $3.6 | $31.5 |
| breakout $100 | $65.1 | $31.0 | $1.9 | $21.9 |
| breakout $300 | $79.3 | $43.8 | $26.7 | $45.3 |
| 3 losers (pick) | $86.6 | $20.2 | $3.8 | $34.6 |
| the evaluation's lock (1.0 / +2.5) | $64.8 | $55.9 | $5.7 | $44.1 |

**Not adopted**: the pick, 3 losers, nets half as much on 2019-25. The funded breakout at $300 nets more in all four
periods but was not the pick; like 6 MNQ in the evaluation (round 133) it is one setting away ("Risk a trade on the
funded account" 300) and is to be re-tested on new weeks before it becomes the default. Several near-misses now sit
on the same side (more risk on the breakout, more size in the evaluation): taken together that is a pattern, but each
was found on data already used several times, which is why none is adopted after the fact.

## Round one hundred and thirty-six: volatility-targeted size

`research/vol_target.py`. Moreira and Muir (2017): scale exposure by the inverse of recent volatility. Each session's
size multiple = (median of the 14-session average range over all earlier sessions) / (the last 14 sessions' average
range), clipped; the whole day scaled, evaluation and funded; bar as rounds 133-135.

| Net $ a week at $100 (funded day Sharpe) | 2011-18 | 2019-25 | Jul 2025-Aug 2026 | NQ 2015-24 |
|---|---|---|---|---|
| now | $69.6 (0.095) | $42.4 (0.080) | $3.6 (0.023) | $31.5 (0.084) |
| vol, 0.5-1.0x | $61.2 (0.101) | $31.0 (0.085) | $5.4 (0.021) | $30.5 (0.086) |
| vol, 0.75-1.25x | $60.2 (0.098) | $37.7 (0.084) | -$4.1 (0.025) | $27.7 (0.085) |
| vol, 0.5-1.5x | $65.2 (0.099) | $39.9 (0.086) | -$2.7 (0.024) | $30.1 (0.084) |

**Not adopted** (the pick is the current setting). Volatility targeting lifts the return for the risk by about 6%
(0.095 to 0.101 a day), against the roughly 3x the $1,500 a week would need (docs/CHECKLIST.md, "the arithmetic"), and
the smaller average size nets less a week. The strategy's daily Sharpe is set by its edge, not by how it is sized.

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

## Round one hundred and thirty-seven: does the breakout deserve its place? (the audit's stage 6)

`research/components.py`. Each configuration is the whole strategy re-run (never trades removed from a list), on the
evaluation's settings as in the user's NinjaTrader run; the account column is the running-account model (52 weeks,
payout stop on, net of $100 an evaluation). Fixed before running.

| | Net $ | $ a trade | Winners | Intraday DD | Net / intraday DD | Worst day | Top-5 share | Net, +2 ticks | Account $/wk |
|---|---|---|---|---|---|---|---|---|---|
| **2011-18** combined | 145,240 | 28.9 | 49.7% | 18,556 | 7.8 | -1,475 | 12.5% | 126,445 | **69.6** |
| momentum only | 113,516 | 29.8 | 51.3% | 13,321 | 8.5 | -1,475 | 14.1% | 98,268 | 36.3 |
| breakout only | 91,937 | 67.3 | 36.0% | 15,384 | 6.0 | -762 | 24.6% | 88,117 | 29.7 |
| no breakout shorts | 142,469 | 32.5 | 50.8% | 15,080 | 9.4 | -1,475 | 11.8% | 125,508 | 68.0 |
| equal risk ($200) | 131,678 | 26.6 | 49.7% | 15,111 | 8.7 | -1,475 | 12.1% | 114,733 | 58.9 |
| **2019-25** combined | 131,071 | 34.0 | 48.4% | 13,041 | 10.1 | -3,182 | 14.9% | 117,320 | **42.4** |
| momentum only | 96,227 | 33.1 | 49.4% | 14,707 | 6.5 | -1,173 | 20.0% | 84,595 | 13.9 |
| breakout only | 78,229 | 73.5 | 34.9% | 10,340 | 7.6 | -3,182 | 34.4% | 75,961 | 16.6 |
| no breakout shorts | 115,398 | 34.4 | 49.1% | 15,360 | 7.5 | -3,182 | 17.0% | 102,738 | 20.5 |
| equal risk ($200) | 110,246 | 29.7 | 48.6% | 12,359 | 8.9 | -2,864 | 17.5% | 97,562 | 39.2 |
| **Jul 2025-Aug 2026** combined | 19,329 | 25.3 | 50.3% | 10,061 | 1.9 | -943 | 67.2% | 16,594 | **3.6** |
| momentum only | 17,104 | 30.4 | 52.4% | 8,260 | 2.1 | -628 | 76.0% | 14,852 | 2.0 |
| breakout only | 1,484 | 6.5 | 34.6% | 8,081 | 0.2 | -407 | - | 957 | -25.2 |
| no breakout shorts | 20,364 | 31.0 | 51.5% | 8,532 | 2.4 | -677 | 63.8% | 17,871 | 0.1 |
| equal risk ($200) | 17,884 | 23.8 | 50.1% | 8,501 | 2.1 | -803 | 72.6% | 15,388 | 0.3 |
| **NQ 2015-24** combined | 169,996 | 27.0 | 49.6% | 12,925 | 13.2 | -1,061 | 11.7% | 146,973 | **31.5** |
| momentum only | 126,079 | 26.2 | 50.9% | 13,366 | 9.4 | -652 | 15.0% | 106,847 | 17.0 |
| breakout only | 137,080 | 82.6 | 35.5% | 8,470 | 16.2 | -586 | 21.5% | 133,014 | 32.8 |
| no breakout shorts | 163,672 | 29.7 | 50.6% | 13,480 | 12.1 | -1,061 | 12.2% | 142,622 | 27.0 |
| equal risk ($200) | 147,958 | 24.2 | 49.8% | 11,841 | 12.5 | -843 | 12.8% | 126,893 | 25.0 |

- **The breakout stays.** With it, the account nets more a week than the bot alone in every period ($69.6 / $42.4 /
  $3.6 / $31.5 against $36.3 / $13.9 / $2.0 / $17.0) and more in total; the intraday drawdown is larger in two
  periods and smaller in two. It rarely interferes: it trades only in the bot's gaps.
- **The breakout's shorts stay.** Without them the account nets less in every period; the export's 8 shorts (7
  losers) are a small sample, not a pattern (a hypothesis it raised, rejected here on 16 years).
- **The $400 risk is mostly exposure.** Against the breakout at the bot's $200, net per unit of intraday drawdown is
  about the same (7.8 vs 8.7, 10.1 vs 8.9, 1.9 vs 2.1, 13.2 vs 12.5): the higher return comes with proportionally more
  risk. On the account it still nets more a week (evaluations pass sooner), which is why round 134 kept it.
- Every period here was used by earlier rounds; no data before 16 October 2026 is untouched.

## Round one hundred and thirty-eight: the lock's giveback, and two other exits (the audit's stages 7-8)

`research/exits.py`; the two exits are research-only options in `mnqbot/noise.py` (tests in `tests/test_noise.py`),
the whole strategy re-run for each. **The giveback is the lock as designed**: once a trade is 1R up (25 points in
the evaluation) its stop moves to entry + 2.5 and stays there unless the line or the take-profit ends the trade first.
In the export, trade #50 reached $738 of open profit and closed at +$10.40 on that stop: no delayed update, no
mismatch between model and fills. Defined before running: **trail 1R** (once the lock arms, the stop also sits 25
points behind the best price since the entry, from the next bar, never loosening) and **half at 1R** (half the
contracts close at a limit 25 points from the fill; the rest keeps every rule; R not redefined; one trade). Bar: more
on the account in all four periods and an intraday drawdown no larger in three.

| Account net $ a week at $100 (intraday DD; net) | 2011-18 | 2019-25 | Jul 2025-Aug 2026 | NQ 2015-24 |
|---|---|---|---|---|
| **lock (now)** | **$69.6** ($18,556; $145,240) | **$42.4** ($13,041; $131,071) | **$3.6** ($10,061; $19,329) | **$31.5** ($12,925; $169,996) |
| trail 1R | $64.1 ($11,899; $101,695) | $34.2 ($15,326; $71,424) | -$8.1 ($8,496; $13,776) | $16.6 ($12,287; $84,872) |
| half at 1R | $66.6 ($15,604; $93,790) | $45.7 ($11,283; $81,308) | -$12.7 ($7,741; $13,077) | $22.0 ($9,719; $116,858) |

**Neither adopted.** Both keep more of the small trades' open profit and win slightly more often (50-51%), and both
cut the large winners the strategy lives on: net falls 29-50%. Half at 1R lowers the intraday drawdown in all four
periods (by 13-25%) for 31-38% less net: a trade of profit for smoothness, not an improvement; on the account it nets
more only on 2019-25. The trail lowers the drawdown in three periods and nets less on the account in all four.

## Round one hundred and thirty-nine: a stop that only tightens, and the breakout's over-budget contract

`research/exits2.py`, the two rule changes the audit logged (docs/AUDIT.md: concern 10, the line stop stepping back
toward the price in 28.8% of half-hour steps; stage 5, one breakout contract forced when it costs 1-1.5x its budget),
judged as round 138. Account net $ a week at $100 (intraday drawdown):

| | 2011-18 | 2019-25 | Jul 2025-Aug 2026 | NQ 2015-24 |
|---|---|---|---|---|
| now | $69.6 ($18,556) | $42.4 ($13,041) | $3.6 ($10,061) | $31.5 ($12,925) |
| **tighten-only stop** | **$71.6** ($18,231) | **$44.9** ($13,006) | **$3.8** ($9,976) | **$37.5** ($12,779) |
| skip an over-budget breakout | $65.2 ($19,032) | $36.9 ($12,819) | $3.8 ($10,061) | $29.9 ($11,943) |

**Adopted: the stop only ever tightens.** More on the account in all four periods, the intraday drawdown slightly
smaller in all four; the trading total itself barely moves (+$1,104, -$927, -$2,616, -$721). A small, consistent gain
and a safer rule (a stop never moves back toward the price), not a new edge. Built into the NinjaTrader strategy and
its engine ("Stop only ever tightens", on), verified trade for trade against the research model with it on and off,
and the rule changes trades on the test bars. Skipping the over-budget breakout trade: not adopted.

## The first run in NinjaTrader itself: Strategy Analyzer, September 8 to October 16, 2026

The user ran the strategy in NinjaTrader's Strategy Analyzer on real MNQ DEC26 1-minute data (18 Aug - 17 Oct 2026,
slippage 1 tick, commission on, default settings; the first 14 sessions are the noise's history, so trades start 8
Sep). Trade list: [`data/nt_strategy_analyzer_2026-08-18_10-17.csv`](../data/nt_strategy_analyzer_2026-08-18_10-17.csv);
check: [`research/nt_run_check.py`](../research/nt_run_check.py).

- **70 trades, +$9,276 net, 52.9% winners, profit factor 2.08**, largest loss $410, max drawdown $3,750 (28 Sep - 13
  Oct, 9 red days in 10).
- **The rules held in NinjaTrader's own fills**: every bot trade 4 MNQ, every losing bot stop $207.60-209.60 (the $200
  max loss + fees + a tick), the lock's +$10.40 exits; breakout trades 1-9 MNQ from the $400 risk, worst -$409.50;
  bot entries the minute after the half-hour checks; three breakout trades handed to the bot in the same minute;
  everything flat by 16:01.
- **Through the Apex evaluation's rules** (the $2,000 trail, close at $3,000; worst point of each trade first): started
  8 Sep it passes on **21 Sep at 12:33** (10 sessions). Started on each day: 14 pass, **7 bust** (the starts from 23 Sep
  to 5 Oct, which run into the slide), 2 too late to finish.
- Six weeks of a strongly trending stretch: well above the 16-year average (35-37% of evaluations passed). It shows the
  strategy runs in NinjaTrader as tested; it is not a forecast.

## Round one hundred and forty: v1.7, the v1.5 size with more winners (October 22, 2026)

**What the user asked:** the v1.5 results (10 MNQ, $350 max loss) with more winning trades, after the daily
candidate G (docs/CANDIDATE_G.md) made about $170 on the same TradingView chart.

**What was changed:** the lock trigger, from 1.0 to 0.85 max losses, so 14.9 points at 10 MNQ instead of 17.5. Nothing
else changed. The evidence is the earlier rounds:
- "The lock dial, finely": NQ futures 2015-2025 on 1-minute bars, 51.1% winners against 48.8%, $132 against $129 a
  day ×10, and a worst stretch of $16,377 against $18,347.

**On the user's MNQ bars** (traded contracts, 6/29-10/16/2026, `research/v15_lock_mnq.py`; the user's v1.5 source in
the interpreter at 10 MNQ and $350):

| | 5-min, script costs ($0.62 / 1 tick) | 5-min, $0.95 / 2 ticks | 1-min, script costs | 1-min, $0.95 / 2 ticks |
|---|---|---|---|---|
| Lock 1.0 (v1.5) | 45 / 111 winners (40.5%), +$21,487 | 40.9%, +$21,731 | 50.8%, +$20,624 | 48.7%, +$19,438 |
| **Lock 0.85 (v1.7)** | **49 / 112 (43.8%), +$24,078** | **43.4%, +$20,501** | **52.0%, +$23,625** | **52.4%, +$19,746** |
| Lock 0.75 | 43.4%, +$23,710 | 42.1%, +$20,087 | 50.4%, +$20,918 | 50.0%, +$17,312 |

The closed-trade drawdown is the same, $4,181 (5-minute, script costs).

**The trade-off is the one rounds 52-58 found:**
- An earlier lock saves stopped-out losers and cuts some runners short.
- At $0.95 and 2 ticks on the 5-minute chart, 0.85 made about 6% less than 1.0 on these weeks.
- Over 2023-2025 on NQ futures it roughly tied.

**The evaluation size:** v1.7's evaluation size is 10 MNQ, as v1.5 traded, at the user's choice. 3 MNQ passed more
historical $50K evaluations (round thirteen).

**The chart:** the 1-minute chart, or a broker's auto-breakeven, shows the lock's real win rate. The 5-minute chart moves
it a bar late.

## v1.8: the stop only ever tightens, on TradingView too (October 22, 2026)

**The rule:** round one hundred and thirty-nine adopted it for the NinjaTrader strategy. In a trade, the stop never
moves back toward the price. The Pine script had it only in webhook mode; v1.8 adds the setting **"Stop only ever
tightens"**, on by default.

**On the user's MNQ bars** (5-minute chart, 10 MNQ, $350):
- At the script's costs: +$24,296 against +$24,078.
- At $0.95 / 2 ticks: +$20,704 against +$20,501.
- On the 1-minute chart: +$23,858 against +$23,625.

The same trades, winners and drawdown each time.

**The user's request this time:** "more profits and less losses."

**What the earlier rounds found about filtering the quick stop-outs, which are most of the losses:**
- The S&P confirmation, spike filters, better entry prices, waiting, time exits, a second chance, more room and a
  VWAP stop each cost more profit than they saved, or failed the recent years (rounds 36-58, 95, 116, 138).
- Over the first minutes after an entry, price is close to a coin flip. The lock trigger is the dial between more
  winners and more profit from the runners.

## v1.9: a $450 max loss at 10 MNQ (October 22, 2026)

**The request:** the user's TradingView chart of v1.8 showed +$15,838 (7/27-10/21/2026, 10 MNQ). They asked for
$20,000 with fewer losses.

**The search** (`research/v18_scan.py`):
- 168 combinations of take-profit, loser limit, lock trigger and lock offset, on the user's MNQ bars and on NQ futures
  2015-2025 and the index 2011-2026 (5-minute bars, scaled).
- **No combination beat v1.8's net ÷ drawdown on both histories.** The settings that raised the window most removed the
  loser limit, and added 28-32% to the historical drawdowns.

**The max loss, the setting not in that grid:**
- At 10 MNQ, $350 is a 17.5-point stop, which ordinary 5-minute noise hits.

| 10 MNQ, script costs | Window net | Window DD | Window win % | NQ net / DD | Index net / DD |
|---|---:|---:|---:|---:|---:|
| $350 (17.5 pts, v1.8) | 23,483 | 4,181 | 42.6 | 242,616 / 25,169 | 478,204 / 39,239 |
| $375 | 19,899 | 4,481 | 40.7 | 242,551 / 24,228 | 485,259 / 39,455 |
| $400 | 27,409 | 3,799 | 47.3 | 235,263 / 27,757 | 464,219 / 42,426 |
| $425 | 31,123 | 3,904 | 51.5 | 260,035 / 27,424 | 490,854 / 36,146 |
| $437.50 | 30,601 | 4,016 | 51.5 | 273,173 / 24,030 | 509,656 / 36,722 |
| **$450 (22.5 pts, v1.9)** | **29,506** | **4,161** | **50.0** | **277,715 / 24,149** | **485,245 / 39,271** |
| $462.50 | 30,398 | 3,761 | 52.0 | 294,942 / 22,657 | 514,502 / 35,781 |
| $475 | 31,085 | 3,861 | 54.0 | 279,615 / 25,174 | 501,269 / 35,820 |
| $500 | 33,697 | 3,958 | 56.0 | 291,791 / 27,946 | 499,096 / 38,925 |
| $550 | 32,039 | 5,583 | 54.5 | 288,827 / 31,170 | 529,686 / 38,343 |

The window is the user's MNQ bars, trades from 7/27 to 10/16/2026 (the end of the data).

**At $0.95 / 2 ticks, $450 against $350:**

| | $450 | $350 |
|---|---:|---:|
| Window net | 28,317 | 19,418 |
| Window DD | 4,289 | 4,778 |
| NQ net | 186,130 | 143,620 |
| NQ DD | 32,421 | 34,582 |
| Index net | 345,962 | 354,778 |
| Index DD | 45,291 | 45,282 |

**$425-$475 is a plateau**; $400 and below are worse. v1.9 takes $450, the middle of the plateau and not its best
point.

**On the window** (the Pine script itself, in tests/pine_interpreter.py):
- 102 trades, 51 winners (50%), +$29,506, drawdown $4,161.
- v1.8: 108, 46 (43%), +$23,483, drawdown $4,181.
- Losing trades fall from 62 to 51. Each can lose up to $450 plus costs, so their total is a little larger ($22,122
  against $20,899).
- Four losers in a day, the daily limit, is now about $1,850, close to a $2,000 trailing drawdown.

**The caveats:**
- The setting was chosen after looking at the user's window. The histories are what support it.
- On the index at the higher costs it is level, not better.

## v2.0: a $500 max loss, take-profit 2.0, lock 0.75 (October 22, 2026)

**Why v1.9 missed on the user's chart:**
- v1.9 showed +$15,813 on the user's chart against v1.8's +$15,838, with a larger drawdown.
- **The bars are the same:** the trades of 10/16 match the user's trade log to the tick.
- **The chart starts trading on 8/24, not 7/27.** TradingView loads too little 5-minute history for the 14 warm-up
  sessions before then.
- From 8/24 to 10/16 the model gives v1.8 $17,973 and v1.9 $18,562. The chart, less its 10/19-10/21 trades (from the
  user's log), gives $17,975 and $18,550.
- The earlier window (from 7/27) had included a July that the chart never trades.

**The search on the chart's window** (8/24-10/16 from the bars, plus 10/19-10/21 estimated as six full stops and one
locked win, as the user's log shows them):
- 72 combinations of max loss ($350-$500), take-profit (1.25-2.0), loser limit (3, 4) and lock (0.75-1.0).
- Then 60 around the best: $475-$600, take-profit 1.75-2.5, lock 0.65-0.85.
- Every row with NQ futures 2015-2025 and the index 2011-2026 (5-minute, scaled) beside it, in
  `verification/noise_v2/`.

| 10 MNQ, script costs | Window net | Est. with 10/19-21 | Window DD | Losers / trades | Losses $ | NQ net, net/DD vs v1.8 | Index net, net/DD vs v1.8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1.8 ($350, TP 1.5, lock 0.85) | 17,973 | 15,801 | 3,100 | 42 / 77 | -14,026 | 1.00, 1.00 | 1.00, 1.00 |
| **v2.0 ($500, TP 2.0, lock 0.75)** | **22,762** | **19,690** | **2,934** | **24 / 62** | **-11,392** | **1.30, 1.20** | **1.12, 1.12** |
| $500, TP 2.25, lock 0.75 | 25,071 | 21,999 | 2,934 | 23 / 59 | -10,865 | 1.30, 1.20 | 1.02, 0.89 |
| $525, TP 2.0, lock 0.85 | 24,264 | 21,042 | 4,234 | 25 / 62 | -13,005 | 1.50, 1.22 | 1.17, 1.23 |

**Why v2.0 and not the others:**
- v2.0 is the only setting that improves net and net per drawdown on both histories.
- On the window it also lowers the drawdown, the number of losers and the total lost.
- The window rides on a few take-profits: from take-profit 2.25 to 2.5 its net falls by about $10,000. So the settings
  that show more than $20,000 there were not taken, since they are worse on the index or on NQ 2023-2025.

**Its weak spot:** NQ 2023-2025 nets $11,767, against v1.8's $22,747. The index 2023-2026 nets $79,283, against
$73,672.

**The daily loser limit:** four losers in a day is about $2,070. On an evaluation with a $2,000 trailing drawdown, set
the daily loser limit to 3.

## The v2.1 study: no daily stop, fewer losers in a row (October 22, 2026; not adopted)

**The request:** v2.0 showed +$19,749 on the user's chart (drawdown $3,280, 57% winners). The user asked for more, to
keep trading after losses, and for fewer losing trades back to back.

**What was tested** (`research/v21_streak_scan.py`; `verification/noise_v2/streak_scan.csv`):
- the research-only rules added to `mnqbot/noise.py`, all off by default;
- the daily loser limit removed;
- a skip of the next one or two signals after two or three losers in a row;
- a cooldown on the side that lost;
- a stronger breakout required on the side that lost.

| v2.0 settings, 10 MNQ | Window net | Window DD | Window losers / trades | Window longest streak | NQ net / DD | NQ longest streak | Index net / DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| **v2.0 (loser limit 4)** | **22,762** | **2,934** | **24 / 62** | **4** | **315,996 / 27,294** | 17 | **533,461 / 39,085** |
| No loser limit | 22,230 | 2,934 | 25 / 63 | 5 | 311,467 / 37,878 | 13 | 533,662 / 47,775 |
| No limit, skip 1 after 2 in a row | 24,116 | 2,908 | 23 / 54 | 5 | 233,094 / 41,025 | 13 | 493,593 / 39,162 |
| No limit, skip 2 after 2 in a row | 14,353 | 2,962 | 22 / 52 | 4 | 270,467 / 27,225 | 10 | 436,134 / 33,046 |
| No limit, skip 1 after 3 in a row | 18,548 | 3,087 | 26 / 59 | 4 | 276,146 / 54,503 | 12 | 503,596 / 46,966 |
| No limit, side cooldown 1 | 17,549 | 3,441 | 29 / 61 | 5 | 204,755 / 45,902 | 16 | 388,086 / 39,775 |
| No limit, side margin 0.25 | 22,784 | 2,075 | 22 / 55 | 4 | 300,638 / 44,304 | 14 | 519,580 / 42,487 |
| Limit 4, skip 1 after 3 in a row | 18,583 | 3,087 | 25 / 59 | 4 | 330,195 / 33,105 | 14 | 549,908 / 42,016 |

**What it found:**
- **Removing the daily loser limit** changes little on the window ($532 less, one more loser in a row). Over the
  histories it adds 39% to the NQ drawdown and 22% to the index drawdown. The limit is what caps the bad days.
- **No streak rule shortened the losing streaks without costing money or drawdown on the histories.** The best on the
  window, the side margin, has a drawdown 62% larger on NQ.
- **Why:** losers come in runs because the first minutes after an entry are close to a coin flip (round forty-three).
  A skipped signal is as likely to be the winner as the next loser.

**Not adopted:** v2.0 stays.

## v2.1: a wider stop on the trade after a losing trade (October 22, 2026)

**The request:** turn consecutive losses into wins, with fewer losers back to back.

**The idea:** losers come in runs on choppy days, when ordinary noise reaches a 25-point stop. So the trade after a
loser gets a wider stop and is not skipped. Skipping was the v2.1 study's approach, and it failed.

**What was tested** (`research/v22_after_loss.py`, the research-only `after_loss_*` options of `mnqbot/noise.py`):
- an earlier lock on that trade;
- hourly checks only after a loss;
- fewer contracts, the same max loss;
- a larger max loss with the same contracts;
- combinations of these.

**The "back-to-back" measure:** the share of losers followed by another loser. All rows in
`verification/noise_v2/after_loss*.csv`.

| v2.0 otherwise, 10 MNQ | Window net | Window DD | Back-to-back % | Longest streak | NQ net / DD | NQ back-to-back % | Index net / DD | Index back-to-back % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v2.0 | 22,762 | 2,934 | 41.7 | 4 | 315,996 / 27,294 | 56.7 | 533,461 / 39,085 | 55.4 |
| Earlier lock (0.4) after a loss | 19,430 | 3,451 | 46.4 | 4 | 283,875 / 33,972 | 56.0 | 550,548 / 36,286 | 54.1 |
| Hourly checks only after a loss | 23,776 | 3,061 | 43.5 | 5 | 168,060 / 36,822 | 57.1 | 418,054 / 38,930 | 55.2 |
| 5 MNQ, $500 after a loss | 19,726 | 2,142 | 30.0 | 3 | 252,544 / 30,740 | 46.8 | 432,892 / 30,214 | 47.5 |
| 10 MNQ, $750 after a loss | 25,729 | 3,314 | 39.1 | 3 | 323,486 / 33,444 | 50.6 | 605,499 / 37,100 | 49.9 |
| 8 MNQ, $625 after a loss | 23,752 | 2,446 | 36.4 | 3 | 300,272 / 29,574 | 50.4 | 553,479 / 33,111 | 49.5 |
| **9 MNQ, $700 after a loss (v2.1)** | **25,052** | **2,580** | **36.4** | **3** | **317,536 / 31,550** | **50.5** | **587,013 / 33,394** | **49.5** |

**What the scan shows:**
- **A wider stop after a loss cuts the back-to-back losers on every dataset**, in all nine variants of the
  neighbourhood scan, and the window's longest streak falls to 3 in every one.
- An earlier lock or hourly-only checks don't.

**What v2.1 costs:**
- NQ's worst drawdown grows 16% ($31,550 against $27,294) at the same net.
- That trade risks up to $700.
- NQ 2023-2025 nets $13,549 against $11,767. The index 2023-2026 nets $105,731 against $79,283.

**On the window:** the Pine script itself gives the same as the model: 57 trades (22 of them at 9 MNQ), +$25,052,
drawdown $2,580.

## v2.2: no new entries from the 15:30 check (October 22, 2026)

**The user's chart for v2.1:** +$21,257, drawdown $3,845, 56% winners. Most of the drawdown is 10/19-10/21: four
after-loss trades in a row, each stopped for about $700.

**Tested on top of v2.1, not adopted** (`verification/noise_v2/after_loss4.csv`, `runner.csv`):
- **A second tier after two or more losers in a row** (7 MNQ / $500, 5 / $500, 9 / $500, back to 10 / $500, 9 / $900,
  8 / $625):
  - The best, 8 / $625, keeps the stop distance and risks less on the third and later trades of a run.
  - Net and drawdown came out about equal to v2.1: index net per drawdown 1.31 against 1.29 of v2.0's, NQ 0.88
    against 0.87, the window $23,840 against $25,052.
- **The wider stop only on the losing trade's side:** the back-to-back share rose again (39% on the window).
- **A runner after the take-profit:**
  - Keeping 30% or 50% of the contracts past the target, with or without locking half its distance and a second
    target at 4 noise units.
  - Less on every dataset: the window $17,270-$18,600 against $25,052; NQ and the index 6-20% less.
  - The full take-profit is the better exit for this strategy.

**Adopted: no new entries from the 15:30 check.**

By entry time at v2.1's settings, the 15:30 entries lost on average on every dataset:

| | 15:30 entries | Average | Total |
|---|---:|---:|---:|
| NQ 2015-2025 | 258 | -$58 | -$14,869 |
| Index 2011-2026 | 370 | -$53 | -$19,481 |
| Window | 4 | -$293 | -$1,173 |

They have 25 minutes to reach a two-noise-unit target before 15:55. Round thirty-four found the opposite at the old
settings (a 17.5-point stop and a 1.5 target), where the 15:30 entries paid.

| | Window net / DD | NQ net / DD | Index net / DD |
|---|---|---|---|
| v2.1 | 25,052 / 2,580 | 317,536 / 31,550 | 587,013 / 33,394 |
| **v2.2: last entry 15:00** | **26,425 / 2,613** | **329,768 / 31,888** | **606,437 / 30,697** |
| Last entry 14:30 | 26,360 / 2,613 | 300,549 / 30,015 | 537,357 / 32,702 |

**Year by year it is mixed:** better in 6 of 11 NQ years and 9 of 16 index years. It is a small edge with a reason
behind it, not a large one.

**The heads-up:** v2.2 also stops the five-minutes-ahead alert for a check that can no longer open a trade.

**The Pine script on the window:** 53 trades, 33 winners, +$26,425, drawdown $2,613, the same as the model.

## On top of v2.2: none adopted (October 22, 2026)

**The tests** (`verification/noise_v2/lockplus.csv`, `v23_scan.csv`), against v2.2 on the window, NQ 2015-2025 and
the index 2011-2026:

| Change | Window net | Net per drawdown vs v2.2: NQ / index | Verdict |
|---|---:|---|---|
| None (v2.2: lock trigger 0.75, offset 2.5 points) | 26,425 | 1.00 / 1.00 | |
| Lock trigger 0.65 or 0.85, offset 2.5 | 27,173 / 26,425 | 0.90 / 0.94 and 0.97 / 0.96 | lower on the histories |
| Lock offset 5 or 8 points (each trigger) | 17,994-23,649 | 0.62-0.88 / 0.61-0.81 | lower |
| Take-profit 1.5 / 1.75 / 2.5 on the after-loss trade | 22,044 / 22,990 / 20,777 | 0.78-0.99 / 0.75-0.90 | lower |
| Daily loser limit 3 / 5 | 25,649 / 26,425 | 0.98 / 0.73 and 0.90 / 0.82 | lower |
| Second tier 8 MNQ / $625 from the second loser in a row | 25,055 | 1.02 / 1.00 | level; less on the window |

## v2.2 on the user's chart, and the next rounds (October 22, 2026)

**The user's chart for v2.2** (MNQ1! 5-minute, 7/27-10/21, trading from 8/24):

| Net | Drawdown | Winners | Profit factor |
|---:|---:|---:|---:|
| +$22,641 | $3,845 | 33 / 58 (56.9%) | 2.54 |

v2.1 showed +$21,257 and $3,845. The drawdown is the six-loser run of 10/19-10/21, which is past the end of the bars
here.

**Re-tested under v2.2, none better on both histories** (`research/v23_scan.py`; `verification/noise_v2/v23_dials.csv`,
`v23_risk.csv`):
- **The noise lookback (10, 20)** gives a smaller net per drawdown on the window and on one of the histories.
- **The line-stop buffer (0, 0.5, 1.0):**
  - 0.5 and 1.0 are level with 0.24: net per drawdown 0.99-1.00 on NQ and 0.96-0.97 on the index, $544 less on the
    window.
  - 0 is worse.
- **The entry band (0.9 / 1.1 / 1.25 x the noise area):**
  - 1.1 is the best on the window: +$27,416, 67% winners.
  - It cuts NQ's net per drawdown to 0.65 of v2.2's, and loses money on NQ 2023-2025.
- **A smaller take-profit for afternoon entries:** level or lower.
- **Max loss $475 / $500 / $525 x take-profit 1.9 / 2.0 / 2.1 x after-loss max loss $650 / $700 / $750 (27 rows):**
  - A plateau. The best rows trade the window against the histories: take-profit 2.1 makes $28,100-28,600 on the
    window but 0.73-0.93 of NQ's net per drawdown.
  - Nothing is better on all three.
- **The Williams breakout in the bot's gaps** (rounds 98-137): more net, but about 35% winners. Its standalone record
  is weak in the newest year (round 137). Not added, since the user's request is more winners and fewer losers.

**Bar length, the same rules on the window:**

| | Trades | Winners | Net | Drawdown | Losses |
|---|---:|---:|---:|---:|---:|
| 5-minute bars | 53 | 33 (62%) | +$26,425 | $2,613 | -$10,909 |
| **1-minute bars** | **60** | **41 (68%)** | **+$26,542** | **$2,613** | **-$10,377** |

The lock acts within a minute instead of a bar late, so more trades close as small winners. A broker's auto-breakeven
set to the same trigger (18.75 points at 10 MNQ and $500, offset +2.5) gets the 1-minute behaviour live.

## v2.3: after a big day, no trades in its direction the next day (October 22, 2026)

**The finding** (descriptive at first, at v2.2's settings): the trades the day after a big-range session, by whether
they go the way that session went. A big session has a range over 1.5 x the 20-session average.

| | With the big day's direction | Against it | Other days |
|---|---|---|---|
| NQ 2015-2025 | 365 trades, -$112 each (-$40,803) | 474, +$148 each | about +$75 each |
| Index 2011-2026 | 536, -$67 each (-$35,715) | 615, +$190 each | about +$90 each |
| User's window | 7, +$9 each | 11, +$999 each | |

After an outsized session the next one tends to retrace, so breakouts that continue it fail.

**The rule as tested** (`research/v23_scan.py` set "bigday", `mnqbot/noise.py` `big_day_k` / `big_day_n`):
- At 09:30, if the last session's 09:30-16:00 range (as a share of its open) beat big_day_k x the average of the last
  big_day_n sessions (it included), no entries or heads-ups today in its direction (close against open).
- The other direction trades as usual.
- The whole strategy is re-run, not trades removed from a list.

| Rule | Window net | NQ net / DD | NQ net per DD vs v2.2 | NQ 2015-19 / 2020-25 | NQ years better | Index net / DD | Index net per DD vs v2.2 | Index 2011-18 / 2019-26 | Index years better |
|---|---:|---|---:|---|---:|---|---:|---|---:|
| v2.2 | 26,425 | 329,768 / 31,888 | 1.00 | 169,589 / 160,179 | | 606,437 / 30,697 | 1.00 | 294,342 / 312,095 | |
| 1.25 x / 10 | 25,811 | 324,159 / 27,066 | 1.16 | 150,112 / 174,047 | 7 / 11 | 578,170 / 28,714 | 1.02 | 311,311 / 266,859 | 8 / 16 |
| 1.25 x / 20 | 25,811 | 330,852 / 23,231 | 1.38 | 170,640 / 160,212 | 7 | 588,651 / 28,739 | 1.04 | 323,122 / 265,529 | 6 |
| **1.5 x / 10 (v2.3)** | **25,295** | **375,170 / 26,135** | **1.39** | **183,401 / 191,769** | **8** | **669,794 / 29,602** | **1.15** | **350,774 / 319,020** | **12** |
| 1.5 x / 20 | 25,295 | 358,874 / 27,346 | 1.27 | 178,899 / 179,975 | 7 | 639,619 / 29,602 | 1.09 | 336,297 / 303,322 | 11 |
| 1.75 x / 10 | 25,295 | 377,127 / 30,131 | 1.21 | 184,438 / 192,690 | 10 | 642,307 / 30,354 | 1.07 | 313,951 / 328,356 | 13 |
| 1.75 x / 20 | 25,295 | 349,913 / 30,787 | 1.10 | 160,607 / 189,305 | 8 | 655,604 / 29,602 | 1.12 | 327,917 / 327,687 | 13 |
| 2.0 x / 10 | 26,425 | 336,083 / 31,888 | 1.02 | 167,050 / 169,032 | 7 | 623,082 / 30,697 | 1.03 | 298,827 / 324,255 | 10 |
| 2.0 x / 20 | 25,295 | 359,611 / 31,762 | 1.09 | 172,162 / 187,449 | 10 | 636,979 / 30,697 | 1.05 | 317,698 / 319,280 | 14 |

**From 1.5 x to 2.0 x every row improves both halves of both histories.** At 1.25 x the late index half falls. 1.5 x
/ 10 is taken, the best on both histories, with its neighbours also better than v2.2.

**v2.3 against v2.2, across the histories:**

| | Net | Drawdown | Winners | Trades |
|---|---|---|---|---|
| NQ | +14% | -18% | 49.7% against 49.0% | 4,497 against 4,818 |
| Index | +10% | -4% | 50.3% against 49.7% | 6,407 against 6,862 |

NQ 2023-2025 nets $37,217 against $20,493.

**On the user's window** it skips one day, 9/22: four longs after the big up day of 9/21, which there made +$1,130.
So the window shows +$25,295 against +$26,425, with the same drawdown. (The other blocked day in the bars, 7/28, is
before the chart trades and lost $1,065.)

**The Pine script on the window:** 49 trades, 30 winners, +$25,295, drawdown $2,613, the same as the model. The
setting is "After a big day" (0 turns it off).

## After v2.3: checks and studies (October 22, 2026)

**Every component of v2.3 still earns its place with the others present** (`research/v23_scan.py` set "ablate",
`verification/noise_v2/v23_ablate.csv`). One at a time back to its earlier value:

| v2.3 without | Window net | NQ net per DD vs v2.3 | Index net per DD vs v2.3 |
|---|---:|---:|---:|
| (v2.3) | 25,295 | 1.00 | 1.00 |
| the after-loss size and max loss | 21,909 | 0.93 | 0.75 |
| the 15:00 last entry | 23,923 | 0.84 | 0.90 |
| the stop that only tightens | 25,072 | 0.97 | 0.99 |
| v2.0's risk ($500, take-profit 2.0, lock 0.75), back to v1.8's | 20,112 | 0.62 | 0.65 |
| the daily loser limit (0 = none) | 25,295 | 0.94 | 0.73 |

**Not adopted:**
- **A larger take-profit for trades against the big day** (none / 2.5 / 3.0; `v23_against.csv`): none +1-3%, 2.5
  -2%, 3.0 +4% on the histories, all less on the window. Not monotone, so not trusted.
- **Day-level descriptions, at v2.3's settings, on NQ and the index:**
  - the overnight gap's size and direction;
  - yesterday's direction alone;
  - yesterday's range in buckets below 1.5 x;
  - two days after a big day;
  - how far price had already run from the open at entry, in fifths.

  No bucket loses on both histories, so there is nothing to filter. Two days after a big day the effect is gone (NQ
  -$59 against, the index +$17).

**Also not adopted, on top of v2.3** (`research/v23_scan.py` set "next", `v23_next.csv`):
- a second after-loss tier;
- fewer contracts against the big day, or no trades at all the day after it;
- skipping a side after 2, 3 or 4 losers in a row on that side across days.

None was better on both histories.

## v2.4: room for the trade (October 22, 2026)

The user's TradingView view of v2.3 over January 2, 2025 - October 21, 2026 (MNQ1!, 30-minute chart, 50K): +$55,485,
drawdown $19,185, 41.9% winners, profit factor 1.29. The user trades on 5-minute charts.

**A stand-in for that view.** TradingView's 5-minute history doesn't reach back that far, and these files hold no MNQ
bars before mid-2026. `research/v24_proxy.py` splices three sources at raw prices, each later piece scaled to meet the
earlier one at the splice:
- NQ futures to 7/23/2025;
- the Nasdaq-100 index (HistData) to 6/30/2026;
- the user's MNQ bars after.

It is not TradingView's bars. The three sources disagree month by month: April 2025 is +$3.9k on NQ and +$16.3k on the
index at 30 minutes. So it shows direction, not the chart's dollar figures.

The script and `mnqbot/noise.py` agree trade for trade on 30-minute bars as well (the interpreter, 100 trades,
January-May 2025).

| v2.3 | Net | Drawdown | Trades | Winners | Profit factor |
|---|---:|---:|---:|---:|---:|
| stand-in, 5-minute | 60,345 | 27,577 | 651 | 52.5% | 1.36 |
| stand-in, 30-minute | 69,861 | 18,693 | 539 | 43.2% | 1.40 |

**Where v2.3 lost (5-minute stand-in).**
- 253 max-loss stops: -$150k.
- 281 lock exits: +$4k (scratches).
- 55 trades held to 16:00 and 24 take-profits: +$216k.

The $500 max loss (25 points at 10 MNQ) sat inside ordinary 5-minute noise. v2.0's grid only covered $475-525, so it
missed this.

**Wider stops** (`research/v24_scan.py`; `verification/noise_v2/v24_grid1.csv`, `v24_grid2.csv`, `v24_grid3.csv`,
`v24_refB.csv`):
- Every max loss from $1,000 to $1,500, at every lock trigger tried, beat $500 on the stand-in, NQ futures 2015-2025 and
  the index 2011-2026.
- Above $1,500 the index got worse (rare large losses): net per drawdown 0.6-0.9 of v2.3's at $2,500-3,000.
- One at a time around the pick (none better on both histories):
  - take-profit 1.5-3.0 or off;
  - lock offset 5 or 10 points;
  - after-loss size or max loss;
  - the max loss $1,250 or $1,750;
  - the big-day rule off or at 1.25 / 1.75;
  - the 15:30 entries back;
  - stop buffer 0.5;
  - lookback 10 or 20.
- The one small gain was 3 losers a day instead of 4: net per drawdown 1.07 on both histories, and a smaller worst day.

**v2.4:** max loss $1,500, lock at 0.5 max losses (37.5 points), after a loser 9 MNQ and $2,100, 3 losers a day.

| | v2.3 | v2.4 | v2.4, 2 ticks a side |
|---|---:|---:|---:|
| Stand-in 5-min 2025-10/2026: net | 60,345 | **106,385** | 101,033 |
| drawdown | 27,577 | **14,811** | 15,054 |
| winners | 52.5% | **59.5%** | 59.5% |
| profit factor | 1.36 | **1.55** | 1.52 |
| NQ 2015-2025: net | 375,170 | **597,743** | 553,614 |
| drawdown | 26,135 | 27,333 | 31,834 |
| winners / profit factor | 49.7% / 1.29 | **59.7% / 1.38** | 59.6% / 1.35 |
| Index 2011-2026: net | 669,794 | **904,778** | 849,406 |
| drawdown | 29,602 | 33,928 | 34,414 |
| winners / profit factor | 50.3% / 1.38 | **58.8% / 1.41** | 58.6% / 1.38 |
| User's window 8/24-10/16 (5-min): net | **25,295** | 17,730 | 17,468 |
| drawdown | **2,613** | 4,129 | 4,189 |
| Stand-in 30-min: net | **69,861** | 64,571 | 61,120 |
| drawdown | **18,693** | 20,995 | 22,580 |

**Year by year.** v2.4 is better in 10 of 11 NQ years and 12 of 16 index years.

**Costs of the change.**
- NQ's worst trade (-$23.6k) is not real. The scaled history's day-to-day rescaling made a 1,300-point gap after the
  11/29/2024 half day, and a position held through it.
- A v2.4 loser costs up to about $1,500, or $2,100 after a loser. The worst day on the stand-in is -$4,585, against
  -$2,822. That is too much for a $2,000 trailing-drawdown evaluation.
- On the user's 8/24-10/16 window it makes less. v2.3's settings were chosen on that window.
- On 30-minute bars it makes less too. The lock moves only at a bar's close there. v2.4 is chosen for the 5-minute
  chart the user trades.

**Not adopted along the way:**
- **Contracts added when the lock arms** (3, 5, 10; `v24_add.csv`). The lock's scratch trades turn into losers: the
  stand-in fell to $48-49k, and the index's net per drawdown to 0.44-0.62.
- **A trend filter**: the last close against the average of the last 5-50 closes (`v24_trend.csv`, `v24_trend2.csv`,
  `v24_trend3.csv`).
  - Against $500 stops, a wider stop on counter-trend trades helped a lot. That was the stop, not the trend: a wider
    stop on every trade did as well.
  - On top of v2.4 (`v24_filtB.csv`), blocking counter-trend trades raised the stand-in's profit factor to 1.6-1.8 but
    cut NQ's net by 16-51%.
- **Other filters on top of v2.4** (`v24_filtB.csv`). None better on both histories:
  - no 14:00 or 13:00 entries;
  - no 10:00 entries (the stand-in's weakest check, but the histories' best);
  - no entries after a take-profit fills;
  - a stricter entry band (1.1, 1.2);
  - stop buffer 0 or 0.1;
  - a side cooldown, a side run or a streak skip.
- **Volatility regime**: no quintile of the 10-day against 100-day range ratio, or of the 10-day range itself, loses on
  all three sets. So nothing to size by.

**Toward the user's 30-minute targets** (net $100k+, drawdown under $10k, 70%+ winners, profit factor 2+ on the
30-minute chart; `SCAN_MINUTES=30 research/v24_scan.py`):
- **The 30-minute chart.**
  - v2.4 there: $64,571, drawdown $20,995, 49.6% winners, profit factor 1.32.
  - Why it lags the 5-minute chart: on a 30-minute bar the lock arms only at the bar's close.
  - 112 of 417 trades stop out inside the bar they entered, for -$129k. The line stop sits about 20-25 points from the
    fill (0.24 noise units past the line).
- **Within the strategy's own settings** (`v24_g30_1.csv`, 81 combinations): max loss $1,000-2,000, lock trigger
  15-37.5 points, take-profit 1.0-2.0, trend filter none / 5 / 10. The 30-minute stand-in topped out at profit factor
  1.63 and 60% winners. The best profit factors all used the 5-day trend filter, which halves net on the histories.
- **Not adopted:**
  - **A trailing stop once the lock arms** (`v24_trail5.csv`). TradingView's broker would run it inside the bar on a
    30-minute chart. Every offset (22.5-100 points) cut the stand-in's profit factor to 1.20-1.39 and both histories'
    net per drawdown to 0.52-0.97.
  - **Scaling out** part of the position at 0.1-0.5 R (`v24_part5.csv`). Winners as TradingView counts them rose to
    75-78% and the stand-in's drawdown fell to $8.8-11.4k. But net fell to $48-83k, profit factor to 1.37-1.47, and
    both histories' net per drawdown to 0.29-0.93.
  - **A wider line stop** (0.5-3 noise units on 30-minute bars; `v24_sb30.csv`). The stand-in made less with a larger
    drawdown: the tight line stop keeps losers small.
  - **Equity-curve sizing** (`v24_eq5.csv`, `v24_eq30.csv`): fewer contracts while the closed P&L is under its average
    of the last 5-40 trades. Net fell 30-50% on the histories, and drawdown wasn't better on both.

## v2.5: no trades after a calm stretch (October 22, 2026)

**The rule.** When the last 10 sessions' average 09:30-16:00 range (as a share of the open) is under 0.7 x the last 40
sessions', there are no new entries or heads-ups that day (`calm_k`, `calm_short`, `calm_long` in `mnqbot/noise.py`).

**The evidence.**
- A per-trade look at v2.4's trades (the noise level, distance past the line, run from the open, range so far, gap,
  yesterday's return, 5/20-day trend, trades earlier today, the 10/60-day range ratio, check time) found one pattern
  that held on all three sets: the lowest fifth of the range ratio.
  - 5-minute bars: index +$41 a trade, NQ +$96, the stand-in -$94 (the other fifths +$127 to +$375).
  - 30-minute bars: -$31, +$96, -$136.
- Robustness (`verification/noise_v2/v24_calm5.csv`, `v24_calm30.csv`, `v24_calm2_5.csv`, `v24_calm2_30.csv`): at
  every pair of lengths (5, 10 or 20 against 40, 60 or 100 sessions) and both thresholds (0.7, 0.8), the profit factor
  rose on the stand-in, NQ and the index, on 5- and 30-minute bars. The one exception was NQ at 20/100 (1.371 against
  1.375).
- Net per drawdown on the histories was mostly 0.85-1.06x. 10 against 40 at 0.7 kept both histories' net level or
  better (5-minute: NQ 1.01x, index 1.03x; 30-minute: 1.01x, 1.06x).
- Taking half the contracts instead of none (`calm_div` 2) was in between.

**Also in v2.5:**
- The 2025 holidays, half days and Fed days are now in the default lists, for TradingView backtests from January 2025.
- On half days (e.g. 11/29/2024, 11/26/2021) a position can otherwise be held past the early close into the next
  session. On the scaled histories that produced -$4k to -$24k trades, worse for the scaling but real as a risk.
- Some other overnight holds on the histories come from missing 16:00 bars in the data, which TradingView's bars
  don't have.

| Stand-in 1/2025-10/2026 (with the 2025 dates) | Net | Drawdown | Trades | Winners | Profit factor |
|---|---:|---:|---:|---:|---:|
| 5-min v2.3 | 63,033 | 24,889 | 644 | 52.5% | 1.38 |
| 5-min v2.4 | 109,026 | 14,811 | 473 | 59.8% | 1.58 |
| 5-min **v2.5** | **112,731** | **14,811** | 439 | **60.1%** | **1.64** |
| 30-min v2.3 | 72,047 | 18,693 | 533 | 43.2% | 1.42 |
| 30-min v2.4 | 67,212 | 18,354 | 413 | 49.9% | 1.34 |
| 30-min **v2.5** | **71,111** | **17,524** | 383 | **50.4%** | **1.39** |

| Histories, 5-minute | Net | Drawdown | Winners | Profit factor |
|---|---:|---:|---:|---:|
| NQ 2015-2025 v2.4 | 597,743 | 27,333 | 59.7% | 1.375 |
| NQ 2015-2025 **v2.5** | 600,937 | 29,836 | 59.9% | **1.407** |
| Index 2011-2026 v2.4 | 904,778 | 33,928 | 58.8% | 1.414 |
| Index 2011-2026 **v2.5** | **932,901** | 33,928 | 59.3% | **1.459** |

On the user's 8/24-10/16 window (5-minute) v2.5 makes +$16,607: profit factor 2.10, 60% winners, 35 trades.

**Not adopted on the way:**
- **A two-stage lock** (`v24_lock1_5.csv`, `v24_lock1_30.csv`): at +11-25 points the stop to the entry -10/-25/-40
  points, then the lock. Net per drawdown 0.72-1.14, not better on both histories.
- **The last half hour in the direction of the first** (Gao et al.): -$127k to +$78k on the histories, profit factor
  0.93-1.05. The effect is gone in these data.
- **No entries from the 14:00 or 13:00 checks** (weak on all three sets). The 30-minute stand-in made less.
- **Two checks in a row past the line before entering** (`confirm`; `v25_confirm5.csv`, `v25_confirm30.csv`). The
  30-minute stand-in made $45-55k against $71k, and NQ's net was 0.67-0.77x. Waiting gives up the move.
- **A grace period**: only the max loss until the first check after the fill (`grace`; `v25_grace5.csv`,
  `v25_grace30.csv`). The 30-minute stand-in made $55-69k with a $19.7-24.8k drawdown, and the index's net was
  0.89-0.91x. The line stop's early exits save more than they cost.
- **The max loss in noise units** (`cap_sigma` 0.4-1.0 x the check's noise; `v25_capsig5.csv`, `v25_capsig30.csv`).
  It lowers the stand-in's 5-minute net to $88-93k, and the index's net per drawdown falls to 0.32-0.89x.

**Every setting re-tested under v2.5** (`v25_dials25_5.csv`, `v25_dials25_30.csv`):
- lookback 10/12/16/20;
- take-profit 2.5/3.0;
- stop buffer 0.15/0.35;
- big-day rule off / 1.25 / 1.75;
- 2 or 4 losers a day;
- the 15:30 entries;
- the after-loss rule off;
- the stop that only tightens off;
- lock offset 5.

None is better on the stand-in and both histories at both bar lengths:
- The after-loss rule off improves the histories and the user's window on 5-minute bars (NQ net 1.09x, index 1.02x;
  window 70% winners), but on the 30-minute stand-in it makes $57.8k with a $26.2k drawdown against $71.1k and $17.5k.
- A take-profit of 3.0 helps the 30-minute histories and hurts the 5-minute index (0.95x net).

**Walk-forward** (`research/v25_walk_forward.py`). Each year, the settings with the best net per drawdown over the
earlier years trade that year. The grid: max loss $500 / $1,000 / $1,500, lock 0.5 / 0.75, calm rule off / on.

| | Walk-forward | v2.3's risk ($500, lock 0.75) | v2.5 fixed |
|---|---:|---:|---:|
| NQ 2018-2025: net | 446,368 | 275,568 | 497,659 |
| NQ 2018-2025: drawdown | 25,507 | 26,135 | 29,836 |
| Index 2014-2026: net | 621,639 | 560,795 | 742,249 |
| Index 2014-2026: drawdown | 32,423 | 29,602 | 33,928 |

- Picked in real time, the wider stop ($1,000-1,500) wins from the first years. The calm rule is picked in most years.
- v2.5's fixed figures include hindsight. A live expectation sits between the walk-forward column and v2.5's.

```
python research/v24_proxy.py <data dir> MNQ_09-26.Last.txt MNQ_12-26.Last.txt          # the stand-in
python research/v24_scan.py '[{"max_losers": 4}]' out.csv '{"max_loss_per_trade": 1500, "lock_at": 0.5, "max_losers": 3}' \
    <data dir> MNQ_09-26.Last.txt MNQ_12-26.Last.txt                                    # v2.4 against a variant
```

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
python research/better_entry.py nsx_1m_scaled.pkl nq_1m_scaled.pkl    # limit-then-market, second chance (no pass)
python research/es_confirm.py spx_1m.pkl nsx_1m_scaled.pkl             # the S&P at the signal (descriptive)
python research/drop_losers.py nsx_1m_scaled.pkl nq_1m_scaled.pkl     # options-expiry Fridays, walk-forward checks (no)
python research/time_exits.py nsx_1m_scaled.pkl nq_1m_scaled.pkl      # time lock, time exit (no)
python research/release_days.py nsx_1m_scaled.pkl nq_1m_scaled.pkl    # no 10:00 entry on ISM days (no)
python research/mes.py nsx_1m_scaled.pkl spx_1m_scaled.pkl             # the same bot on MES (no edge)
python research/confirm_lock.py spx_1m.pkl nsx_1m_scaled.pkl nq_1m_scaled.pkl  # earlier lock if the S&P disagrees (no)
python research/walkforward_tp35.py nsx_1m_scaled.pkl nq_1m_scaled.pkl  # the take-profit at $35, walk-forward (1.5 stays)
python research/walkforward_more.py nsx_1m_scaled.pkl nq_1m_scaled.pkl  # lookback, lock offset, loser limit (all stay)
python research/lock_sigma.py nsx_1m_scaled.pkl nq_1m_scaled.pkl       # a noise-scaled lock trigger (ties 2019-22)
python research/lock_early.py nsx_1m_scaled.pkl nq_1m_scaled.pkl       # the earlier lock in the first minutes (no)
python research/noise_median.py nsx_1m_scaled.pkl nq_1m_scaled.pkl     # median / trimmed-mean noise (no)
python research/checks15.py nsx_1m_scaled.pkl nq_1m_scaled.pkl        # a check every 15 minutes (no)
python research/offset_checks.py nsx_1m_scaled.pkl nq_1m_scaled.pkl    # checks off the half hour (no)
python research/lock_half.py nsx_1m_scaled.pkl nq_1m_scaled.pkl        # earlier lock for half-hour entries (no, by $0.06)
python research/weak_trend_lock.py spx_1m.pkl nsx_1m_scaled.pkl nq_1m_scaled.pkl  # weak-trend lock (index yes, NQ no)
python research/williams_combo.py nsx1m_scaled.pkl nq1m_scaled.pkl     # the Williams breakout added to the bot (no)
python research/williams_sized.py nsx1m_scaled.pkl nq1m_scaled.pkl     # sized to a fixed risk (positive alone)
python research/combo_live.py nsx1m_scaled.pkl nq1m_scaled.pkl         # one position at a time, first come (no)
python research/combo_priority.py nsx1m_scaled.pkl nq1m_scaled.pkl     # the bot first, Williams in the gaps (built in)
python research/combo_more.py nsx1m_scaled.pkl nq1m_scaled.pkl         # breakout together, stop-and-reverse (no)
python research/w_manage.py nsx1m_scaled.pkl nq1m_scaled.pkl           # lock / take-profit for the breakout (no)
python research/overnight_drift.py nsx1m_scaled.pkl nq1m_scaled.pkl    # the overnight drift (positive, below the bar)
python research/overnight_combo.py nsx1m_scaled.pkl nq1m_scaled.pkl    # the overnight long on the account (no)
python research/overnight_first.py nsx1m_scaled.pkl nq1m_scaled.pkl    # ... until the first payout (no)
python research/eod_plan.py nsx1m_scaled.pkl nq1m_scaled.pkl          # the EOD-trail evaluation (reference)
python research/eod_full.py nsx1m_scaled.pkl nq1m_scaled.pkl          # the EOD route end to end (reference)
python research/eval_lock.py nsx1m_scaled.pkl nq1m_scaled.pkl         # if the evaluation's threshold stops (no)
python research/last_half_hour.py nsx1m_scaled.pkl nq1m_scaled.pkl    # intraday momentum into the close (no)
python research/combo_late.py nsx1m_scaled.pkl nq1m_scaled.pkl        # late breakout entries, a smaller together (no)
python research/eval_lock_w.py nsx1m_scaled.pkl nq1m_scaled.pkl       # the evaluation's lock with the breakout (no)
python research/day_giveback.py nsx1m_scaled.pkl nq1m_scaled.pkl      # a daily give-back stop (no)
python research/overnight_early.py nsx1m_scaled.pkl nq1m_scaled.pkl   # overnight 18:00-02:00 (passes; recent data no)
python research/cushion_size.py nsx1m_scaled.pkl nq1m_scaled.pkl      # smaller size on a thin cushion (no)
python research/vwap_stop.py nsx1m_scaled.pkl nq1m_scaled.pkl         # the paper's VWAP trailing stop (no)
python research/w_long.py nsx1m_scaled.pkl nq1m_scaled.pkl            # the breakout's shorts smaller or dropped (no)
python research/touch_size.py nsx1m_scaled.pkl nq1m_scaled.pkl        # smaller bot trades before a breakout touch (no)
python research/edge_hours.py nsx1m_scaled.pkl nq1m_scaled.pkl        # after the close, before the open (nothing)
python research/overnight_range.py nsx1m_scaled.pkl nq1m_scaled.pkl   # a breakout of the overnight range (no)
python research/funded_w.py nsx1m_scaled.pkl nq1m_scaled.pkl          # the breakout's risk on the funded side ($200 stays)
python research/funded_bot.py nsx1m_scaled.pkl nq1m_scaled.pkl        # the bot's funded settings with the breakout (stay)
python research/eval_bot.py nsx1m_scaled.pkl nq1m_scaled.pkl          # the bot's evaluation settings with the breakout (stay)
python research/pass_lock.py nsx1m_scaled.pkl nq1m_scaled.pkl         # close everything at the evaluation's target (adopted)
python research/pass_lock_size.py nsx1m_scaled.pkl nq1m_scaled.pkl    # the evaluation's size with it (4 MNQ stays)
python research/retest_lock.py nsx1m_scaled.pkl nq1m_scaled.pkl       # the near-misses with close-at-target (no)
python research/payout_buffer.py nsx1m_scaled.pkl nq1m_scaled.pkl     # when to ask for a payout (as soon as allowed)
python research/payout_lock.py nsx1m_scaled.pkl nq1m_scaled.pkl       # stop when payout-eligible (faster, not more)
python research/bold_finish.py nsx1m_scaled.pkl nq1m_scaled.pkl       # bolder near the evaluation's end (option, off)
python research/w_bracket.py nsx1m_scaled.pkl nq1m_scaled.pkl         # a take-profit for the breakout (8 stops)
python research/w_lock_target.py nsx1m_scaled.pkl nq1m_scaled.pkl     # the breakout's lock for more winners (no)
python research/accounts_needed.py nsx1m_scaled.pkl nq1m_scaled.pkl 260 # $ a week per account slot (payout stop on)
python research/slot_size.py nsx1m_scaled.pkl nq1m_scaled.pkl          # sizes judged per week (6 MNQ eval: setting, not default)
python research/slot_eval.py nsx1m_scaled.pkl nq1m_scaled.pkl          # breakout $400 in the evaluation (adopted)
python research/slot_funded.py nsx1m_scaled.pkl nq1m_scaled.pkl        # funded settings per week (none adopted)
python research/vol_target.py nsx1m_scaled.pkl nq1m_scaled.pkl         # volatility-targeted size (not adopted)
python research/components.py nsx1m_scaled.pkl nq1m_scaled.pkl         # the breakout's place (stays, shorts too)
python research/exits.py nsx1m_scaled.pkl nq1m_scaled.pkl              # trail / half at 1R vs the lock (lock stays)
python research/exits2.py nsx1m_scaled.pkl nq1m_scaled.pkl             # tighten-only stop (adopted)
python research/nt_run_check.py data/nt_strategy_analyzer_2026-08-18_10-17.csv  # the NinjaTrader run
```

The raw data isn't stored in this repo.
