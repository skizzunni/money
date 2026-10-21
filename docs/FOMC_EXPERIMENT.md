# The pre-FOMC drift: a separate experiment (not the daily strategy)

**Status:**
- **A labelled research experiment.** It is not part of the daily MNQ strategy and is not deployed under any
  main-bot preset.
- **Package:** `release/MnqFomcDrift_experiment/`, its own install and settings. Run it only on its own simulation
  account.

**Why it is not the main deliverable:**
- It trades about 8 announcements a year. The user's requirement is a daily strategy with 2-3 qualified entry
  campaigns per eligible session.
- Its overnight hold, its 2-MNQ size with only a 4% catastrophe stop (planned risk far past $125), and its lack of
  breakeven, half and runner all differ from the daily strategy's shared rules.
- **No variant of it is progress toward the daily participation requirement.**

**The rule** (`ninjatrader/Strategies/MnqFomcDrift.cs`, `mnqbot/fomc.py`; trade-for-trade parity on the stand-in,
`tests/test_fomc_drift.py`):
- Long at the 14:00 bar's open on the weekday before a scheduled FOMC announcement.
- Sold at the 13:55 bar's open on the day.

**Simulator results** (docs/NET_VS_DRAWDOWN.md section 4):
- 2011-2026: 125 announcements, +$108.70 a trade at 1 MNQ and 2 ticks, t 2.11.
- Carried by 2020 and 2022.
- July 2025 to September 2026: 10 announcements, −$1,588 at 2 MNQ.

## Native NinjaTrader run (the user's, `NinjaTrader_Grid_2026-10-21_06-47_PM.csv`)

**The run:**
- Strategy Analyzer, MNQ, 1/1 to 10/20/2026.
- The native DEC26 data has bars from 5/3, with a hole from 5/22 to 6/26, so only the 7/29 and 9/16 announcements
  had bars.
- **The settings:** $0.95 a side; the grid shows slippage $0.

| Native | Value |
|---|---|
| Trades | 2 (long) |
| Net | −$335.60 |
| Gross profit / gross loss | $722.20 / −$1,057.80 |
| Commission | $7.60 (2 trades × 2 MNQ × 2 sides × $0.95) |
| Average time in market | 1,435 minutes |

**Reconciliation with the stand-in** (`mnqbot/fomc.py` on the user's MNQ bars, at 0 ticks):

| Announcement | Stand-in | Native |
|---|---:|---:|
| 2026-07-29 | −$1,057.80 | −$1,057.80 |
| 2026-09-16 | +$722.20 | +$722.20 |

**Native and simulator agree to the cent on both trades.**
