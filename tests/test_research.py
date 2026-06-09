import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from datetime import date

from vts.stages.research import ResearchStage
from vts.artifacts.schemas import MacroSnapshot, MarketStance


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    dates = pd.date_range("2025-06-01", periods=250, freq="B")
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(250) * 0.5)
    ohlcv = pd.DataFrame(
        {
            "open": prices, "high": prices + 1, "low": prices - 1,
            "close": prices, "volume": [1_000_000] * 250,
        },
        index=dates,
    )
    loader.fetch_macro_indicators.return_value = {
        "treasury_10y": {"latest": 4.28, "data": ohlcv},
        "vix": {"latest": 17.5, "data": ohlcv},
        "dxy": {"latest": 104.0, "data": ohlcv},
        "spy": {"latest": 540.0, "data": ohlcv},
        "qqq": {"latest": 470.0, "data": ohlcv},
        "hyg": {"latest": 78.0, "data": ohlcv},
    }
    loader.compute_ma_status.side_effect = lambda ticker, periods=None: {50: True, 200: True}
    return loader


def test_research_produces_snapshot(store, mock_loader):
    stage = ResearchStage(store, loader=mock_loader)
    artifact_id = stage.run()
    assert artifact_id == date.today().isoformat()
    snapshot = store.load("snapshots", artifact_id, MacroSnapshot)
    assert snapshot.treasury_10y == 4.28
    assert snapshot.vix == 17.5


def test_research_offensive_stance(store, mock_loader):
    mock_loader.fetch_macro_indicators.return_value["vix"]["latest"] = 14.0
    mock_loader.compute_ma_status.side_effect = lambda ticker, periods=None: {50: True, 200: True}
    stage = ResearchStage(store, loader=mock_loader)
    artifact_id = stage.run()
    snapshot = store.load("snapshots", artifact_id, MacroSnapshot)
    assert snapshot.stance == MarketStance.OFFENSIVE


def test_research_defensive_stance(store, mock_loader):
    mock_loader.fetch_macro_indicators.return_value["vix"]["latest"] = 30.0
    mock_loader.compute_ma_status.side_effect = lambda ticker, periods=None: {50: False, 200: False}
    stage = ResearchStage(store, loader=mock_loader)
    artifact_id = stage.run()
    snapshot = store.load("snapshots", artifact_id, MacroSnapshot)
    assert snapshot.stance == MarketStance.DEFENSIVE


def test_research_cautious_stance(store, mock_loader):
    mock_loader.fetch_macro_indicators.return_value["vix"]["latest"] = 22.0
    mock_loader.compute_ma_status.side_effect = lambda ticker, periods=None: {50: True, 200: False}
    stage = ResearchStage(store, loader=mock_loader)
    artifact_id = stage.run()
    snapshot = store.load("snapshots", artifact_id, MacroSnapshot)
    assert snapshot.stance == MarketStance.CAUTIOUS
