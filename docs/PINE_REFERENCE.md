# The Pine reference and the two-loss candidate (pre-registration, October 20, 2026)

Written and committed **before any run** described here. Nothing below replaces a working version: the Pine script,
frozen B and candidate C stay as they are. The candidate is a **settings preset**, compared with its reference.

## The reference

**The user's exact Pine script:** `pine/reference/mnq_noise_momentum_v1.5_user.pine`.
- sha256 `cd44ee68d575e74019cd308f1079838a2b5cb7453d8b7c40473436c59b851975`; the bytes as pasted, CRLF line endings.
- Its content is the repo's Pine v1.5 at commit 5e092d0: 0 differing lines, ignoring line endings.
- The repo's current `pine/mnq_noise_momentum.pine` is v1.6 and is not the reference.

**Its settings (R4):**
- the script's own defaults, except 2 contracts and a $70 max loss per trade;
- that keeps the defaults' stop distance of 17.5 points a contract (the $350 over 10 contracts), and with it the lock
  trigger of 17.5 points;
- 5-minute chart; 4 losing trades a day.
- These are the settings of the independent tests the user quoted.
- **Assumption:** the user's saved TradingView inputs were not provided. If they differ, the reference runs again with
  them.

**The candidate (R2):** R4 with the daily losing-trade limit at **2 instead of 4**. Nothing else changes: not the stop
distance, size, lock, take-profit or entry filters.

## Reproduction, before any comparison

The reference runs three ways on the same bars:
- the MNQ traded-contract series (09-26 to the 9/10 roll session, then 12-26, 09-26 back-adjusted);
- aggregated to 5-minute bars, 09:30 to 16:00, warm-up from 6/29.

| | What runs | Label |
|---|---|---|
| (a) | The Pine v1.5 source itself, in the repo's Pine interpreter (`tests/pine_interpreter.py`, TradingView's fill rules as emulated there) | Pine source, emulated; not TradingView |
| (b) | The NinjaTrader strategy MnqNoiseMomentum, frozen B's code (sha256 `1fbdcea0...`, engine `e5a1ec0c...`), at R4's settings, in the NinjaTrader stand-in | NinjaTrader code, stand-in simulator |
| (c) | The Python reference `mnqbot/noise.py` | Reference model |

**R-check:** (a) and (c) must agree trade for trade. (a) against (b) is joined trade by trade, and every mismatch must
be explained by a documented platform difference.
- A true TradingView-versus-NinjaTrader join needs TradingView's own List of Trades export and the matching NinjaTrader
  run: the user's to produce. The join tool takes both files.

## Comparison R2 against R4: full strategy runs, not trades deleted from an export

**Primary evidence:**
- the NinjaTrader strategy (b) on the MNQ traded contracts, 7/20 to 10/16/2026;
- commission $0.95 a side; slippage 1 and 2 ticks.
- **This period is development data:** examined in earlier rounds. It is not untouched.

**Secondary:**
- NQ 2015-03 to 2025-06, rescaled to MNQ terms (also examined before), by calendar year;
- 2023-01 to 2025-06 shown apart, the span closest to the quoted tests.

**Reported for each:**
- **Continuous research, every eligible session counted:**
  - trades per eligible session and the share of sessions with 0 / 1 / 2 / 3+ trades;
  - net and net per session; months (MNQ) or years (NQ); long and short apart;
  - profit factor; expectancy per trade; the five largest winners' share;
  - closed and intraday drawdown (open P/L at bar extremes); losing streak; worst day;
  - the trades R4 has and R2 does not.
- **Evaluation replay, Apex $50K intraday trail:**
  - from every start, identical for both, to the first pass, breach or expiry;
  - the highest equity including open P/L, a trail that persists across days;
  - 30 calendar days; unfinished starts apart.

## Acceptance criteria (decided now): R2 replaces R4 as the reference's daily limit only if all hold

- **Q1:** R2's net after costs is positive at 1 and 2 ticks, on MNQ and on NQ.
- **Q2:** R2's net divided by its intraday drawdown is higher than R4's at 1 and 2 ticks, on MNQ and on NQ.
- **Q3:** the trades the limit removes are net negative at both slippages, on MNQ and on NQ. These are R4's trades that
  R2 does not take.
- **Q4:** in the evaluation replay, R2's chance of passing (expirations counted) is at least R4's, and its certain
  breaches are no more, at both slippages, on MNQ and on NQ.
- **Q5:** on NQ at 1 tick, R2 nets more than R4 in at least 7 of the 11 calendar years.

**Frequency** (1-2 trades per eligible session preferred) is reported but not a criterion. No entry is ever added to
meet it.

**If a criterion fails, R4 stays the reference** and the result is reported as a rejection.

## Candidate C: separate items in this round

- **Shutdown:** outcomes reported as pass / breach / expired while still able to trade / unable to fund another trade
  under the internal reserve (then expired). Individual evaluations from explicit start dates.
- **Execution fixes, each with a focused test:**
  - a partially filled entry's remainder is tracked until it is filled or cancelled;
  - losing positions are counted by the entry order's identity, not by fill timestamps;
  - an unrealized peak reached in a bar where the position exits is captured.
- **Unchanged:** C's rules, settings and exits otherwise.
