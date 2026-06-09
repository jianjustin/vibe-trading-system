"""Backtest stage: run historical validation and produce BacktestReport artifacts."""

from typing import Callable

import pandas as pd

from vts.artifacts.schemas import BacktestReport
from vts.artifacts.store import ArtifactStore
from vts.backtest.engine import SimpleEquityEngine
from vts.backtest.metrics import calc_metrics
from vts.loaders.yfinance_loader import YFinanceLoader
from vts.stages.base import Stage


class BacktestStage(Stage):
    """Run a backtest for a given signal function and save BacktestReport."""

    def __init__(self, store: ArtifactStore, loader: YFinanceLoader | None = None):
        super().__init__(store)
        self.loader = loader or YFinanceLoader()

    def run(self, **kwargs) -> str:
        ticker: str = kwargs["ticker"]
        rule_name: str = kwargs["rule_name"]
        signal_fn: Callable[[pd.DataFrame], pd.Series] = kwargs["signal_fn"]
        start_date: str = kwargs.get("start_date", "2022-01-01")
        end_date: str = kwargs.get("end_date", "2026-01-01")
        market_filter: str = kwargs.get("market_filter", "")

        data = self.loader.fetch_ohlcv(ticker, start_date, end_date)
        signals = signal_fn(data)

        engine = SimpleEquityEngine()
        trades = engine.run(data, signals)
        metrics = calc_metrics(trades)

        conclusion = self._derive_conclusion(metrics)

        report = BacktestReport(
            rule_name=rule_name,
            ticker_scope=ticker,
            market_filter=market_filter,
            entry_rule=kwargs.get("entry_rule", ""),
            exit_rule=kwargs.get("exit_rule", ""),
            time_range=f"{start_date} to {end_date}",
            sample_count=metrics["sample_count"],
            win_rate=metrics["win_rate"],
            profit_loss_ratio=metrics["profit_loss_ratio"],
            max_drawdown=metrics["max_drawdown"],
            conclusion=conclusion,
        )

        artifact_id = f"{ticker}-{rule_name}"
        self.store.save(report, "reports", artifact_id)
        return artifact_id

    def _derive_conclusion(self, metrics: dict) -> str:
        if metrics["sample_count"] < 10:
            return "样本不足，不下结论"
        win_rate = metrics.get("win_rate") or 0
        plr = metrics.get("profit_loss_ratio") or 0
        if win_rate < 0.4 and plr < 1.0:
            return "放弃"
        if win_rate > 0.55 and plr > 1.5:
            return "小仓位验证"
        if win_rate > 0.45:
            return "模拟观察"
        return "修改"
