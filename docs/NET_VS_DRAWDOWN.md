# Net and gross profit against the maximum drawdown (October 21, 2026, overnight)

**The user's objective:**
> "make the total net profit and gross far exceed the maximum drawdown … only that."

**Measures:**
- Net after costs, and gross profit (the sum of the winners), each ÷ the **intraday maximum drawdown**: open P/L at
  each minute's worst price, from the highest equity before it.
- Closed-trade drawdown beside it.

**Conditions:**
- **Data:** NQ 2015-03 to 2025-06 (rescaled, $2 a point), its roll-adjusted version (docs/NQ_ROLLS.md), and the
  user's MNQ 7/20 to 10/16/2026.
- **Costs:** $0.95 a side; 2 ticks (base) and 3 ticks (stress).
- **Engine:** every result is frozen B's NinjaScript (`MnqNoiseMomentum.cs`, sha256 `d1a4f863…`) on the NinjaTrader
  stand-in (`research/ratio_study.py`). Native NinjaTrader has not run the breakout settings.

**All of it is development data.** B was built on these years. The guard against fitting is to judge every change in
both halves of NQ, at 3 ticks, on the roll-adjusted series and on MNQ. Choices are made only by walk-forward: each
year's configuration is chosen from earlier years only.

## 1. Where frozen B already stands

| Frozen B, 4 MNQ | Net | Gross profit | Intraday max DD | **Net ÷ DD** | **Gross ÷ DD** |
|---|---:|---:|---:|---:|---:|
| NQ 2015-2025, 2 ticks | $91,575 | $598,588 | $14,935 | **6.1** | **40.1** |
| NQ, 3 ticks | $73,310 | $588,400 | $15,815 | 4.6 | 37.2 |
| MNQ 2026, 2 ticks | $13,031 | $21,495 | $2,653 | **4.9** | **8.1** |
| MNQ, 3 ticks | $11,607 | $20,364 | $2,693 | 4.3 | 7.6 |

- **Over the whole record, the objective is already met.** Net is 5-6 times the worst drawdown, and gross profit 8-40
  times.
- **Not within a single year.** A year's drawdown is $6-14k on NQ every year, while the year's net ranges from −$3.9k
  to +$24.8k. 2017, 2023 and 2025 lost, and in only 6 of 11 years did net exceed that year's drawdown.
- Net ÷ drawdown rises with time and with the edge per unit of risk, not with size. Raising it needs more edge per
  unit of risk, and diversification gives that.

## 2. What was tested tonight, and the outcome

| Change | Net ÷ intraday DD, NQ 2t: all / 2015-19 / 2020-25 | 3t: all | MNQ 2t | Verdict |
|---|---|---|---|---|
| Frozen B | 6.13 / 5.42 / 3.10 | 4.64 | 4.91 | reference |
| **B + Williams breakout in the gaps, risk $200** | 9.95 / 8.84 / 4.10 | 8.01 | 4.37 | better on NQ in both halves |
| **B + breakout, risk $400 (the code's default)** | 10.46 / 8.91 / 3.77 | 8.54 | 2.36 | better on NQ in both halves |
| **B + breakout, risk $600** | **12.89 / 9.19 / 4.31** | **9.84** | 1.53 | best on NQ in both halves |
| B + breakout, risk $800 | 11.24 / 9.04 / 3.53 | 9.58 | 1.02 | |
| Volatility-scaled contracts (Zarattini et al. sizing), on B | 6.73 / 3.66 / 3.72 | 5.08 | 5.18 | **rejected**: worse in 2015-19 |
| Volatility-scaled contracts, on B + breakout $400 | 7.79 / 4.90 / 3.55 | 6.25 | 2.46 | **rejected** |
| B + breakout + 1 MNQ long overnight (18:00-09:30) | 11.00 against 11.42 (closed-day DD, roll-adjusted) | | | **rejected**: t 1.6 alone, lowers the whole-period ratio |
| B + breakout, roll-adjusted NQ | 10.55 (B 6.43) | 8.48 (B 4.80) | | the result holds |

**What earlier rounds had already tested** (docs/RESULTS.md and the research notes), restated for this objective:
- Regime, trend, spike and time filters: none held out of sample.
- Time exits and re-entries: none significant.
- Quiet-day and VWAP fades, market profile: all lost.
- Lead-lag from other markets: 0 of 200 rules survived.
- The trap reversal: consistently negative. Its mirror image, a re-entry in the original direction, was not
  significant.
- None of them adds to the objective. The Williams breakout is the one documented positive stream that is
  nearly independent of B.

**Why the breakout helps:**
- Its trades lose or win independently of B's: the daily P/L correlation is 0.03 on NQ.
- It is positive on its own: 1,618 trades over 2015-2025, $31.80 a trade, t 2.69.
- B's own trades are unchanged in the combination: 4,938 trades, $91,575.
- The diversification raises net more than it raises drawdown.

**The MNQ sample disagrees:**
- The breakout's 42 MNQ trades lost $1,686. At $600 risk the combination's ratio on MNQ is 1.5, against B's 4.9.
- Under the NQ distribution of breakout trades, 42 trades lose that much 16% of the time. So it is consistent with
  noise, but it is also the only post-2025 evidence there is, and it points the other way.
- **The breakout's edge is established on ten years of NQ only, not on MNQ.**

## 3. The out-of-sample test: walk-forward choice of the breakout's weight

**The rule** (`research/walk_forward.py`):
- Each year from 2017, choose among B and the breakout at $200 / $400 / $600 / $800 the configuration with the best
  net ÷ closed drawdown over every earlier year.
- Trade it that year. Chain the chosen years.

| 2017-2025, NQ | Net | Gross profit | Intraday DD | **Net ÷ DD** | **Gross ÷ DD** |
|---|---:|---:|---:|---:|---:|
| **Walk-forward, 2 ticks** | $99,869 | $750,618 | $13,383 | **7.46** | **56.1** |
| Frozen B, 2 ticks, same years | $69,198 | $490,630 | $14,935 | 4.63 | 32.9 |
| **Walk-forward, 3 ticks** | $116,991 | $856,931 | $17,781 | **6.58** | **48.2** |
| Frozen B, 3 ticks | $56,499 | $484,346 | $15,815 | 3.57 | 30.6 |

**The choices:**
- At 2 ticks: $200 in 2017-2019 and $600 from 2020.
- At 3 ticks: $200 / $600 / $800 / $800, then $600 from 2021.
- B alone was never chosen.
- **The choice for the year ahead is $600** (PRESET_BW).

**By year** (NQ, 2 ticks; `verification/net_vs_dd/years_B_W600_WF.csv`):

| | B | B + breakout $600 |
|---|---:|---:|
| Years with a positive net | 8 of 11 | 9 of 11 |
| Years where net exceeds that year's drawdown | 6 of 11 | 7 of 11 |

- 2020, 2023 and 2025 stay weak for both.
- **Both streams are trend-following, so choppy years hurt both.** No stream tested so far profits in those years.

## 4. A third stream: the pre-FOMC drift

**What it is:**
- Long MNQ from 14:00 on the weekday before each scheduled FOMC announcement to 13:55 on the day, out before the
  statement.
- Lucca & Moench (2015) found it on 1994-2011 data, so 2015-2025 is after its publication.
- `ninjatrader/Strategies/MnqFomcDrift.cs` and `mnqbot/fomc.py` agree trade for trade on the stand-in: on the user's
  MNQ bars, and on synthetic sessions with hand-computed values (`tests/test_fomc_drift.py`).
- **The candidates fixed beforehand:** the turn-of-month long (t 0.70 / 0.99, failed) and the pre-FOMC drift.

| Pre-FOMC, 1 MNQ, 2 ticks | Trades | $ a trade | t | Win % | Worst |
|---|---:|---:|---:|---:|---:|
| 2015-2019 | 40 | +$41 | 0.79 | 52% | −$777 |
| 2020-2025 | 43 | +$290 | 2.66 | 65% | −$1,023 |

- It was weak after publication and strong since 2020.
- Over 83 trades it never came within 2.7% of a 4% catastrophe stop.

**Added to B and its breakout** (minute equity on the full electronic session; net ÷ intraday DD):

| | 2015-19, 2t | 2020-25, 2t | 2015-19, 3t | 2020-25, 3t | 2015-2025, 2t |
|---|---:|---:|---:|---:|---:|
| Frozen B | 5.43 | 3.16 | 3.40 | 2.58 | 6.17 |
| B + 2 MNQ pre-FOMC | 6.22 | 6.88 | 4.35 | 5.78 | 11.32 |
| B + breakout $600 | 9.36 | 4.39 | 6.76 | 3.53 | 13.13 |
| B + breakout $600 + 2 pre-FOMC | 11.22 | 7.07 | 7.93 | 6.17 | 17.18 |
| **B + breakout $200 + 2 pre-FOMC** | 9.60 | **7.71** | 7.25 | **6.73** | 15.31 |

**The walk-forward portfolio, out of sample** (`research/wf_portfolio.py`):
- **The menu, fixed before running:** breakout off / $200 / $400 / $600 / $800 × 0 / 1 / 2 MNQ pre-FOMC.
- Each year it was chosen on every earlier year.
- **The choices:** $200 and 2 MNQ in most years, never B alone. For 2026: $200 and 2 MNQ, at both 2 and 3 ticks.

| 2017-2025, NQ | Net | Gross profit | Intraday max DD | **Net ÷ DD** | **Gross ÷ DD** |
|---|---:|---:|---:|---:|---:|
| **Walk-forward portfolio, 2 ticks** | $126,944 | $682,703 | $10,475 | **12.1** | **65.2** |
| Frozen B, 2 ticks | $69,198 | $490,630 | $14,837 | 4.7 | 33.1 |
| **Walk-forward portfolio, 3 ticks** | $103,508 | $668,102 | $11,844 | **8.7** | **56.4** |
| Frozen B, 3 ticks | $56,499 | $484,346 | $15,719 | 3.6 | 30.8 |

**One account.**
- Live, B blocks its entries while the account's position differs from its own, that is, while the FOMC position is
  held.
- The trades it would skip lost $8,573 over 2015-2025 (106 trades). On one account the 2015-2025 figure is 16.2
  against 15.3 (2 ticks) and 13.7 against 12.9 (3 ticks).
- This was found, not chosen. It is reported as the live behaviour.

**MNQ 2026** (62 sessions; the execution check, not deciding):

| 2 ticks | Net | Intraday DD | Net ÷ DD |
|---|---:|---:|---:|
| Frozen B | $13,031 | $2,339 | 5.6 |
| B + breakout $200 | $12,614 | $2,850 | 4.4 |
| **B + breakout $200 + 2 pre-FOMC, one account** | $12,911 | $3,365 | 3.8 |

- The two 2026 announcements in the sample gave −$1,062 (7/29) and +$718 (9/16).
- **MNQ does not confirm the improvement.** Its 62 sessions hold 2 FOMC trades and 42 breakout trades, too few to
  settle it either way.

## 5. Verdict and what to run

**The result for the objective:**
- **BWF:** frozen B + its breakout in the gaps at $200 + the pre-FOMC drift at 2 MNQ
  (`release/MnqPortfolioBWF_candidate/`).
- On NQ, out of sample by walk-forward (2017-2025):
  - net is **12.1 times** the worst intraday drawdown (frozen B: 4.7) at 2 ticks, and **8.7 times** (B: 3.6) at 3;
  - gross profit is **65 times** the drawdown (B: 33).
- Over the whole 2015-2025 record the same portfolio has 15.3-16.2 (B: 6.2).
- Every half and both slippages improve.

**What is not established:**
- **MNQ:** it is worse there, on too little data to tell.
- **Native NinjaTrader:** it has not run the breakout settings or MnqFomcDrift.
- **Every year:** not every year is profitable.
- **The FOMC drift's future:** a published effect can fade, as this one did in 2015-2019.
- **It is a candidate for a simulation account,** run beside B on the same sessions.

### The earlier step (kept for the record): BW


**BW** (frozen B + its breakout in the gaps at $600 risk; `release/MnqMomentumBW_candidate/PRESET_BW.md`):
- On ten years of NQ it raises net ÷ maximum drawdown from 6.1 to 12.9 (2 ticks) and from 4.6 to 9.8 (3 ticks). It
  improves both halves.
- **The honest out-of-sample figure is the walk-forward one: 7.5 against B's 4.6.**
- Gross profit is 56-79 times the drawdown, against 33-40.
- It needs no new code. It is B's file with two settings changed.

**What it is not:**
- It is not confirmed on MNQ, where the breakout lost over 62 sessions.
- It has not run in native NinjaTrader.
- It does not make every year profitable.
- **It is a candidate for a simulation account,** run side by side with B (PRESET_B-PRACTICE-v1.1) so that both are
  measured on the same live sessions.

**What would raise the ratio further** is a stream that makes money in the choppy years when B and the breakout both
stall: a mean-reversion or volatility-selling edge. None of the ones tested so far has one.
