from __future__ import annotations

from scanner.core.models import FilterResult, StockSnapshot
from scanner.filters.base import BaseFilter


class RewardRiskFilter(BaseFilter):
    def __init__(self, minimum_ratio: float = 2.0) -> None:
        self._minimum_ratio = minimum_ratio

    def evaluate(self, snapshot: StockSnapshot) -> FilterResult:
        reward_risk = snapshot.indicators.get('reward_risk')
        if reward_risk is None:
            return FilterResult('RewardRiskFilter', False, 'Reward-to-risk ratio unavailable.')
        passed = reward_risk >= self._minimum_ratio
        rationale = (
            f'Reward-to-risk ratio {reward_risk:.2f} meets the minimum threshold.'
            if passed
            else f'Reward-to-risk ratio {reward_risk:.2f} is below the required 2.0 threshold.'
        )
        return FilterResult('RewardRiskFilter', passed, rationale, reward_risk if passed else 0.0)
