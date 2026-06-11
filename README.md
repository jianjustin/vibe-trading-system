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

### Dashboard

```bash
# build the frontend once (requires Node >= 20)
cd frontend && npm install && npm run build && cd ..

# start the API server + dashboard at http://127.0.0.1:8000
vts serve
```

The dashboard (Vite + React + TypeScript + Tailwind) lets you manually run every
pipeline stage, inspect all artifacts, and approve/reject/revise execution plans.
Backtests run against named signal rules from `src/vts/backtest/signals.py`
(`GET /api/backtest/rules` lists them).

For frontend development with hot reload: `vts serve` in one terminal,
`cd frontend && npm run dev` in another (Vite proxies `/api` to port 8000).

## Boundaries

- No broker API integration. No auto-trading.
- ExecutionPlan requires human approval before manual order placement.
- AI provides frameworks, evidence, and counter-arguments; stage progression and trading decisions are made by the user.

## Architecture

Central orchestrator drives a DAG of five stage modules. Each stage produces typed artifacts (JSON + Markdown) stored locally. Artifacts can sync to an Obsidian vault. A lightweight frontend dashboard provides visualization and the human gate approval workflow.

## Tech Stack

- **Backend**: Python / FastAPI
- **Data**: yfinance / public APIs
- **Frontend**: Vite + React + TypeScript + Tailwind CSS (`frontend/`)
- **Scheduling**: Built-in scheduler
