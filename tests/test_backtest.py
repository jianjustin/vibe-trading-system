import pandas as pd
import numpy as np
import pytest
from unittest.mock import MagicMock

from vts.stages.backtest import BacktestStage
from vts.artifacts.schemas import BacktestReport


@pytest.fixture
def mock_loader_for_bt():
    loader = MagicMock()
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=250, freq="B")
    prices = 100 + np.cumsum(np.random.randn(250) * 1.5)
    ohlcv = pd.DataFrame(
        {
            "open": prices + np.random.rand(250) * 0.5,
            "high": prices + abs(np.random.randn(250)),
            "low": prices - abs(np.random.randn(250)),
            "close": prices,
            "volume": np.random.randint(1_000_000, 5_000_000, 250),
        },
        index=dates,
    )
    loader.fetch_ohlcv.return_value = ohlcv
    return loader


def test_backtest_stage_produces_report(store, mock_loader_for_bt):
    def signal_fn(data):
        signals = pd.Series(0, index=data.index)
        signals.iloc[10] = 1
        signals.iloc[20] = -1
        signals.iloc[50] = 1
        signals.iloc[65] = -1
        return signals

    stage = BacktestStage(store, loader=mock_loader_for_bt)
    artifact_id = stage.run(
        ticker="TSLA.US",
        rule_name="test_setup",
        signal_fn=signal_fn,
        start_date="2024-01-01",
        end_date="2025-01-01",
    )
    report = store.load("reports", artifact_id, BacktestReport)
    assert report.rule_name == "test_setup"
    assert report.sample_count == 2
    assert report.win_rate is not None


def test_backtest_stage_no_trades(store, mock_loader_for_bt):
    def signal_fn(data):
        return pd.Series(0, index=data.index)

    stage = BacktestStage(store, loader=mock_loader_for_bt)
    artifact_id = stage.run(
        ticker="TSLA.US",
        rule_name="no_trades",
        signal_fn=signal_fn,
        start_date="2024-01-01",
        end_date="2025-01-01",
    )
    report = store.load("reports", artifact_id, BacktestReport)
    assert report.sample_count == 0
