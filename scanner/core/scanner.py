from __future__ import annotations

import logging
from collections.abc import Sequence

from scanner.core.models import ScanSummary, TradeCandidate

LOGGER = logging.getLogger(__name__)


class ScannerService:
    def __init__(
        self,
        tickers: Sequence[str],
        data_provider: object,
        indicator_service: object,
        filters: Sequence[object],
        output_writer: object,
        trade_builder: object | None = None,
    ) -> None:
        self._tickers = list(tickers)
        self._data_provider = data_provider
        self._indicator_service = indicator_service
        self._filters = list(filters)
        self._output_writer = output_writer
        self._trade_builder = trade_builder
        self._last_summary = ScanSummary()

    @property
    def last_summary(self) -> ScanSummary:
        return self._last_summary

    def run(self, limit: int | None = None) -> list[TradeCandidate]:
        selected_tickers = self._tickers[:limit] if limit is not None else self._tickers
        LOGGER.info('Starting scan for %d tickers.', len(selected_tickers))
        summary = ScanSummary(total_tickers=len(selected_tickers))
        for scan_filter in self._filters:
            summary.filter_failures[scan_filter.__class__.__name__] = 0

        candidates: list[TradeCandidate] = []
        total = len(selected_tickers)
        for index, ticker in enumerate(selected_tickers, start=1):
            LOGGER.info('[%d/%d] Processing %s', index, total, ticker)
            try:
                snapshot = self._data_provider.fetch_snapshot(ticker)
            except Exception as exc:
                summary.fetch_failures += 1
                LOGGER.exception('Fetch failed for %s: %s', ticker, exc)
                continue
            if snapshot is None:
                summary.fetch_failures += 1
                LOGGER.warning('Skipping %s because no snapshot was returned.', ticker)
                continue

            try:
                snapshot = self._indicator_service.enrich(snapshot)
            except Exception as exc:
                summary.enrichment_failures += 1
                LOGGER.exception('Indicator enrichment failed for %s: %s', ticker, exc)
                continue

            if self._trade_builder is not None:
                try:
                    snapshot = self._trade_builder.apply(snapshot)
                except Exception as exc:
                    summary.trade_failures += 1
                    LOGGER.exception('Trade construction failed for %s: %s', ticker, exc)
                    continue

            try:
                filter_results = [scan_filter.evaluate(snapshot) for scan_filter in self._filters]
            except Exception as exc:
                summary.enrichment_failures += 1
                LOGGER.exception('Filter evaluation failed for %s: %s', ticker, exc)
                continue

            failed_results = [result for result in filter_results if not result.passed]
            if failed_results:
                failed_names = []
                for result in failed_results:
                    summary.filter_failures[result.filter_name] = (
                        summary.filter_failures.get(result.filter_name, 0) + 1
                    )
                    failed_names.append(result.filter_name)
                LOGGER.info('%s rejected by filters: %s', ticker, ', '.join(failed_names))
                continue

            candidates.append(self._build_candidate(snapshot, filter_results))
            LOGGER.info('%s passed all active filters.', ticker)

        candidates.sort(key=lambda candidate: candidate.rank_score, reverse=True)
        summary.passed_tickers = len(candidates)
        self._last_summary = summary
        LOGGER.info(
            'Scan complete. total=%d passed=%d fetch_failures=%d enrichment_failures=%d trade_failures=%d',
            summary.total_tickers,
            summary.passed_tickers,
            summary.fetch_failures,
            summary.enrichment_failures,
            summary.trade_failures,
        )
        return candidates

    def _build_candidate(self, snapshot: object, filter_results: Sequence[object]) -> TradeCandidate:
        rationale = ' | '.join(result.rationale for result in filter_results if result.rationale)
        indicators = snapshot.indicators
        metadata = snapshot.metadata
        reward_risk = indicators.get('reward_risk')
        rank_score = float(sum(result.score for result in filter_results) + (reward_risk or 0.0))
        entry_lower = indicators.get('entry_lower')
        entry_upper = indicators.get('entry_upper')
        entry_zone = None
        if entry_lower is not None and entry_upper is not None:
            entry_zone = f'{entry_lower:.2f}-{entry_upper:.2f}'
        return TradeCandidate(
            ticker=snapshot.ticker,
            current_price=metadata.get('current_price'),
            entry_zone=entry_zone,
            price_target=indicators.get('price_target'),
            stop_loss=indicators.get('stop_loss'),
            reward_risk=reward_risk,
            setup_rationale=rationale,
            market_cap=snapshot.market_cap,
            avg_volume=indicators.get('avg_volume_20'),
            rank_score=rank_score,
        )
