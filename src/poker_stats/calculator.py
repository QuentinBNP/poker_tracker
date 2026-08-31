from __future__ import annotations

from database.database import Database
from database.filters import HistoryFilter
from poker_stats.statistics_service import StatisticsService


class StatisticsCalculator:
    def __init__(self, database: Database, hero_name: str) -> None:
        self.database = database
        self.hero_name = hero_name
        self.service = StatisticsService(database, hero_name)

    def calculate(self, filters: HistoryFilter | None = None) -> dict[str, float]:
        statistics = self.service.calculate(filters)
        return {
            **statistics,
            "money_result": statistics["total_profit"],
        }