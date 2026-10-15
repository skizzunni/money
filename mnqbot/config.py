"""All tunable settings in one place.

Defaults are sized for a $25K prop-firm evaluation (Take Profit Trader style:
$1,500 end-of-day trailing drawdown, 30 micro max). Verify your firm's
current rules and change PropRules if they differ.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


@dataclass
class Instrument:
    symbol: str = "MNQ"
    tick_size: float = 0.25
    point_value: float = 2.0  # $ per 1.00 index point per contract (MNQ = $2, NQ = $20)


@dataclass
class StrategyConfig:
    # Which setups to trade (both can be on; at most one position at a time)
    use_sweep: bool = True  # liquidity sweep -> displacement -> fair value gap
    use_orb: bool = True  # opening range breakout, limit entry on the retest

    # Entry window, America/New_York, "HHMM" strings. Sweeps and setups outside it are ignored.
    window_start: str = "0935"
    window_end: str = "1130"
    flatten_at: str = "1550"  # force flat at or after this bar-open time

    # Liquidity levels to watch
    use_prev_day: bool = True  # previous RTH high/low
    use_overnight: bool = True  # overnight (18:00-09:30) high/low
    use_swings: bool = True  # most recent confirmed swing high/low of the trading day
    swing_len: int = 5  # bars left/right to confirm a swing

    sweep_min_ticks: int = 2  # how far price must trade through a level to count as a sweep
    max_bars_after_sweep: int = 12  # displacement must show up within this many bars

    atr_len: int = 14
    displacement_atr: float = 1.0  # displacement candle body >= this * ATR
    min_fvg_ticks: int = 4  # minimum fair value gap size

    entry_level: float = 0.5  # 0 = near edge of the gap, 0.5 = midpoint, 1 = far edge
    stop_buffer_ticks: int = 4  # beyond the sweep extreme
    reward_risk: float = 2.0
    min_stop_points: float = 8.0
    max_stop_points: float = 60.0
    order_expiry_bars: int = 6  # cancel unfilled limit after this many bars
    breakeven_at_r: float = 1.0  # move stop to entry once price reaches this many R (0 = off)

    # Opening range breakout
    or_minutes: int = 5  # opening range = RTH bars from 09:30 for this many minutes
    or_stop_frac: float = 0.5  # stop this share of the range behind the entry (0.5 = midpoint, 1 = far side)


@dataclass
class RiskConfig:
    risk_per_trade: float = 150.0  # max $ loss per trade, including costs
    max_contracts: int = 15  # hard cap regardless of sizing
    daily_max_loss: float = 300.0  # stop for the day at or below this realized loss
    daily_profit_lock: float = 600.0  # stop for the day at or above this realized profit
    max_trades_per_day: int = 3
    drawdown_buffer_frac: float = 0.25  # never risk more than this share of distance to the drawdown line
    no_trade_dates: list[str] = field(default_factory=list)  # e.g. FOMC/CPI days, "2026-10-29"
    blackout_windows: list[str] = field(default_factory=list)  # NY time, e.g. ["1355-1415"]


@dataclass
class CostModel:
    commission_per_side: float = 0.62  # $ per contract per side (exchange + clearing + commission)
    slippage_ticks: int = 1  # applied to stop and market fills
    limit_fill_through_ticks: int = 1  # limit fills only if price trades this far through it


@dataclass
class PropRules:
    start_balance: float = 25_000.0
    profit_target: float = 1_500.0
    max_drawdown: float = 1_500.0  # end-of-day trailing
    drawdown_lock: float | None = None  # trail stops rising at this balance (None = start_balance)
    consistency_max_day_frac: float = 0.5  # best day must be < this share of total profit (0 = off)
    min_trading_days: int = 5
    max_contracts: int = 30  # micros

    @property
    def lock_level(self) -> float:
        return self.start_balance if self.drawdown_lock is None else self.drawdown_lock


@dataclass
class BotConfig:
    instrument: Instrument = field(default_factory=Instrument)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    costs: CostModel = field(default_factory=CostModel)
    prop: PropRules = field(default_factory=PropRules)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "BotConfig":
        cfg = cls()
        for section in fields(cls):
            values = d.get(section.name, {})
            target = getattr(cfg, section.name)
            known = {f.name for f in fields(target)}
            unknown = set(values) - known
            if unknown:
                raise ValueError(f"unknown {section.name} settings: {sorted(unknown)}")
            for k, v in values.items():
                setattr(target, k, v)
        return cfg

    @classmethod
    def load(cls, path: str | Path) -> "BotConfig":
        return cls.from_dict(json.loads(Path(path).read_text()))
