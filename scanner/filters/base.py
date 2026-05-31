from __future__ import annotations

from abc import ABC, abstractmethod

from scanner.core.models import FilterResult, StockSnapshot


class BaseFilter(ABC):
    @abstractmethod
    def evaluate(self, snapshot: StockSnapshot) -> FilterResult:
        raise NotImplementedError

