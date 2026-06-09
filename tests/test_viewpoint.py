import pytest
from datetime import date

from vts.stages.viewpoint import ViewpointStage
from vts.artifacts.schemas import (
    MacroSnapshot, MarketStance, ResearchBrief, NextAction,
    BacktestReport, Viewpoint, ViewpointDirection, Confidence,
)


def _seed_artifacts(store, stance=MarketStance.CAUTIOUS, conclusion="模拟观察"):
    store.save(
        MacroSnapshot(date=date(2026, 6, 9), stance=stance, vix=18.0),
        "snapshots", "2026-06-09",
    )
    store.save(
        ResearchBrief(
            ticker="TSLA.US", thesis="EV momentum", invalidation="Delivery miss",
            key_evidence=["Evidence A", "Evidence B"],
        ),
        "briefs", "TSLA.US",
    )
    store.save(
        BacktestReport(
            rule_name="gap_cont", ticker_scope="TSLA.US",
            entry_rule="gap > 3%", exit_rule="5d hold",
            sample_count=20, win_rate=0.6, profit_loss_ratio=1.8,
            max_drawdown=0.1, conclusion=conclusion,
        ),
        "reports", "TSLA.US-gap_cont",
    )


def test_viewpoint_synthesizes(store):
    _seed_artifacts(store)
    stage = ViewpointStage(store)
    artifact_id = stage.run(ticker="TSLA.US")
    vp = store.load("viewpoints", artifact_id, Viewpoint)
    assert vp.ticker == "TSLA.US"
    assert vp.direction in list(ViewpointDirection)
    assert vp.confidence in list(Confidence)
    assert len(vp.counter_arguments) >= 1


def test_viewpoint_bullish_on_good_backtest_and_offensive(store):
    _seed_artifacts(store, stance=MarketStance.OFFENSIVE, conclusion="小仓位验证")
    stage = ViewpointStage(store)
    stage.run(ticker="TSLA.US")
    vp = store.load("viewpoints", "TSLA.US", Viewpoint)
    assert vp.direction == ViewpointDirection.BULLISH


def test_viewpoint_bearish_on_bad_backtest(store):
    _seed_artifacts(store, conclusion="放弃")
    stage = ViewpointStage(store)
    stage.run(ticker="TSLA.US")
    vp = store.load("viewpoints", "TSLA.US", Viewpoint)
    assert vp.direction == ViewpointDirection.BEARISH


def test_viewpoint_missing_brief_raises(store):
    store.save(
        MacroSnapshot(date=date(2026, 6, 9), stance=MarketStance.CAUTIOUS),
        "snapshots", "2026-06-09",
    )
    stage = ViewpointStage(store)
    with pytest.raises(FileNotFoundError):
        stage.run(ticker="UNKNOWN.US")
