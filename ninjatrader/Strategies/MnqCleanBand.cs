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
            public readonly Dictionary<int, double> Moves = new Dictionary<int, double>();
        }

        TimeZoneInfo newYork;
        readonly List<Day> hist = new List<Day>();
        Day today;
        double dayOpen, prevClose, sma, vwapNum, vwapDen, dayCumStart, hardRef, stop, entryPx;
        int pos, tradesToday, qty;
        bool ready, exitSent, beDone, early;
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
                IsExitOnSessionCloseStrategy = false;
                BarsRequiredToTrade = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelCloseIgnoreRejects;
                TrendDays = 20;
                HardStop = 200;
                BreakEvenAt = 0.5;
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
            vwapNum = vwapDen = 0;
            tradesToday = 0;
            dayCumStart = CumProfit;
            ready = hist.Count >= Math.Max(21, TrendDays + 1);
            sigma.Clear();
            if (!ready) return;
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
        }

        protected override void OnBarUpdate()
        {
            if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 5)
                return;
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
            if (pos == 0 && mp != 0 && !exitSent)  // the entry filled at this bar's open
            {
                pos = mp;
                entryPx = Position.AveragePrice;
                beDone = false;
            }
            exitSent = false;
            if (!ready)
                return;
            double tick = TickSize, pv = Instrument.MasterInstrument.PointValue;

            if (pos != 0 && mm >= 950)  // out at the 15:55 open
            {
                Exit("Session end");
                return;
            }
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
            if (want > 0) EnterLong(qty, name); else EnterShort(qty, name);
            tradesToday++;
            Print(Time[0] + "  Clean band: " + (want > 0 ? "long " : "short ") + qty + " MNQ, stop " + stop.ToString("F2", CultureInfo.InvariantCulture));
        }

        void Exit(string why)
        {
            if (pos > 0) ExitLong(why, "Long"); else ExitShort(why, "Short");
            exitSent = true;
            pos = 0;
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
        #endregion
    }
}
