"""CLI entry point for vibe-trading-system."""

import json

import click

from vts.artifacts.schemas import (
    BacktestReport, ExecutionPlan, MacroSnapshot, ResearchBrief, Viewpoint,
)
from vts.artifacts.store import ArtifactStore
from vts.orchestrator.pipeline import Pipeline


def _get_pipeline(artifacts_dir: str) -> Pipeline:
    store = ArtifactStore(base_dir=artifacts_dir)
    return Pipeline(store)


@click.group()
@click.version_option(package_name="vibe-trading-system")
@click.option("--artifacts-dir", default="artifacts", help="Artifact storage directory")
@click.pass_context
def cli(ctx, artifacts_dir):
    """vts - Five-stage US equity investment automation pipeline."""
    ctx.ensure_object(dict)
    ctx.obj["artifacts_dir"] = artifacts_dir


@cli.command()
@click.pass_context
def research(ctx):
    """Run the Research stage: fetch macro indicators and produce MacroSnapshot."""
    pipe = _get_pipeline(ctx.obj["artifacts_dir"])
    artifact_id = pipe.run_research()
    store = ArtifactStore(ctx.obj["artifacts_dir"])
    snapshot = store.load("snapshots", artifact_id, MacroSnapshot)
    click.echo(f"MacroSnapshot saved: {artifact_id}")
    click.echo(f"  Stance: {snapshot.stance.value}")
    click.echo(f"  VIX: {snapshot.vix}")
    click.echo(f"  10Y Treasury: {snapshot.treasury_10y}")


@cli.command()
@click.argument("ticker")
@click.option("--thesis", prompt=True, help="One-sentence investment thesis")
@click.option("--evidence", prompt=True, help="Key evidence (comma-separated, max 3)")
@click.option("--invalidation", prompt=True, help="What would collapse the thesis")
@click.option("--next-action", default="继续研究", help="继续研究/决策挑战/回测 setup/放弃")
@click.pass_context
def discover(ctx, ticker, thesis, evidence, invalidation, next_action):
    """Run the Discover stage: create a ResearchBrief for TICKER."""
    pipe = _get_pipeline(ctx.obj["artifacts_dir"])
    evidence_list = [e.strip() for e in evidence.split(",")]
    artifact_id = pipe.run_discover(
        ticker=ticker, thesis=thesis, key_evidence=evidence_list,
        invalidation=invalidation, next_action=next_action,
    )
    click.echo(f"ResearchBrief saved: {artifact_id}")


@cli.command()
@click.argument("ticker")
@click.pass_context
def viewpoint(ctx, ticker):
    """Run the Viewpoint stage: synthesize a comprehensive viewpoint for TICKER."""
    pipe = _get_pipeline(ctx.obj["artifacts_dir"])
    artifact_id = pipe.run_viewpoint(ticker=ticker)
    store = ArtifactStore(ctx.obj["artifacts_dir"])
    vp = store.load("viewpoints", artifact_id, Viewpoint)
    click.echo(f"Viewpoint saved: {artifact_id}")
    click.echo(f"  Direction: {vp.direction.value}")
    click.echo(f"  Confidence: {vp.confidence.value}")
    click.echo(f"  Counter-arguments: {len(vp.counter_arguments)}")


@cli.command()
@click.argument("ticker")
@click.pass_context
def plan(ctx, ticker):
    """Generate an ExecutionPlan for TICKER (requires Viewpoint)."""
    pipe = _get_pipeline(ctx.obj["artifacts_dir"])
    try:
        artifact_id = pipe.run_plan(ticker=ticker)
        store = ArtifactStore(ctx.obj["artifacts_dir"])
        ep = store.load("plans", artifact_id, ExecutionPlan)
        click.echo(f"ExecutionPlan saved: {artifact_id}")
        click.echo(f"  Direction: {ep.direction}")
        click.echo(f"  Status: {ep.approval_status.value}")
    except ValueError as e:
        click.echo(f"Cannot generate plan: {e}", err=True)


@cli.command()
@click.argument("plan_id")
@click.argument("action", type=click.Choice(["approve", "reject", "revise"]))
@click.option("--notes", default="", help="Review notes")
@click.pass_context
def review(ctx, plan_id, action, notes):
    """Review an ExecutionPlan: approve, reject, or revise."""
    pipe = _get_pipeline(ctx.obj["artifacts_dir"])
    pipe.review_plan(plan_id, action, notes)
    click.echo(f"Plan {plan_id} → {action}")


@cli.command()
@click.pass_context
def status(ctx):
    """Show current artifact counts and latest snapshot stance."""
    store = ArtifactStore(ctx.obj["artifacts_dir"])
    click.echo("Artifact counts:")
    for atype in ["snapshots", "briefs", "reports", "viewpoints", "plans"]:
        ids = store.list_ids(atype)
        click.echo(f"  {atype}: {len(ids)}")
    latest = store.latest("snapshots", MacroSnapshot)
    if latest:
        click.echo(f"\nLatest macro stance: {latest.stance.value} ({latest.date})")
