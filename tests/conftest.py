import pytest
from pathlib import Path
from datetime import date

from vts.artifacts.store import ArtifactStore
from vts.artifacts.schemas import (
    MacroSnapshot, MarketStance, ResearchBrief, NextAction,
    BacktestReport, Viewpoint, ViewpointDirection, Confidence,
    ExecutionPlan, ApprovalStatus,
)


@pytest.fixture
def store(tmp_path):
    return ArtifactStore(base_dir=tmp_path)


@pytest.fixture
def sample_snapshot():
    return MacroSnapshot(
        date=date(2026, 6, 9),
        stance=MarketStance.CAUTIOUS,
        treasury_10y=4.28,
        vix=18.5,
        dxy=104.2,
        spy_above_50d=True,
        spy_above_200d=True,
        qqq_above_50d=True,
        qqq_above_200d=False,
        most_important_change="VIX dropped below 20",
        impact_on_growth="Favorable for growth equities",
        next_step="Monitor treasury curve",
    )


@pytest.fixture
def sample_brief():
    return ResearchBrief(
        ticker="TSLA.US",
        thesis="EV leader with strong delivery momentum",
        key_evidence=[
            "Q1 deliveries beat estimates by 8%",
            "Gross margin expanding for 3 quarters",
            "FSD licensing revenue emerging",
        ],
        core_driver="Quarterly delivery numbers",
        macro_sensitivity="Interest rates affect auto financing",
        valuation_sensitivity="Revenue growth rate, margin trajectory",
        catalysts="Q2 earnings July 23",
        invalidation="Deliveries miss 2 consecutive quarters",
        next_action=NextAction.BACKTEST_SETUP,
    )


@pytest.fixture
def sample_backtest():
    return BacktestReport(
        rule_name="Post-earnings gap continuation",
        ticker_scope="TSLA.US",
        market_filter="QQQ above 50d MA",
        entry_rule="Buy at close on earnings day if gap > 3%",
        exit_rule="Sell after 5 trading days or -5% stop loss",
        time_range="2022-01-01 to 2026-01-01",
        sample_count=16,
        win_rate=0.625,
        profit_loss_ratio=1.8,
        max_drawdown=0.12,
        vs_spy="Alpha +3.2% annualized",
        conclusion="模拟观察",
    )


@pytest.fixture
def sample_viewpoint():
    return Viewpoint(
        ticker="TSLA.US",
        direction=ViewpointDirection.BULLISH,
        confidence=Confidence.MEDIUM,
        macro_support="Low VIX, growth-friendly environment",
        core_logic="Strong deliveries + margin expansion in favorable macro",
        supporting_evidence="Backtest shows positive edge on gap continuation",
        counter_arguments=[
            "Valuation stretched at 60x forward P/E",
            "Competition intensifying in China EV market",
        ],
        invalidation="Fed pivots hawkish or deliveries miss",
        valid_until="Q2 earnings (2026-07-23)",
    )


@pytest.fixture
def sample_plan():
    return ExecutionPlan(
        ticker="TSLA.US",
        direction="做多",
        position_pct="5%",
        entry_condition="Price pulls back to 50d MA or post-earnings gap > 3%",
        entry_price_range="$280-$310",
        stop_loss="$265 (-8%)",
        target="$340 first target, $380 second target",
        holding_period="中线 (4-8 weeks)",
        prerequisites="VIX stays below 25, QQQ above 50d MA",
    )
