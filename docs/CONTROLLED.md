# Original vs revised code: a controlled comparison (October 18, 2026)

Labels: **executed** (run here, numbers below), **from the exports** (computed from the user's two NinjaTrader
exports), **proposed** (defined, not run), **unavailable** (needs something not here).

## 1. What changed in the code (from the exports' runs: original `d4cb597`, revised `23bca3b`)

Full diff: [`baseline/original_to_revised.diff`](baseline/original_to_revised.diff) (2 files, +91 / -7 lines);
original sources kept in [`baseline/`](baseline/).

| Change | File | What it does | Can it change a backtest? |
|---|---|---|---|
| Account guard from the first bar | Strategy | entries blocked from the first bar the account's position differs from the strategy's (was: from the second) | no: in a backtest the guard is off (live only) |
| Exit retry | Strategy | a rejected exit is sent again each bar until flat (was: alert only) | no: backtests have no rejections |
| Honest entry alerts | Strategy | "sent" / "NOT sent, and why" (was: always "placed") | no: text only |
| Session-close backstop | Strategy | NinjaTrader's exit 60 s before the session end (`IsExitOnSessionCloseStrategy`) | only if no 16:00 bar arrives; with an RTH template it would exit at 15:59 |
| **Stop only ever tightens** | Strategy + engine | in a trade the stop never moves back toward the price (setting on) | **yes**: the only trading-rule change |

## 2. The two runs' settings, and the one-tick fills (from the exports and screenshots)

| Setting | Original run | Revised run |
|---|---|---|
| Start / end date | 8/18/2026 - 10/17/2026 (screenshot) | **8/9/2026** - 10/17/2026 (summary export) |
| Slippage | **1 tick** (screenshot) | **0** ("Total slippage 0" in the summary) |
| Commission | $1.90 a contract a round trip | $1.90 (the same $7.60 per 4 MNQ in the trades) |
| Instrument, bars | MNQ DEC26, 1 minute, Last | MNQ DEC26, 1 minute (trades) |
| Fill resolution, trading hours, limit on touch | Standard, instrument settings, on | **unavailable** (not in the export; a screenshot of the revised run's settings is needed) |

- **The one-tick better entries (69 of 70) are the slippage setting, not the code.** Slippage 1 puts every market
  fill one tick against the trade; the revised run had slippage 0. The code does not set slippage. The 70th entry
  (Oct 16, 11:31, short, 29682.25 in both) is likely a fill at the bar's low: NinjaTrader does not apply
  slippage beyond the bar's range, so there was nothing to remove (to confirm with the bars).
- **The earlier start (8/9) is why the revised run has 13 more trades** (Aug 28 - Sep 4, -$785): the 14-session
  warm-up ends earlier.
- On the shared 70 trades the revised run made +$415. Of the 64 trades with the same exit time and reason, the
  change is +$0 to +$4.50 each, mostly +$2.00 (one tick x 4 MNQ x $0.50): slippage.

## 3. The two largest matched-trade changes (from the exports)

- **Sep 16, 11:31, long: -$207.60 -> +$12.40. Cause: the slippage setting.** Original fill 29507.00 (slippage 1), so
  the $200 stop sat at 29482.00; that minute's low was exactly 29482.00 (MAE exactly $200.00): stopped out. Revised
  fill 29506.75 (no slippage), stop one tick lower at 29481.75: not touched. The trade went on, reached the +25-point
  lock and closed at entry + 2.5 = 29509.25: +$20 - $7.60 = +$12.40.
- **Oct 12, 10:01, short: +$22.40 -> +$102.40. Consistent with the code change** (the stop that only tightens), plus
  $2 of slippage. Original: the stop followed the noise line back up and filled at 30956.75 at 11:49. Revised: stopped
  three minutes earlier at 30947.00, a stop 9.75 points tighter that the original no longer had - what "never back
  toward the price" does. Confirming it needs the bars (**unavailable**: the 1-minute export).
- So of the +$415: **about $78 is attributable to the code** (Oct 12) and **about $337 to the slippage setting**
  (Sep 16 $220, the one-tick pattern on the rest).

## 4-6. Four complete backtests, three slippage scenarios (executed)

`research/controlled.py`: the original and the revised C# code compiled against the same NinjaTrader stand-in, each
run in full on identical 1-minute bars (09:30-16:00 and the 16:00 bar), identical 14-session warm-up, commission
$0.95 a side (the export's), default evaluation settings and fixed sizing (bot 4 MNQ; breakout $400 risk, 1-10 MNQ),
RoundPrices on; slippage 0, 1 or 2 ticks on every market fill. The stand-in is not NinjaTrader: it models orders and
fills (market at the next open, stops at the stop or the open past it, the stop first in a bar that reaches both).
Account replay: the Apex 50K intraday-trail evaluation from every session (worst point of a minute before its best).

**Real NQ futures, March 2015 - July 2025 (1,031,943 bars), slippage 1 tick:**

| | Net $ | Trades | Bot $ | Breakout $ (shorts) | Winners | Losing streak | Intraday DD | Worst day | Days < -$1,000 | Evaluations passed / failed |
|---|---|---|---|---|---|---|---|---|---|---|
| Original, breakout on | 169,114 | 6,696 | 111,527 | 57,587 (14,911) | 49.5% | 10 | 14,374 | -1,066 | 7 | 32.7% / 65.1% |
| Revised, breakout on | 169,237 | 6,690 | 111,812 | 57,425 (14,749) | 49.5% | 10 | 14,348 | -1,066 | 7 | 32.7% / 65.1% |
| Original, breakout off | 111,527 | 5,047 | 111,527 | - | 50.6% | 11 | 14,130 | -838 | 0 | 31.8% / 60.2% |
| Revised, breakout off | 111,812 | 5,041 | 111,812 | - | 50.6% | 11 | 14,124 | -838 | 0 | 31.9% / 60.1% |

**Index data rescaled to futures, July 2025 - September 2026 (the most recent), slippage 1 tick:**

| | Net $ | Trades | Bot $ | Breakout $ (shorts) | Winners | Losing streak | Intraday DD | Worst day | Days < -$1,000 | Evaluations passed / failed |
|---|---|---|---|---|---|---|---|---|---|---|
| Original, breakout on | 15,333 | 724 | 14,186 | 1,146 (-1,693) | 49.0% | 8 | 9,308 | -1,556 | 2 | 23.8% / 75.5% |
| Revised, breakout on | 15,389 | 724 | 14,242 | 1,146 (-1,693) | 49.0% | 8 | 9,286 | -1,556 | 2 | 23.8% / 75.5% |
| Original, breakout off | 14,186 | 526 | 14,186 | - | 51.1% | 7 | 7,553 | -629 | 0 | 30.8% / 62.6% |
| Revised, breakout off | 14,242 | 526 | 14,242 | - | 51.1% | 7 | 7,531 | -629 | 0 | 30.8% / 62.6% |

**Slippage scenarios** (net $, breakout on, original / revised): NQ 2015-25: 0 ticks 197,349 / 197,357; 1 tick
169,114 / 169,237; 2 ticks 138,259 / 141,335. 2025-26: 0 ticks 17,864 / 17,918; 1 tick 15,333 / 15,389; 2 ticks
12,382 / 12,440. Full tables (all 12 runs per dataset): `data/controlled_nq_2015-2025.csv`, `data/controlled_index_2025-2026.csv`.

What this establishes:
- **The code changes do not change performance in a way that matters**: +$123 over ten years on NQ (+0.07%),
  +$56 in the latest 15 months, drawdown $22-26 lower, the same evaluation pass rate. The repairs are for live
  safety and do not act in a backtest; the stop that only tightens moves a few trades. The revised export's +$415 was
  mostly the slippage setting.
- **Each tick of slippage costs about $28,000-31,000 over ten years (17%) and about $2,500-3,000 in the latest 15
  months.** Fill assumptions matter far more than the code changes.
- **The breakout, rerun in full**: over ten years of NQ it adds $57,600 at one tick (its shorts +$14,900) with about
  the same intraday drawdown (14,374 vs 14,130), a slightly higher evaluation pass rate, but 7 days below -$1,000
  (none without it). In the latest 15 months it adds only $1,146, its shorts lose $1,693, the drawdown is larger
  (9,308 vs 7,553) and **fewer evaluations pass with it (23.8% vs 30.8%)**. On recent data, momentum only is the
  better evaluation strategy; on ten years the breakout earns its place. That conflict is the open question, not a
  settled answer, and fifteen months is one regime.

## 7. One exit alternative, on untouched data

**Unavailable as asked.** Every period before 16 October 2026 has been used by earlier rounds (the latest 15 months
included), so no historical data is untouched. **Proposed**: one alternative, fixed now - "half at 1R" (half the
contracts close at a limit 25 points from the fill; the rest keeps every rule; R not redefined; one trade), the
only exit that lowered the drawdown in every period of round 138 - tested **forward** on Sim101 from the first
session after installation, against the current exit run in parallel on the same account data in the stand-in, for
20 sessions or 60 trades, judged on intraday drawdown and net after costs at one tick.

## Still needed from the user (unavailable without it)

1. The revised run's settings (a screenshot of the Strategy Analyzer settings panel): fill resolution, trading hours.
2. The 1-minute MNQ DEC26 bars of the runs (Tools -> Historical Data -> Export), to replay both exports trade by trade
   in the stand-in and confirm the Oct 12 explanation.
