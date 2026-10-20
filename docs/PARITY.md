# NinjaTrader ↔ Python parity on a fixed MNQ sample (October 20, 2026)

**What is compared:**
- **NinjaTrader:** the strategy's own code, `MnqNoiseMomentum.cs` (B v1.1), compiled and run on the simulator.
  Separately, the user's native NinjaTrader run at 2 ticks (B_L2).
- **Python:** the reference `mnqbot.noise.run`, with `nt_execution=True, round_prices=True`.

**The sample** (`tests/data/mnq_traded_2026-06-29_2026-10-16.csv.gz`, sha256 of the CSV
`ad73d17ab1abc11e7a4507680fe4774d4b5159f3117efbeb20c1eeafaa0f003b`):
- The user's MNQ 1-minute bars, traded contracts: 09-26 to the 9/10 roll session (back-adjusted +284.50), then 12-26.
- 09:30 to 16:00 plus the 16:00 bar.
- 6/29 to 10/16/2026: 14 sessions of warm-up, then **7/20 to 10/16 traded, 64 sessions, about three months.**

**Settings:**
- Frozen B: 4 MNQ, $200 max loss, 3 losers a day, lock 1.0 / +2.5, take-profit 1.5, line stop 0.24, tighten-only.
- $0.95 a side, **2 ticks** of slippage, prices on the 0.25 grid.

## Result (`tests/test_parity_mnq.py`)

| | Trades | Net | Agreement |
|---|---:|---:|---|
| NinjaTrader code (simulator) | 97 | $13,030.80 | |
| Python reference | 97 | $13,030.80 | **97 of 97 identical:** direction, entry and exit bar, entry and exit price, P/L |
| Native NinjaTrader, B_L2 (from 7/20) | 97 | $13,040.80 | Every trade: same entry minute, direction, contracts, exit minute and exit kind |

**Native B_L2 in detail:**
- From 10/1, where both use the same bars and noise history, the dollars are identical. One trade (10/16 11:31) filled
  0.50 point higher at both ends, for the same dollars.
- Before 10/1, every trade is within $4.00: DEC26 against 09-26 bars and a mixed noise history (docs/B_NATIVE.md).

**Exact at every slippage tried:** the same exact agreement holds at 0, 1, 2 and 3 ticks, with tick rounding on or
off (checked when the options were built).

## What made it exact: `nt_execution` and `round_prices`

The Python reference follows the Pine script by default. Three NinjaTrader behaviours differ from it. They are now
options, off by default, so every Pine parity test is unchanged.

1. **The bracket.** At the signal, the stop distance (the closer of the line stop and the max loss) and the
   take-profit distance are measured from the expected fill: the signal close plus slippage. They are placed that far
   from the **actual** fill, rounded down (stop) and up (take-profit) to whole ticks.
   - This is the "category C" difference between Pine and NinjaTrader (docs/PINE_REFERENCE.md section 1b).
2. **The 16:00 exit** is a market order filled at the 16:00 bar's open, not at the 15:59 close.
3. **A stop that the bar's close has already passed** is sent as a market exit and fills at the next bar's open
   ("Stop passed").

**And tick rounding:**
- After the fill bar, the stop is rounded toward the price before the tighten-only comparison.
- The take-profit is rounded away from the price.

**Without these options** the same sample gives 97 trades with the same entries, but only 57 of them identical: the
exits differ by these four rules.
