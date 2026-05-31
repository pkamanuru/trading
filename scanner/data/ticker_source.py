from __future__ import annotations

from pathlib import Path

SP500_FILE = Path(__file__).with_name("sp500.txt")


def load_sp500_tickers(limit: int | None = None) -> list[str]:
    tickers = [
        line.strip()
        for line in SP500_FILE.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]
    if limit is not None:
        return tickers[:limit]
    return tickers

