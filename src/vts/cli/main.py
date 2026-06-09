"""CLI entry point for vibe-trading-system."""

import click


@click.group()
@click.version_option(package_name="vibe-trading-system")
def cli():
    """vts - Five-stage US equity investment automation pipeline."""


@cli.command()
def research():
    """Run the Research stage: fetch macro indicators and produce MacroSnapshot."""
    click.echo("Research stage — not yet implemented")


@cli.command()
@click.argument("ticker")
def discover(ticker: str):
    """Run the Discover stage: generate ResearchBrief for a ticker."""
    click.echo(f"Discover stage for {ticker} — not yet implemented")


@cli.command()
@click.argument("ticker")
@click.argument("setup")
def backtest(ticker: str, setup: str):
    """Run the Backtest stage: historical validation for a setup."""
    click.echo(f"Backtest stage for {ticker}/{setup} — not yet implemented")


@cli.command()
@click.argument("ticker")
def viewpoint(ticker: str):
    """Run the Viewpoint stage: synthesize a comprehensive viewpoint."""
    click.echo(f"Viewpoint stage for {ticker} — not yet implemented")


@cli.command()
@click.argument("ticker")
def plan(ticker: str):
    """Run the Plan stage: generate execution plan for human review."""
    click.echo(f"Plan stage for {ticker} — not yet implemented")


@cli.command()
def pipeline():
    """Run the full five-stage pipeline end-to-end."""
    click.echo("Full pipeline — not yet implemented")


@cli.command()
def sync():
    """Sync artifacts to Obsidian vault."""
    click.echo("Vault sync — not yet implemented")
