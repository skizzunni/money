# Master checklist

Every requirement from the conversation, its status and the evidence. Status: **done** (verified), **partly**
(improved, the stated goal not reached), **not met** (with why and what would change it), **open** (being worked on),
**blocked** (needs something only the user can do). Last updated: October 18, 2026 (rounds through 136).

## The account and its rules

| # | Requirement (source) | Status | Evidence |
|---|---|---|---|
| 1 | Trade MNQ only ("keep my market") | done | Every setup is MNQ; other markets were tested only as checks (rounds 72, 97) |
| 2 | Apex only, one 50K account, intraday trail ("i dont have EOD only intraday rn") | done | All defaults and results are for the 50K intraday-trail evaluation and funded account; EOD kept as reference only (rounds 107-108) |
| 3 | At most 10 MNQ ("you can trade 10 contracts of mnq") | done | Bot 4 MNQ, breakout 1-10 ($400 risk in the evaluation, $200 funded), bold finish capped at 10 (`ApexMaxQty`); Apex's 50K evaluation allows 6 minis / 60 micros (third-party, Oct 2026); funded accounts reportedly start at half their contract limit until the balance clears the threshold (2-5 minis by the sources = 20-50 MNQ): 10 MNQ is within it either way |
| 4 | Stay within Apex's rules, no hedging, no rule-breaking | partly (the user's call) | One position at a time (no hedging); flat by 16:00; **Apex bans automation**, so Place orders off is the compliant mode, and its alerts are verified to reproduce the strategy's trades exactly (`test_alerts_only_trader_matches_the_strategy`); orders on (the user's choice, Oct 18: "i need it to auto place orders"), with a guard: live, if the account's own MNQ position differs from the strategy's, a loud alert and no new entries until they agree (no doubling up on a leftover position) |
| 5 | Every order with a stop and a take-profit (2026 rule, third-party, unconfirmed on Apex's site) | done | Bot: both from the fill; breakout: stop + take-profit 8x its stop (round 130); parity tests cover both |
| 6 | Apex's rules verified at the source | blocked | `apextraderfunding.com` is blocked by this environment's network policy; the user can add it under Allowed domains (environment settings). Apex's help center, as quoted by search results (pages themselves blocked here): the intraday evaluation has no daily loss limit; Tradovate's group copier for your own accounts. Third-party sources used meanwhile: 30-day evaluation, $3,000 target, $2,000 intraday trail, no evaluation DLL or consistency rule, funded: threshold locks at +$100, $1,000 DLL tier, 5 x $200 days, $52,600 balance, 50% consistency, caps $1,500-3,000, 6 payouts |

## Performance goals

| # | Requirement | Status | Evidence / what would change it |
|---|---|---|---|
| 7 | More trades a week; no days without trading | done | ~12 trades a week (bot + breakout, round 101) against ~8 for the bot alone |
| 8 | Pass the evaluation more often | done (improved) | Close-at-target: 35-37% passed over 16 years (was 22-26%), 27.9% in the newest 13 months (round 124); bold finish option: about 39% (round 129, off by default); per week of a running account: breakout $400 in the evaluation (round 134) nets $70 / $42 / $4 / $32 a week against $59 / $39 / $0 / $25 |
| 9 | More money per evaluation (the six payouts) | done (improved) | $1,163-1,835 paid per evaluation (was $690-1,268), round 124 |
| 10 | More likely to win than lose; more winning streaks | partly | 49-50% of trades win; locks raise it to 53-55% and cut red days 5-7 points but cost payouts, re-tested with close-at-target (rounds 103, 112, 131) |
| 11 | $1,500 a week (at one point $500 a day), on one account ("there are no copied accounts. its all just one") | not met | One account, run the way you would (a new evaluation after each failed one, one at a time), pays about $88 / $67 / $29 / $55 a week before fees at tonight's settings (2011-18 / 2019-25 / newest 13 months / NQ; rounds 132-134). On one account the only route to $1,500 is about four times the strategy's return for its risk (a daily Sharpe of 0.35 against 0.09): the $2,000 drawdown already ends about half the funded accounts at the strategy's swings. No rule in 135 rounds came near it |
| 12 | First payout within two weeks | partly | 0.2-0.6% of funded accounts pay within 10 sessions (needs ~$1,300 a week). The payout stop (round 128) doubles the first payout within 20 sessions (8.8% against 4.4% in 2019-25); on by default since round 132 (more money a week per account in every period, 26 and 52 weeks); the cycle's state entered once, then kept from the account and remembered in a file across restarts, a payout asked for kept out of the balance until it leaves the account; tested against a replica through five payout cycles and six restart points |
| 13 | Profit uncapped, only losses capped | done | No daily profit cap anywhere; loss caps per trade and per day (losers) |
| 14 | "A little riskier but don't be stupid" | done | Bold finish only adds size when a timeout (= a failed evaluation) is the alternative; off by default |

## The software

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 15 | NinjaTrader 8 files that compile and run | done | C# 5, compiled with no warnings against the stand-in; the user ran earlier versions |
| 16 | Backtested with 0 errors; the strategy trades what was tested | done | 103 NinjaTrader tests: the bot, the breakout (take-profit 8 and 1 stops), the cut / reversal, close-at-target, bold finish, the payout stop and its remembered cycle, rejected stops, alerts only; mutation checks |
| 17 | Alerts complete enough to trade by hand | done | Follow-the-alerts test: the manual trader's trades equal the strategy's, to the cent |
| 18 | Clear setup instructions | done | `docs/NINJATRADER.md`: install, settings, "Trading it by hand on Apex", Playback check |
| 19 | Verified in NinjaTrader itself (not just the stand-in) | partly (user ran it) | Strategy Analyzer, MNQ DEC26, 8 Sep - 16 Oct 2026: 70 trades, +$9,276, 52.9% winners; every trade's size, stop, lock exit, breakout risk and 16:00 exit as the rules say (`research/nt_run_check.py`); through the Apex evaluation's rules it passes on 21 Sep from a 8 Sep start (14 of 21 start days pass, 7 bust in the late-Sep slide). Still open: a bar-by-bar comparison (needs the exported bars) and a Playback run watching live orders |
| 20 | One account, one platform, one dashboard ("ONE ACCOUNT. ONE PLATFORM.") | done | Everything that trades runs in the one NinjaTrader strategy on the one Apex account: orders with brackets, both setups, evaluation or funded read from the account's name (no switch to flip), the evaluation's target from the account's balance, the payout cycle kept in a file, the position guard, the on-chart dashboard and alerts (`test_account_type_from_the_account_name` and the tests above). Outside it, only what Apex's website alone does: buying the evaluation, requesting a payout (the strategy says when and about how much) |

## Can the targets be reached on one 50K account? The arithmetic

The account's binding limit is the $2,000 drawdown trailing the highest equity. A strategy whose day has mean m and
standard deviation s (both scale with size; their ratio, the daily Sharpe m / s, does not) ends the account with
probability about exp(-2 m 2000 / s^2) before drifting away from it. Size only chooses where on that line you sit:

| Daily Sharpe | $300 a day ($1,500 a week): sd, chance of failing | $560 a day (first payout in ~2 weeks): sd, chance of failing |
|---|---|---|
| **0.09 (this strategy, 2011-25)** | $3,333, **~90%** | $6,222, **~94%** |
| 0.20 | $1,500, ~59% | $2,800, ~75% |
| 0.35 | $857, ~20% | $1,600, ~42% |
| 0.50 | $600, ~4% | $1,120, ~17% |

- **$1,500 a week** is $300 a day of trading profit (payouts are withdrawals of profit), on top of the first cycle's
  $3,600 cushion ($52,600 balance + the $1,500 payout over $52,100). Reaching it with even odds needs a daily Sharpe
  around 0.3, more than three times this strategy's; nothing in 136 rounds tested above about 0.1.
- **The first payout within two weeks** means passing the $3,000 evaluation and then five $200 days to $52,600 (no
  day over half the cycle's profit) inside ~10 sessions: about $5,600 in 10 days, $560 a day.
- **The 10 MNQ limit** caps the size: at 10 MNQ a 30-point day is $600. The drawdown, not the contract limit, binds
  first at this strategy's Sharpe.
- **Apex's payout rules** cap one funded account at $13,000 in six payouts ($1,500, $1,500, $2,000, $2,500, $2,500,
  $3,000), each needing five $200 days: the most a perfect record could take is about $1,500-3,000 a week, so the
  rules themselves allow the target; the strategy's return for its risk does not.
- **More than 50% winners** is possible on its own (a lock that takes small wins early: 53-55%, rounds 103, 112, 131)
  but it cut the money paid every time it was tested, because the winners it cuts short are the big trend days.

## Open items and next steps

1. Done: the payout stop is an option (round 128), its cycle remembered in a file across restarts, and a payout
   asked for now kept out of the balance until it leaves the account, and its leaving no longer counted as a losing
   day (found while adding the file: before, the balance read too high until the payout left, and once it left, the
   new cycle started with a loss the size of the payout, which held the payout stop back).
2. Done: with orders on, the evaluation's target read from the account's balance, so a restart or a reconnect (NinjaTrader
   recalculates the strategy) no longer resets the count and aims for $3,000 more (found in an adversarial review of
   the automated mode; tested: restarted mid-evaluation it stops at the target, the old count trades past it).
3. Re-check the overnight 18:00-02:00 long as more real nights come in (passed 2011-25, lost in 2025-26).
4. Evaluation size per week (round 133): 6 MNQ / 3 losers / $300 netted more in all four periods but wasn't the
   pre-registered pick; re-test it as new real weeks come in before making it the default.
   The same for the funded breakout at $300 (round 135).
5. Evaluation price: on the newest 13 months a slot's payouts cover an evaluation only up to $65-101 (round 132);
   buy evaluations at promotional prices, not list.
6. Allow `apextraderfunding.com` (user) so the rules above can be read at the source.
7. A Playback run in NinjaTrader with Place orders on (your mode): check the trades, the brackets and the alerts
   match the chart.

## Failed approaches (and why), so they are not repeated

Sizing up on any signal (busts the trail: 63, 76, 102, 111, 125); volatility-targeted size (+6% Sharpe, less a week: 136); safety rules that cut risk (give-back stop, thin
cushion, locks: time runs out instead: 103, 112, 113, 115, 118); new setups that held in history but not in 2025-26
(overnight drift 104-106, 114; overnight-range breakout 120; gap and go 71-72); filters (wick, touch, shorts: 76-77,
117, 118). The method errors found and fixed: passes counted only at a trade's close (124); the same-minute high/low
bias in the give-back test (113); take-profit rounding toward the price (130).
