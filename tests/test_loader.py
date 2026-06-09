import pandas as pd
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from vts.loaders.yfinance_loader import YFinanceLoader, MACRO_TICKERS


@pytest.fixture
def loader():
    return YFinanceLoader()


@pytest.fixture
def mock_ohlcv():
    dates = pd.date_range("2026-01-01", periods=250, freq="B")
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(250) * 0.5)
    return pd.DataFrame(
        {
            "Open": prices + np.random.rand(250),
            "High": prices + abs(np.random.randn(250)),
            "Low": prices - abs(np.random.randn(250)),
            "Close": prices,
            "Volume": np.random.randint(1_000_000, 10_000_000, 250),
        },
        index=dates,
    )


def test_fetch_ohlcv_normalizes_columns(loader, mock_ohlcv):
    with patch("vts.loaders.yfinance_loader.yf.download", return_value=mock_ohlcv):
        df = loader.fetch_ohlcv("SPY", "2026-01-01", "2026-12-01")
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]
        assert len(df) == 250


def test_fetch_ohlcv_empty_raises(loader):
    with patch("vts.loaders.yfinance_loader.yf.download", return_value=pd.DataFrame()):
        with pytest.raises(ValueError, match="No data"):
            loader.fetch_ohlcv("INVALID", "2026-01-01", "2026-12-01")


def test_compute_ma_status(loader, mock_ohlcv):
    with patch("vts.loaders.yfinance_loader.yf.download", return_value=mock_ohlcv):
        result = loader.compute_ma_status("SPY", [50, 200])
        assert 50 in result
        assert 200 in result
        assert isinstance(result[50], bool)
        assert isinstance(result[200], bool)


def test_compute_ma_status_insufficient_data(loader):
    short_data = pd.DataFrame(
        {"Open": [1], "High": [2], "Low": [0.5], "Close": [1.5], "Volume": [100]},
        index=pd.date_range("2026-06-01", periods=1),
    )
    with patch("vts.loaders.yfinance_loader.yf.download", return_value=short_data):
        result = loader.compute_ma_status("SPY", [50])
        assert result[50] is None


def test_fetch_macro_indicators(loader, mock_ohlcv):
    with patch("vts.loaders.yfinance_loader.yf.download", return_value=mock_ohlcv):
        indicators = loader.fetch_macro_indicators()
        for key in ["treasury_10y", "vix", "dxy", "spy", "qqq"]:
            assert key in indicators
            assert indicators[key] is not None
            assert "latest" in indicators[key]
