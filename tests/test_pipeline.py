import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

from vts.orchestrator.pipeline import Pipeline
from vts.artifacts.schemas import MacroSnapshot, ResearchBrief, Viewpoint


@pytest.fixture
def mock_loader_pipeline():
    loader = MagicMock()
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=250, freq="B")
    prices = 100 + np.cumsum(np.random.randn(250) * 1.5)
    ohlcv = pd.DataFrame(
        {
            "open": prices, "high": prices + 1, "low": prices - 1,
            "close": prices, "volume": [1_000_000] * 250,
        },
        index=dates,
    )
    loader.fetch_macro_indicators.return_value = {
        "treasury_10y": {"latest": 4.28, "data": ohlcv},
        "vix": {"latest": 15.0, "data": ohlcv},
        "dxy": {"latest": 104.0, "data": ohlcv},
        "spy": {"latest": 540.0, "data": ohlcv},
        "qqq": {"latest": 470.0, "data": ohlcv},
        "hyg": {"latest": 78.0, "data": ohlcv},
    }
    loader.compute_ma_status.return_value = {50: True, 200: True}
    loader.fetch_ohlcv.return_value = ohlcv
    return loader


def test_pipeline_research_only(store, mock_loader_pipeline):
    pipe = Pipeline(store, loader=mock_loader_pipeline)
    result = pipe.run_research()
    assert result is not None
    snapshot = store.load("snapshots", result, MacroSnapshot)
    assert snapshot.vix == 15.0


def test_pipeline_discover(store, mock_loader_pipeline):
    pipe = Pipeline(store, loader=mock_loader_pipeline)
    result = pipe.run_discover(
        ticker="TSLA.US",
        thesis="Test thesis",
        key_evidence=["A", "B"],
        invalidation="Fail condition",
    )
    brief = store.load("briefs", result, ResearchBrief)
    assert brief.ticker == "TSLA.US"


def test_pipeline_full_to_viewpoint(store, mock_loader_pipeline):
    pipe = Pipeline(store, loader=mock_loader_pipeline)
    pipe.run_research()
    pipe.run_discover(
        ticker="TSLA.US", thesis="Test", key_evidence=["A"],
        invalidation="X",
    )

    def signal_fn(data):
        signals = pd.Series(0, index=data.index)
        for i in range(0, len(data) - 20, 30):
            signals.iloc[i] = 1
            signals.iloc[i + 15] = -1
        return signals

    pipe.run_backtest(
        ticker="TSLA.US", rule_name="test", signal_fn=signal_fn,
        start_date="2024-01-01", end_date="2025-01-01",
    )
    vp_id = pipe.run_viewpoint(ticker="TSLA.US")
    vp = store.load("viewpoints", vp_id, Viewpoint)
    assert vp.ticker == "TSLA.US"
