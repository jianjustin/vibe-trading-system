"""Simplified US equity backtest engine. Long-only, bar-by-bar."""

import pandas as pd


class SimpleEquityEngine:
    """Run a bar-by-bar backtest on OHLCV data with entry/exit signals.

    Signals: 1 = buy, -1 = sell, 0 = hold.
    """

    def __init__(self, initial_capital: float = 100_000, slippage: float = 0.0005):
        self.initial_capital = initial_capital
        self.slippage = slippage

    def run(self, data: pd.DataFrame, signals: pd.Series) -> list[dict]:
        trades = []
        position = None
        capital = self.initial_capital

        for i, (dt, row) in enumerate(data.iterrows()):
            sig = signals.iloc[i] if i < len(signals) else 0

            if sig == 1 and position is None:
                entry_price = row["close"] * (1 + self.slippage)
                shares = int(capital / entry_price)
                if shares > 0:
                    position = {
                        "entry_date": dt,
                        "entry_price": entry_price,
                        "shares": shares,
                    }

            elif sig == -1 and position is not None:
                exit_price = row["close"] * (1 - self.slippage)
                pnl = (exit_price - position["entry_price"]) * position["shares"]
                pnl_pct = (exit_price / position["entry_price"]) - 1
                trades.append(
                    {
                        "entry_date": position["entry_date"],
                        "exit_date": dt,
                        "entry_price": round(position["entry_price"], 4),
                        "exit_price": round(exit_price, 4),
                        "shares": position["shares"],
                        "pnl": round(pnl, 2),
                        "pnl_pct": round(pnl_pct, 6),
                    }
                )
                capital += pnl
                position = None

        return trades
