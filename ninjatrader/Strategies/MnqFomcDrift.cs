// MNQ pre-FOMC drift (docs/NET_VS_DRAWDOWN.md): long before each scheduled FOMC announcement.
//
// On day D, if the next weekday is an FOMC announcement date (FedDates), buy Contracts MNQ at market at the close of
// the 13:59 bar (filled at the 14:00 bar's open); sell at market at the close of the 13:54 bar on the announcement
// day (filled at the 13:55 bar's open), before the 14:00 statement. One position at a time; nothing else. It holds
// overnight, so it does not exit at the session's close: run it on a 1-minute CME US Index Futures ETH chart. A
// catastrophe stop sits CatastropheStopPct of the price below the fill (the 2015-2025 trades never came within 2.7% of the entry).
// research/portfolio_dd.py (fomc_trades) is the same rule in Python; tests/test_fomc_drift.py holds the two to
// trade-for-trade agreement on the NinjaTrader stand-in.
#region Using declarations
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.AddOns.MnqBot;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class MnqFomcDrift : Strategy
    {
        const string EntryName = "FOMC drift";
        TimeZoneInfo newYork;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqFomcDrift";
                Description = "MNQ long from 14:00 the weekday before a scheduled FOMC announcement to 13:55 on the day.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.UniqueEntries;
                IsExitOnSessionCloseStrategy = false;  // it holds overnight
                BarsRequiredToTrade = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelCloseIgnoreRejects;
                Contracts = 2;
                CatastropheStopPct = 4.0;
                FedDates = NoiseEngine.FedDatesDefault;
                PlaceOrders = true;
            }
            else if (State == State.DataLoaded)
            {
                newYork = NewYork();
                Print("FOMC drift settings: " + Instrument.FullName + ", " + BarsPeriod.Value + " " + BarsPeriod.BarsPeriodType +
                      ", account " + (Account == null ? "none" : Account.Name) + ", " + Contracts + " MNQ, catastrophe stop " +
                      CatastropheStopPct + "%, PlaceOrders " + PlaceOrders);
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

        bool IsFomc(DateTime day)
        {
            return !string.IsNullOrEmpty(FedDates) && FedDates.Contains(day.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture));
        }

        static DateTime NextWeekday(DateTime day)
        {
            return day.AddDays(day.DayOfWeek == DayOfWeek.Friday ? 3 : day.DayOfWeek == DayOfWeek.Saturday ? 2 : 1);
        }

        protected override void OnBarUpdate()
        {
            if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 1)
                return;
            DateTime t = ToNy(Time[0]).AddMinutes(-1);  // the bar's start, New York
            int tmin = t.Hour * 60 + t.Minute;
            bool flat = Position.MarketPosition == MarketPosition.Flat;
            if (!flat && tmin == 834 && IsFomc(t.Date))
            {
                ExitLong("FOMC exit", EntryName);
                Print(Time[0] + "  FOMC drift: exit before the " + t.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) + " statement");
            }
            else if (flat && PlaceOrders && tmin == 839 && IsFomc(NextWeekday(t.Date)))
            {
                if (CatastropheStopPct > 0)  // in ticks from the fill: CatastropheStopPct of the decision bar's close
                    SetStopLoss(EntryName, CalculationMode.Ticks, Math.Max(1, Math.Round(Close[0] * CatastropheStopPct / 100.0 / TickSize)), false);
                EnterLong(Contracts, EntryName);
                Print(Time[0] + "  FOMC drift: long " + Contracts + " MNQ for the " +
                      NextWeekday(t.Date).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) + " statement");
            }
        }

        #region Properties
        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name = "Contracts", Order = 1, GroupName = "1. FOMC drift")]
        public int Contracts { get; set; }

        [NinjaScriptProperty]
        [Range(0, 50)]
        [Display(Name = "Catastrophe stop, % below the fill (0 = none)", Order = 2, GroupName = "1. FOMC drift")]
        public double CatastropheStopPct { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "FOMC announcement dates", Order = 3, GroupName = "1. FOMC drift")]
        public string FedDates { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Place orders", Order = 4, GroupName = "1. FOMC drift")]
        public bool PlaceOrders { get; set; }
        #endregion
    }
}
