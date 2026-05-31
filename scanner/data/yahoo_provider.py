from __future__ import annotations

import logging
from typing import Any

from scanner.core.models import StockSnapshot

LOGGER = logging.getLogger(__name__)


class YahooFinanceProvider:
    def __init__(
        self,
        history_period: str = '6mo',
        interval: str = '1d',
        ticker_factory: Any | None = None,
    ) -> None:
        self._history_period = history_period
        self._interval = interval
        self._ticker_factory = ticker_factory

    def normalize_symbol(self, ticker: str) -> str:
        return ticker.strip().upper().replace('.', '-')

    def fetch_snapshot(self, ticker: str) -> StockSnapshot | None:
        normalized_ticker = self.normalize_symbol(ticker)
        LOGGER.info('Fetching Yahoo data for %s.', normalized_ticker)
        ticker_client = self._build_ticker_client(normalized_ticker)
        history = ticker_client.history(
            period=self._history_period,
            interval=self._interval,
            auto_adjust=False,
        )
        if self._is_empty_history(history):
            LOGGER.warning('No Yahoo price history returned for %s.', normalized_ticker)
            return None

        metadata = self._build_metadata(ticker_client, normalized_ticker)
        row_count = len(history)
        LOGGER.info(
            'Fetched %d rows for %s. current_price=%s market_cap=%s',
            row_count,
            normalized_ticker,
            metadata.get('current_price'),
            metadata.get('market_cap'),
        )
        return StockSnapshot(
            ticker=normalized_ticker,
            market_cap=metadata.get('market_cap'),
            price_history=history,
            metadata=metadata,
        )

    def _build_ticker_client(self, ticker: str) -> Any:
        if self._ticker_factory is not None:
            return self._ticker_factory(ticker)

        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError(
                'yfinance is required to fetch market data. Install it before running Stage 2.'
            ) from exc

        return yf.Ticker(ticker)

    def _build_metadata(self, ticker_client: Any, ticker: str) -> dict[str, Any]:
        info = self._safe_get_info(ticker_client)
        fast_info = self._safe_get_fast_info(ticker_client)

        market_cap = info.get('marketCap')
        if market_cap is None:
            market_cap = fast_info.get('marketCap')

        current_price = info.get('currentPrice')
        if current_price is None:
            current_price = fast_info.get('lastPrice')

        return {
            'symbol': ticker,
            'short_name': info.get('shortName'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'currency': info.get('currency'),
            'exchange': info.get('exchange'),
            'market_cap': market_cap,
            'current_price': current_price,
        }

    def _safe_get_info(self, ticker_client: Any) -> dict[str, Any]:
        info = getattr(ticker_client, 'info', None)
        if isinstance(info, dict):
            return info
        return {}

    def _safe_get_fast_info(self, ticker_client: Any) -> dict[str, Any]:
        fast_info = getattr(ticker_client, 'fast_info', None)
        if fast_info is None:
            return {}
        try:
            return dict(fast_info)
        except (TypeError, ValueError):
            return {}

    def _is_empty_history(self, history: Any) -> bool:
        if history is None:
            return True
        empty = getattr(history, 'empty', None)
        if empty is not None:
            return bool(empty)
        try:
            return len(history) == 0
        except TypeError:
            return False
