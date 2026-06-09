"""Typed artifact schemas for the five pipeline stages."""

from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, Field


class MarketStance(str, Enum):
    OFFENSIVE = "进攻"
    CAUTIOUS = "谨慎"
    DEFENSIVE = "防守"


class MacroSnapshot(BaseModel):
    date: date
    stance: MarketStance
    treasury_10y: float | None = None
    treasury_2y: float | None = None
    spread_10y_2y: float | None = None
    dxy: float | None = None
    vix: float | None = None
    spy_above_50d: bool | None = None
    spy_above_200d: bool | None = None
    qqq_above_50d: bool | None = None
    qqq_above_200d: bool | None = None
    hy_spread: float | None = None
    most_important_change: str = ""
    impact_on_growth: str = ""
    impact_on_watchlist: str = ""
    next_step: str = ""


class NextAction(str, Enum):
    CONTINUE_RESEARCH = "继续研究"
    DECISION_CHALLENGE = "决策挑战"
    BACKTEST_SETUP = "回测 setup"
    ABANDON = "放弃"


class ResearchBrief(BaseModel):
    ticker: str
    thesis: str = Field(description="One-sentence thesis")
    key_evidence: list[str] = Field(max_length=3, description="Top 3 pieces of evidence")
    core_driver: str = ""
    macro_sensitivity: str = ""
    valuation_sensitivity: str = ""
    catalysts: str = ""
    invalidation: str = Field(description="Conditions that would collapse the thesis")
    next_action: NextAction = NextAction.CONTINUE_RESEARCH


class BacktestReport(BaseModel):
    rule_name: str
    ticker_scope: str
    market_filter: str = ""
    entry_rule: str
    exit_rule: str
    data_source: str = "yfinance"
    time_range: str = ""
    sample_count: int = 0
    win_rate: float | None = None
    profit_loss_ratio: float | None = None
    max_drawdown: float | None = None
    vs_spy: str = ""
    vs_qqq: str = ""
    conclusion: str = Field(description="放弃 / 修改 / 模拟观察 / 小仓位验证")


class ViewpointDirection(str, Enum):
    BULLISH = "看多"
    NEUTRAL = "中性"
    BEARISH = "看空"


class Confidence(str, Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class Viewpoint(BaseModel):
    ticker: str
    direction: ViewpointDirection
    confidence: Confidence
    macro_support: str = ""
    core_logic: str = ""
    supporting_evidence: str = ""
    counter_arguments: list[str] = Field(default_factory=list, min_length=2)
    invalidation: str = ""
    valid_until: str = ""


class ApprovalStatus(str, Enum):
    PENDING = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"


class ExecutionPlan(BaseModel):
    ticker: str
    direction: str
    position_pct: str = ""
    entry_condition: str = ""
    entry_price_range: str = ""
    stop_loss: str = ""
    target: str = ""
    holding_period: str = ""
    prerequisites: str = ""
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approval_notes: str = ""
    approved_at: datetime | None = None
