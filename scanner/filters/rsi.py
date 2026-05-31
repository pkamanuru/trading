from __future__ import annotations

from scanner.core.models import FilterResult, StockSnapshot
from scanner.filters.base import BaseFilter


class RSIFilter(BaseFilter):
    def __init__(self, min_rsi: float = 40.0, max_rsi: float = 60.0) -> None:
        self._min_rsi = min_rsi
        self._max_rsi = max_rsi

    def evaluate(self, snapshot: StockSnapshot) -> FilterResult:
        rsi = snapshot.indicators.get('rsi_14')
        if rsi is None:
            return FilterResult('RSIFilter', False, 'RSI unavailable.')
        passed = self._min_rsi <= rsi <= self._max_rsi
        rationale = (
            f'RSI {rsi:.2f} is in the reset zone.'
            if passed
            else f'RSI {rsi:.2f} is outside the 40-60 range.'
        )
        return FilterResult('RSIFilter', passed, rationale, 1.0 if passed else 0.0)
