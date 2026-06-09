"""Sequential pipeline orchestrator for the five-stage investment pipeline."""

from typing import Callable

import pandas as pd

from vts.artifacts.store import ArtifactStore
from vts.loaders.yfinance_loader import YFinanceLoader
from vts.stages.backtest import BacktestStage
from vts.stages.discover import DiscoverStage
from vts.stages.plan import PlanStage
from vts.stages.research import ResearchStage
from vts.stages.viewpoint import ViewpointStage


class Pipeline:
    """Orchestrate the five pipeline stages with a shared artifact store."""

    def __init__(self, store: ArtifactStore, loader: YFinanceLoader | None = None):
        self.store = store
        self.loader = loader or YFinanceLoader()

    def run_research(self) -> str:
        stage = ResearchStage(self.store, loader=self.loader)
        return stage.run()

    def run_discover(self, **kwargs) -> str:
        stage = DiscoverStage(self.store)
        return stage.run(**kwargs)

    def run_backtest(self, **kwargs) -> str:
        stage = BacktestStage(self.store, loader=self.loader)
        return stage.run(**kwargs)

    def run_viewpoint(self, **kwargs) -> str:
        stage = ViewpointStage(self.store)
        return stage.run(**kwargs)

    def run_plan(self, **kwargs) -> str:
        stage = PlanStage(self.store)
        return stage.run(**kwargs)

    def review_plan(self, plan_id: str, action: str, notes: str = "") -> None:
        stage = PlanStage(self.store)
        stage.review(plan_id, action, notes)
