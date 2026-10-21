# MnqFomcDrift: a separate experiment, not part of the daily MNQ strategy

**What it is:**
- A long MNQ position from 14:00 on the weekday before each scheduled FOMC announcement to 13:55 on the day: about
  8 trades a year, each held overnight.
- It is **not** the daily strategy (docs/CANDIDATE_D.md, docs/CANDIDATE_F.md), and it does not follow the daily
  strategy's shared rules:
  - it holds overnight instead of flattening at 15:55;
  - it is 2 MNQ with only a 4% catastrophe stop, so its planned risk is far beyond the $125 budget;
  - it has no +1R breakeven, no half at +2R and no runner.
- **Do not run it under any main-bot preset or on the main bot's account.** It is kept as an experiment.
  docs/FOMC_EXPERIMENT.md has its results, including a native NinjaTrader run.

**Settings, for an experiment run on its own simulation account:**

| Setting | Value |
|---|---|
| Chart | MNQ front month, 1 Minute, CME US Index Futures ETH, 10 days to load |
| Contracts | 2 |
| Catastrophe stop, % below the fill | 4 |
| FOMC announcement dates | default (2026-2027); for a backtest before 2026, paste the line in `FOMC_DATES_2011-2027.txt` |
| Exit on session close | Off (it holds overnight) |
| Commission / slippage | $0.95 a side / 2 ticks (base), 3 (stress) |
