from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StockSnapshot:
    ticker: str
    market_cap: int | None = None
    price_history: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    indicators: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FilterResult:
    filter_name: str
    passed: bool
    rationale: str = ""
    score: float = 0.0


@dataclass(slots=True)
class TradeCandidate:
    ticker: str
    current_price: float | None = None
    entry_zone: str | None = None
    price_target: float | None = None
    stop_loss: float | None = None
    reward_risk: float | None = None
    setup_rationale: str = ""
    market_cap: int | None = None
    avg_volume: float | None = None
    rank_score: float = 0.0
    earnings_check: str = "SKIPPED"
    catalyst_check: str = "SKIPPED"


@dataclass(slots=True)
class ScanSummary:
    total_tickers: int = 0
    fetch_failures: int = 0
    enrichment_failures: int = 0
    trade_failures: int = 0
    filter_failures: dict[str, int] = field(default_factory=dict)
    passed_tickers: int = 0
