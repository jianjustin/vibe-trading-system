"""CLI entry point for vibe-trading-system."""


import click

from vts.artifacts.schemas import (
    ExecutionPlan, MacroSnapshot, Viewpoint,
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


@cli.group()
def earnings():
    """Earnings data tools: SEC filing download and earnings calendar scan."""


@earnings.command("fetch")
@click.argument("ticker")
@click.option("--date", "target_date", default=None, help="财报日期 YYYY-MM-DD，下载该日期附近最近的 8-K（默认今天）")
@click.option("--years", type=int, default=None, help="批量模式：拉取过去 N 年的 filings")
@click.option("--since", default=None, help="批量模式：拉取该日期以来的 filings，如 2023-01-01")
@click.option("--form", "forms", default="8-K,10-Q", help="批量模式表单类型，逗号分隔（默认：8-K,10-Q）")
@click.option("--out", default="data/earnings_reports", help="输出根目录")
@click.option(
    "--user-agent", envvar="SEC_USER_AGENT", required=True,
    help="EDGAR User-Agent，格式 '名字 邮箱'（或设置环境变量 SEC_USER_AGENT）",
)
def earnings_fetch(ticker, target_date, years, since, forms, out, user_agent):
    """Download SEC earnings filings (8-K Exhibit 99.1 / 10-Q) for TICKER."""
    from datetime import date as date_cls, timedelta
    from pathlib import Path

    from vts.loaders.sec_loader import SECDownloader

    if years and since:
        raise click.UsageError("--years 和 --since 不能同时使用")
    if (years or since) and target_date:
        raise click.UsageError("--date 不能与 --years / --since 同时使用")

    sec = SECDownloader(user_agent=user_agent)
    ticker = ticker.upper()
    out_path = Path(out)

    if years or since:
        since_date = since or (date_cls.today() - timedelta(days=365 * years)).isoformat()
        form_types = [f.strip().upper() for f in forms.split(",") if f.strip()]
        paths = sec.download_filings_batch(ticker, form_types, since_date, out_path)
        click.echo(f"Downloaded {len(paths)} filing(s) to {out_path}/{ticker}/")
        for p in paths:
            click.echo(f"  {p}")
        if not paths:
            raise SystemExit(1)
        return

    target = target_date or date_cls.today().isoformat()
    path = sec.get_latest_8k_for_earnings(ticker, target, out_path)
    if path:
        click.echo(f"Downloaded: {path}")
    else:
        click.echo(f"No 8-K found for {ticker} around {target}", err=True)
        raise SystemExit(1)


@earnings.command("scan")
@click.argument("tickers", nargs=-1, required=True)
@click.option("--date", "target_date", default=None, help="目标日期 YYYY-MM-DD（默认今天）")
@click.option("--window", default=2, help="日期容差（± 天数，默认 2）")
def earnings_scan(tickers, target_date, window):
    """Scan TICKERS for earnings released around the target date."""
    from datetime import date as date_cls

    from vts.loaders.earnings_calendar import scan_watchlist

    target = target_date or date_cls.today().isoformat()
    hits = scan_watchlist([t.upper() for t in tickers], target, window_days=window)
    if hits:
        click.echo(f"Earnings near {target}: {', '.join(hits)}")
    else:
        click.echo(f"No earnings found near {target}")


@cli.command()
@click.option("--host", default="127.0.0.1", help="Bind host")
@click.option("--port", default=8000, type=int, help="Bind port")
@click.option("--frontend-dist", default="frontend/dist", help="Built dashboard directory")
@click.pass_context
def serve(ctx, host, port, frontend_dist):
    """Start the dashboard API server (serves frontend/dist if built)."""
    import uvicorn

    from vts.api.server import create_app
    from vts.artifacts.store import ArtifactStore

    store = ArtifactStore(base_dir=ctx.obj["artifacts_dir"])
    app = create_app(store=store, frontend_dist=frontend_dist)
    uvicorn.run(app, host=host, port=port)


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
