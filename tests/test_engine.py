import pandas as pd
import numpy as np
import pytest
from vts.backtest.engine import SimpleEquityEngine
from vts.backtest.metrics import calc_metrics


@pytest.fixture
def price_data():
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    prices = 100 + np.cumsum(np.random.randn(100) * 1.5)
    return pd.DataFrame(
        {
            "open": prices + np.random.rand(100) * 0.5,
            "high": prices + abs(np.random.randn(100)),
            "low": prices - abs(np.random.randn(100)),
            "close": prices,
            "volume": np.random.randint(1_000_000, 5_000_000, 100),
        },
        index=dates,
    )


def test_engine_buy_and_hold(price_data):
    signals = pd.Series(0, index=price_data.index)
    signals.iloc[5] = 1
    signals.iloc[50] = -1
    engine = SimpleEquityEngine(initial_capital=100_000)
    trades = engine.run(price_data, signals)
    assert len(trades) == 1
    assert trades[0]["entry_date"] == price_data.index[5]
    assert trades[0]["exit_date"] == price_data.index[50]


def test_engine_no_signals(price_data):
    signals = pd.Series(0, index=price_data.index)
    engine = SimpleEquityEngine(initial_capital=100_000)
    trades = engine.run(price_data, signals)
    assert len(trades) == 0


def test_engine_multiple_trades(price_data):
    signals = pd.Series(0, index=price_data.index)
    signals.iloc[5] = 1
    signals.iloc[15] = -1
    signals.iloc[30] = 1
    signals.iloc[45] = -1
    engine = SimpleEquityEngine(initial_capital=100_000)
    trades = engine.run(price_data, signals)
    assert len(trades) == 2


def test_calc_metrics_basic():
    trades = [
        {"pnl_pct": 0.05},
        {"pnl_pct": -0.03},
        {"pnl_pct": 0.08},
        {"pnl_pct": -0.02},
        {"pnl_pct": 0.04},
    ]
    m = calc_metrics(trades)
    assert m["sample_count"] == 5
    assert m["win_rate"] == 0.6
    assert m["profit_loss_ratio"] > 0
    assert "max_drawdown" in m
