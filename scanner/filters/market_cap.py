from __future__ import annotations

from scanner.core.models import FilterResult, StockSnapshot
from scanner.filters.base import BaseFilter


class MarketCapFilter(BaseFilter):
    def __init__(self, min_cap: int = 500_000_000, max_cap: int = 20_000_000_000) -> None:
        self._min_cap = min_cap
        self._max_cap = max_cap

    def evaluate(self, snapshot: StockSnapshot) -> FilterResult:
        market_cap = snapshot.market_cap
        if market_cap is None:
            return FilterResult('MarketCapFilter', False, 'Market cap unavailable.')
        passed = self._min_cap <= market_cap <= self._max_cap
        rationale = (
            f'Market cap {market_cap} is within range.'
            if passed
            else f'Market cap {market_cap} is outside the required $500M-$20B range.'
        )
        return FilterResult('MarketCapFilter', passed, rationale, 1.0 if passed else 0.0)
