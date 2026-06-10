from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from vts.loaders.earnings_calendar import (
    check_earnings_on_date,
    get_earnings_date_for_ticker,
    scan_watchlist,
)


def _earnings_df(rows: dict[str, float | None]) -> pd.DataFrame:
    """rows: {date_str: reported_eps_or_None}"""
    index = pd.DatetimeIndex([pd.Timestamp(d, tz="America/New_York") for d in rows])
    return pd.DataFrame(
        {"EPS Estimate": [1.0] * len(rows), "Reported EPS": list(rows.values())},
        index=index,
    )


def _patch_ticker(df):
    ticker = MagicMock()
    ticker.earnings_dates = df
    return patch("vts.loaders.earnings_calendar.yf.Ticker", return_value=ticker)


def test_earnings_hit_within_window():
    with _patch_ticker(_earnings_df({"2026-06-09": 2.5})):
        assert check_earnings_on_date("TSLA", "2026-06-10", window_days=2) is True
        assert get_earnings_date_for_ticker("TSLA", "2026-06-10") == "2026-06-09"


def test_earnings_outside_window_misses():
    with _patch_ticker(_earnings_df({"2026-06-01": 2.5})):
        assert check_earnings_on_date("TSLA", "2026-06-10", window_days=2) is False


def test_unreported_eps_does_not_count():
    with _patch_ticker(_earnings_df({"2026-06-09": float("nan")})):
        assert check_earnings_on_date("TSLA", "2026-06-09") is False


def test_empty_data_returns_none():
    with _patch_ticker(pd.DataFrame()):
        assert get_earnings_date_for_ticker("TSLA", "2026-06-09") is None


def test_yfinance_error_returns_false():
    with patch(
        "vts.loaders.earnings_calendar.yf.Ticker", side_effect=RuntimeError("rate limited")
    ):
        assert check_earnings_on_date("TSLA", "2026-06-09") is False


def test_scan_watchlist_returns_hits_only():
    hit = MagicMock()
    hit.earnings_dates = _earnings_df({"2026-06-09": 2.5})
    miss = MagicMock()
    miss.earnings_dates = _earnings_df({"2026-03-01": 1.2})

    def fake_ticker(symbol):
        return hit if symbol == "TSLA" else miss

    with patch("vts.loaders.earnings_calendar.yf.Ticker", side_effect=fake_ticker):
        assert scan_watchlist(["TSLA", "AAPL"], "2026-06-09") == ["TSLA"]
