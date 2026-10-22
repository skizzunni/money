# Preset G-CANDIDATE: MnqCandidateD, variant G-D cap line

**Candidate G** (docs/CANDIDATE_G.md) is the daily strategy with its stop fitted to the $125 budget, and noise
campaigns that follow the noise line. It runs on the same strategy file as D/E/F.

**Status:** see docs/CANDIDATE_G.md for the holdout results and the gates. Use it on a simulation account until the
native check below has been run.

## Chart / Strategy Analyzer

| Setting | Value |
|---|---|
| Instrument | MNQ front month (DEC26 now) |
| Data series | **1 Minute**, trading hours **CME US Index Futures ETH** |
| Days to load / start date | at least 45 days before the first tested session |
| Commission | a template of **$0.95 a side a contract** |
| Slippage | **2 ticks (base)**, 3 ticks (stress) |
| Order fill resolution | **High**, 1 Tick if the tick history is loaded (else 1 Second) |
| Calculate | On bar close |
| Entries per direction / handling | 1 / Unique entries |
| Exit on session close | On |
| Stop & target submission | Per entry execution |

## Strategy parameters

| Group | Setting | G-D cap line |
|---|---|---|
| 1 | Noise momentum / Williams breakout | **On / On** |
| 1 | Sweep reversal E1 / E2 | **Off / Off** |
| 1 | Sweep initial stop | (unused) |
| 1 | **Stop wider than the budget** | **Cap** |
| 1 | **Noise campaigns: runner trail** | **Line** |
| 2 | Planned risk budget, $ (2 contracts, all-in) | 125 |
| 2 | Commission a side, $ | 0.95 |
| 2 | Slippage allowance, ticks a contract: market / limit | 4 / 2 |
| 2 | Breakeven stop, points past the fill | 1.5 |
| 2 | Half off at R / runner trail R | 2 / 1 (the 1R trail is used by Williams campaigns) |
| 2 | Entry campaigns a day | 3 |
| 2 | Flat bar (minute of day) | 954 (15:54, filled 15:55) |
| 3 | Line stop, noise units | 0.24 |
| 3 | Skip dates / FOMC dates / NFP dates | defaults (as PRESET_D-CANDIDATE.md) |
| 4 | Evaluation target / trailing drawdown, $ | 3000 / 2000 on an account; **0 / 0 in the Strategy Analyzer** |
| 4 | Account starting balance; remember the highest equity | 50000; On |
| 4 | Place orders | On |
| 4 | Print refusals (the daily opportunity audit) | On |

**What the settings do:**
- A qualified setup whose structural stop is wider than 29.25 points (market) is taken with its stop moved in to
  29.25 points. With Skip it would be refused.
- A noise campaign's stop follows the noise line, tightened only. After the half is off, the runner trails that line.

**The same strategy elsewhere:**
- **TradingView:** `pine/mnq_daily_g.pine`, at its defaults.
- **Python:** `DConfig(stop_fit="cap", runner_trail="line")`.

## Native check

**Steps:**
1. Run the Strategy Analyzer on MNQ DEC26, 9/11 to 10/16/2026, with the settings above at 2 ticks.
2. Export the Trades and the NinjaScript Output.
3. Compare them with `research/d_parity.py`'s "G-D cap line" configuration: the same entries, exits and P/L per
   position.

**What to look for in the Output:**
- Each entry prints its stop, R, price risk and planned risk. The planned risk is never above $125.
- A breakeven, line or trail stop that cannot be placed (beyond the bar's close) is replaced by a market exit named
  "Stop passed".
