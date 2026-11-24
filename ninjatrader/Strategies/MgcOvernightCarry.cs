// MGC Overnight Carry: gold's overnight move carried on into the COMEX morning (docs/STRATEGY_SEARCH.md, 37). For the
// days MNQ does not trade (the user, 2026-11-24: "if you can't trade MNQ, trade other stuff"); it runs beside
// MnqCleanBand on the same account, on its own chart.
//
// 5-minute MGC chart with the metals' extended hours (the overnight session and the 13:25 bar), New York times:
//   * the move = the 08:20 bar's open less the prior session's 13:25 bar close (SettleAt);
//   * the last 14 sessions' average |move|: today's at least K x that, and the bars from 08:20 to 08:20 + Confirm
//     minutes closing its way (the last one's close against the 08:20 open): a market order at that close (filled at
//     the next open), the stop a tick past StopAt (0.6) of the way from the 08:20 open to that close, set with the entry;
//   * out at market at the 14:10 bar's close (filled at 14:15, ExitAt; a gap in the bars: the first bar from 14:10 on);
//     a holiday's early close in the trading-hours template: out 5 minutes before it (13:45: at the 13:40 open; the
//     Friday after Thanksgiving and Christmas Eve: by the 13:10 open, whatever the template says); a
//     trade still open when the next trading day starts (no early close in the template) goes out on its first bar; one
//     trade a day at most.
// Size: as MnqCleanBand, by the account's profit over its start balance (1, 2 from Step2At, 3 from Step3At, at most
// MaxContracts; FixedContracts overrides); no trade while the account is under CushionGuard $ above its trailing floor.
// research/zoo/mk_search.py carry is the same rule in Python and
// tests/test_ninjatrader_gold.py holds the two to trade-for-trade agreement on the NinjaTrader stand-in.
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
    public class MgcOvernightCarry : Strategy
    {
        class Day
        {
            public DateTime Date;
            public int Bars;
            public double Open = double.NaN;    // the 08:20 bar's open
            public double Settle = double.NaN;  // the 13:25 bar's close
            public double Move = double.NaN;    // Open less the prior kept session's Settle
        }

        TimeZoneInfo newYork;
        readonly List<Day> hist = new List<Day>();  // complete sessions (at least 180 five-minute bars)
        Day today;
        int qty, pos;
        DateTime posDay = DateTime.MinValue;  // the trading day the open trade entered
        bool tradedToday, entryPending, exiting, stopGone;
        DateTime stopGoneUtc = DateTime.MinValue;
        string status = "waiting for history";
        double hwm = double.NaN, cushion = double.NaN;  // the cushion guard (as MnqCleanBand's): no gold trade near the floor
        bool guarded, hwmLive;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MgcOvernightCarry";
                Description = "Gold's overnight move carried on: a big overnight move confirmed by the COMEX open's first minutes, held to 13:30.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.UniqueEntries;
                IsExitOnSessionCloseStrategy = true;  // a backstop only: the trade is out by 13:30
                ExitOnSessionCloseSeconds = 60;
                BarsRequiredToTrade = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelCloseIgnoreRejects;
                K = 1.5;
                ConfirmMinutes = 15;
                StopAt = 0.6;  // docs/STRATEGY_SEARCH.md 39: PF 1.24 / 1.54 to 1.80 / 1.88, the worst trade -$347 to -$141
                OpenAt = 500;
                ExitAt = 855;    // 14:15 (docs/STRATEGY_SEARCH.md 41; 13:30 as first shipped)
                SettleAt = 810;  // the prior session's 13:25 bar ends at 13:30: the move's reference
                MaxContracts = 3;
                FixedContracts = 0;
                Step2At = 2000;
                Step3At = 3500;
                StartBalance = 50000;
                StartProfit = 0;
                UseAccountBalanceLive = true;
                PlaceOrders = true;
                CushionGuard = 1500;
                TrailingDrawdown = 2000;
                HighestBalance = 0;
            }
            else if (State == State.DataLoaded)
            {
                newYork = NewYork();
                sessions = new SessionIterator(Bars);
                Print("Gold carry settings: " + Instrument.FullName + ", " + BarsPeriod.Value + " " + BarsPeriod.BarsPeriodType +
                      ", account " + (Account == null ? "none" : Account.Name) + ", move at least " + K + "x the 14-session average, " +
                      ConfirmMinutes + " minutes to confirm, out " + (ExitAt / 60) + ":" + (ExitAt % 60).ToString("00") +
                      ", up to " + MaxContracts + " MGC (2 from +$" + Step2At + ", 3 from +$" + Step3At + ")");
            }
            else if (State == State.Realtime)
            {
                qty = Contracts(Profit());  // enabled mid-session: the size from the account, not the replayed history
                ApplyGuard(Profit());
                Print("Gold carry live: " + qty + " MGC a trade");
            }
        }

        static TimeZoneInfo NewYork()
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
            catch (TimeZoneNotFoundException) { return TimeZoneInfo.FindSystemTimeZoneById("America/New_York"); }
        }

        // the bar end (New York minutes) at which to exit: ExitAt, or 5 minutes before an earlier session end from the
        // trading-hours template (a holiday's early close, COMEX 13:45 the day after Thanksgiving: out at the 13:40 open)
        SessionIterator sessions;
        DateTime flatDay = DateTime.MinValue;
        int flatCached;

        int FlatBy(DateTime barEndPlatform)
        {
            DateTime endNy = ToNy(barEndPlatform);
            if (endNy.Date == flatDay) return flatCached;
            int flat = ExitAt;
            try
            {
                if (sessions != null && sessions.GetNextSession(barEndPlatform, true))
                {
                    DateTime end = ToNy(sessions.ActualSessionEnd);
                    if (end.Date == endNy.Date)
                        flat = Math.Min(flat, end.Hour * 60 + end.Minute - 5);
                }
            }
            catch (Exception)
            {
                // no session information: ExitAt, and the next-day rule in OnBarUpdate as the backstop
            }
            // the CME half days, should the template not list them: the Friday after Thanksgiving and Christmas Eve (13:15
            // New York for the index futures, 13:45 for metals): out by the 13:10 open
            if ((endNy.Month == 11 && endNy.DayOfWeek == DayOfWeek.Friday && endNy.Day >= 23 && endNy.Day <= 29) ||
                (endNy.Month == 12 && endNy.Day == 24))
                flat = Math.Min(flat, 790);  // 13:10
            flatDay = endNy.Date;
            flatCached = flat;
            return flat;
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

        void NewDay(DateTime date)
        {
            if (today != null && today.Bars >= 180)
                hist.Add(today);  // only complete sessions count, as research/zoo's gold days
            if (hist.Count > 40) hist.RemoveAt(0);
            today = new Day();
            today.Date = date;
            tradedToday = false;
            qty = Contracts(Profit());
            ApplyGuard(Profit());
        }

        // the floor trails the highest end-of-day balance (HighestBalance, then the balance at each day's start) by
        // TrailingDrawdown and stops at StartBalance; under CushionGuard $ above it: no gold trade that day (with MNQ on the
        // same account, 2015 - Mar 2025: the safest of the guard's versions, docs/STRATEGY_SEARCH.md 38)
        void ApplyGuard(double prof)
        {
            double bal = StartBalance + prof;
            // the replay of the loaded history raises hwm with simulated profits; live, the floor comes from the real
            // account: at the switch to real time start again from HighestBalance (or the start balance)
            if (double.IsNaN(hwm) || (State == State.Realtime && !hwmLive))
            {
                hwm = Math.Max(StartBalance, HighestBalance);
                hwmLive = State == State.Realtime;
            }
            hwm = Math.Max(hwm, bal);
            cushion = bal - Math.Min(hwm - TrailingDrawdown, StartBalance);
            guarded = CushionGuard > 0 && cushion < CushionGuard;
        }

        protected override void OnBarUpdate()
        {
            if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 5)
                return;
            Bar();
            CheckNoStop(true);
            if (State == State.Realtime || CurrentBar >= Bars.Count - 2)
                Draw.TextFixed(this, "gold_dash", "MGC Overnight Carry | " + status + " | " + qty + " MGC a trade | today $" +
                               TodayPnl().ToString("F0", CultureInfo.InvariantCulture), TextPosition.TopRight);
        }

        double dayCumStart;
        double TodayPnl() { return CumProfit - dayCumStart; }

        void Bar()
        {
            DateTime t = ToNy(Time[0]).AddMinutes(-5);  // the bar's start, New York
            DateTime tday = t.AddHours(6).Date;         // the trading day: 18:00 the evening before to 17:00
            int mm = t.Hour * 60 + t.Minute;
            if (today == null || tday != today.Date)
            {
                NewDay(tday);
                dayCumStart = CumProfit;
            }
            today.Bars++;
            if (mm == OpenAt)
            {
                today.Open = Open[0];
                Day prev = hist.Count > 0 ? hist[hist.Count - 1] : null;
                today.Move = prev != null ? today.Open - prev.Settle : double.NaN;
            }
            if (mm == SettleAt - 5)
                today.Settle = Close[0];

            int mp = Position.MarketPosition == MarketPosition.Long ? 1 : Position.MarketPosition == MarketPosition.Short ? -1 : 0;
            if (mp == 0)
            {
                pos = 0;
                exiting = false;
            }
            if (entryPending && mp != 0)
            {
                pos = mp;
                posDay = today.Date;
            }
            entryPending = false;

            if (pos != 0 && posDay != today.Date)  // the session ended before the exit (a holiday's early close): out now
            {
                Exit("Session end");
                return;
            }
            if (pos != 0 && mm + 5 >= FlatBy(Time[0]) && mm < 1020)  // out at the next open (14:15's, or the first bar after a gap)
            {
                Exit("Time exit");
                return;
            }
            if (mm != OpenAt + ConfirmMinutes - 5 || mp != 0 || tradedToday || !PlaceOrders)
                return;
            if (guarded)
            {
                status = "CUSHION GUARD: $" + cushion.ToString("F0", CultureInfo.InvariantCulture) + " above the floor - no gold trade today";
                return;
            }
            if (hist.Count < 14 || double.IsNaN(today.Move))
            {
                status = hist.Count < 14 ? "NOT READY: " + hist.Count + " complete sessions, needs 14 (load 30 days)" : "no move today";
                return;
            }
            double sum = 0;
            for (int j = hist.Count - 14; j < hist.Count; j++)
            {
                if (double.IsNaN(hist[j].Move)) { status = "a session without its 08:20 / 13:25 bars in the last 14"; return; }
                sum += Math.Abs(hist[j].Move);
            }
            double avg = sum / 14;
            status = "OK: move " + today.Move.ToString("F1", CultureInfo.InvariantCulture) + ", needs " + (K * avg).ToString("F1", CultureInfo.InvariantCulture);
            if (Math.Abs(today.Move) < K * avg)
                return;
            int side = today.Move > 0 ? 1 : -1;
            if (side * (Close[0] - today.Open) <= 0)
                return;
            double tick = TickSize;
            double stop = Instrument.MasterInstrument.RoundToTickSize(today.Open + StopAt * (Close[0] - today.Open) - side * tick);
            string name = side > 0 ? "CarryLong" : "CarryShort";
            SetStopLoss(name, CalculationMode.Price, stop, false);
            if (side > 0) EnterLong(qty, name); else EnterShort(qty, name);
            entryPending = true;
            tradedToday = true;
            Print(Time[0] + "  Gold carry: " + (side > 0 ? "long " : "short ") + qty + " MGC, overnight move " +
                  today.Move.ToString("F1", CultureInfo.InvariantCulture) + ", stop " + stop.ToString("F1", CultureInfo.InvariantCulture));
        }

        void Exit(string why)
        {
            int d = Position.MarketPosition == MarketPosition.Long ? 1 : Position.MarketPosition == MarketPosition.Short ? -1 : pos;
            if (d > 0) ExitLong(why, "CarryLong"); else ExitShort(why, "CarryShort");
            exiting = true;
            pos = 0;
        }

        // a position must never be without its stop: if the broker cancels or rejects it, out at market (as MnqCleanBand)
        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
                                              double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error,
                                              string comment)
        {
            if (order == null || order.Name != "Stop loss")
                return;
            if (orderState == OrderState.Accepted || orderState == OrderState.Working || orderState == OrderState.Filled)
            {
                stopGone = false;
                return;
            }
            if (orderState != OrderState.Cancelled && orderState != OrderState.Rejected)
                return;
            if (Position.MarketPosition == MarketPosition.Flat || exiting)
                return;
            stopGone = true;
            stopGoneUtc = DateTime.UtcNow;
            Print(time + "  Gold carry: the stop was " + orderState + " (" + comment + ") with the position open");
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
            Print(Time[0] + "  Gold carry: no stop on the open position - closing it at market");
            Exit("No stop");
        }

        #region Properties
        [NinjaScriptProperty]
        [Range(0.1, 10)]
        [Display(Name = "Overnight move at least this many 14-session averages", Order = 1, GroupName = "1. Entry")]
        public double K { get; set; }

        [NinjaScriptProperty]
        [Range(5, 120)]
        [Display(Name = "Minutes from 08:20 that must close its way", Order = 2, GroupName = "1. Entry")]
        public int ConfirmMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(0, 0.95)]
        [Display(Name = "Stop: this share of the way from the 08:20 open to the 08:30 bar's close (0 = the open)", Order = 5, GroupName = "1. Entry")]
        public double StopAt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1439)]
        [Display(Name = "Session open (minutes from midnight New York; 500 = 08:20)", Order = 3, GroupName = "1. Entry")]
        public int OpenAt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1439)]
        [Display(Name = "Out at (minutes from midnight New York; 855 = 14:15)", Order = 4, GroupName = "1. Entry")]
        public int ExitAt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1439)]
        [Display(Name = "The move's reference: the prior session's bar ending at (810 = 13:30)", Order = 6, GroupName = "1. Entry")]
        public int SettleAt { get; set; }

        [NinjaScriptProperty]
        [Range(1, 3)]
        [Display(Name = "Most contracts", Order = 1, GroupName = "2. Size")]
        public int MaxContracts { get; set; }

        [NinjaScriptProperty]
        [Range(0, 50)]
        [Display(Name = "Fixed contracts (0 = the profit steps)", Order = 2, GroupName = "2. Size")]
        public int FixedContracts { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "2 contracts from this profit $", Order = 3, GroupName = "2. Size")]
        public double Step2At { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "3 contracts from this profit $", Order = 4, GroupName = "2. Size")]
        public double Step3At { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000)]
        [Display(Name = "Cushion guard: no trade below this $ above the floor (0 = off)", Order = 1, GroupName = "4. Cushion guard")]
        public double CushionGuard { get; set; }

        [NinjaScriptProperty]
        [Range(100, 100000)]
        [Display(Name = "The account's trailing drawdown $", Order = 2, GroupName = "4. Cushion guard")]
        public double TrailingDrawdown { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000000)]
        [Display(Name = "Highest end-of-day balance so far $ (from the prop firm's dashboard; 0 = the start balance)", Order = 3, GroupName = "4. Cushion guard")]
        public double HighestBalance { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000000)]
        [Display(Name = "Account start balance $", Order = 1, GroupName = "3. Account")]
        public double StartBalance { get; set; }

        [NinjaScriptProperty]
        [Range(-100000, 1000000)]
        [Display(Name = "Profit already made at the start $ (backtests)", Order = 2, GroupName = "3. Account")]
        public double StartProfit { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Live: size from the account's balance", Order = 3, GroupName = "3. Account")]
        public bool UseAccountBalanceLive { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Place orders", Order = 4, GroupName = "3. Account")]
        public bool PlaceOrders { get; set; }
        #endregion
    }
}
