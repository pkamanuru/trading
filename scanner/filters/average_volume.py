from __future__ import annotations

from scanner.core.models import FilterResult, StockSnapshot
from scanner.filters.base import BaseFilter


class AverageVolumeFilter(BaseFilter):
    def __init__(self, min_average_volume: float = 500_000) -> None:
        self._min_average_volume = min_average_volume

    def evaluate(self, snapshot: StockSnapshot) -> FilterResult:
        avg_volume = snapshot.indicators.get('avg_volume_20')
        if avg_volume is None:
            return FilterResult('AverageVolumeFilter', False, 'Average volume unavailable.')
        passed = avg_volume > self._min_average_volume
        rationale = (
            f'Average volume {avg_volume:.0f} exceeds threshold.'
            if passed
            else f'Average volume {avg_volume:.0f} is below the 500K minimum.'
        )
        return FilterResult('AverageVolumeFilter', passed, rationale, 1.0 if passed else 0.0)
