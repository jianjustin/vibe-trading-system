"""Named signal rule registry so backtests can be triggered by name (CLI/API)."""

from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass(frozen=True)
class SignalRule:
    name: str
    description: str
    entry_rule: str
    exit_rule: str
    fn: Callable[[pd.DataFrame], pd.Series]


def _ma_cross(fast: int, slow: int) -> Callable[[pd.DataFrame], pd.Series]:
    def signal_fn(data: pd.DataFrame) -> pd.Series:
        fast_ma = data["close"].rolling(fast).mean()
        slow_ma = data["close"].rolling(slow).mean()
        above = (fast_ma > slow_ma).fillna(False)
        signals = pd.Series(0, index=data.index)
        signals[above & ~above.shift(1, fill_value=False)] = 1
        signals[~above & above.shift(1, fill_value=False)] = -1
        return signals

    return signal_fn


def _breakout(entry_window: int, exit_window: int) -> Callable[[pd.DataFrame], pd.Series]:
    def signal_fn(data: pd.DataFrame) -> pd.Series:
        rolling_high = data["close"].rolling(entry_window).max().shift(1)
        rolling_low = data["close"].rolling(exit_window).min().shift(1)
        signals = pd.Series(0, index=data.index)
        signals[data["close"] > rolling_high] = 1
        signals[data["close"] < rolling_low] = -1
        return signals

    return signal_fn


SIGNAL_RULES: dict[str, SignalRule] = {
    rule.name: rule
    for rule in [
        SignalRule(
            name="ma_cross_20_60",
            description="20/60 日均线交叉",
            entry_rule="20 日均线上穿 60 日均线时买入",
            exit_rule="20 日均线下穿 60 日均线时卖出",
            fn=_ma_cross(20, 60),
        ),
        SignalRule(
            name="ma_cross_50_200",
            description="50/200 日均线交叉（金叉/死叉）",
            entry_rule="50 日均线上穿 200 日均线时买入",
            exit_rule="50 日均线下穿 200 日均线时卖出",
            fn=_ma_cross(50, 200),
        ),
        SignalRule(
            name="breakout_20_10",
            description="20 日新高突破",
            entry_rule="收盘价突破前 20 日最高收盘价时买入",
            exit_rule="收盘价跌破前 10 日最低收盘价时卖出",
            fn=_breakout(20, 10),
        ),
    ]
}


def get_signal_rule(name: str) -> SignalRule:
    if name not in SIGNAL_RULES:
        raise KeyError(f"Unknown signal rule: {name}. Available: {sorted(SIGNAL_RULES)}")
    return SIGNAL_RULES[name]
