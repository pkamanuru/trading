from __future__ import annotations

import logging

from scanner.core.models import StockSnapshot

LOGGER = logging.getLogger(__name__)


class TradeBuilder:
    def __init__(self, stop_buffer_pct: float = 0.04, minimum_upside_pct: float = 0.10) -> None:
        self._stop_buffer_pct = stop_buffer_pct
        self._minimum_upside_pct = minimum_upside_pct

    def apply(self, snapshot: StockSnapshot) -> StockSnapshot:
        support_anchor = snapshot.indicators.get('support_anchor')
        current_price = snapshot.metadata.get('current_price') or snapshot.indicators.get('close')
        if support_anchor is None or current_price is None:
            raise ValueError('Support anchor and current price are required for trade construction.')

        entry_lower = float(support_anchor)
        entry_upper = float(max(current_price, support_anchor))
        entry_price = float((entry_lower + entry_upper) / 2.0)
        stop_loss = float(support_anchor * (1.0 - self._stop_buffer_pct))
        risk_per_share = float(entry_price - stop_loss)
        if risk_per_share <= 0:
            raise ValueError('Trade risk must be positive.')

        minimum_target = float(entry_price * (1.0 + self._minimum_upside_pct))
        reward_risk_target = float(entry_price + (2.0 * risk_per_share))
        price_target = float(max(minimum_target, reward_risk_target))
        reward_risk = float((price_target - entry_price) / risk_per_share)

        snapshot.indicators.update(
            {
                'entry_lower': entry_lower,
                'entry_upper': entry_upper,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'risk_per_share': risk_per_share,
                'price_target': price_target,
                'reward_risk': reward_risk,
            }
        )
        LOGGER.info(
            'Trade levels for %s. entry=%0.2f-%0.2f stop=%0.2f target=%0.2f rr=%0.2f',
            snapshot.ticker,
            entry_lower,
            entry_upper,
            stop_loss,
            price_target,
            reward_risk,
        )
        return snapshot
