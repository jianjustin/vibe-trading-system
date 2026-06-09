import pytest
from vts.stages.discover import DiscoverStage
from vts.artifacts.schemas import ResearchBrief, NextAction


def test_discover_saves_brief(store):
    stage = DiscoverStage(store)
    artifact_id = stage.run(
        ticker="TSLA.US",
        thesis="EV leader with delivery momentum",
        key_evidence=["Q1 beat", "Margin expansion", "FSD revenue"],
        core_driver="Quarterly deliveries",
        invalidation="Two consecutive delivery misses",
        next_action="回测 setup",
    )
    assert artifact_id == "TSLA.US"
    brief = store.load("briefs", "TSLA.US", ResearchBrief)
    assert brief.ticker == "TSLA.US"
    assert brief.next_action == NextAction.BACKTEST_SETUP
    assert len(brief.key_evidence) == 3


def test_discover_truncates_evidence(store):
    stage = DiscoverStage(store)
    stage.run(
        ticker="NVDA.US",
        thesis="AI compute demand",
        key_evidence=["A", "B", "C", "D", "E"],
        invalidation="Cloud capex slowdown",
    )
    brief = store.load("briefs", "NVDA.US", ResearchBrief)
    assert len(brief.key_evidence) == 3


def test_discover_requires_ticker(store):
    stage = DiscoverStage(store)
    with pytest.raises(ValueError, match="ticker"):
        stage.run(ticker="", thesis="test", invalidation="test")


def test_discover_requires_thesis(store):
    stage = DiscoverStage(store)
    with pytest.raises(ValueError, match="thesis"):
        stage.run(ticker="TSLA.US", thesis="", invalidation="test")
