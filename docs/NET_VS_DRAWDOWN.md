# Net and gross profit against the maximum drawdown (October 21, 2026, overnight)

## Summary (read this first)

**Already true of frozen B over the long run:**
- 2011-2026: net 6.9 times its worst intraday drawdown ($125,688 against $18,157); gross profit 46 times.

**The improvement found and kept: BWF** (`release/MnqPortfolioBWF_candidate/`):
- frozen B, unchanged;
- its own Williams breakout in the gaps at $200 risk (a setting, no new code);
- a new, separate pre-FOMC drift strategy at 2 MNQ.

**What it did** (2 ticks):

| | Frozen B | BWF |
|---|---:|---:|
| Net ÷ max intraday drawdown (open P/L at each minute's worst), 2011-2026 | 6.9 | **11.4** |
| Gross profit ÷ max intraday drawdown, 2011-2026 | 46 | **67** |
| Net ÷ max closed-day drawdown, 2011-2026 | 7.5 | 12.5 |
| Net ÷ max drawdown, NQ walk-forward 2017-2025 | 4.7 | **12.1** |
| Gross ÷ max drawdown, NQ walk-forward 2017-2025 | 33 | **65** |
| Chance that net exceeds the max drawdown within 1 / 3 / 5 years (bootstrap) | 52% / 73% / 86% | **65% / 89% / 96%** |

**Not achieved, and not hidden:**
- **On the newest 15 months** (July 2025 to September 2026) nothing tested made more than half its drawdown. BWF did
  slightly worse than B there (0.16 against 0.21), and is in an open drawdown since February 2025.
- **In 2011-2014** the improvement was neutral.
- **On MNQ (62 sessions) and in native NinjaTrader** it is unconfirmed.
- **No configuration makes every year, or every month, net far above its drawdown.** That property holds over years.

**Rejected tonight, each on data it was not chosen on:**
- volatility-scaled contracts;
- an overnight long;
- the turn of the month;
- daily loss limits;
- a long-only breakout;
- the pre-holiday drift.


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
| Breakout long only (its shorts off), $200 / $600 | 2011-2026 closed-day: 9.48 / 10.98 against 10.34 / 10.62 with shorts; lower in 2011-14, 2020-25 and 2025-26 | 6.76 / 8.59 against 7.72 / 8.41 | | **rejected**: mixed, mostly worse |
| Equity-curve filter on BWF: no bot or breakout trading on a day when their last 20 / 60 / 120 sessions lost | 2011-2026 closed-day: 4.90 / 6.89 / 9.40 against 12.46 without; walk-forward choice 11.27 against 11.88 | 3.26 / 3.58 / 5.80 against 8.61 | | **rejected**: it stands aside before the rebounds |
| The bot's losers a day 2 / 4 (frozen at 3), on B + breakout $200 | 2011-2026 closed-day: 8.88 / 9.88 against 10.34 at 3 (4 was better in 2025-07 to 2026-09 only: 1.04 against 0.27) | 6.64 / 7.22 against 7.72 | | **kept at 3**: best over the whole record; choosing 4 from the newest months would fit the holdout |
| Pre-holiday drift (Ariel 1990; long 2 MNQ from the 16:00 close two sessions before an NYSE holiday to the pre-holiday close), as a stream | discovery NQ 2015-19: t −0.09 (45 trades); 2020-25 t 2.08; NSX 2011-14 t 1.15; 2025-26 t 0.39 | | | **rejected** at discovery, by the protocol fixed before running |
| B + breakout $200 with B's own daily loss gate at $400 / $600 / $1,000 (both setups) | 2011-2026 closed-day: 6.91 / 8.64 / 10.49 against 10.34 without | 5.88 / 6.38 / 7.83 against 7.72 | | **rejected**: tight limits cut the recoveries; $1,000 rarely binds |

**What earlier rounds had already tested** (docs/RESULTS.md and the research notes), restated for this objective:
- Regime, trend, spike and time filters: none held out of sample.
- Time exits and re-entries: none significant.
- Quiet-day and VWAP fades, market profile: all lost.
- Lead-lag from other markets: 0 of 200 rules survived.
- The trap reversal: consistently negative. Its mirror image, a re-entry in the original direction, was not
  significant.
- None of them adds to the objective. The Williams breakout is the one documented positive stream that is
  nearly independent of B.

**The breakout's settings are not a knife-edge** (NQ, $200; sensitivity only, the defaults are kept;
`verification/net_vs_dd/ratios_breakout_sensitivity.csv`):

| Breakout | 2t: 2015-19 / 2020-25 / all | 3t: all |
|---|---|---:|
| Frozen B (none) | 5.42 / 3.10 / 6.13 | 4.64 |
| k 0.5, stop 0.25 (the defaults) | 8.84 / 4.10 / 9.95 | 8.01 |
| k 0.4 | 8.76 / 3.82 / 9.02 | 7.33 |
| k 0.6 | 6.96 / 3.86 / 8.67 | 6.87 |
| stop 0.20 | 10.09 / 4.39 / 10.68 | 8.66 |
| stop 0.30 | 9.25 / 4.49 / 10.33 | 8.40 |

Every neighbour beats B in every period and at both slippages.

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

## 4b. The newest data: NSX, July 2025 to September 2026 (none of tonight's choices saw it)

**The data:**
- The NSX Nasdaq-100 1-minute series runs past the NQ file's June 2025 end. It was month-rescaled like NQ, with its
  factors rebuilt from the raw histdata files.
- **It is a faithful proxy for MNQ:**
  - over 7/20-9/30/2026, B made $7,584 on NSX and $8,423 on the user's MNQ;
  - the daily correlation is 0.96.

| NSX 2025-07 to 2026-09 | 2t net | 2t intraday DD | **2t net ÷ DD** | 3t net ÷ DD |
|---|---:|---:|---:|---:|
| Frozen B | $2,276 | $10,860 | **0.21** | 0.09 |
| B + 2 MNQ pre-FOMC | $690 | $11,766 | 0.06 | −0.05 |
| B + breakout $200 | $2,390 | $9,492 | 0.25 | 0.10 |
| B + breakout $400 | $4,123 | $10,295 | 0.40 | 0.23 |
| B + breakout $600 | $5,749 | $12,474 | 0.46 | 0.31 |
| **BWF: breakout $200 + 2 pre-FOMC, one account** | $1,857 | $11,318 | **0.16** | 0.04 |

**What it shows:**
- **On the newest 15 months the objective is not met by anything tested:** net was a fifth of the drawdown or less.
- **B itself:**
  - B lost about $4,700 from July 2025 to July 2026 (−$3,984 in August 2025 alone), then made $7,904 in August and
    September 2026.
  - The user's MNQ export (7/20-10/16/2026) covers that good stretch only.
- **The breakout** still added: every weight raised net and the ratio.
- **The pre-FOMC drift lost:** 10 announcements, net −$1,588 at 2 MNQ, 4 up and 6 down.
  - It had been weak in 2015-2019 too. Its 2020-2025 strength did not carry on.
  - BWF is therefore worse than B here: 0.16 against 0.21.
- **These are holdout results.** Choosing a configuration from them now (breakout $600 without the FOMC leg, the
  best row here) would fit the holdout. The walk-forward rule's choice was made before this data was seen, and that
  choice is BWF.

## 4c. The walk-forward rule updated with the new data, and the whole record

**The update:**
- Appending the NSX holdout (2025-07 to 2026-09) to the history and re-running the same rule, the choice becomes
  breakout **$600** and **2 MNQ** pre-FOMC, at both 2 and 3 ticks.
- Over the full history its score is 14.1 (2 ticks) and 11.3 (3 ticks), on the closed-day drawdown.
- This is the rule's own update, not a choice made from the holdout's best row: its best row was without the FOMC
  leg.

**The whole record, 2015-03 to 2026-09** (NQ, then NSX; 2 ticks; closed-day drawdown;
`verification/net_vs_dd/years_2015_2026_B_vs_BWF600.csv`):

| | Net | Max DD | **Net ÷ DD** | Positive years | Years with net > that year's DD |
|---|---:|---:|---:|---:|---:|
| Frozen B | $93,851 | $16,670 | **5.6** | 9 of 12 | 7 of 12 |
| **B + breakout $600 + 2 MNQ pre-FOMC** | $204,977 | $14,556 | **14.1** | 11 of 12 | 8 of 12 |

| Year | B net | B DD | Portfolio net | Portfolio DD |
|---|---:|---:|---:|---:|
| 2015 | 10,297 | 6,796 | 16,230 | 6,299 |
| 2016 | 12,080 | 5,167 | 16,352 | 9,717 |
| 2017 | −1,989 | 7,159 | 8,366 | 6,349 |
| 2018 | 24,815 | 6,241 | 45,832 | 6,855 |
| 2019 | 3,787 | 6,423 | 31,425 | 6,139 |
| 2020 | 2,897 | 12,020 | 7,006 | 10,547 |
| 2021 | 18,018 | 6,389 | 13,654 | 5,020 |
| 2022 | 17,606 | 7,174 | 29,391 | 8,234 |
| 2023 | −719 | 7,898 | 3,006 | 8,701 |
| 2024 | 8,673 | 6,216 | 33,898 | 7,919 |
| 2025 | −9,060 | 12,847 | −10,010 | 14,556 |
| 2026 (to Sep) | 7,446 | 5,510 | 9,827 | 12,090 |

- 2025 lost for both, and its drawdown is the record's largest.
- 2026's portfolio drawdown is twice B's: the FOMC leg's losses in March and July.

## 4d. Four earlier years: NSX 2011-2014, and the whole 2011-2026 record

**NSX 2011-2014** (a caveat: B and its breakout were built on NSX 2011-2018, so these years are in-sample for them;
the FOMC leg is new evidence):

| 2 ticks, closed-day DD | Net | DD | Net ÷ DD |
|---|---:|---:|---:|
| Frozen B | $31,836 | $12,289 | 2.59 |
| B + breakout $200 | $38,159 | $15,310 | 2.49 |
| B + breakout $600 | $54,063 | $21,878 | 2.47 |
| B + breakout $200 + 2 pre-FOMC | $38,644 | $14,886 | 2.60 |

- Here the breakout adds net in proportion to the drawdown, so it does not raise the ratio.
- The FOMC leg was flat: 32 announcements, +$485.

**The whole record, 2011-01 to 2026-09** (`verification/net_vs_dd/record_2011_2026_*t.csv`):

| | 2t net | 2t DD | **2t net ÷ DD** | **3t net ÷ DD** | Positive years (2t) |
|---|---:|---:|---:|---:|---:|
| Frozen B | $125,688 | $16,670 | **7.54** | 5.25 | 12 of 16 |
| B + 2 pre-FOMC | $152,855 | $15,059 | 10.15 | 7.34 | 12 of 16 |
| B + breakout $200 | $158,279 | $15,310 | 10.34 | 7.72 | 14 of 16 |
| **B + breakout $200 + 2 pre-FOMC (BWF)** | **$185,446** | **$14,886** | **12.46** | **8.61** | 13 of 16 |
| B + breakout $400 + 2 pre-FOMC | $219,442 | $17,664 | 12.42 | 9.19 | 13 of 16 |
| B + breakout $600 + 2 pre-FOMC | $259,526 | $22,163 | 11.71 | 8.94 | 13 of 16 |

**Where the gain comes from:**
- Every combination beats frozen B over the 16 years, at 2 and at 3 ticks.
- The gain is concentrated in 2015-2024. It is neutral in 2011-2014 and absent in the latest 15 months.
- **The preset is BWF at $200:** the rule's choice on the longest history at the base cost.

**The pre-FOMC drift over all 16 years** (1 MNQ, 2 ticks):
- 125 announcements: +$108.70 a trade, t 2.11, 54% winners.
- Positive in 10 of 16 years. Most of it comes from 2020 (+$3,696) and 2022 (+$6,083), years when the Fed drove the
  market.
- **The evidence for it is borderline.** It earns its place by paying in years when B is weak (2020), not by being
  reliable.
- **Its timing is not a knife-edge.** Sixteen entry and exit times were tried: entry at 10:00, 14:00, 15:00 or 18:00 the
  day before; exit at 10:00, 13:00, 13:30 or 13:55 on the day.
  - All 16 are positive over 2011-2026, t 2.02 to 3.35.
  - The rule's 14:00 to 13:55 window is mid-range, at t 2.61.
  - This is a sensitivity check, not a selection: the rule is unchanged.

**The whole record at the minute level** (open P/L at each minute's worst price, chained across NSX, NQ and NSX):

| 2011-2026 | Net | Gross profit | Max intraday DD (trough) | **Net ÷ DD** | Gross ÷ DD |
|---|---:|---:|---:|---:|---:|
| Frozen B, 2 ticks | $125,688 | $836,287 | $18,157 (2026-01-29) | **6.92** | 46.1 |
| **BWF, 2 ticks** | $185,446 | $1,094,195 | $16,239 (2026-07-29) | **11.42** | **67.4** |
| Frozen B, 3 ticks | $97,261 | $818,622 | $20,002 (2026-01-29) | 4.86 | 40.9 |
| **BWF, 3 ticks** | $154,455 | $1,075,117 | $18,844 (2012-04-09) | **8.20** | 57.1 |

## 4e. How likely "net far above drawdown" is, by horizon

**The method:**
- A block bootstrap of the 2011-2026 daily P/L: 20-session blocks, so losing streaks stay together. 4,000 paths a
  horizon, 2 ticks.
- `verification/net_vs_dd/bootstrap_horizons_2t.csv`.

| Horizon | Portfolio | P(net > 0) | P(net > max DD) | P(net > 2 × DD) | P(net > 3 × DD) | Median net ÷ DD | Median DD |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 year | Frozen B | 80% | 52% | 32% | 19% | 1.09 | $6,742 |
| 1 year | **BWF** | 89% | **65%** | 44% | 28% | 1.70 | $6,642 |
| 3 years | Frozen B | 93% | 73% | 52% | 34% | 2.08 | $10,601 |
| 3 years | **BWF** | 98% | **89%** | 73% | 58% | 3.43 | $9,578 |
| 5 years | Frozen B | 97% | 86% | 69% | 50% | 3.02 | $12,394 |
| 5 years | **BWF** | 100% | **96%** | 89% | 77% | 4.96 | $11,155 |

**Reading it:**
- **Net far above the maximum drawdown is a property of years, not months.** Over one year even BWF ends below its
  own drawdown about one time in three.
- **BWF raises every probability, at a slightly lower drawdown.**
- **The bootstrap assumes the next years resemble 2011-2026.** The latest 15 months (section 4b) were worse than this
  sample's typical year.

## 4f. BWF's drawdowns are slow grinds, and one is open now

**BWF's largest drawdown episodes, 2011-2026** (closed-day, 2 ticks):

| Peak | Trough | Recovered | Depth |
|---|---|---|---:|
| 2011-08-02 | 2012-04-09 | 2012-05-21 | $14,886 |
| **2025-02-27** | **2026-07-29** | **not yet (data to 2026-09-30)** | **$13,950** |
| 2013-06-19 | 2013-09-04 | 2014-02-06 | $8,661 |
| 2011-03-08 | 2011-06-15 | 2011-08-01 | $7,343 |
| 2023-01-23 | 2023-03-20 | 2023-11-10 | $6,988 |
| 2014-10-09 | 2015-03-13 | 2015-05-06 | $6,876 |
| 2017-07-10 | 2017-10-04 | 2018-01-22 | $6,669 |
| 2020-02-21 (Covid) | 2020-04-06 | 2020-07-27 | $6,587 |

- **The deep drawdowns are months of choppy, trendless trading,** not crashes. The 2020 crash is eighth.
- **A cap on size in extreme volatility would not reach them,** so it was not tested.
- **The portfolio is in its second-deepest drawdown now,** open since February 2025. Anyone starting it today starts
  inside that episode, and its end is unknown.

**Who lost in the two deepest:**

| Episode | Bot (B) | Breakout | Pre-FOMC |
|---|---:|---:|---:|
| 2025-02 to 2026-07 | −$11,840 (550 trades) | −$449 (182) | −$1,510 (12) |
| 2011-08 to 2012-04 | −$9,070 (300 trades) | −$3,252 (68) | −$1,937 (6) |

- **The bot carries them.** In those stretches all three legs lost together: their low correlation holds on average,
  not in every regime.
- **In 2025-2026 the bot was about break-even before costs.** Its 550 trades paid about $8,600 in commission and
  2 ticks of slippage (4 MNQ × ($1.90 + 2 × 2 × $0.50) = $15.60 a trade).

## 4g. What a tick of execution is worth

**Net ÷ max drawdown** (closed-day; BWF on two accounts):

| Slippage a side | Frozen B, 2011-2026 | BWF, 2011-2026 | Frozen B, 2025-07 to 2026-09 | BWF, 2025-07 to 2026-09 |
|---|---:|---:|---:|---:|
| 1 tick | 10.36 ($152,903) | **15.68** ($216,637) | 0.33 | 0.21 |
| 2 ticks (base) | 7.54 ($125,688) | **12.46** ($185,446) | 0.22 | 0.08 |
| 3 ticks | 5.25 ($97,261) | **8.61** ($154,455) | 0.09 | −0.06 |

- **Each tick of slippage costs about a third of the long-run ratio.** Fill quality matters as much as any rule
  tested tonight.
- **It does not rescue the newest 15 months.**

## 5. Verdict and what to run

**The result for the objective:**
- **BWF:** frozen B + its breakout in the gaps + the pre-FOMC drift at 2 MNQ
  (`release/MnqPortfolioBWF_candidate/`). The breakout is at $200: the rule's choice on the longest history (2011-2026)
  at the base cost (section 4d). With 2015-2026 it would be $600, within noise of it.
- On NQ, out of sample by walk-forward (2017-2025):
  - net is **12.1 times** the worst intraday drawdown (frozen B: 4.7) at 2 ticks, and **8.7 times** (B: 3.6) at 3;
  - gross profit is **65 times** the drawdown (B: 33).
- Over the whole 2015-2025 record the same portfolio has 15.3-16.2 (B: 6.2).
- Every half and both slippages improve.

**What is not established:**
- **The newest 15 months** (section 4b): BWF did worse than B. The FOMC leg lost, and nothing reached a net above
  its drawdown.
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
