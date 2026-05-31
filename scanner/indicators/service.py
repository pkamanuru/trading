from __future__ import annotations

import logging
from typing import Any

from scanner.core.models import StockSnapshot

LOGGER = logging.getLogger(__name__)


class IndicatorService:
    def __init__(
        self,
        rsi_length: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        volume_window: int = 20,
        support_window: int = 20,
    ) -> None:
        self._rsi_length = rsi_length
        self._macd_fast = macd_fast
        self._macd_slow = macd_slow
        self._macd_signal = macd_signal
        self._volume_window = volume_window
        self._support_window = support_window

    def enrich(self, snapshot: StockSnapshot) -> StockSnapshot:
        history = self._coerce_history(snapshot.price_history)
        LOGGER.info('Enriching indicators for %s with %d price rows.', snapshot.ticker, len(history))
        close = history['Close'].astype(float)
        high = history['High'].astype(float)
        low = history['Low'].astype(float)
        volume = history['Volume'].astype(float)

        try:
            import pandas_ta as ta
        except ImportError as exc:
            raise RuntimeError(
                'pandas-ta is required to compute indicators. Install project dependencies first.'
            ) from exc

        rsi_series = ta.rsi(close, length=self._rsi_length)
        macd_frame = ta.macd(
            close,
            fast=self._macd_fast,
            slow=self._macd_slow,
            signal=self._macd_signal,
        )
        sma_20 = ta.sma(close, length=20)
        sma_50 = ta.sma(close, length=50)
        ema_21 = ta.ema(close, length=21)
        avg_volume_20 = volume.rolling(self._volume_window).mean()
        recent_low_20 = low.rolling(self._support_window).min()
        previous_low_20 = low.shift(self._support_window).rolling(self._support_window).min()
        recent_high_20 = high.rolling(self._support_window).max()
        previous_high_20 = high.shift(self._support_window).rolling(self._support_window).max()
        recent_volume_max_3 = volume.rolling(3).max()

        latest_macd = self._latest_value(macd_frame.iloc[:, 0])
        latest_macd_signal = self._latest_value(macd_frame.iloc[:, 1])
        latest_macd_hist = self._latest_value(macd_frame.iloc[:, 2])
        previous_macd_hist = self._latest_value(macd_frame.iloc[:, 2], offset=1)
        latest_avg_volume = self._latest_value(avg_volume_20)
        latest_recent_volume = self._latest_value(recent_volume_max_3)
        latest_close = self._latest_value(close)
        latest_sma_20 = self._latest_value(sma_20)
        latest_sma_50 = self._latest_value(sma_50)
        latest_ema_21 = self._latest_value(ema_21)
        latest_recent_low = self._latest_value(recent_low_20)

        support_anchor = self._derive_support_anchor(
            latest_close,
            latest_recent_low,
            latest_sma_20,
            latest_ema_21,
        )

        snapshot.indicators.update(
            {
                'close': latest_close,
                'volume': self._latest_value(volume),
                'rsi_14': self._latest_value(rsi_series),
                'macd': latest_macd,
                'macd_signal': latest_macd_signal,
                'macd_hist': latest_macd_hist,
                'prev_macd_hist': previous_macd_hist,
                'sma_20': latest_sma_20,
                'sma_50': latest_sma_50,
                'ema_21': latest_ema_21,
                'avg_volume_20': latest_avg_volume,
                'recent_volume_max_3': latest_recent_volume,
                'recent_volume_ratio_3': self._safe_ratio(latest_recent_volume, latest_avg_volume),
                'recent_low_20': latest_recent_low,
                'previous_low_20': self._latest_value(previous_low_20),
                'recent_high_20': self._latest_value(recent_high_20),
                'previous_high_20': self._latest_value(previous_high_20),
                'support_anchor': support_anchor,
                'support_distance_pct': self._support_distance_pct(latest_close, support_anchor),
            }
        )
        snapshot.metadata.setdefault('current_price', latest_close)
        LOGGER.info(
            'Indicators ready for %s. close=%s rsi=%s volume_ratio=%s support=%s',
            snapshot.ticker,
            snapshot.indicators.get('close'),
            snapshot.indicators.get('rsi_14'),
            snapshot.indicators.get('recent_volume_ratio_3'),
            snapshot.indicators.get('support_anchor'),
        )
        return snapshot

    def _coerce_history(self, history: Any) -> Any:
        if history is None:
            raise ValueError('Price history is required for indicator enrichment.')

        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError(
                'pandas is required to process price history. Install project dependencies first.'
            ) from exc

        if hasattr(history, 'columns'):
            frame = history.copy()
        else:
            frame = pd.DataFrame(history)

        if 'High' not in frame.columns:
            frame['High'] = frame['Close']
        if 'Low' not in frame.columns:
            frame['Low'] = frame['Close']

        required_columns = {'Close', 'High', 'Low', 'Volume'}
        missing_columns = required_columns.difference(frame.columns)
        if missing_columns:
            raise ValueError(f'Missing required price history columns: {sorted(missing_columns)}')
        if frame.empty:
            raise ValueError('Price history is empty.')
        return frame

    def _latest_value(self, series: Any, offset: int = 0) -> float | None:
        if series is None:
            return None
        cleaned = series.dropna()
        if cleaned.empty or len(cleaned) <= offset:
            return None
        return float(cleaned.iloc[-1 - offset])

    def _safe_ratio(self, numerator: float | None, denominator: float | None) -> float | None:
        if numerator is None or denominator in (None, 0):
            return None
        return float(numerator / denominator)

    def _derive_support_anchor(
        self,
        close: float | None,
        recent_low: float | None,
        sma_20: float | None,
        ema_21: float | None,
    ) -> float | None:
        if close is None:
            return None
        support_levels = [
            level for level in (recent_low, sma_20, ema_21) if level is not None and level <= close
        ]
        if not support_levels:
            return None
        return max(support_levels)

    def _support_distance_pct(
        self, close: float | None, support_anchor: float | None
    ) -> float | None:
        if close is None or support_anchor in (None, 0):
            return None
        return float((close - support_anchor) / support_anchor)
