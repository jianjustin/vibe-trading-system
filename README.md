# vibe-trading-system

Five-stage US equity investment automation pipeline.

```
Research → Discover → Backtest → Viewpoint → Plan → [Human Gate] → Manual Execution
```

## Stages

| Stage | Input | Output | Trigger |
|-------|-------|--------|---------|
| **Research** | Macro indicator APIs | `MacroSnapshot` | Weekly schedule |
| **Discover** | MacroSnapshot + watchlist | `ResearchBrief` | Weekly (1-2 tickers) |
| **Backtest** | ResearchBrief + OHLCV data | `BacktestReport` + run card | On-demand |
| **Viewpoint** | All upstream artifacts | `Viewpoint` | Auto (when inputs ready) |
| **Plan** | Viewpoint (confidence ≥ medium) | `ExecutionPlan` | Auto → human approval |

## Quick Start

```bash
pip install -e ".[dev]"
vts --help
```

## Boundaries

- No broker API integration. No auto-trading.
- ExecutionPlan requires human approval before manual order placement.
- AI provides frameworks, evidence, and counter-arguments; stage progression and trading decisions are made by the user.

## Architecture

Central orchestrator drives a DAG of five stage modules. Each stage produces typed artifacts (JSON + Markdown) stored locally. Artifacts can sync to an Obsidian vault. A lightweight frontend dashboard provides visualization and the human gate approval workflow.

## Tech Stack

- **Backend**: Python / FastAPI
- **Data**: yfinance / public APIs
- **Frontend**: Lightweight dashboard (TBD)
- **Scheduling**: Built-in scheduler
