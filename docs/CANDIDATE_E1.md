# Candidate E1 — UNVERIFIED (pre-registration)

Written and committed on 2026-10-30, before `research/e1_ema_pullback.py` was run.

## Where it comes from

The user pasted a "Perfect Trading Strategy" from another chat assistant. Its stated results cannot have come from a
backtest:
- **"Zero Loss Guarantee"**, alongside a 75.3% win rate.
- **The profit factor.** With a 2.8R target, a 1R stop and 75.3% winners, the profit factor would be about 8.5, not
  the 2.78 stated.
- **The expectancy.** Those figures give about +1.86R, or about +$1,160 a trade at $625 risk, not $1,225.
- **The total.** 61 days at $1,225 is about $75k, not the $187,240 stated.
- **The worst-case drawdown** is −$2,500 in one table and $8,942 in another.
- **The sample trade's** target is 1R away, not 2.8R, and its profit would be about $627, not $1,225.
- **The "Time Machine" probability check** does not exist as a tool.

None of those claims is used here. Only the rules that can be written down objectively are tested.

## Frozen rules (MNQ, regular hours, New York time)

1. **Opening range and bias:** the 09:30-10:00 bar. If it closes above its open, only longs; below, only shorts; flat,
   no trade.
2. **Trend:** on completed 30-minute bars, the 9-period EMA is above the 20-period SMA (longs), or below it (shorts).
   - The averages run continuously across sessions, on regular-hours bars.
   - The ">30° angle" depends on chart scale, so it is replaced by: the 30-minute EMA9 higher (lower, for shorts) than
     2 bars earlier.
3. **Pullback:** a 5-minute bar's low touches the 5-minute EMA9 and the bar closes above it (shorts mirrored). Then
   enter at the next bar's open.
4. **Time windows:** signal bars from 10:00 to 10:55, and from 14:00 to 15:25.
5. **Stop:** 1 tick outside the opening range: below its low for longs, above its high for shorts. A trade is skipped
   if the entry is already past the stop.
6. **Size:** the most whole MNQ whose risk to the stop, plus costs, is at most $625. A trade is skipped if not even 1
   fits.
7. **Target:** 2.8 × the risk in points.
8. **Breakeven:** once price reaches +1R, the stop moves to the entry, from the next bar.
9. **Exit:** at the 15:55 bar's close, if neither the stop nor the target has filled.
10. **Daily limits:** one position at a time. No new trade after a losing trade that day; at most one trade in each
    window.

**Not testable, so left out:**
- "respects a clear swing high/low or supply/demand zone" (condition 1);
- "no choppy price action" (condition 5);
- the "Time Machine" (condition 4).

## Data and costs

- **Data:**
  - the Jan 2 2025 – Oct 2026 MNQ stand-in, at its own prices;
  - NQ futures 2015 – Jul 2025;
  - the Nasdaq-100 index 2011 – Sep 2026, with $ scaled to a 30,000 price level.
- **Costs:**
  - $0.62 a contract a side;
  - 1 tick on market and stop fills;
  - none on target limits.
- A bar that reaches both the stop and the target counts as the stop.

## Acceptance

The user's targets on the stand-in: net at least $75,000, net win at least 80%, PF at least 2.0 and marked-equity DD
under $4,000. Also reported against the pasted claims: 75.3% wins, PF 2.78 and $187,240.

One run. No settings are tuned afterwards.
