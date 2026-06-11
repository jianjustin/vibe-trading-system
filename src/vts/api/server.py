"""FastAPI server exposing the five-stage pipeline for the web dashboard."""

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from vts.artifacts.schemas import (
    BacktestReport, ExecutionPlan, MacroSnapshot, ResearchBrief, Viewpoint,
)
from vts.artifacts.store import ArtifactStore
from vts.backtest.signals import SIGNAL_RULES, get_signal_rule
from vts.loaders.yfinance_loader import YFinanceLoader
from vts.orchestrator.pipeline import Pipeline

ARTIFACT_MODELS = {
    "snapshots": MacroSnapshot,
    "briefs": ResearchBrief,
    "reports": BacktestReport,
    "viewpoints": Viewpoint,
    "plans": ExecutionPlan,
}


class DiscoverRequest(BaseModel):
    ticker: str
    thesis: str
    key_evidence: list[str] = Field(min_length=1)
    invalidation: str
    next_action: str = "继续研究"


class BacktestRequest(BaseModel):
    ticker: str
    rule: str
    start_date: str = "2022-01-01"
    end_date: str = "2026-01-01"
    market_filter: str = ""


class TickerRequest(BaseModel):
    ticker: str


class ReviewRequest(BaseModel):
    action: Literal["approve", "reject", "revise"]
    notes: str = ""


def create_app(
    store: ArtifactStore | None = None,
    loader: YFinanceLoader | None = None,
    frontend_dist: str | Path | None = None,
) -> FastAPI:
    store = store or ArtifactStore()
    pipeline = Pipeline(store, loader=loader)

    app = FastAPI(title="vibe-trading-system", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _load(artifact_type: str, artifact_id: str) -> dict:
        model = ARTIFACT_MODELS[artifact_type]
        artifact = store.load(artifact_type, artifact_id, model)
        return artifact.model_dump(mode="json")

    def _stage_result(artifact_type: str, artifact_id: str) -> dict:
        return {
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "artifact": _load(artifact_type, artifact_id),
        }

    @app.get("/api/status")
    def status() -> dict:
        counts = {atype: len(store.list_ids(atype)) for atype in ARTIFACT_MODELS}
        latest = store.latest("snapshots", MacroSnapshot)
        return {
            "counts": counts,
            "latest_stance": latest.stance.value if latest else None,
            "latest_snapshot_date": latest.date.isoformat() if latest else None,
        }

    @app.get("/api/backtest/rules")
    def backtest_rules() -> list[dict]:
        return [
            {
                "name": r.name,
                "description": r.description,
                "entry_rule": r.entry_rule,
                "exit_rule": r.exit_rule,
            }
            for r in SIGNAL_RULES.values()
        ]

    @app.post("/api/stages/research/run")
    def run_research() -> dict:
        artifact_id = pipeline.run_research()
        return _stage_result("snapshots", artifact_id)

    @app.post("/api/stages/discover/run")
    def run_discover(req: DiscoverRequest) -> dict:
        artifact_id = pipeline.run_discover(
            ticker=req.ticker,
            thesis=req.thesis,
            key_evidence=req.key_evidence,
            invalidation=req.invalidation,
            next_action=req.next_action,
        )
        return _stage_result("briefs", artifact_id)

    @app.post("/api/stages/backtest/run")
    def run_backtest(req: BacktestRequest) -> dict:
        try:
            rule = get_signal_rule(req.rule)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))
        artifact_id = pipeline.run_backtest(
            ticker=req.ticker,
            rule_name=rule.name,
            signal_fn=rule.fn,
            start_date=req.start_date,
            end_date=req.end_date,
            market_filter=req.market_filter,
            entry_rule=rule.entry_rule,
            exit_rule=rule.exit_rule,
        )
        return _stage_result("reports", artifact_id)

    @app.post("/api/stages/viewpoint/run")
    def run_viewpoint(req: TickerRequest) -> dict:
        try:
            artifact_id = pipeline.run_viewpoint(ticker=req.ticker)
        except FileNotFoundError as e:
            raise HTTPException(status_code=409, detail=str(e))
        return _stage_result("viewpoints", artifact_id)

    @app.post("/api/stages/plan/run")
    def run_plan(req: TickerRequest) -> dict:
        try:
            artifact_id = pipeline.run_plan(ticker=req.ticker)
        except FileNotFoundError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        return _stage_result("plans", artifact_id)

    @app.post("/api/plans/{plan_id}/review")
    def review_plan(plan_id: str, req: ReviewRequest) -> dict:
        try:
            pipeline.review_plan(plan_id, req.action, req.notes)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        return _stage_result("plans", plan_id)

    @app.get("/api/artifacts/{artifact_type}")
    def list_artifacts(artifact_type: str) -> list[dict]:
        if artifact_type not in ARTIFACT_MODELS:
            raise HTTPException(status_code=404, detail=f"Unknown artifact type: {artifact_type}")
        return [
            {"id": artifact_id, "data": _load(artifact_type, artifact_id)}
            for artifact_id in store.list_ids(artifact_type)
        ]

    @app.get("/api/artifacts/{artifact_type}/{artifact_id}")
    def get_artifact(artifact_type: str, artifact_id: str) -> dict:
        if artifact_type not in ARTIFACT_MODELS:
            raise HTTPException(status_code=404, detail=f"Unknown artifact type: {artifact_type}")
        try:
            return {"id": artifact_id, "data": _load(artifact_type, artifact_id)}
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    dist = Path(frontend_dist) if frontend_dist else Path("frontend/dist")
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")

    return app
