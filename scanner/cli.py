from __future__ import annotations

import argparse
import logging

from scanner.core.scanner import ScannerService
from scanner.core.trade_builder import TradeBuilder
from scanner.data.ticker_source import load_sp500_tickers
from scanner.data.yahoo_provider import YahooFinanceProvider
from scanner.filters import (
    AverageVolumeFilter,
    DailyUptrendFilter,
    MACDFilter,
    RewardRiskFilter,
    RSIFilter,
    SupportPullbackFilter,
    VolumeExpansionFilter,
)
from scanner.indicators.service import IndicatorService
from scanner.logging_config import configure_logging
from scanner.output.writer import OutputWriter

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Swing trade scanner with trade construction and ranked output.'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit the number of tickers loaded into the scan.',
    )
    parser.add_argument(
        '--output',
        default='swing_trade_candidates.csv',
        help='CSV output path.',
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        help='Logging level: DEBUG, INFO, WARNING, ERROR.',
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    configure_logging(args.log_level)

    tickers = load_sp500_tickers(limit=args.limit)
    LOGGER.info('Loaded %d tickers from local S&P 500 source.', len(tickers))
    output_writer = OutputWriter()

    scanner = ScannerService(
        tickers=tickers,
        data_provider=YahooFinanceProvider(),
        indicator_service=IndicatorService(),
        filters=[
            AverageVolumeFilter(),
            RSIFilter(),
            MACDFilter(),
            VolumeExpansionFilter(),
            DailyUptrendFilter(),
            SupportPullbackFilter(),
            RewardRiskFilter(),
        ],
        output_writer=output_writer,
        trade_builder=TradeBuilder(),
    )
    candidates = scanner.run(limit=args.limit)
    summary = scanner.last_summary
    output_writer.write(candidates, args.output)

    print(f'Loaded {len(tickers)} tickers from the local S&P 500 universe source.')
    print(f'Tickers evaluated: {summary.total_tickers}')
    print(f'Candidates passing the active filters: {len(candidates)}')
    print(f'Fetch failures: {summary.fetch_failures}')
    print(f'Indicator enrichment failures: {summary.enrichment_failures}')
    print(f'Trade construction failures: {summary.trade_failures}')
    print('Filter failure counts:')
    for filter_name, fail_count in summary.filter_failures.items():
        print(f'  - {filter_name}: {fail_count}')
    print(f'CSV output: {args.output}')
    if not candidates:
        print('No candidates passed the current filter set.')
        return 0

    for line in output_writer.format_console(candidates):
        print(line)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
