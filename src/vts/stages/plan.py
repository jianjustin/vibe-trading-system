"""Plan stage: generate ExecutionPlan with human gate approval workflow."""

from datetime import datetime

from vts.artifacts.schemas import (
    ApprovalStatus, Confidence, ExecutionPlan,
    Viewpoint, ViewpointDirection,
)
from vts.artifacts.store import ArtifactStore
from vts.stages.base import Stage

_DIRECTION_MAP = {
    ViewpointDirection.BULLISH: "做多",
    ViewpointDirection.BEARISH: "做空",
}


class PlanStage(Stage):
    """Generate an ExecutionPlan from a Viewpoint and manage human approval."""

    def __init__(self, store: ArtifactStore):
        super().__init__(store)

    def run(self, **kwargs) -> str:
        return self.generate(**kwargs)

    def generate(self, ticker: str) -> str:
        viewpoint = self.store.load("viewpoints", ticker, Viewpoint)

        if viewpoint.direction == ViewpointDirection.NEUTRAL:
            raise ValueError(f"Cannot generate plan for neutral viewpoint on {ticker}")
        if viewpoint.confidence == Confidence.LOW:
            raise ValueError(f"Cannot generate plan: confidence too low for {ticker}")

        direction = _DIRECTION_MAP.get(viewpoint.direction, "观望")

        plan = ExecutionPlan(
            ticker=ticker,
            direction=direction,
            position_pct="5%",
            entry_condition=f"Based on: {viewpoint.core_logic}",
            prerequisites=viewpoint.macro_support,
        )

        artifact_id = ticker
        self.store.save(plan, "plans", artifact_id)
        return artifact_id

    def review(self, plan_id: str, action: str, notes: str = "") -> None:
        plan = self.store.load("plans", plan_id, ExecutionPlan)

        status_map = {
            "approve": ApprovalStatus.APPROVED,
            "reject": ApprovalStatus.REJECTED,
            "revise": ApprovalStatus.REVISED,
        }
        if action not in status_map:
            raise ValueError(f"Invalid action: {action}. Use: approve, reject, revise")

        plan.approval_status = status_map[action]
        plan.approval_notes = notes
        if action == "approve":
            plan.approved_at = datetime.now()

        self.store.save(plan, "plans", plan_id)
