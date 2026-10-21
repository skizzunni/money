# Preset BWF: frozen B + its Williams breakout ($600 risk) + the pre-FOMC drift (2 MNQ)

**Two strategies on MNQ** (docs/NET_VS_DRAWDOWN.md section 5):

| | Strategy | Chart | Settings |
|---|---|---|---|
| 1 | `MnqNoiseMomentum` (frozen B v1.1's file, unchanged) | MNQ front month, 1 Minute, CME US Index Futures ETH, 45 days | As PRESET_B-PRACTICE-v1.1 / PRESET_B-NATIVE-v1.1, except: **Breakout in the bot's gaps = On**, **Risk a trade in the evaluation, $ = 600**, **Evaluation: close everything at this profit = 0 (off)** |
| 2 | `MnqFomcDrift` (new) | the same instrument, 1 Minute, **ETH**, 10 days | **Contracts 2**; catastrophe stop 4%; FOMC dates: the default list (2026-2027 scheduled announcements); **Exit on session close Off** (it holds overnight) |

**One account or two:**
- **Two accounts** (one for each strategy) reproduce the backtest exactly.
- **On one account:**
  - Live, B blocks its own new entries while the account's MNQ position differs from its own. It does so while the
    FOMC position is held: 14:00-16:00 the day before, and 09:30-13:55 on the announcement day.
  - Over 2015-2025 the trades B and its breakout would have taken in those windows lost $8,573 (106 trades). One
    account was therefore slightly better: net ÷ DD 16.2 against 15.3.
  - **Either works.** In a Strategy Analyzer backtest the block does not apply: it is realtime only.

**Why these sizes:**
- **The rule:** each year, the breakout risk (off / 200 / 400 / 600 / 800) and the FOMC contracts (0 / 1 / 2) with
  the best net ÷ drawdown over all history to date (docs/NET_VS_DRAWDOWN.md).
- **The rule's choices:**
  - with NQ through 2025-06 it chose $200 and 2 MNQ;
  - with the NSX holdout added (to 2026-09) it chooses **$600 and 2 MNQ**, at both 2 and 3 ticks, and that is this
    preset;
  - it is re-run with each new year of data.
- **Over 2015-03 to 2026-09** (closed-day drawdown, 2 ticks): net $204,977 against a $14,556 maximum drawdown,
  14.1 times; frozen B made $93,851 against $16,670, 5.6 times.

**Checks:**
- **MnqFomcDrift:**
  - The Output prints "FOMC drift settings: … 2 MNQ, catastrophe stop 4%".
  - The day before each announcement it prints "long 2 MNQ for the <date> statement", and on the day "exit before
    the <date> statement".
  - The stand-in and `mnqbot/fomc.py` agree trade for trade (`tests/test_fomc_drift.py`).
- **MnqNoiseMomentum:** the "MNQ settings:" line shows "UseBreakout True". The breakout part has run on the stand-in
  only.
