// MNQ Clean Noise-Band: the user's "Clean Noise-Band Momentum (Prop Version)" spec with the changes research/zoo found
// it needs to keep a 50K account with the $2,000 trailing floor (docs/STRATEGY_SEARCH.md, sections 1-33).
//
// 5-minute MNQ chart (ETH, so the news rule can read the 08:30 bar). Every half hour from 10:00 to LastEntry (14:00):
//   * the noise area: sigma = the mean over the last 14 complete sessions of |close at that time / the 09:30 open - 1|;
//     upper = max(today's open, the prior close) x (1 + sigma), lower = min(...) x (1 - sigma);
//   * flat: long when the close is above upper and above the TrendDays-session average of closes, at least RangePos up
//     the day's range, and (after 10:00) the day not already MaxMove usual ranges up from its open; short mirrored;
//     a market order at the bar's close (filled at the next open);
//   * the stop, set with the entry: the tighter of the band on the trade's side (or VWAP when tighter) and a hard stop
//     HardStop $ a contract from the expected fill (the signal close + a tick); at each check it moves to the tighter
//     of the new band / VWAP and the hard stop, never looser; if that is already at or past the close, out at market;
//   * a take profit TakeProfitAt hard stops from the fill; once a bar closes BreakEvenAt x the hard stop in profit,
//     the stop goes to the entry + BreakEvenPlus points; out at market at the 15:50 bar's close (15:55's open);
//   * a close StretchAddAt sigmas or more past the band trades one contract more (at most MaxContracts).
// Gap trade: a gap of GapK x the 14-session average whose 09:30 bar moves the gap's way by GapMinBody x the average
// range; in at 09:35, the stop at the 09:30 open (at most GapCap points), out at 09:55.
// News days (the 08:30 volume against 08:20-08:29): NewsSkipFrom-NewsSkipTo x no trades; NewsBigAt x and up a contract
// more. Account: no new entry once the day's closed P/L is down DayStop $; contracts by profit over the start balance
// (1, 2 from Step2At, 3 from Step3At, never more than MaxContracts). research/zoo/strats.py (noise with nt=True, gap_go)
// is the same rule in Python and tests/test_ninjatrader_clean.py holds the two to trade-for-trade agreement.
#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class MnqCleanBand : Strategy
    {
        static readonly int[] Checks = { 600, 630, 660, 690, 720, 750, 780, 810, 840, 870, 900 };

        class Day
        {
            public DateTime Date;
            public double Close;
            public int Bars;
            public double Gap = double.NaN;  // the 09:30 open less the prior complete session's close
            public double Range;  // the session's high - low (09:30-16:00)
            public readonly Dictionary<int, double> Moves = new Dictionary<int, double>();
        }

        TimeZoneInfo newYork;
        readonly List<Day> hist = new List<Day>();
        Day today;
        double dayOpen, prevClose, sma, vwapNum, vwapDen, dayCumStart, hardRef, stop, entryPx, dayHigh, dayLow, avgRange;
        int pos, tradesToday, qty, gapPos;
        bool ready, beDone, early, exiting, gapWarned, noisePending, gapPending, gapToday, stopGone;
        DateTime stopGoneUtc = DateTime.MinValue;
        // news days (docs/STRATEGY_SEARCH.md, 15): the 08:30 bar's volume against the 08:20 and 08:25 bars' average
        DateTime preDate = DateTime.MinValue;
        double preVol, atVol, newsSpike = double.NaN;
        int preBars;
        bool newsSkip;
        readonly Dictionary<int, double> sigma = new Dictionary<int, double>();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqCleanBand";
                Description = "The Clean Noise-Band spec with the 50K fixes: trend entries at the half-hour checks, the band as the stop, a hard stop, a take profit, break-even, a day stop, the gap trade and news days.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.UniqueEntries;
                IsExitOnSessionCloseStrategy = true;  // a backstop: half days close before the 15:55 exit
                ExitOnSessionCloseSeconds = 60;
                BarsRequiredToTrade = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelCloseIgnoreRejects;
                TrendDays = 20;
                HardStop = 200;
                BreakEvenAt = 0.4;
                BreakEvenPlus = 2;  // points past entry: the scratch exits close as small wins (docs/STRATEGY_SEARCH.md, 23)
                LastEntry = 840;
                MaxTradesPerDay = 9;
                DayStop = 600;
                MaxContracts = 3;
                FixedContracts = 0;
                Step2At = 2000;
                Step3At = 3500;  // was 4500: safe since the strong-break contract and the gap rule (docs 32)
                EarlyMaxTrades = 0;
                EarlyCushion = 0;
                StartBalance = 50000;
                StartProfit = 0;
                UseAccountBalanceLive = true;
                VwapStop = true;
                VwapEntry = false;  // off since docs/STRATEGY_SEARCH.md, 9
                RangePos = 0.65;  // docs/STRATEGY_SEARCH.md, 20
                MaxMove = 1.1;  // docs/STRATEGY_SEARCH.md, 22 and 26
                PlaceOrders = true;
                BlockOnDataGap = true;
                TakeProfitAt = 2.5;
                GapLeg = true;
                GapFrom = 0;  // 2026-11-24: from day one with the news-day rule: 0 of 104 starts lost, more days (docs 19)
                GapK = 0.5;  // 0.3 with a 40-point cap was tried and taken back (docs 29)
                GapCap = 30;
                GapMinBody = 0.03;  // docs 28
                StretchAddAt = 1.5;  // docs 30
                NewsDays = true;
                NewsBigAt = 6;
                NewsSkipFrom = 2;
                NewsSkipTo = 3;
            }
            else if (State == State.Realtime && today != null)
            {
                // enabled mid-session: today's size and gap leg came from the replay of the loaded history, not from the
                // account; size them from the account's balance now
                double prof = Profit();
                qty = Contracts(prof);
                early = EarlyMaxTrades > 0 && prof < EarlyCushion;
                gapToday = GapLeg && (GapFrom <= 0 || prof >= GapFrom) && ready;
                ApplyNews();
                Print("Clean band live: profit over the start balance $" + prof.ToString("F0", CultureInfo.InvariantCulture) + ", " + qty +
                      " MNQ a trade, gap trade " + (gapToday ? "on" : "off") + (ready ? "" : " - NOT READY (history)"));
            }
            else if (State == State.DataLoaded)
            {
                newYork = NewYork();
                Print("Clean band settings: " + Instrument.FullName + ", " + BarsPeriod.Value + " " + BarsPeriod.BarsPeriodType +
                      ", account " + (Account == null ? "none" : Account.Name) + ", trend " + TrendDays + " days, hard stop $" +
                      HardStop + ", break-even at " + BreakEvenAt + "x, last entry " + (LastEntry / 60) + ":" + (LastEntry % 60).ToString("00") +
                      ", day stop $" + DayStop + ", up to " + MaxContracts + " MNQ (2 from +$" + Step2At + ", 3 from +$" + Step3At +
                      (StretchAddAt > 0 ? ", +1 on a break " + StretchAddAt + " sigma past the band" : "") + ")");
            }
        }

        static TimeZoneInfo NewYork()
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
            catch (TimeZoneNotFoundException) { return TimeZoneInfo.FindSystemTimeZoneById("America/New_York"); }
        }

        DateTime ToNy(DateTime t)
        {
            TimeZoneInfo platform = NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;
            return TimeZoneInfo.ConvertTime(DateTime.SpecifyKind(t, DateTimeKind.Unspecified), platform, newYork);
        }

        double CumProfit { get { return SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit; } }

        double Profit()
        {
            if (State == State.Realtime && UseAccountBalanceLive && Account != null)
            {
                double liq = Account.Get(AccountItem.NetLiquidation, Currency.UsDollar);
                if (liq > 0) return liq - StartBalance;
            }
            return StartProfit + CumProfit;
        }

        int Contracts(double profit)
        {
            if (FixedContracts > 0)
                return FixedContracts;
            int q = 1;
            if (profit >= Step2At) q = 2;
            if (profit >= Step3At) q = 3;
            return Math.Max(1, Math.Min(q, MaxContracts));
        }

        const int MaxMissingWeekdays = 5;

        static int MissingWeekdays(DateTime from, DateTime to)  // weekdays in [from, to) less the 14 sessions held
        {
            int n = 0;
            for (DateTime d = from.Date; d < to.Date; d = d.AddDays(1))
                if (d.DayOfWeek != DayOfWeek.Saturday && d.DayOfWeek != DayOfWeek.Sunday) n++;
            return n - 14;
        }

        void NewDay(DateTime date)
        {
            if (today != null && today.Bars >= 76)
            {
                today.Range = dayHigh - dayLow;
                hist.Add(today);
            }  // only complete sessions count, as research/zoo's day sets
            if (hist.Count > 60) hist.RemoveAt(0);
            today = new Day();
            today.Date = date;
            dayOpen = Open[0];
            dayHigh = double.MinValue;
            dayLow = double.MaxValue;
            if (hist.Count > 0) today.Gap = dayOpen - hist[hist.Count - 1].Close;
            gapToday = false;
            vwapNum = vwapDen = 0;
            tradesToday = 0;
            dayCumStart = CumProfit;
            ready = hist.Count >= Math.Max(21, TrendDays + 1);
            sigma.Clear();
            if (!ready) return;
            // the chart's history must be whole. A hole (NinjaTrader's Oct 19 - Nov 6 2026 gap) would compute the noise
            // area from stale days. Counted in weekdays without a complete session in the 14-session window: holidays
            // and half days leave at most 4 (Jan 2025, 2015-2025 NQ), a real hole many more. (Calendar days, the old
            // test, blocked the Mondays after Thanksgiving, Christmas and New Year: docs/STRATEGY_SEARCH.md, 27.)
            int missing = MissingWeekdays(hist[hist.Count - 14].Date, date);
            if (BlockOnDataGap && missing > MaxMissingWeekdays)
            {
                ready = false;
                if (!gapWarned)
                    Print(Time[0] + "  Clean band: NO TRADING - the chart's history has a hole (" + missing + " weekdays without a session " +
                          "in the last 14). Reload the historical data (Tools > Historical Data, or right-click the chart > Reload All Historical Data).");
                gapWarned = true;
                return;
            }
            prevClose = hist[hist.Count - 1].Close;
            double s = 0;
            for (int j = 1; j <= TrendDays; j++) s += hist[hist.Count - j].Close;
            sma = TrendDays > 0 ? s / TrendDays : double.NaN;
            double rs = 0;
            for (int j = hist.Count - 14; j < hist.Count; j++) rs += hist[j].Range;
            avgRange = rs / 14;
            foreach (int t in Checks)
            {
                double sum = 0;
                bool all = true;
                for (int j = hist.Count - 14; j < hist.Count; j++)
                {
                    double m;
                    if (!hist[j].Moves.TryGetValue(t, out m)) { all = false; break; }
                    sum += m;
                }
                sigma[t] = all ? sum / 14 : double.NaN;
            }
            double prof = Profit();
            qty = Contracts(prof);
            early = EarlyMaxTrades > 0 && prof < EarlyCushion;  // decided at the day's start
            gapToday = GapLeg && (GapFrom <= 0 || prof >= GapFrom);  // GapFrom 0: always; else once the account has that cushion
            newsSpike = preDate == date && preBars == 2 && preVol > 0 && !double.IsNaN(atVol) ? atVol / (preVol / 2) : double.NaN;
            ApplyNews();
        }

        // a mild-news day (spike in [NewsSkipFrom, NewsSkipTo)): no trades; a big-news day (>= NewsBigAt): a contract more,
        // never past MaxContracts. Unknown spike (an RTH chart, a missing bar): the day as usual.
        void ApplyNews()
        {
            newsSkip = false;
            if (!NewsDays || double.IsNaN(newsSpike))
                return;
            if (newsSpike >= NewsSkipFrom && newsSpike < NewsSkipTo)
                newsSkip = true;
            else if (newsSpike >= NewsBigAt && FixedContracts == 0)
                qty = Math.Min(qty + 1, MaxContracts);
        }

        protected override void OnBarUpdate()
        {
            if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 5)
                return;
            Bar();
            CheckNoStop(true);
            if (State == State.Realtime || CurrentBar >= Bars.Count - 2)
                Dashboard();
        }

        // the chart's top-right corner: is it ready, how big, today's P/L
        void Dashboard()
        {
            string setup;
            if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 5)
                setup = "WRONG CHART: use a 5-minute MNQ chart";
            else if (hist.Count < Math.Max(21, TrendDays + 1))
                setup = "NOT READY: " + hist.Count + " complete sessions loaded, needs " + Math.Max(21, TrendDays + 1) +
                        " - set the chart's Days to load to 40 or more";
            else if (!ready)
                setup = "NO TRADING: the chart's history has a hole - reload the historical data";
            else
                setup = "OK";
            string txt = "MNQ Clean Noise-Band | Setup: " + setup +
                         " | " + qty + " MNQ a trade, gap trade " + (gapToday ? "on" : "off") +
                         " | today $" + (CumProfit - dayCumStart).ToString("F0", CultureInfo.InvariantCulture) +
                         (DayStop > 0 && CumProfit - dayCumStart <= -DayStop ? " (day stop: done for today)" : "") +
                         " | news " + (!NewsDays ? "off" : double.IsNaN(newsSpike) ? "n/a (needs an ETH chart)" :
                                       newsSkip ? newsSpike.ToString("F1", CultureInfo.InvariantCulture) + "x: no trades today" :
                                       newsSpike.ToString("F1", CultureInfo.InvariantCulture) + "x" + (newsSpike >= NewsBigAt ? " (+1 contract)" : "")) +
                         " | trades today " + tradesToday + " | profit over start $" + Profit().ToString("F0", CultureInfo.InvariantCulture);
            Draw.TextFixed(this, "clean_dash", txt, TextPosition.TopRight);
        }

        void Bar()
        {
            DateTime t = ToNy(Time[0]).AddMinutes(-5);  // the bar's start, New York
            int mm = t.Hour * 60 + t.Minute;
            if (mm >= 500 && mm <= 510)  // an ETH chart's pre-open bars: the news spike's inputs
            {
                if (t.Date != preDate) { preDate = t.Date; preVol = 0; preBars = 0; atVol = double.NaN; }
                if (mm < 510) { preVol += Volume[0]; preBars++; }
                else atVol = Volume[0];
            }
            if (mm < 570 || mm >= 960)
                return;
            if (today == null || t.Date != today.Date)
                NewDay(t.Date);
            today.Bars++;
            dayHigh = Math.Max(dayHigh, High[0]);
            dayLow = Math.Min(dayLow, Low[0]);
            double vol = Volume[0] > 0 ? Volume[0] : 1;
            vwapNum += (High[0] + Low[0] + Close[0]) / 3 * vol;
            vwapDen += vol;
            double vwap = vwapNum / vwapDen;
            int end = mm + 5;
            if (Array.IndexOf(Checks, end) >= 0)
                today.Moves[end] = Math.Abs(Close[0] / dayOpen - 1);
            today.Close = Close[0];

            int mp = Position.MarketPosition == MarketPosition.Long ? 1 : Position.MarketPosition == MarketPosition.Short ? -1 : 0;
            if (pos != 0 && mp == 0)  // stopped out (or the exit filled)
                pos = 0;
            if (mp == 0)
                exiting = false;
            if (gapPos != 0 && mp == 0)
                gapPos = 0;
            if (noisePending && mp != 0 && pos == 0)  // the band entry filled at this bar's open
            {
                pos = mp;
                entryPx = Position.AveragePrice;
                beDone = false;
            }
            if (gapPending && mp != 0 && gapPos == 0)  // the gap entry filled
                gapPos = mp;
            noisePending = gapPending = false;
            if (!ready)
                return;
            double tick = TickSize, pv = Instrument.MasterInstrument.PointValue;

            if (pos != 0 && mm >= 950)  // out at the 15:55 open
            {
                Exit("Session end");
                return;
            }
            if (gapPos != 0 && mm >= 590)  // the gap trade: out at the 09:55 open
            {
                Exit("Gap exit");
                return;
            }
            if (newsSkip && mp == 0)  // a mild-news day: no new trades
                return;
            if (mm == 570 && gapToday && mp == 0 && PlaceOrders)
                GapEntry(tick);
            if (pos != 0 && BreakEvenAt > 0 && !beDone && pos * (Close[0] - entryPx) >= BreakEvenAt * HardStop / pv)
            {
                double be = Instrument.MasterInstrument.RoundToTickSize(entryPx + pos * Math.Max(tick, BreakEvenPlus));
                if (pos * (be - stop) > 0)
                {
                    stop = be;
                    SetStopLoss(pos > 0 ? "Long" : "Short", CalculationMode.Price, stop, false);
                }
                beDone = true;
            }
            double sg;
            if (!sigma.TryGetValue(end, out sg) || double.IsNaN(sg))
                return;
            double up = Math.Max(dayOpen, prevClose) * (1 + sg), dn = Math.Min(dayOpen, prevClose) * (1 - sg);
            double bl = VwapStop ? Math.Max(up, vwap) : up, bs = VwapStop ? Math.Min(dn, vwap) : dn;
            if (pos != 0)
            {
                double hardPx = hardRef - pos * HardStop / pv;
                double nw = Instrument.MasterInstrument.RoundToTickSize(pos > 0 ? Math.Max(bl, hardPx) : Math.Min(bs, hardPx));
                nw = pos > 0 ? Math.Max(nw, stop) : Math.Min(nw, stop);  // never looser
                if (pos * (Close[0] - nw) <= 0)
                    Exit("Back inside");
                else if (nw != stop)
                {
                    stop = nw;
                    SetStopLoss(pos > 0 ? "Long" : "Short", CalculationMode.Price, stop, false);
                }
                return;
            }
            if (mp != 0 || end > LastEntry || mm >= 950 || tradesToday >= MaxTradesPerDay || !PlaceOrders)
                return;
            if (DayStop > 0 && CumProfit - dayCumStart <= -DayStop)
                return;
            if (early && tradesToday >= EarlyMaxTrades)
                return;
            int want = Close[0] > up ? 1 : Close[0] < dn ? -1 : 0;
            if (want != 0 && VwapEntry && want * (Close[0] - vwap) <= 0) want = 0;
            if (want != 0 && TrendDays > 0 && want * (Close[0] - sma) <= 0) want = 0;
            if (want != 0 && MaxMove > 0 && end != 600 && want * (Close[0] - dayOpen) > MaxMove * avgRange)  // not at 10:00 (24)
                want = 0;  // the day has already run past its usual range its way (docs/STRATEGY_SEARCH.md, 22)
            if (want != 0 && RangePos > 0)  // the close still near the day's extreme its way (docs/STRATEGY_SEARCH.md, 20)
            {
                double posR = dayHigh > dayLow ? (Close[0] - dayLow) / (dayHigh - dayLow) : 0.5;
                if ((want > 0 && posR < RangePos) || (want < 0 && posR > 1 - RangePos)) want = 0;
            }
            if (want == 0)
                return;
            hardRef = Close[0] + want * tick;
            double hp = hardRef - want * HardStop / pv;
            stop = want > 0 ? Math.Max(bl, hp) : Math.Min(bs, hp);
            if (want * (hardRef - stop) <= 0)  // VWAP on the wrong side of the fill: the band alone (a stop past the price is rejected)
                stop = want > 0 ? Math.Max(up, hp) : Math.Min(dn, hp);
            stop = Instrument.MasterInstrument.RoundToTickSize(stop);
            string name = want > 0 ? "Long" : "Short";
            SetStopLoss(name, CalculationMode.Price, stop, false);
            if (TakeProfitAt > 0)
                SetProfitTarget(name, CalculationMode.Ticks, Math.Max(1, Math.Round(TakeProfitAt * HardStop / pv / tick)));
            noisePending = true;
            // a close StretchAddAt sigmas or more past the band: one more contract, at most MaxContracts (not with
            // FixedContracts). Those entries win 65-74% on 2015-2025 NQ, PF 2.1-2.8 (docs/STRATEGY_SEARCH.md, 30)
            double refPx = want > 0 ? Math.Max(dayOpen, prevClose) : Math.Min(dayOpen, prevClose);
            double stretch = want * (Close[0] - (want > 0 ? up : dn)) / (sg * refPx);
            int q = StretchAddAt > 0 && FixedContracts <= 0 && sg > 0 && stretch >= StretchAddAt ? Math.Min(qty + 1, MaxContracts) : qty;
            if (want > 0) EnterLong(q, name); else EnterShort(q, name);
            tradesToday++;
            Print(Time[0] + "  Clean band: " + (want > 0 ? "long " : "short ") + q + " MNQ" + (q > qty ? " (a strong break: +1)" : "") +
                  ", stop " + stop.ToString("F2", CultureInfo.InvariantCulture));
        }

        // gap and go (research/zoo/strats.py gap_go): a gap of GapK x the last 14 sessions' average |gap| whose 09:30 bar
        // closes the gap's way by GapMinBody x the average range; in at 09:35, the stop at the 09:30 open but no farther
        // than GapCap points; out at 09:55
        void GapEntry(double tick)
        {
            if (hist.Count < 15 || double.IsNaN(today.Gap))
                return;
            double sum = 0;
            for (int j = hist.Count - 14; j < hist.Count; j++)
            {
                if (double.IsNaN(hist[j].Gap)) return;
                sum += Math.Abs(hist[j].Gap);
            }
            double gap = today.Gap, avg = sum / 14;
            int side = gap > 0 ? 1 : -1;
            if (Math.Abs(gap) < GapK * avg || side * (Close[0] - dayOpen) <= 0)
                return;
            // the 09:30 bar must move the gap's way by GapMinBody x the 14-day average range: a smaller bar puts the
            // stop (its open) a few points away, inside the noise (2015-2025 NQ, ES, live: PF 0.0-0.76, 0-8% winners;
            // docs/STRATEGY_SEARCH.md, 28)
            if (side * (Close[0] - dayOpen) < GapMinBody * avgRange)
                return;
            double e = Close[0] + side * tick;
            double dist = Math.Min(Math.Max(Math.Abs(e - dayOpen), 4 * tick), GapCap);
            string name = side > 0 ? "GapLong" : "GapShort";
            SetStopLoss(name, CalculationMode.Price, e - side * dist, false);
            if (side > 0) EnterLong(qty, name); else EnterShort(qty, name);
            gapPending = true;
            Print(Time[0] + "  Clean band: gap trade " + (side > 0 ? "long " : "short ") + qty + " MNQ, stop " +
                  (e - side * dist).ToString("F2", CultureInfo.InvariantCulture));
        }

        void Exit(string why)
        {
            int d = Position.MarketPosition == MarketPosition.Long ? 1 : Position.MarketPosition == MarketPosition.Short ? -1 : pos;
            bool gapLeg = gapPos != 0 && pos == 0;
            string from = gapLeg ? (d > 0 ? "GapLong" : "GapShort") : (d > 0 ? "Long" : "Short");
            if (d > 0) ExitLong(why, from); else ExitShort(why, from);
            exiting = true;
            pos = 0;
            gapPos = 0;
        }

        // a position must never be without its stop: if the broker cancels or rejects it, out at market (live 2026-11-17).
        // The cancel of a stop whose target just filled can reach here before the position shows flat, so the position is
        // closed at this bar's close, or live on the first tick 2 seconds after the cancel, if it is still open then and
        // no stop has come back (V38's rule, MnqNoiseV38.cs CheckNoStop).
        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
                                              double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error,
                                              string comment)
        {
            if (order == null || order.Name != "Stop loss")
                return;
            if (orderState == OrderState.Accepted || orderState == OrderState.Working || orderState == OrderState.Filled)
            {
                stopGone = false;  // a stop is back (or it did its job)
                return;
            }
            if (orderState != OrderState.Cancelled && orderState != OrderState.Rejected)
                return;
            if (Position.MarketPosition == MarketPosition.Flat || exiting)
                return;
            stopGone = true;
            stopGoneUtc = DateTime.UtcNow;
            Print(time + "  Clean band: the stop was " + orderState + " (" + comment + ") with the position open");
        }

        protected override void OnMarketData(NinjaTrader.Data.MarketDataEventArgs marketDataUpdate)
        {
            if (State == State.Realtime)
                CheckNoStop(false);
        }

        void CheckNoStop(bool atClose)
        {
            if (!stopGone)
                return;
            if (Position.MarketPosition == MarketPosition.Flat || exiting)
            {
                stopGone = false;
                return;
            }
            if (!atClose && (DateTime.UtcNow - stopGoneUtc).TotalSeconds < 2.0)
                return;
            stopGone = false;
            Print(Time[0] + "  Clean band: no stop on the open position - closing it at market");
            Exit("No stop");
        }

        #region Properties
        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Trend filter: sessions in the average of closes (0 = off)", Order = 1, GroupName = "1. Entries")]
        public int TrendDays { get; set; }

        [NinjaScriptProperty]
        [Range(600, 900)]
        [Display(Name = "Last entry check (minutes from midnight New York; 840 = 14:00)", Order = 2, GroupName = "1. Entries")]
        public int LastEntry { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Most trades a day", Order = 3, GroupName = "1. Entries")]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "The stop is also never looser than VWAP", Order = 4, GroupName = "1. Entries")]
        public bool VwapStop { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Entries also need the close on VWAP's side", Order = 5, GroupName = "1. Entries")]
        public bool VwapEntry { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1)]
        [Display(Name = "Entry close at least this far up the day's range (long; short mirrored; 0 = off)", Order = 6, GroupName = "1. Entries")]
        public double RangePos { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10)]
        [Display(Name = "No entry once the day has moved this many usual ranges its way (0 = off)", Order = 7, GroupName = "1. Entries")]
        public double MaxMove { get; set; }

        [NinjaScriptProperty]
        [Range(1, 2000)]
        [Display(Name = "Hard stop, $ a contract", Order = 1, GroupName = "2. Risk")]
        public double HardStop { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10)]
        [Display(Name = "Break-even once up this many hard stops (0 = off)", Order = 2, GroupName = "2. Risk")]
        public double BreakEvenAt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Break-even stop: points past the entry", Order = 5, GroupName = "2. Risk")]
        public double BreakEvenPlus { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000)]
        [Display(Name = "Day stop: no new entry once the day is down $ (0 = off)", Order = 3, GroupName = "2. Risk")]
        public double DayStop { get; set; }

        [NinjaScriptProperty]
        [Range(0, 20)]
        [Display(Name = "Take profit at this many hard stops (0 = off)", Order = 4, GroupName = "2. Risk")]
        public double TakeProfitAt { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "News days (needs an ETH chart: the 08:30 volume)", Order = 1, GroupName = "6. News")]
        public bool NewsDays { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Big news: a contract more from this 08:30 volume spike (x)", Order = 2, GroupName = "6. News")]
        public double NewsBigAt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Mild news: no trades from this spike (x)", Order = 3, GroupName = "6. News")]
        public double NewsSkipFrom { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Mild news: ... up to this spike (x)", Order = 4, GroupName = "6. News")]
        public double NewsSkipTo { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Gap trade (09:35-09:55)", Order = 1, GroupName = "5. Gap trade")]
        public bool GapLeg { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "Gap trade only from this profit $ (0 = always)", Order = 2, GroupName = "5. Gap trade")]
        public double GapFrom { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10)]
        [Display(Name = "Gap at least this many 14-session average gaps", Order = 3, GroupName = "5. Gap trade")]
        public double GapK { get; set; }

        [NinjaScriptProperty]
        [Range(1, 1000)]
        [Display(Name = "Gap stop at most this many points", Order = 4, GroupName = "5. Gap trade")]
        public double GapCap { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1)]
        [Display(Name = "Gap: the 09:30 bar moves its way at least this x the average range", Order = 5, GroupName = "5. Gap trade")]
        public double GapMinBody { get; set; }

        [NinjaScriptProperty]
        [Range(1, 3)]
        [Display(Name = "Most contracts", Order = 1, GroupName = "3. Size")]
        public int MaxContracts { get; set; }

        [NinjaScriptProperty]
        [Range(0, 20)]
        [Display(Name = "One more contract when the entry closes this many sigmas past the band (0 = off)", Order = 7, GroupName = "3. Size")]
        public double StretchAddAt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 50)]
        [Display(Name = "Fixed contracts (0 = the profit steps; any other number trades that many from the start)", Order = 6, GroupName = "3. Size")]
        public int FixedContracts { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "2 contracts from this profit $", Order = 2, GroupName = "3. Size")]
        public double Step2At { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "3 contracts from this profit $", Order = 3, GroupName = "3. Size")]
        public double Step3At { get; set; }

        [NinjaScriptProperty]
        [Range(0, 20)]
        [Display(Name = "Early: most trades a day until the cushion (0 = off)", Order = 4, GroupName = "3. Size")]
        public int EarlyMaxTrades { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "Early: the cushion $", Order = 5, GroupName = "3. Size")]
        public double EarlyCushion { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000000)]
        [Display(Name = "Account start balance $", Order = 1, GroupName = "4. Account")]
        public double StartBalance { get; set; }

        [NinjaScriptProperty]
        [Range(-100000, 1000000)]
        [Display(Name = "Profit already made at the start $ (backtests)", Order = 2, GroupName = "4. Account")]
        public double StartProfit { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Live: size from the account's balance", Order = 3, GroupName = "4. Account")]
        public bool UseAccountBalanceLive { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Place orders", Order = 4, GroupName = "4. Account")]
        public bool PlaceOrders { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "No trading when the chart's history has a hole", Order = 5, GroupName = "4. Account")]
        public bool BlockOnDataGap { get; set; }
        #endregion
    }
}
