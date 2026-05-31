from __future__ import annotations

from scanner.core.models import FilterResult, StockSnapshot
from scanner.filters.base import BaseFilter


class DailyUptrendFilter(BaseFilter):
    def evaluate(self, snapshot: StockSnapshot) -> FilterResult:
        indicators = snapshot.indicators
        close = indicators.get('close')
        sma_20 = indicators.get('sma_20')
        sma_50 = indicators.get('sma_50')
        recent_low_20 = indicators.get('recent_low_20')
        previous_low_20 = indicators.get('previous_low_20')
        recent_high_20 = indicators.get('recent_high_20')
        previous_high_20 = indicators.get('previous_high_20')

        required = (close, sma_20, sma_50, recent_low_20, previous_low_20, recent_high_20, previous_high_20)
        if any(value is None for value in required):
            return FilterResult('DailyUptrendFilter', False, 'Daily trend structure unavailable.')

        moving_average_trend = sma_20 > sma_50
        price_above_support = close >= sma_20
        higher_lows = recent_low_20 > previous_low_20
        higher_highs = recent_high_20 > previous_high_20
        passed = moving_average_trend and price_above_support and higher_lows and higher_highs
        if passed:
            rationale = (
                f'Uptrend confirmed with SMA20 {sma_20:.2f} above SMA50 {sma_50:.2f}, '
                f'higher lows, and higher highs.'
            )
        else:
            rationale = 'Daily uptrend is not confirmed by moving averages and swing structure.'
        return FilterResult('DailyUptrendFilter', passed, rationale, 1.0 if passed else 0.0)
