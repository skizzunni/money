// MNQ Clean Noise-Band (2026-11-23): the user's "Clean Noise-Band Momentum (Prop Version)" spec, with the four fixes
// research/zoo found it needs to keep a 50K account with the $2,000 trailing floor (docs/STRATEGY_SEARCH.md).
//
// 5-minute chart, regular hours (09:30-16:00 New York). Every half hour from 10:00 to LastEntry (14:00):
//   * the noise area: sigma = the mean over the last 14 complete sessions of |close at that time / the 09:30 open - 1|;
//     upper = max(today's open, the prior close) x (1 + sigma), lower = min(...) x (1 - sigma);
//   * flat: long when the close is above upper, above the session VWAP and above the TrendDays-session average of
//     closes; short mirrored; a market order at the bar's close (filled at the next open);
//   * the stop, set with the entry: the tighter of the band on the trade's side (or VWAP when tighter) and a hard stop
//     HardStop $ a contract from the expected fill (the signal close + a tick); at each check it moves to the tighter
//     of the new band / VWAP and the hard stop, never looser; if that is already at or past the close, out at market;
//   * once a bar closes BreakEvenAt x the hard stop in profit, the stop goes to the entry + a tick;
//   * out at market at the 15:50 bar's close (filled at 15:55's open).
// Account: no new entry once the day's closed P/L is down DayStop $; contracts by profit over the start balance (1, 2
// from Step2At, 3 from Step3At, never more than MaxContracts); at most EarlyMaxTrades a day until the profit reaches
// EarlyCushion. research/zoo/strats.py (noise, nt=True) is the same rule in Python and tests/test_ninjatrader_clean.py
// holds the two to trade-for-trade agreement on the NinjaTrader stand-in.
#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
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
            public double Gap = double.NaN;  // today's 09:30 open less the prior complete session's close
            public readonly Dictionary<int, double> Moves = new Dictionary<int, double>();
        }

        TimeZoneInfo newYork;
        readonly List<Day> hist = new List<Day>();
        Day today;
        double dayOpen, prevClose, sma, vwapNum, vwapDen, dayCumStart, hardRef, stop, entryPx;
        int pos, tradesToday, qty, gapPos;
        bool ready, beDone, early, exiting, gapWarned, noisePending, gapPending, gapToday, stopGone;
        DateTime stopGoneUtc = DateTime.MinValue;
        readonly Dictionary<int, double> sigma = new Dictionary<int, double>();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqCleanBand";
                Description = "The Clean Noise-Band spec with the 50K fixes: VWAP + trend entries at the half-hour checks, the band as the stop, a hard stop, break-even, a day stop.";
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
                LastEntry = 840;
                MaxTradesPerDay = 9;
                DayStop = 600;
                MaxContracts = 3;
                Step2At = 2000;
                Step3At = 4500;
                EarlyMaxTrades = 0;
                EarlyCushion = 0;
                StartBalance = 50000;
                StartProfit = 0;
                UseAccountBalanceLive = true;
                VwapStop = true;
                PlaceOrders = true;
                BlockOnDataGap = true;
                TakeProfitAt = 2.5;
                GapLeg = true;
                GapFrom = 4500;
                GapK = 1.0;
                GapCap = 50;
            }
            else if (State == State.Realtime && today != null)
            {
                // enabled mid-session: today's size and gap leg came from the replay of the loaded history, not from the
                // account; size them from the account's balance now
                double prof = Profit();
                qty = Contracts(prof);
                early = EarlyMaxTrades > 0 && prof < EarlyCushion;
                gapToday = GapLeg && prof >= GapFrom && ready;
                Print("Clean band live: profit over the start balance $" + prof.ToString("F0", CultureInfo.InvariantCulture) + ", " + qty +
                      " MNQ a trade, gap trade " + (gapToday ? "on" : "off") + (ready ? "" : " - NOT READY (history)"));
            }
            else if (State == State.DataLoaded)
            {
                newYork = NewYork();
                Print("Clean band settings: " + Instrument.FullName + ", " + BarsPeriod.Value + " " + BarsPeriod.BarsPeriodType +
                      ", account " + (Account == null ? "none" : Account.Name) + ", trend " + TrendDays + " days, hard stop $" +
                      HardStop + ", break-even at " + BreakEvenAt + "x, last entry " + (LastEntry / 60) + ":" + (LastEntry % 60).ToString("00") +
                      ", day stop $" + DayStop + ", up to " + MaxContracts + " MNQ (2 from +$" + Step2At + ", 3 from +$" + Step3At + ")");
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
            int q = 1;
            if (profit >= Step2At) q = 2;
            if (profit >= Step3At) q = 3;
            return Math.Max(1, Math.Min(q, MaxContracts));
        }

        void NewDay(DateTime date)
        {
            if (today != null && today.Bars >= 76)
                hist.Add(today);  // only complete sessions count, as research/zoo's day sets
            if (hist.Count > 60) hist.RemoveAt(0);
            today = new Day();
            today.Date = date;
            dayOpen = Open[0];
            if (hist.Count > 0) today.Gap = dayOpen - hist[hist.Count - 1].Close;
            gapToday = false;
            vwapNum = vwapDen = 0;
            tradesToday = 0;
            dayCumStart = CumProfit;
            ready = hist.Count >= Math.Max(21, TrendDays + 1);
            sigma.Clear();
            if (!ready) return;
            // the chart's history must be whole: 14 sessions span at most 23 calendar days (holidays included). A hole
            // (NinjaTrader's Oct 19 - Nov 6 2026 gap) would compute the noise area from stale days.
            double span = (date - hist[hist.Count - 14].Date).TotalDays;
            if (BlockOnDataGap && span > 23)
            {
                ready = false;
                if (!gapWarned)
                    Print(Time[0] + "  Clean band: NO TRADING - the chart's history has a hole (the last 14 sessions span " + span +
                          " days). Reload the historical data (Tools > Historical Data, or right-click the chart > Reload All Historical Data).");
                gapWarned = true;
                return;
            }
            prevClose = hist[hist.Count - 1].Close;
            double s = 0;
            for (int j = 1; j <= TrendDays; j++) s += hist[hist.Count - j].Close;
            sma = TrendDays > 0 ? s / TrendDays : double.NaN;
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
            gapToday = GapLeg && prof >= GapFrom;  // the gap leg only once the account has its cushion
        }

        protected override void OnBarUpdate()
        {
            if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 5)
                return;
            Bar();
            CheckNoStop(true);
        }

        void Bar()
        {
            DateTime t = ToNy(Time[0]).AddMinutes(-5);  // the bar's start, New York
            int mm = t.Hour * 60 + t.Minute;
            if (mm < 570 || mm >= 960)
                return;
            if (today == null || t.Date != today.Date)
                NewDay(t.Date);
            today.Bars++;
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
            if (mm == 570 && gapToday && mp == 0 && PlaceOrders)
                GapEntry(tick);
            if (pos != 0 && BreakEvenAt > 0 && !beDone && pos * (Close[0] - entryPx) >= BreakEvenAt * HardStop / pv)
            {
                double be = Instrument.MasterInstrument.RoundToTickSize(entryPx + pos * tick);
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
            if (want != 0 && want * (Close[0] - vwap) <= 0) want = 0;
            if (want != 0 && TrendDays > 0 && want * (Close[0] - sma) <= 0) want = 0;
            if (want == 0)
                return;
            hardRef = Close[0] + want * tick;
            double hp = hardRef - want * HardStop / pv;
            stop = Instrument.MasterInstrument.RoundToTickSize(want > 0 ? Math.Max(bl, hp) : Math.Min(bs, hp));
            string name = want > 0 ? "Long" : "Short";
            SetStopLoss(name, CalculationMode.Price, stop, false);
            if (TakeProfitAt > 0)
                SetProfitTarget(name, CalculationMode.Ticks, Math.Max(1, Math.Round(TakeProfitAt * HardStop / pv / tick)));
            noisePending = true;
            if (want > 0) EnterLong(qty, name); else EnterShort(qty, name);
            tradesToday++;
            Print(Time[0] + "  Clean band: " + (want > 0 ? "long " : "short ") + qty + " MNQ, stop " + stop.ToString("F2", CultureInfo.InvariantCulture));
        }

        // gap and go (research/zoo/strats.py gap_go): a gap of GapK x the last 14 sessions' average |gap| whose 09:30 bar
        // closes the gap's way; in at 09:35, the stop at the 09:30 open but no farther than GapCap points; out at 09:55
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
        [Range(1, 2000)]
        [Display(Name = "Hard stop, $ a contract", Order = 1, GroupName = "2. Risk")]
        public double HardStop { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10)]
        [Display(Name = "Break-even once up this many hard stops (0 = off)", Order = 2, GroupName = "2. Risk")]
        public double BreakEvenAt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000)]
        [Display(Name = "Day stop: no new entry once the day is down $ (0 = off)", Order = 3, GroupName = "2. Risk")]
        public double DayStop { get; set; }

        [NinjaScriptProperty]
        [Range(0, 20)]
        [Display(Name = "Take profit at this many hard stops (0 = off)", Order = 4, GroupName = "2. Risk")]
        public double TakeProfitAt { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Gap trade (09:35-09:55)", Order = 1, GroupName = "5. Gap trade")]
        public bool GapLeg { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "Gap trade only from this profit $", Order = 2, GroupName = "5. Gap trade")]
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
        [Range(1, 3)]
        [Display(Name = "Most contracts", Order = 1, GroupName = "3. Size")]
        public int MaxContracts { get; set; }

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
