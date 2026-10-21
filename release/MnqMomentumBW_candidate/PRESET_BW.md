# Preset BW: frozen B plus its Williams breakout in the gaps, breakout risk $600 (continuous trading)

**What it is:** frozen B v1.1's own file (`MnqNoiseMomentum.cs`, unchanged) with two settings changed. The bot trades
exactly as B. The breakout stream trades only while the bot is flat, and is closed when the bot enters.

**The two changes:**

| Setting (group) | B | **BW** |
|---|---|---|
| Breakout in the bot's gaps (5) | Off | **On** |
| Risk a trade in the evaluation, $ (sets the contracts; 5) | 400 (unused) | **600** |

**For a continuous account,** not an evaluation:
- Evaluation: close everything at this profit, $ (1) = **0 (off)**. With 3000 the strategy stops once it is $3,000
  up, which is the evaluation's rule, not this objective's.

**Every other setting is as PRESET_B-NATIVE-v1.1.md / PRESET_B-PRACTICE-v1.1.md:**
- 4 MNQ, $200 max loss, 3 losers, take-profit 1.5 / line stop 0.24 noise units, lock 1.0 / 2.5;
- 1-minute bars, CME US Index Futures ETH, 45 days to load;
- commission $0.95 a side; slippage 2 ticks (base), 3 (stress).

**Why $600** (docs/NET_VS_DRAWDOWN.md):
- Each year from 2017, the breakout risk with the best net / drawdown over all earlier NQ years was chosen. The
  choice was $200 for 2017-2019, then $600 from 2020 on.
- $600 is the choice for the next year.
- The breakout's sizing: contracts = floor(risk / its stop's dollars), at most 10.

**Checking it natively:**
1. Strategy Analyzer on MNQ DEC26 with the settings above.
2. The Output's "MNQ settings:" line must show "UseBreakout True".
3. Compare with `research/ratio_study.py`'s "B + W risk 600" trades on the same bars.
- The breakout part of this file has run on the NinjaTrader stand-in only. Native NinjaTrader reconciled B
  (UseBreakout Off).
