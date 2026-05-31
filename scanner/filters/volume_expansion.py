from __future__ import annotations

from scanner.core.models import FilterResult, StockSnapshot
from scanner.filters.base import BaseFilter


class VolumeExpansionFilter(BaseFilter):
    def __init__(self, min_ratio: float = 1.30) -> None:
        self._min_ratio = min_ratio

    def evaluate(self, snapshot: StockSnapshot) -> FilterResult:
        ratio = snapshot.indicators.get('recent_volume_ratio_3')
        if ratio is None:
            return FilterResult('VolumeExpansionFilter', False, 'Volume expansion data unavailable.')
        passed = ratio >= self._min_ratio
        rationale = (
            f'Recent volume expanded to {ratio:.2f}x average volume.'
            if passed
            else f'Recent volume expansion of {ratio:.2f}x is below the required 1.30x threshold.'
        )
        return FilterResult('VolumeExpansionFilter', passed, rationale, 1.0 if passed else 0.0)
