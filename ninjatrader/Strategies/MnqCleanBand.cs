// MNQ Clean Noise-Band: the user's "Clean Noise-Band Momentum (Prop Version)" spec with the changes research/zoo found
// it needs to keep a 50K account with the $2,000 trailing floor (docs/STRATEGY_SEARCH.md, sections 1-97).
//
// 5-minute MNQ chart (ETH, so the news rule can read the 08:30 bar). Every half hour from 10:00 to LastEntry (14:00):
//   * the noise area: sigma = the mean over the last 14 complete sessions of |close at that time / the 09:30 open - 1|
//     (over those with that bar, at least SigmaMinSessions = 10 of them: docs 162, a missing bar keeps the check on;
//     a session without its 09:30 bar trades nothing and stays out of the history: docs 164);
//     upper = max(today's open, the prior close) x (1 + sigma), lower = min(...) x (1 - sigma);
//   * flat: long when the close is above upper and above the TrendDays-session average of closes, at least RangePos up
//     the day's range, and (after 10:00) the day not already MaxMove usual ranges up from its open; short mirrored;
//     a market order at the bar's close (filled at the next open);
//   * the stop, set with the entry: the tighter of the band on the trade's side (or VWAP when tighter) and a hard stop
//     HardStop $ a contract from the expected fill (the signal close + a tick); at each check it moves to the tighter
//     of the new band / VWAP and the hard stop, never looser; if that is already at or past the close, out at market;
//   * a take profit TakeProfitAt hard stops from the fill; once a bar closes BreakEvenAt x the hard stop in profit,
//     the stop goes to the entry + BreakEvenPlus points; once a bar closes LadderAt (1.5) hard stops up, to the entry +
//     LadderLock (0.5) hard stops; out at market at the 15:50 bar's close (15:55's open);
//     a half day (the trading-hours template's early close; the Friday after Thanksgiving and Christmas Eve, 13:15,
//     whatever the template says): out 5 minutes before it; a trade still open after any other early close goes out on
//     the next bar;
//   * a close StretchAddAt sigmas or more past the band trades one contract more (at most MaxContracts).
// Gap trade: a gap of GapK x the 14-session average whose 09:30 bar moves the gap's way by GapMinBody x the average
// range, its own range not over GapMaxBar (1.75) x the last 14 sessions' 09:30 bars' average (a wild open); in at
// 09:35, the stop at the 09:30 open (at most GapCap points), out at 09:55.
// News days (the 08:30 volume against 08:20-08:29): NewsSkipFrom-NewsSkipTo x no trades; NewsBigAt x and up a contract
// more. FOMC statement days (FomcDates, the 14:00 Fed statement; docs 180): no trades. Account: no new entry once the
// day's closed P/L is down DayStop $; contracts by profit over the start balance (1, 2 from Step2At, 3 from Step3At,
// never more than MaxContracts); the cushion guard: less than CushionGuard $ above the trailing floor, 1 contract and a
// day stop of GuardDayStopShare x the cushion; under GuardStrongOnlyBelow $, only band entries GuardStrongOnlyStretch
// sigmas past the band (and the gap trade). research/zoo/strats.py (noise with nt=True, gap_go) is the same rule in
// Python and tests/test_ninjatrader_clean.py holds the two to trade-for-trade agreement.
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
            public double Bar0Range = double.NaN;  // the first regular-hours bar's high - low (the 09:30 bar)
            public bool NoOpen;  // docs 164: the session's first bar is not the 09:30 bar: no trades, not in the history
            public readonly Dictionary<int, double> Moves = new Dictionary<int, double>();
        }

        TimeZoneInfo newYork;
        readonly List<Day> hist = new List<Day>();
        Day today;
        double dayOpen, prevClose, sma, vwapNum, vwapDen, dayCumStart, hardRef, stop, entryPx, dayHigh, dayLow, avgRange;
        int pos, tradesToday, qty, gapPos;
        bool ready, beDone, early, exiting, gapWarned, noisePending, gapPending, gapToday, stopGone;
        DateTime stopGoneUtc = DateTime.MinValue;
        // docs/STRATEGY_SEARCH.md 167-168: an exit the broker refused is sent again; an entry's unfilled rest is cancelled
        int exitBar = -1;
        string exitFrom = "";
        bool exitRefused, entryPart;
        Order entryOrder;
        // news days (docs/STRATEGY_SEARCH.md, 15): the 08:30 bar's volume against the 08:20 and 08:25 bars' average
        DateTime preDate = DateTime.MinValue;
        double preVol, atVol, newsSpike = double.NaN;
        int preBars;
        bool newsSkip;
        bool fomcToday;  // docs 180: an FOMC statement day (14:00): no trades
        HashSet<DateTime> fomcSet;
        DateTime fomcLast = DateTime.MinValue;
        bool fomcListOld;  // docs 185: within 30 days of the list's last date (or an empty list): add next year's dates
        // the cushion guard (docs/STRATEGY_SEARCH.md, 38): the trailing floor from the high-water mark, today's cap and day stop
        double hwm = double.NaN, cushion = double.NaN, dayStopToday;
        bool guarded, strongOnly, hwmLive;  // strongOnly: under GuardStrongOnlyBelow $ above the floor, only strong breaks (and the gap trade)
        int capToday = 3;
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
                SigmaMinSessions = 10;  // docs 162 (14 = all of the 14, as before)
                HardStop = 200;
                BreakEvenAt = 0.4;
                BreakEvenPlus = 2;  // points past entry: the scratch exits close as small wins (docs/STRATEGY_SEARCH.md, 23)
                LadderAt = 1.5;     // docs 61
                LadderLock = 0.5;
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
                GapK = 0.6;  // docs 87 (0.5 before; 0.3 with a 40-point cap was tried and taken back, docs 29)
                GapCap = 30;
                GapMinBody = 0.03;  // docs 28
                GapMaxBar = 1.75;   // docs 61
                StretchAddAt = 1.5;  // docs 30
                NewsDays = true;
                NewsBigAt = 6;
                NewsSkipFrom = 2;
                NewsSkipTo = 3;
                FomcSkip = true;  // docs 180
                FomcDates = "2011-01-26,2011-03-15,2011-04-27,2011-06-22,2011-08-09,2011-09-21,2011-11-02,2011-12-13,2012-01-25,2012-03-13,2012-04-25,2012-06-20,2012-08-01,2012-09-13,2012-10-24,2012-12-12,2013-01-30,2013-03-20,2013-05-01,2013-06-19,2013-07-31,2013-09-18,2013-10-30,2013-12-18,2014-01-29,2014-03-19,2014-04-30,2014-06-18,2014-07-30,2014-09-17,2014-10-29,2014-12-17,2015-01-28,2015-03-18,2015-04-29,2015-06-17,2015-07-29,2015-09-17,2015-10-28,2015-12-16,2016-01-27,2016-03-16,2016-04-27,2016-06-15,2016-07-27,2016-09-21,2016-11-02,2016-12-14,2017-02-01,2017-03-15,2017-05-03,2017-06-14,2017-07-26,2017-09-20,2017-11-01,2017-12-13,2018-01-31,2018-03-21,2018-05-02,2018-06-13,2018-08-01,2018-09-26,2018-11-08,2018-12-19,2019-01-30,2019-03-20,2019-05-01,2019-06-19,2019-07-31,2019-09-18,2019-10-30,2019-12-11,2020-01-29,2020-04-29,2020-06-10,2020-07-29,2020-09-16,2020-11-05,2020-12-16,2021-01-27,2021-03-17,2021-04-28,2021-06-16,2021-07-28,2021-09-22,2021-11-03,2021-12-15,2022-01-26,2022-03-16,2022-05-04,2022-06-15,2022-07-27,2022-09-21,2022-11-02,2022-12-14,2023-02-01,2023-03-22,2023-05-03,2023-06-14,2023-07-26,2023-09-20,2023-11-01,2023-12-13,2024-01-31,2024-03-20,2024-05-01,2024-06-12,2024-07-31,2024-09-18,2024-11-07,2024-12-18,2025-01-29,2025-03-19,2025-05-07,2025-06-18,2025-07-30,2025-09-17,2025-10-29,2025-12-10,2026-01-28,2026-03-18,2026-04-29,2026-06-17,2026-07-29,2026-09-16,2026-10-28,2026-12-09,2027-01-27,2027-03-17,2027-04-28,2027-06-09,2027-07-28,2027-09-15,2027-10-27,2027-11-17";
                CushionGuard = 1500;
                GuardDayStopShare = 0.25;
                TrailingDrawdown = 2000;
                HighestBalance = 0;
                GuardStrongOnlyBelow = 1000;
                GuardStrongOnlyStretch = 1.5;
            }
            else if (State == State.Realtime && today != null)
            {
                // enabled mid-session: today's size and gap leg came from the replay of the loaded history, not from the
                // account; size them from the account's balance now
                double prof = Profit();
                qty = Contracts(prof);
                early = EarlyMaxTrades > 0 && prof < EarlyCushion;
                gapToday = GapLeg && (GapFrom <= 0 || prof >= GapFrom) && ready;
                ApplyGuard(prof);
                ApplyNews();
                Print("Clean band live: profit over the start balance $" + prof.ToString("F0", CultureInfo.InvariantCulture) + ", " + qty +
                      " MNQ a trade, gap trade " + (gapToday ? "on" : "off") + (ready ? "" : " - NOT READY (history)"));
            }
            else if (State == State.DataLoaded)
            {
                newYork = NewYork();
                fomcSet = new HashSet<DateTime>();
                foreach (string x in (FomcDates ?? "").Split(new[] { ',', ';', ' ' }, StringSplitOptions.RemoveEmptyEntries))
                {
                    DateTime f;
                    if (DateTime.TryParseExact(x.Trim(), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out f))
                    {
                        fomcSet.Add(f.Date);
                        if (f.Date > fomcLast) fomcLast = f.Date;
                    }
                    else
                        Print("Clean band: FOMC date '" + x + "' is not yyyy-MM-dd - ignored");
                }
                sessions = new SessionIterator(Bars);
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

        // the bar end (New York minutes) by which to be out: the 15:55 open, or 5 minutes before an earlier session end
        // from the trading-hours template (a half day's 13:15 close: out at the 13:10 open). As MnqMomentumC.cs FlatBy.
        SessionIterator sessions;
        DateTime flatDay = DateTime.MinValue;
        int flatCached = 955;

        int FlatBy(DateTime barEndPlatform)
        {
            DateTime endNy = ToNy(barEndPlatform);
            if (endNy.Date == flatDay) return flatCached;
            int flat = 955;
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
                // no session information: 15:55, and the next-bar rule in Bar() as the backstop
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

        const int MaxMissingWeekdays = 5;

        static int MissingWeekdays(DateTime from, DateTime to)  // weekdays in [from, to) less the 14 sessions held
        {
            int n = 0;
            for (DateTime d = from.Date; d < to.Date; d = d.AddDays(1))
                if (d.DayOfWeek != DayOfWeek.Saturday && d.DayOfWeek != DayOfWeek.Sunday) n++;
            return n - 14;
        }

        void NewDay(DateTime date, int firstMm)
        {
            if (today != null && today.Bars >= 76 && !today.NoOpen)
            {
                today.Range = dayHigh - dayLow;
                hist.Add(today);
            }  // only complete sessions count, as research/zoo's day sets
            if (hist.Count > 60) hist.RemoveAt(0);
            today = new Day();
            today.Date = date;
            // docs/STRATEGY_SEARCH.md 163-164: without the 09:30 bar (a feed drop at the open) the day's open, its bands
            // and moves would come from a later bar: no trades today and the day kept out of the history
            today.NoOpen = firstMm != 570;
            fomcToday = FomcSkip && fomcSet != null && fomcSet.Contains(date.Date);
            bool wasOld = fomcListOld;
            fomcListOld = FomcSkip && (fomcSet == null || fomcSet.Count == 0 || date.Date > fomcLast.AddDays(-30));
            if (fomcListOld && !wasOld)
                Print(Time[0] + "  Clean band: the FOMC dates end " + (fomcLast == DateTime.MinValue ? "(none listed)" : fomcLast.ToString("yyyy-MM-dd")) +
                      " - add next year's statement days to \"FOMC statement days\" (federalreserve.gov, docs 180)");
            if (fomcToday)
                Print(Time[0] + "  Clean band: an FOMC day (the 14:00 Fed statement) - no trades today (docs 180)");
            if (today.NoOpen)
                Print(Time[0] + "  Clean band: NO TRADING TODAY - the session's first bar is " + (firstMm / 60) + ":" +
                      (firstMm % 60).ToString("00") + ", not 09:30 (the 09:30 bar is missing: reload the chart's history)");
            today.Bar0Range = High[0] - Low[0];
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
            string off = "";
            foreach (int t in Checks)
            {
                // docs/STRATEGY_SEARCH.md 160-162: the mean over the last 14 sessions that have this time's move, if at
                // least SigmaMinSessions of them do (14 = all, as first shipped): one missing bar (a halt, a feed drop)
                // no longer turns the check off for 14 sessions.
                double sum = 0;
                int n = 0;
                for (int j = hist.Count - 14; j < hist.Count; j++)
                {
                    double m;
                    if (hist[j].Moves.TryGetValue(t, out m)) { sum += m; n++; }
                }
                sigma[t] = n >= SigmaMinSessions ? sum / n : double.NaN;
                if (double.IsNaN(sigma[t]))
                    off += (off.Length > 0 ? ", " : "") + (t / 60) + ":" + (t % 60).ToString("00");
            }
            if (off.Length > 0)
                Print(Time[0] + "  Clean band: check(s) " + off + " off today - fewer than " + SigmaMinSessions +
                      " of the last 14 sessions have that bar (reload the chart's history: Reload All Historical Data)");
            double prof = Profit();
            qty = Contracts(prof);
            ApplyGuard(prof);
            early = EarlyMaxTrades > 0 && prof < EarlyCushion;  // decided at the day's start
            gapToday = GapLeg && (GapFrom <= 0 || prof >= GapFrom);  // GapFrom 0: always; else once the account has that cushion
            newsSpike = preDate == date && preBars == 2 && preVol > 0 && !double.IsNaN(atVol) ? atVol / (preVol / 2) : double.NaN;
            if (NewsDays && preDate == date && double.IsNaN(newsSpike))  // docs 164: an ETH chart, but a news bar missing
                Print(Time[0] + "  Clean band: news rule n/a today - the 08:20 / 08:25 / 08:30 bars are incomplete " +
                      "(the day trades as a normal day; reload the chart's history)");
            ApplyNews();
        }

        // the cushion guard, at the day's start: the floor trails the highest end-of-day balance (HighestBalance, then the
        // balance at each day's start) by TrailingDrawdown and stops at StartBalance; with less than CushionGuard $ above it,
        // 1 contract (no strong-break or news contract) and a day stop of GuardDayStopShare x the cushion ($100 at least).
        // 2015-2025 NQ: accounts started $1,000-1,200 above the floor lose 1-5% of 6-month runs, not 7-16%
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
            double floor = Math.Min(hwm - TrailingDrawdown, StartBalance);
            cushion = bal - floor;
            guarded = CushionGuard > 0 && cushion < CushionGuard;
            strongOnly = CushionGuard > 0 && GuardStrongOnlyBelow > 0 && cushion < GuardStrongOnlyBelow;  // CushionGuard 0: all off
            capToday = guarded ? 1 : MaxContracts;
            qty = Math.Min(qty, capToday);
            double ds = DayStop > 0 ? DayStop : double.MaxValue;
            dayStopToday = guarded ? Math.Max(100, Math.Min(ds, GuardDayStopShare * cushion)) : DayStop;
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
                qty = Math.Min(qty + 1, capToday);
        }

        // docs 178: only a 5-minute MNQ chart; anything else (a 1-minute chart, gold, NQ at 10x the risk) trades nothing
        // and says so on the chart and in the Output window
        string WrongSetup()
        {
            if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 5)
                return "WRONG CHART: use a 5-minute MNQ chart (this one is " + BarsPeriod.Value + " " + BarsPeriod.BarsPeriodType + ") - no trades";
            string root = (Instrument.FullName ?? "").Trim().Split(' ')[0].ToUpperInvariant();
            if (root != "MNQ")
                return "WRONG INSTRUMENT: MnqCleanBand trades MNQ only (this chart is " + Instrument.FullName + ") - no trades";
            return null;
        }

        bool wrongSaid;

        protected override void OnBarUpdate()
        {
            string wrong = WrongSetup();
            if (wrong != null)
            {
                if (!wrongSaid) { Print("Clean band: " + wrong); wrongSaid = true; }
                if (State == State.Realtime || CurrentBar >= Bars.Count - 2)
                    Draw.TextFixed(this, "clean_dash", "MNQ Clean Band | " + wrong, TextPosition.TopRight);
                return;
            }
            Bar();
            CheckNoStop(true);
            if (State == State.Realtime || CurrentBar >= Bars.Count - 2)
                Dashboard();
        }

        // the chart's top-right corner: is it ready, how big, today's P/L
        void Dashboard()
        {
            string setup;
            if (hist.Count < Math.Max(21, TrendDays + 1))
                setup = "NOT READY: " + hist.Count + " complete sessions loaded, needs " + Math.Max(21, TrendDays + 1) +
                        " - set the chart's Days to load to 40 or more";
            else if (!ready)
                setup = "NO TRADING: the chart's history has a hole - reload the historical data";
            else if (today != null && today.NoOpen)
                setup = "NO TRADING TODAY: the 09:30 bar is missing - reload the historical data";
            else
                setup = "OK";
            string txt = "MNQ Clean Noise-Band | Setup: " + setup +
                         " | " + qty + " MNQ a trade, gap trade " + (gapToday ? "on" : "off") +
                         " | today $" + (CumProfit - dayCumStart).ToString("F0", CultureInfo.InvariantCulture) +
                         (dayStopToday > 0 && CumProfit - dayCumStart <= -dayStopToday ? " (day stop: done for today)" : "") +
                         (guarded ? " | CUSHION GUARD: $" + cushion.ToString("F0", CultureInfo.InvariantCulture) + " above the floor, 1 contract, day stop $" +
                                    dayStopToday.ToString("F0", CultureInfo.InvariantCulture) + (strongOnly ? ", strong breaks only" : "") : "") +
                         " | news " + (!NewsDays ? "off" : double.IsNaN(newsSpike) ? "n/a (needs an ETH chart)" :
                                       newsSkip ? newsSpike.ToString("F1", CultureInfo.InvariantCulture) + "x: no trades today" :
                                       newsSpike.ToString("F1", CultureInfo.InvariantCulture) + "x" + (newsSpike >= NewsBigAt ? " (+1 contract)" : "")) +
                         (fomcToday ? " | FOMC day (14:00 Fed statement): no trades today" : "") +
                         (fomcListOld ? " | ADD NEXT YEAR'S FOMC DATES (the list ends " + (fomcLast == DateTime.MinValue ? "empty" : fomcLast.ToString("yyyy-MM-dd")) + ")" : "") +
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
            bool inTrade = Position.MarketPosition != MarketPosition.Flat;
            RetryExit();  // docs 168: a refused exit, sent again (any time of day; the bar's bookkeeping still runs)
            if (entryPart && entryOrder != null)  // docs 168: a part-filled entry: cancel its unfilled rest (in or out)
            {
                Print(Time[0] + "  Clean band: cancelling the entry's unfilled rest (" + entryOrder.Name + ")");
                CancelOrder(entryOrder);
                entryPart = false;
            }
            if (mm < 570 || mm >= 960)
            {
                // a trade still open outside regular hours (a half day's 13:15 close came before the 15:55 exit, and the
                // session-close backstop did not fire): out now, never carried into the next session
                if (inTrade && !exiting && (pos != 0 || gapPos != 0))
                    Exit("Session end");
                return;
            }
            bool carried = false;
            if (today == null || t.Date != today.Date)
            {
                carried = inTrade && today != null;  // the same on a regular-hours chart: out on the new session's first bar
                NewDay(t.Date, mm);
            }
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
            if (carried && mp != 0 && !exiting)
            {
                Exit("Session end");
                return;
            }
            if (!ready)
                return;
            double tick = TickSize, pv = Instrument.MasterInstrument.PointValue;

            int flatAt = FlatBy(Time[0]);
            if (pos != 0 && end >= flatAt)  // out at the 15:55 open (a half day: 5 minutes before its early close)
            {
                Exit("Session end");
                return;
            }
            if (gapPos != 0 && (mm >= 590 || end >= flatAt))  // the gap trade: out at the 09:55 open
            {
                Exit("Gap exit");
                return;
            }
            if ((newsSkip || fomcToday) && mp == 0)  // a mild-news day or an FOMC day (docs 180): no new trades
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
            // the second step: once a bar closes LadderAt hard stops up, the stop to the entry + LadderLock hard stops
            // (docs/STRATEGY_SEARCH.md 61)
            if (pos != 0 && LadderAt > 0 && pos * (Close[0] - entryPx) >= LadderAt * HardStop / pv)
            {
                double lk = Instrument.MasterInstrument.RoundToTickSize(entryPx + pos * LadderLock * HardStop / pv);
                if (pos * (lk - stop) > 0)
                {
                    stop = lk;
                    SetStopLoss(pos > 0 ? "Long" : "Short", CalculationMode.Price, stop, false);
                }
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
            if (mp != 0 || end > LastEntry || end >= flatAt || tradesToday >= MaxTradesPerDay || !PlaceOrders || today.NoOpen)
                return;
            if (dayStopToday > 0 && CumProfit - dayCumStart <= -dayStopToday)
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
            // under GuardStrongOnlyBelow $ above the floor only a close GuardStrongOnlyStretch sigmas past the band enters
            // (docs/STRATEGY_SEARCH.md 50: shuffled years lost 19.7% / 14.7% to 10.2% / 6.5% from $800-1,000 above it)
            if (strongOnly && want * (Close[0] - (want > 0 ? up : dn)) < GuardStrongOnlyStretch * sg * (want > 0 ? Math.Max(dayOpen, prevClose) : Math.Min(dayOpen, prevClose)))
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
            int q = StretchAddAt > 0 && FixedContracts <= 0 && sg > 0 && stretch >= StretchAddAt ? Math.Min(qty + 1, capToday) : qty;
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
            // a wild open: no gap trade when the 09:30 bar's range is over GapMaxBar x its 14-session average (the stop
            // is then the 30-point cap inside a bar that size; docs/STRATEGY_SEARCH.md 61)
            if (GapMaxBar > 0)
            {
                double bs = 0;
                for (int j = hist.Count - 14; j < hist.Count; j++)
                    bs += hist[j].Bar0Range;
                if (High[0] - Low[0] > GapMaxBar * bs / 14)
                    return;
            }
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
            exitRefused = false;
            exitBar = CurrentBar;
            exitFrom = from;
            if (d > 0) ExitLong(why, from); else ExitShort(why, from);
            exiting = true;
            pos = 0;
            gapPos = 0;
        }

        // docs 168: an exit sent on an earlier bar that has not closed the position (the broker refused it) goes again
        bool RetryExit()
        {
            int mp = Position.MarketPosition == MarketPosition.Long ? 1 : Position.MarketPosition == MarketPosition.Short ? -1 : 0;
            if (!exiting || mp == 0 || (!exitRefused && CurrentBar <= exitBar))
                return false;
            Print(Time[0] + "  Clean band: the exit was not filled - sending it again (" + (mp > 0 ? "long" : "short") + ")");
            exitRefused = false;
            exitBar = CurrentBar;
            if (mp > 0) ExitLong("Exit retry", exitFrom); else ExitShort("Exit retry", exitFrom);
            return true;
        }

        // a position must never be without its stop: if the broker cancels or rejects it, out at market (live 2026-11-17).
        // The cancel of a stop whose target just filled can reach here before the position shows flat, so the position is
        // closed at this bar's close, or live on the first tick 2 seconds after the cancel, if it is still open then and
        // no stop has come back (V38's rule, MnqNoiseV38.cs CheckNoStop).
        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
                                              double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error,
                                              string comment)
        {
            if (order == null)
                return;
            string nm = order.Name;
            if (nm == "Long" || nm == "Short" || nm == "GapLong" || nm == "GapShort")  // an entry (docs 168)
            {
                if (orderState == OrderState.PartFilled) { entryOrder = order; entryPart = true; }
                else if (orderState == OrderState.Working || orderState == OrderState.Accepted) entryOrder = order;
                else if (orderState == OrderState.Filled || orderState == OrderState.Cancelled || orderState == OrderState.Rejected)
                {
                    if (entryOrder == null || entryOrder == order) { entryOrder = null; entryPart = false; }
                }
                return;
            }
            if (nm != "Stop loss" && nm != "Profit target")  // an exit at market (docs 168)
            {
                if (orderState == OrderState.Rejected && Position.MarketPosition != MarketPosition.Flat)
                {
                    exitRefused = true;
                    Print(time + "  Clean band: the exit (" + nm + ") was refused (" + comment + ") - it is sent again on the next bar");
                }
                return;
            }
            if (nm != "Stop loss")
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
        [Range(1, 14)]
        [Display(Name = "Sigma needs at least this many of the 14 sessions (14 = all, as before)", Order = 8, GroupName = "1. Entries")]
        public int SigmaMinSessions { get; set; }

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
        [Range(0, 10)]
        [Display(Name = "Second stop step once up this many hard stops (0 = off)", Order = 6, GroupName = "2. Risk")]
        public double LadderAt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10)]
        [Display(Name = "Second stop step: the stop this many hard stops past the entry", Order = 7, GroupName = "2. Risk")]
        public double LadderLock { get; set; }

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
        [Display(Name = "FOMC days (the 14:00 Fed statement): no trades", Order = 5, GroupName = "6. News")]
        public bool FomcSkip { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "FOMC statement days (yyyy-MM-dd, comma-separated; federalreserve.gov's calendar)", Order = 6, GroupName = "6. News")]
        public string FomcDates { get; set; }

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
        [Range(0, 10000)]
        [Display(Name = "Cushion guard: below this $ above the floor, 1 contract and a smaller day stop (0 = off)", Order = 1, GroupName = "7. Cushion guard")]
        public double CushionGuard { get; set; }

        [NinjaScriptProperty]
        [Range(0.05, 1)]
        [Display(Name = "Cushion guard: the day stop as this share of the cushion", Order = 2, GroupName = "7. Cushion guard")]
        public double GuardDayStopShare { get; set; }

        [NinjaScriptProperty]
        [Range(100, 100000)]
        [Display(Name = "The account's trailing drawdown $", Order = 3, GroupName = "7. Cushion guard")]
        public double TrailingDrawdown { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000000)]
        [Display(Name = "Highest end-of-day balance so far $ (from the prop firm's dashboard; 0 = the start balance)", Order = 4, GroupName = "7. Cushion guard")]
        public double HighestBalance { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Gap trade (09:35-09:55)", Order = 1, GroupName = "5. Gap trade")]
        public bool GapLeg { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000)]
        [Display(Name = "Cushion guard: below this $ above the floor, only strong breaks and the gap trade (0 = off)", Order = 5, GroupName = "7. Cushion guard")]
        public double GuardStrongOnlyBelow { get; set; }

        [NinjaScriptProperty]
        [Range(0, 20)]
        [Display(Name = "Cushion guard: a strong break is this many sigmas past the band", Order = 6, GroupName = "7. Cushion guard")]
        public double GuardStrongOnlyStretch { get; set; }

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
        [Range(0, 20)]
        [Display(Name = "Gap: no trade when the 09:30 bar's range is over this x its 14-session average (0 = off)", Order = 6, GroupName = "5. Gap trade")]
        public double GapMaxBar { get; set; }

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
