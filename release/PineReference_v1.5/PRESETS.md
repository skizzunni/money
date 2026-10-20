# Presets: the Pine v1.5 reference (R4) and its two-loss comparison (R2)

The two presets differ in **one setting only**: the daily losing-trade limit (4 or 2). Everything else is the
reference's.
- 2 MNQ, $70 max loss per trade (17.5 points a contract, the script's default distance); lock at 17.5 points to entry
  + 2.5; take-profit 1.5 noise units; line stop 0.24 noise units past the line, free to follow the line; 5-minute
  chart.
- These are the settings of the independent tests the user quoted. Change them only if the user's saved TradingView
  inputs differ.

## TradingView (the Pine script `pine/mnq_noise_momentum_v1.5_user.pine`, unchanged)

**Chart:** MNQ1! (or the front contract), **5 minutes**, the default session (ETH). Bar magnifier off.

**Inputs:**

| Input | R4 (reference) | R2 (comparison) |
|---|---|---|
| Sessions in the noise average | 14 | 14 |
| Contracts | **2** | **2** |
| Max loss per trade, $ | **70** | **70** |
| Don't trade on these dates / Fed days / Fed dates | defaults | defaults |
| Exit | Resting stop at the line | Resting stop at the line |
| Stop distance past the line | 0.24 | 0.24 |
| Take profit, noise units | 1.5 | 1.5 |
| Lock trigger / lock plus | 1.0 / 2.5 | 1.0 / 2.5 |
| **Max losing trades a day** | **4** | **2** |
| Webhook orders | Off | Off |

**Properties tab:**
- Commission **0.95 USD per contract** (the script's own default is 0.62).
- Slippage **1 tick**, then a second run at **2 ticks**.
- Initial capital 50,000. Order size: from the script.

## NinjaTrader (MnqNoiseMomentum: frozen B's two files, sha256 in `SHA256SUMS.txt`)

**Chart or Strategy Analyzer:**
- MNQ (DEC26, or the traded contract per period), **5 Minute**, trading hours CME US Index Futures ETH.
- Commission template $0.95 a side; slippage 1, then 2.

| Setting (group) | R4 | R2 |
|---|---|---|
| FUNDED ACCOUNT (1) | Off | Off |
| Evaluation or funded from the account's name (1) | Off | Off |
| Contracts in an evaluation (1) | **2** | **2** |
| Evaluation: max loss per trade, $ (1) | **70** | **70** |
| **Evaluation: no new entries after this many losers today (1)** | **4** | **2** |
| Place orders (1) | On | On |
| Evaluation: close everything at this profit, $ (1) | 3000 (live only; no effect in a backtest) | 3000 |
| Stop only ever tightens (1) | **Off** (the Pine script's stop follows the line) | **Off** |
| Bot: close half at R / Daily gate losers / Daily gate $ (1) | 0 / 0 / 0 | 0 / 0 / 0 |
| Take-profit, noise units (2) | 1.5 | 1.5 |
| Line stop, noise units past the line (2) | 0.24 | 0.24 |
| Evaluation: lock at / lock plus (2) | 1.0 / 2.5 | 1.0 / 2.5 |
| Noise lookback (3) | 14 | 14 |
| Fed days: no shorts before 14:00; skip and Fed dates (3) | On; defaults | On; defaults |
| Breakout in the bot's gaps (5) | **Off** | **Off** |
| Diagnostics (6) | On | On |

Save these as templates **PINE-REF-4L** and **PINE-REF-2L**.

## Known, measured differences between the two platforms (`docs/PINE_REFERENCE.md`)

On identical 5-minute MNQ bars, these explain every mismatch between the Pine source and the NinjaTrader strategy:

| | What differs | Effect |
|---|---|---|
| A | 16:00 exit: Pine closes at the 15:55 bar's close; NinjaTrader's market exit fills at the next bar's open | Small |
| B | Same exit price, named differently: Pine "Lock"; NinjaTrader "Stop passed" | Name only |
| C | Fill-bar max-loss stop: Pine measures it from the expected fill (signal close ± 1 tick); NinjaTrader's bracket from the actual fill | Either way, depending on the bars. At 1 tick: 13 trades better and 20 worse for NinjaTrader, −$1,195 in all, of which −$1,168 is one trade (8/3 10:30, a low exactly at NinjaTrader's stop). At 2 ticks: 30 better, 11 worse. |
| D | NinjaTrader rounds stops and targets to a tick | Cents |

**Also:** at 2 ticks of slippage, Pine's fill-bar stop still uses 1 tick for the expected fill.
