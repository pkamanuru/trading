from __future__ import annotations

from scanner.core.models import FilterResult, StockSnapshot
from scanner.filters.base import BaseFilter


class MACDFilter(BaseFilter):
    def evaluate(self, snapshot: StockSnapshot) -> FilterResult:
        macd = snapshot.indicators.get('macd')
        signal = snapshot.indicators.get('macd_signal')
        hist = snapshot.indicators.get('macd_hist')
        prev_hist = snapshot.indicators.get('prev_macd_hist')
        if macd is None or signal is None or hist is None:
            return FilterResult('MACDFilter', False, 'MACD unavailable.')

        bullish_cross = macd > signal
        momentum_improving = prev_hist is not None and hist > prev_hist
        passed = bullish_cross or momentum_improving
        if passed:
            if bullish_cross:
                rationale = f'MACD {macd:.3f} is above signal {signal:.3f}.'
            else:
                rationale = f'MACD histogram improved from {prev_hist:.3f} to {hist:.3f}.'
        else:
            rationale = 'MACD is below signal and momentum is not improving.'
        return FilterResult('MACDFilter', passed, rationale, 1.0 if passed else 0.0)
