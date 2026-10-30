# Candidate P1 — UNVERIFIED (pre-registration)

Written and committed on 2026-10-30, before `research/p1_spread.py` was run on any data.

Nothing here promises a profit, a win rate or the absence of losses.

## The hypothesis

The Nasdaq-100 and the S&P 500 move together. Within a session, the gap between them, after hedging the S&P part,
stretches and then tends to snap back toward where the day began.

A hedged position trades only that gap, not the market's direction:
- short MNQ / long MES when the Nasdaq has run ahead;
- the reverse when it has lagged.

**Not tested before:**
- Round 69 (`leadlag.py`) used the Nasdaq-minus-S&P return only as a cue to trade the Nasdaq alone.
- Every other candidate was a one-sided MNQ position.

## Frozen rules

**Data and the spread**
- Data: 5-minute regular-hours bars of the Nasdaq-100 and the S&P 500, matched by timestamp. The sources are
  `nsx1m_scaled.pkl` and `spx1m_scaled.pkl`: HistData cash indices, with each session scaled to today's price level.
- The spread at bar t: x = ln(N_t / N_open) − β · ln(S_t / S_open). N_open and S_open are the 09:30 bar's opens.
- β: the least-squares slope of the 5-minute Nasdaq log returns on the S&P's, over the previous 20 sessions.
- σ: the standard deviation of the 5-minute spread returns over the previous 20 sessions, × √(bars since 09:30).
- z = x / σ.

**Entry**
- At a bar close from 10:00 to 15:00, if |z| ≥ Z: fade the gap at the next bar's open.
  - z > 0: short MNQ, long MES.
  - z < 0: long MNQ, short MES.
- At most 2 trades a day, one at a time.

**Size**
- 2 MNQ against q MES, with q = round(2 × β × (2 × N) / (5 × S)), at least 1.
- That is about dollar-neutral after β.

**Exit** at the next bar's open after a bar closes with:
- z back to Zexit or nearer zero; or
- |z| ≥ Z + Zstop (the stop);
- else at the 15:55 bar's close.

**Costs**
- $0.62 a contract a side on both legs.
- 1 tick of slippage on every fill: $0.50 for MNQ and $1.25 for MES.

## Development grid (2011-2018 only)

| Setting | Values |
|---|---|
| Z | 1.5, 2.0, 2.5 |
| Zstop | 1.0, 2.0, none |
| Zexit | 0.0, 0.5 |

That makes 18 settings, all reported.

**Selection:**
- Keep the settings with at least 25 trades a year and a positive mean net per trade.
- Of those, pick the one with the highest t-statistic of net per trade.
- If none qualifies, P1 is rejected.

## Holdouts (one run, the frozen setting only)

1. 2019-2024.
2. The user's window, Jan 2 2025 – Sep 30 2026. That is where the index data ends, and both legs are needed, so the
   MNQ stand-in cannot be used.

## Measured

- Trades, and the share of sessions with a trade.
- Gross, costs and net $ per trade.
- t.
- The net win % (a win means above $0 after all costs) and the breakeven win %.
- PF and net $.
- Closed drawdown, and marked-equity drawdown.
  - The marked drawdown is conservative: at every bar, each leg is marked at its own adverse extreme (high or low) at
    the same moment.

## Gate and acceptance

**Gate before any change in size:** on the 2019-2024 holdout, the mean net per trade is above $0 and t ≥ 2.0.

**Acceptance:** the user's targets on the user's window:
- net at least $75,000;
- net win at least 80%;
- PF at least 2.0;
- marked-equity DD under $4,000.

At the base size they are reported as measured. A larger size would be a separate, later step, taken only if the gate
passes, and it would be reported with its drawdown.

## Development results (2011-2018; `verification/noise_v2/p1_dev.csv`): P1 rejected

- **All 18 settings lost money.**
  - Net per trade was −$23.64 to −$62.21, with t from −4.2 to −6.7.
  - Even gross, before costs, every setting lost (−$5.83 to −$44.41 a trade). Costs were about $17.80 a trade for 2
    MNQ plus about 3.6 MES.
- No setting qualifies, so P1 is rejected at the development stage, and its holdout is not run.
- **What it shows:** inside a session, the hedged gap between the Nasdaq-100 and the S&P 500 tended to keep going,
  not to come back. Fading it lost before costs.

## Candidate P2 (registered 2026-10-30, after P1's development run and before any run of P2)

**Disclosure:** P2 is the opposite of P1, and the idea comes from P1's development losses. So 2011-2018 is not an
independent test for P2. P2's evidence is only its holdouts, 2019-2024 and the user's window, which no candidate has
been run on.

**Rules:** as P1, except:
- **Entry:** follow the gap. At a bar close from 10:00 to 15:00 with |z| ≥ Z, z > 0: long MNQ / short MES; z < 0:
  the reverse.
- **Exit:** at the next bar's open after z falls back to Zback or nearer zero (|z| shrinking toward zero is the
  stop); else at the 15:55 bar's close. There is no target.
- At most 1 trade a day.
- The development grid (2011-2018): Z in {1.5, 2.0, 2.5}; Zback in {0.0, 1.0, none}. That is 9 settings.
- Selection, gate and acceptance are the same as P1:
  - at least 25 trades a year and a positive mean on development, and the highest t;
  - holdout 2019-2024: mean above $0 and t ≥ 2.0;
  - then the user's targets on Jan 2025 – Sep 2026.

**Note, stated before the run:** a follow-the-trend trade with no target usually wins less than half the time, so the
80% net win target is unlikely by its structure. It is tested because it may have a real edge, and the results are
reported whatever they show.
