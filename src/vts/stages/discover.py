"""Discover stage: create and save ResearchBrief artifacts."""

from vts.artifacts.schemas import NextAction, ResearchBrief
from vts.artifacts.store import ArtifactStore
from vts.stages.base import Stage

_ACTION_MAP = {
    "继续研究": NextAction.CONTINUE_RESEARCH,
    "决策挑战": NextAction.DECISION_CHALLENGE,
    "回测 setup": NextAction.BACKTEST_SETUP,
    "放弃": NextAction.ABANDON,
}


class DiscoverStage(Stage):
    """Create a ResearchBrief from structured input and save it."""

    def __init__(self, store: ArtifactStore):
        super().__init__(store)

    def run(self, **kwargs) -> str:
        ticker = kwargs.get("ticker", "")
        thesis = kwargs.get("thesis", "")
        if not ticker:
            raise ValueError("ticker is required")
        if not thesis:
            raise ValueError("thesis is required")

        evidence = kwargs.get("key_evidence", [])
        if len(evidence) > 3:
            evidence = evidence[:3]

        action_str = kwargs.get("next_action", "继续研究")
        next_action = _ACTION_MAP.get(action_str, NextAction.CONTINUE_RESEARCH)

        brief = ResearchBrief(
            ticker=ticker,
            thesis=thesis,
            key_evidence=evidence,
            core_driver=kwargs.get("core_driver", ""),
            macro_sensitivity=kwargs.get("macro_sensitivity", ""),
            valuation_sensitivity=kwargs.get("valuation_sensitivity", ""),
            catalysts=kwargs.get("catalysts", ""),
            invalidation=kwargs.get("invalidation", ""),
            next_action=next_action,
        )

        self.store.save(brief, "briefs", ticker)
        return ticker
