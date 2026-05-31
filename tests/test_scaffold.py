import csv
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scanner.core.models import FilterResult, StockSnapshot, TradeCandidate
from scanner.core.scanner import ScannerService
from scanner.core.trade_builder import TradeBuilder
from scanner.data.ticker_source import load_sp500_tickers
from scanner.data.yahoo_provider import YahooFinanceProvider
from scanner.filters import (
    AverageVolumeFilter,
    DailyUptrendFilter,
    MACDFilter,
    MarketCapFilter,
    RewardRiskFilter,
    RSIFilter,
    SupportPullbackFilter,
    VolumeExpansionFilter,
)
from scanner.indicators.service import IndicatorService
from scanner.output.writer import OutputWriter


class FakeHistory:
    def __init__(self, rows: list[dict[str, float]]) -> None:
        self.rows = rows
        self.empty = len(rows) == 0

    def __len__(self) -> int:
        return len(self.rows)


class FakeTicker:
    def __init__(
        self,
        symbol: str,
        history_rows: list[dict[str, float]],
        info: dict[str, object] | None = None,
        fast_info: dict[str, object] | None = None,
    ) -> None:
        self.symbol = symbol
        self.info = info or {}
        self.fast_info = fast_info or {}
        self._history_rows = history_rows
        self.history_calls: list[dict[str, object]] = []

    def history(self, **kwargs: object) -> FakeHistory:
        self.history_calls.append(kwargs)
        return FakeHistory(self._history_rows)


class StubProvider:
    def __init__(self, snapshots: dict[str, StockSnapshot | None]) -> None:
        self._snapshots = snapshots

    def fetch_snapshot(self, ticker: str) -> StockSnapshot | None:
        return self._snapshots.get(ticker)


class PassThroughOutputWriter(OutputWriter):
    def write(self, candidates, output_path: str) -> None:
        del candidates
        del output_path


class ScaffoldTests(unittest.TestCase):
    def test_ticker_loader_returns_values(self) -> None:
        tickers = load_sp500_tickers()
        self.assertTrue(tickers)
        self.assertIn('AAPL', tickers)

    def test_domain_models_instantiate(self) -> None:
        snapshot = StockSnapshot(ticker='AAPL')
        result = FilterResult(filter_name='ExampleFilter', passed=True)
        candidate = TradeCandidate(ticker='AAPL')

        self.assertEqual(snapshot.ticker, 'AAPL')
        self.assertTrue(result.passed)
        self.assertEqual(candidate.earnings_check, 'SKIPPED')

    def test_scanner_service_scaffold_runs(self) -> None:
        scanner = ScannerService(
            tickers=['AAPL', 'MSFT'],
            data_provider=StubProvider({'AAPL': None, 'MSFT': None}),
            indicator_service=IndicatorService(),
            filters=[],
            output_writer=PassThroughOutputWriter(),
        )

        self.assertEqual(scanner.run(limit=1), [])
        self.assertEqual(scanner.last_summary.total_tickers, 1)

    def test_yahoo_provider_normalizes_symbols(self) -> None:
        provider = YahooFinanceProvider(ticker_factory=lambda symbol: FakeTicker(symbol, []))
        self.assertEqual(provider.normalize_symbol(' brk.b '), 'BRK-B')

    def test_yahoo_provider_maps_snapshot(self) -> None:
        created: list[FakeTicker] = []

        def factory(symbol: str) -> FakeTicker:
            ticker = FakeTicker(
                symbol=symbol,
                history_rows=[{'Close': 100.0}, {'High': 101.0, 'Low': 99.0, 'Volume': 800000.0}],
                info={
                    'shortName': 'Apple Inc.',
                    'sector': 'Technology',
                    'industry': 'Consumer Electronics',
                    'currency': 'USD',
                    'exchange': 'NMS',
                    'marketCap': 2500000000,
                    'currentPrice': 101.5,
                },
            )
            created.append(ticker)
            return ticker

        provider = YahooFinanceProvider(ticker_factory=factory)
        snapshot = provider.fetch_snapshot('aapl')

        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.ticker, 'AAPL')
        self.assertEqual(snapshot.market_cap, 2500000000)
        self.assertEqual(snapshot.metadata['current_price'], 101.5)
        self.assertEqual(snapshot.metadata['short_name'], 'Apple Inc.')
        self.assertEqual(len(snapshot.price_history), 2)
        self.assertEqual(
            created[0].history_calls[0],
            {'period': '6mo', 'interval': '1d', 'auto_adjust': False},
        )

    def test_yahoo_provider_returns_none_for_empty_history(self) -> None:
        provider = YahooFinanceProvider(ticker_factory=lambda symbol: FakeTicker(symbol, []))
        snapshot = provider.fetch_snapshot('MSFT')
        self.assertIsNone(snapshot)

    def test_yahoo_provider_uses_fast_info_fallbacks(self) -> None:
        provider = YahooFinanceProvider(
            ticker_factory=lambda symbol: FakeTicker(
                symbol,
                history_rows=[{'Close': 50.0, 'High': 51.0, 'Low': 49.0, 'Volume': 900000.0}],
                info={},
                fast_info={'marketCap': 123456789, 'lastPrice': 50.0},
            )
        )

        snapshot = provider.fetch_snapshot('amd')

        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.market_cap, 123456789)
        self.assertEqual(snapshot.metadata['current_price'], 50.0)

    def test_indicator_service_enriches_snapshot(self) -> None:
        close_values = [100.0] * 45 + [99.0, 98.5, 98.0, 98.2, 98.7, 99.3, 100.0, 101.2, 102.5, 104.0]
        volume_values = [600_000.0] * 52 + [650_000.0, 900_000.0, 1_200_000.0]
        high_values = [value + 1.0 for value in close_values]
        low_values = [value - 1.0 for value in close_values]
        history = pd.DataFrame(
            {'Close': close_values, 'High': high_values, 'Low': low_values, 'Volume': volume_values}
        )
        snapshot = StockSnapshot(
            ticker='AAPL',
            market_cap=1_500_000_000,
            price_history=history,
            metadata={},
        )

        enriched = IndicatorService().enrich(snapshot)

        self.assertIn('rsi_14', enriched.indicators)
        self.assertIn('macd', enriched.indicators)
        self.assertIn('avg_volume_20', enriched.indicators)
        self.assertIn('recent_volume_ratio_3', enriched.indicators)
        self.assertIn('support_anchor', enriched.indicators)
        self.assertIn('recent_high_20', enriched.indicators)
        self.assertEqual(enriched.metadata['current_price'], enriched.indicators['close'])

    def test_stage_4_filters_pass_on_valid_snapshot(self) -> None:
        snapshot = StockSnapshot(
            ticker='AAPL',
            market_cap=1_500_000_000,
            indicators={
                'avg_volume_20': 700_000.0,
                'rsi_14': 52.0,
                'macd': 1.4,
                'macd_signal': 1.2,
                'macd_hist': 0.2,
                'prev_macd_hist': 0.1,
                'recent_volume_ratio_3': 1.6,
            },
        )
        filters = [
            MarketCapFilter(),
            AverageVolumeFilter(),
            RSIFilter(),
            MACDFilter(),
            VolumeExpansionFilter(),
        ]

        results = [scan_filter.evaluate(snapshot) for scan_filter in filters]

        self.assertTrue(all(result.passed for result in results))

    def test_stage_4_filters_fail_when_thresholds_miss(self) -> None:
        snapshot = StockSnapshot(
            ticker='AAPL',
            market_cap=100_000_000,
            indicators={
                'avg_volume_20': 200_000.0,
                'rsi_14': 72.0,
                'macd': -0.2,
                'macd_signal': 0.1,
                'macd_hist': -0.3,
                'prev_macd_hist': -0.2,
                'recent_volume_ratio_3': 1.1,
            },
        )
        filters = [
            MarketCapFilter(),
            AverageVolumeFilter(),
            RSIFilter(),
            MACDFilter(),
            VolumeExpansionFilter(),
        ]

        results = [scan_filter.evaluate(snapshot) for scan_filter in filters]

        self.assertFalse(any(result.passed for result in results))

    def test_stage_5_filters_pass_on_valid_structure(self) -> None:
        snapshot = StockSnapshot(
            ticker='AAPL',
            indicators={
                'close': 104.0,
                'sma_20': 102.5,
                'sma_50': 98.0,
                'recent_low_20': 98.0,
                'previous_low_20': 94.0,
                'recent_high_20': 106.0,
                'previous_high_20': 101.0,
                'support_anchor': 102.5,
                'support_distance_pct': 0.0146,
            },
        )
        filters = [DailyUptrendFilter(), SupportPullbackFilter()]

        results = [scan_filter.evaluate(snapshot) for scan_filter in filters]

        self.assertTrue(all(result.passed for result in results))

    def test_stage_5_filters_fail_on_broken_structure(self) -> None:
        snapshot = StockSnapshot(
            ticker='AAPL',
            indicators={
                'close': 104.0,
                'sma_20': 100.0,
                'sma_50': 101.0,
                'recent_low_20': 92.0,
                'previous_low_20': 94.0,
                'recent_high_20': 100.0,
                'previous_high_20': 101.0,
                'support_anchor': 95.0,
                'support_distance_pct': 0.0947,
            },
        )
        filters = [DailyUptrendFilter(), SupportPullbackFilter()]

        results = [scan_filter.evaluate(snapshot) for scan_filter in filters]

        self.assertFalse(any(result.passed for result in results))

    def test_trade_builder_populates_trade_fields(self) -> None:
        snapshot = StockSnapshot(
            ticker='AAPL',
            metadata={'current_price': 101.5},
            indicators={'support_anchor': 100.8},
        )
        TradeBuilder().apply(snapshot)
        self.assertEqual(snapshot.indicators['entry_lower'], 100.8)
        self.assertGreater(snapshot.indicators['entry_upper'], snapshot.indicators['entry_lower'])
        self.assertGreater(snapshot.indicators['price_target'], snapshot.indicators['entry_price'])
        self.assertGreaterEqual(snapshot.indicators['reward_risk'], 2.0)

    def test_reward_risk_filter_enforces_threshold(self) -> None:
        passed_snapshot = StockSnapshot(ticker='AAPL', indicators={'reward_risk': 2.1})
        failed_snapshot = StockSnapshot(ticker='AAPL', indicators={'reward_risk': 1.7})
        self.assertTrue(RewardRiskFilter().evaluate(passed_snapshot).passed)
        self.assertFalse(RewardRiskFilter().evaluate(failed_snapshot).passed)

    def test_output_writer_writes_csv(self) -> None:
        candidate = TradeCandidate(
            ticker='AAPL',
            current_price=101.5,
            entry_zone='100.80-101.50',
            price_target=111.65,
            stop_loss=96.77,
            reward_risk=2.15,
            setup_rationale='test rationale',
            market_cap=1_500_000_000,
            avg_volume=700_000.0,
            rank_score=9.15,
        )
        writer = OutputWriter()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'candidates.csv'
            writer.write([candidate], str(output_path))
            with output_path.open('r', encoding='ascii') as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['ticker'], 'AAPL')
        self.assertEqual(rows[0]['entry_zone'], '100.80-101.50')

    def test_scanner_service_returns_ranked_candidate_for_passing_snapshot(self) -> None:
        snapshot = StockSnapshot(
            ticker='AAPL',
            market_cap=1_500_000_000,
            price_history=pd.DataFrame({'Close': [1.0], 'Volume': [1_000_000.0]}),
            metadata={'current_price': 101.5},
            indicators={
                'avg_volume_20': 700_000.0,
                'rsi_14': 52.0,
                'macd': 1.4,
                'macd_signal': 1.2,
                'macd_hist': 0.2,
                'prev_macd_hist': 0.1,
                'recent_volume_ratio_3': 1.6,
                'close': 101.5,
                'sma_20': 100.8,
                'sma_50': 97.2,
                'recent_low_20': 98.4,
                'previous_low_20': 95.8,
                'recent_high_20': 103.1,
                'previous_high_20': 100.2,
                'support_anchor': 100.8,
                'support_distance_pct': 0.0069,
            },
        )

        class StubIndicatorService:
            def enrich(self, source_snapshot: StockSnapshot) -> StockSnapshot:
                return source_snapshot

        scanner = ScannerService(
            tickers=['AAPL'],
            data_provider=StubProvider({'AAPL': snapshot}),
            indicator_service=StubIndicatorService(),
            filters=[
                MarketCapFilter(),
                AverageVolumeFilter(),
                RSIFilter(),
                MACDFilter(),
                VolumeExpansionFilter(),
                DailyUptrendFilter(),
                SupportPullbackFilter(),
                RewardRiskFilter(),
            ],
            output_writer=PassThroughOutputWriter(),
            trade_builder=TradeBuilder(),
        )

        candidates = scanner.run()

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].ticker, 'AAPL')
        self.assertEqual(candidates[0].current_price, 101.5)
        self.assertIsNotNone(candidates[0].entry_zone)
        self.assertGreater(candidates[0].reward_risk, 0.0)
        self.assertGreater(candidates[0].rank_score, 0.0)
        self.assertEqual(scanner.last_summary.passed_tickers, 1)
        self.assertEqual(scanner.last_summary.filter_failures['AverageVolumeFilter'], 0)

    def test_scanner_service_tracks_filter_failures(self) -> None:
        failing_snapshot = StockSnapshot(
            ticker='MSFT',
            metadata={'current_price': 100.0},
            indicators={
                'avg_volume_20': 100000.0,
                'rsi_14': 70.0,
                'macd': -1.0,
                'macd_signal': 0.5,
                'macd_hist': -1.5,
                'prev_macd_hist': -1.0,
                'recent_volume_ratio_3': 1.0,
                'close': 100.0,
                'sma_20': 99.0,
                'sma_50': 101.0,
                'recent_low_20': 90.0,
                'previous_low_20': 95.0,
                'recent_high_20': 100.0,
                'previous_high_20': 105.0,
                'support_anchor': 90.0,
                'support_distance_pct': 0.11,
                'reward_risk': 1.8,
            },
        )

        class StubIndicatorService:
            def enrich(self, source_snapshot: StockSnapshot) -> StockSnapshot:
                return source_snapshot

        scanner = ScannerService(
            tickers=['MSFT'],
            data_provider=StubProvider({'MSFT': failing_snapshot}),
            indicator_service=StubIndicatorService(),
            filters=[
                AverageVolumeFilter(),
                RSIFilter(),
                MACDFilter(),
                VolumeExpansionFilter(),
                DailyUptrendFilter(),
                SupportPullbackFilter(),
                RewardRiskFilter(),
            ],
            output_writer=PassThroughOutputWriter(),
            trade_builder=None,
        )

        candidates = scanner.run()

        self.assertEqual(candidates, [])
        self.assertEqual(scanner.last_summary.passed_tickers, 0)
        self.assertEqual(scanner.last_summary.filter_failures['AverageVolumeFilter'], 1)
        self.assertEqual(scanner.last_summary.filter_failures['RSIFilter'], 1)
        self.assertEqual(scanner.last_summary.filter_failures['MACDFilter'], 1)
        self.assertEqual(scanner.last_summary.filter_failures['VolumeExpansionFilter'], 1)
        self.assertEqual(scanner.last_summary.filter_failures['DailyUptrendFilter'], 1)
        self.assertEqual(scanner.last_summary.filter_failures['SupportPullbackFilter'], 1)
        self.assertEqual(scanner.last_summary.filter_failures['RewardRiskFilter'], 1)


if __name__ == '__main__':
    unittest.main()
