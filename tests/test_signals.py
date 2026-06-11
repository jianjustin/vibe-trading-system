import numpy as np
import pandas as pd
import pytest

from vts.backtest.signals import SIGNAL_RULES, get_signal_rule


@pytest.fixture
def trending_data():
    np.random.seed(7)
    dates = pd.date_range("2024-01-01", periods=300, freq="B")
    prices = 100 + np.cumsum(np.random.randn(300) * 1.5 + 0.1)
    return pd.DataFrame(
        {
            "open": prices, "high": prices + 1, "low": prices - 1,
            "close": prices, "volume": [1_000_000] * 300,
        },
        index=dates,
    )


def test_registry_has_rules_with_metadata():
    assert len(SIGNAL_RULES) >= 2
    for name, rule in SIGNAL_RULES.items():
        assert rule.name == name
        assert rule.entry_rule
        assert rule.exit_rule
        assert callable(rule.fn)


def test_get_signal_rule_unknown():
    with pytest.raises(KeyError):
        get_signal_rule("nonexistent")


def test_signals_are_valid_series(trending_data):
    for rule in SIGNAL_RULES.values():
        signals = rule.fn(trending_data)
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(trending_data)
        assert set(signals.unique()).issubset({1, -1, 0})
