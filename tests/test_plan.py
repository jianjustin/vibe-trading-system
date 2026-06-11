import pytest

from vts.stages.plan import PlanStage
from vts.artifacts.schemas import (
    Viewpoint, ViewpointDirection, Confidence,
    ExecutionPlan, ApprovalStatus,
)


def _seed_viewpoint(store, direction=ViewpointDirection.BULLISH, confidence=Confidence.MEDIUM):
    store.save(
        Viewpoint(
            ticker="TSLA.US",
            direction=direction,
            confidence=confidence,
            macro_support="Favorable",
            core_logic="Strong thesis",
            counter_arguments=["Risk A", "Risk B"],
            invalidation="Delivery miss",
            valid_until="Next earnings",
        ),
        "viewpoints", "TSLA.US",
    )


def test_plan_generates_from_viewpoint(store):
    _seed_viewpoint(store)
    stage = PlanStage(store)
    artifact_id = stage.generate(ticker="TSLA.US")
    plan = store.load("plans", artifact_id, ExecutionPlan)
    assert plan.ticker == "TSLA.US"
    assert plan.direction == "做多"
    assert plan.approval_status == ApprovalStatus.PENDING


def test_plan_skips_neutral(store):
    _seed_viewpoint(store, direction=ViewpointDirection.NEUTRAL)
    stage = PlanStage(store)
    with pytest.raises(ValueError, match="neutral"):
        stage.generate(ticker="TSLA.US")


def test_plan_skips_low_confidence(store):
    _seed_viewpoint(store, confidence=Confidence.LOW)
    stage = PlanStage(store)
    with pytest.raises(ValueError, match="confidence"):
        stage.generate(ticker="TSLA.US")


def test_plan_approve(store):
    _seed_viewpoint(store)
    stage = PlanStage(store)
    plan_id = stage.generate(ticker="TSLA.US")
    stage.review(plan_id, "approve", "Looks good, will enter at market open")
    plan = store.load("plans", plan_id, ExecutionPlan)
    assert plan.approval_status == ApprovalStatus.APPROVED
    assert plan.approval_notes == "Looks good, will enter at market open"
    assert plan.approved_at is not None


def test_plan_reject(store):
    _seed_viewpoint(store)
    stage = PlanStage(store)
    plan_id = stage.generate(ticker="TSLA.US")
    stage.review(plan_id, "reject", "Macro too uncertain")
    plan = store.load("plans", plan_id, ExecutionPlan)
    assert plan.approval_status == ApprovalStatus.REJECTED


def test_plan_revise(store):
    _seed_viewpoint(store)
    stage = PlanStage(store)
    plan_id = stage.generate(ticker="TSLA.US")
    stage.review(plan_id, "revise", "Reduce position to 3%")
    plan = store.load("plans", plan_id, ExecutionPlan)
    assert plan.approval_status == ApprovalStatus.REVISED
