from __future__ import annotations

from scanner.core.models import FilterResult, StockSnapshot
from scanner.filters.base import BaseFilter


class SupportPullbackFilter(BaseFilter):
    def __init__(self, max_distance_pct: float = 0.05) -> None:
        self._max_distance_pct = max_distance_pct

    def evaluate(self, snapshot: StockSnapshot) -> FilterResult:
        support_anchor = snapshot.indicators.get('support_anchor')
        distance_pct = snapshot.indicators.get('support_distance_pct')
        close = snapshot.indicators.get('close')
        if support_anchor is None or distance_pct is None or close is None:
            return FilterResult('SupportPullbackFilter', False, 'Support pullback data unavailable.')

        passed = 0.0 <= distance_pct <= self._max_distance_pct
        if passed:
            rationale = (
                f'Price {close:.2f} is {distance_pct * 100:.2f}% above support anchor {support_anchor:.2f}.'
            )
        else:
            rationale = (
                f'Price {close:.2f} is not trading in a valid pullback zone versus support {support_anchor:.2f}.'
            )
        return FilterResult('SupportPullbackFilter', passed, rationale, 1.0 if passed else 0.0)
