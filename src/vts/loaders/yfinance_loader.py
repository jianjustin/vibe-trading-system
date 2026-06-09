"""yfinance-based data loader for OHLCV and macro indicators."""

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

MACRO_TICKERS = {
    "treasury_10y": "^TNX",
    "vix": "^VIX",
    "dxy": "DX-Y.NYB",
    "spy": "SPY",
    "qqq": "QQQ",
    "hyg": "HYG",
}


class YFinanceLoader:
    """Fetch OHLCV data and macro indicators via yfinance."""

    def fetch_ohlcv(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            raise ValueError(f"No data for {ticker} between {start_date} and {end_date}")
        col_map = {}
        for c in data.columns:
            name = c[0].lower() if isinstance(c, tuple) else c.lower()
            col_map[c] = name
        data = data.rename(columns=col_map)
        return data[["open", "high", "low", "close", "volume"]]

    def fetch_macro_indicators(self) -> dict:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=300)).strftime("%Y-%m-%d")
        results = {}
        for key, ticker in MACRO_TICKERS.items():
            try:
                data = self.fetch_ohlcv(ticker, start, end)
                results[key] = {"latest": float(data["close"].iloc[-1]), "data": data}
            except Exception:
                results[key] = None
        return results

    def compute_ma_status(self, ticker: str, periods: list[int] | None = None) -> dict[int, bool | None]:
        if periods is None:
            periods = [50, 200]
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=max(periods) + 50)).strftime("%Y-%m-%d")
        data = self.fetch_ohlcv(ticker, start, end)
        latest_close = float(data["close"].iloc[-1])
        result = {}
        for period in periods:
            if len(data) >= period:
                ma = float(data["close"].rolling(period).mean().iloc[-1])
                result[period] = latest_close > ma
            else:
                result[period] = None
        return result
