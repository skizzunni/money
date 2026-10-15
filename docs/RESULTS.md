# Does the bot have an edge? A multi-year test

**Verdict: no.** On 3¾ years of Nasdaq-100 data, none of the seven pre-declared variants shows an edge that survives costs. The variant picked on the tuning years lost money on the unseen years. **Don't pay for a prop evaluation to trade these rules.**

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

## What this does and doesn't say

- **It says** that these specific rules, on 5-minute Nasdaq-100 data from 2023 to 2026, have no edge after realistic costs. It also says they would very likely not pass a $25K evaluation.
- **It doesn't say** that sweeps or breakouts can never work. Other rules, timeframes or filters weren't tested.
- **Testing more variants on the same data would be data-mining.** Anything found that way would need fresh unseen data to be believed.
- **Risk control can't create an edge that isn't there.** Once the data holes are removed, the rails kept every loss within 1.01R and every day under the $300 limit, and the rules still lost money.

## Reproduce

Download the `NSXUSD` ASCII 1-minute files from HistData.com, then run:

```bash
python research/nsx_study.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"   # the study
python research/nsx_holes.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"   # the data-hole check and best case
```

The raw data isn't stored in this repo.
