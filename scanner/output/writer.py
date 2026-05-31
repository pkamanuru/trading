from __future__ import annotations

import csv
import logging
from collections.abc import Sequence
from pathlib import Path

from scanner.core.models import TradeCandidate

LOGGER = logging.getLogger(__name__)


class OutputWriter:
    def write(self, candidates: Sequence[TradeCandidate], output_path: str) -> None:
        fieldnames = [
            'ticker',
            'current_price',
            'entry_zone',
            'price_target',
            'stop_loss',
            'reward_risk',
            'setup_rationale',
            'market_cap',
            'avg_volume',
            'rank_score',
            'earnings_check',
            'catalyst_check',
        ]
        path = Path(output_path)
        LOGGER.info('Writing %d candidates to %s.', len(candidates), path)
        with path.open('w', newline='', encoding='ascii') as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for candidate in candidates:
                writer.writerow(
                    {
                        'ticker': candidate.ticker,
                        'current_price': candidate.current_price,
                        'entry_zone': candidate.entry_zone,
                        'price_target': candidate.price_target,
                        'stop_loss': candidate.stop_loss,
                        'reward_risk': candidate.reward_risk,
                        'setup_rationale': candidate.setup_rationale,
                        'market_cap': candidate.market_cap,
                        'avg_volume': candidate.avg_volume,
                        'rank_score': candidate.rank_score,
                        'earnings_check': candidate.earnings_check,
                        'catalyst_check': candidate.catalyst_check,
                    }
                )

    def format_console(self, candidates: Sequence[TradeCandidate], limit: int = 10) -> list[str]:
        lines: list[str] = []
        for candidate in candidates[:limit]:
            lines.append(
                f"{candidate.ticker:>5} | price={self._fmt(candidate.current_price)} | "
                f"entry={candidate.entry_zone or 'n/a'} | target={self._fmt(candidate.price_target)} | "
                f"stop={self._fmt(candidate.stop_loss)} | rr={self._fmt(candidate.reward_risk)} | "
                f"score={self._fmt(candidate.rank_score)}"
            )
        return lines

    def _fmt(self, value: float | None) -> str:
        if value is None:
            return 'n/a'
        return f'{value:.2f}'
