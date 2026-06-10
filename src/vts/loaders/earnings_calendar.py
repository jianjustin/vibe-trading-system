"""财报日历检测模块（基于 yfinance）。

负责：检测 watchlist 中哪些标的在目标日期发布了财报。
迁移自 earnings-agent/data/earnings.py。
"""

import logging
import math
from datetime import datetime, timedelta

import yfinance as yf

logger = logging.getLogger(__name__)


def check_earnings_on_date(ticker: str, target_date: str, window_days: int = 2) -> bool:
    """
    检查 ticker 是否在 target_date ± window_days 内发布了财报。
    window_days=2 可容纳财报日期记录的轻微误差（如 FMP 记为 T+1）。

    返回 True 表示该标的在目标日期附近有财报。
    """
    return get_earnings_date_for_ticker(ticker, target_date, window_days) is not None


def get_earnings_date_for_ticker(ticker: str, target_date: str, window_days: int = 2) -> str | None:
    """
    返回 ticker 在 target_date 附近的实际财报日期（YYYY-MM-DD），未找到返回 None。
    只有已发布（Reported EPS 非 NaN）才算命中。
    """
    try:
        t = yf.Ticker(ticker)
        df = t.earnings_dates  # DataFrame: index=日期, columns=[EPS Estimate, Reported EPS, ...]

        if df is None or df.empty:
            logger.info(f"{ticker}: no earnings_dates data from yfinance")
            return None

        target = datetime.strptime(target_date, "%Y-%m-%d").date()
        window_start = target - timedelta(days=window_days)
        window_end = target + timedelta(days=window_days)

        for idx in df.index:
            # yfinance 返回的 index 是 tz-aware Timestamp
            try:
                earnings_day = idx.date() if hasattr(idx, "date") else idx
                if window_start <= earnings_day <= window_end:
                    reported_eps = df.loc[idx].get("Reported EPS")
                    if reported_eps is not None and not (
                        isinstance(reported_eps, float) and math.isnan(reported_eps)
                    ):
                        logger.info(f"{ticker}: earnings found on {earnings_day} (target {target_date})")
                        return earnings_day.isoformat()
            except Exception:
                continue

        logger.info(f"{ticker}: no earnings found near {target_date}")
        return None

    except Exception as e:
        logger.warning(f"{ticker}: yfinance error - {e}")
        return None


def scan_watchlist(tickers: list[str], target_date: str, window_days: int = 2) -> list[str]:
    """
    批量扫描 watchlist，返回在 target_date 附近发布了财报的 ticker 列表。
    """
    hits = []
    for ticker in tickers:
        if check_earnings_on_date(ticker, target_date, window_days):
            hits.append(ticker)
    logger.info(f"Earnings scan {target_date}: hits = {hits}")
    return hits
