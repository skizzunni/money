# v3.7: v3.6 sized for the most profit inside the user's limits (pre-registration)

Written and committed on 2026-10-30, before the scan in this file was run.

**The goal:** the most net profit v3.6 can make on a 100K account, inside:
- a **$2,000 end-of-day trailing drawdown** that stops at the starting balance;
- a **$1,000 daily loss limit**, with no stop-trading rule.

**What stays fixed:** v3.6's entry, stop, lock, take-profit, filters and session rules are unchanged. Only sizing is
scanned:
- `profit_step`: one more MNQ for each this many dollars of closed profit. Values: 500, 750, 1,000, 1,500, 2,000.
- `size_up_to`: the most MNQ. Values: 5, 10, 15, 20, 30.

That makes 25 settings, each starting at 1 MNQ.

**Selection** (on the histories only, 5-minute bars):
- A setting qualifies if the $2,000 floor is never touched (`tb0` = 0) on both NQ 2015-2025 and the Nasdaq-100 index
  2011-2026.
- Of those, the one with the highest of the smaller of the two histories' net per year.
- The user's window (the Jan 2025 – Oct 2026 stand-in, 5- and 30-minute bars) is not used to choose. It is reported
  once, afterwards.

**Reported:** net, closed drawdown, end-of-day drawdown, winners, PF, worst day and floor touches, for every set.

**Targets:** the user's targets (net at least $75,000, at least 80% winners, PF at least 2, drawdown under $4,000)
are reported as measured. v3.6's entries win about 55-65% of trades, so the win-rate target is not expected to be
met by any sizing.

## Results (2026-10-30; `verification/noise_v2/v37_max_5.csv`, `v37_max_30.csv`)

All 26 runs (the base plus 25 settings) use the $2,000 end-of-day trailing drawdown and the $1,000 daily limit. The
base is v3.6's own sizing: +1 MNQ per $1,500, up to 15.

**Selected by the frozen rule** (5-minute histories): +1 MNQ per $500, up to 20.
- Its smaller net per year is about $29.7k (NQ $313,628 over about 10.6 years; index $483,527 over about 15.8 years).
- v3.6's sizing gives about $27.2k.
- No floor touches on either 5-minute history.

**But it fails on 30-minute bars, the bar length of the user's TradingView chart:**
- On NQ it touched the $2,000 floor and stopped (−$22 net).
- On the index it froze at the floor and stopped trading (net $0).

Every faster step (+1 per $500, $750 or $1,000) freezes or breaks on at least one 30-minute history. The pre-registered
rule looked only at 5-minute bars and did not check for this. So the selected setting is **not adopted**.

**v3.6's sizing** (+1 per $1,500, up to 15) is the fastest that trades through every history on both bar lengths,
with no floor touches. Under the user's limits:

| User's window (Jan 2025 – Oct 2026 stand-in) | 5-minute bars | 30-minute bars |
|---|---|---|
| Net | $19,784 | $26,182 |
| Closed / end-of-day drawdown | $1,848 / $1,835 | $3,228 / $3,099 |
| Winners | 66.2% | 56.2% |
| Profit factor | 1.836 | 1.908 |
| Worst day | −$999 | −$999 |
| Floor touches | 0 | 0 |

**The targets:**

| | Target | 30-minute bars |
|---|---|---|
| Net | $75,000 | $26,182 (no) |
| Winners | 80% | 56.2% (no) |
| Profit factor | 2.0 | 1.908 (no) |
| Drawdown under $4,000 | yes | $3,228 (yes) |

**Settings for the user's limits:** set the v3.6 script's inputs to:
- "Daily loss limit, $" 1000;
- "End-of-day trailing drawdown, $" 2000.

Leave everything else at its defaults. The stand-in flattered v3.6 before: on the user's chart the same rules made
less than here. Expect the chart to show less too.
