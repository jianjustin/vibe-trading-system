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
| **Backtest** | ResearchBrief + OHLCV data | `BacktestReport` | On-demand |
| **Viewpoint** | All upstream artifacts | `Viewpoint` | Auto (when inputs ready) |
| **Plan** | Viewpoint (confidence ≥ medium) | `ExecutionPlan` | Auto → human approval |

## Prerequisites

- **Python** >= 3.11 (tested with 3.14)
- **Node.js** >= 20 (for the dashboard frontend)
- **pip** (or any compatible installer)

## Quick Start

### 1. Install the Python package

```bash
git clone <repo-url> && cd vibe-trading-system

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
vts --help
```

### 2. Build the dashboard frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 3. Start the server

```bash
vts serve
# → http://127.0.0.1:8000
```

This starts the FastAPI backend and serves the built frontend. Open the URL in
your browser to access the dashboard.

Options:

```
vts serve --host 0.0.0.0 --port 3000          # custom bind
vts serve --artifacts-dir /path/to/artifacts   # custom artifact storage
```

### 4. Run the pipeline

You can run each stage from the **dashboard** (click the buttons), or from the
**CLI**:

```bash
# 1. Research — fetch live macro indicators from yfinance
vts research

# 2. Discover — register a research brief
vts discover TSLA \
  --thesis "EV leader with strong delivery momentum" \
  --evidence "Q1 deliveries beat,margin expansion,FSD revenue" \
  --invalidation "two consecutive delivery misses"

# 3. Backtest — run via the API (signal rules are predefined)
curl -X POST http://127.0.0.1:8000/api/stages/backtest/run \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"TSLA","rule":"ma_cross_20_60"}'

# 4. Viewpoint — synthesize all upstream artifacts
vts viewpoint TSLA

# 5. Plan + approval
vts plan TSLA
vts review TSLA approve --notes "confirmed entry conditions"

# Check overall status
vts status
```

### 5. Run the tests

```bash
pytest -v            # all tests (73 expected)
pytest tests/test_api.py -v   # API tests only
```

## Dashboard

The dashboard (Vite + React + TypeScript + Tailwind CSS v4) provides:

- **Status bar** — current market stance badge (进攻/谨慎/防守) and artifact counts
- **Stage cards** — one card per pipeline stage with input forms and run buttons
- **Artifact browser** — tabbed panel to browse all five artifact types
- **Plan review** — inline approve/reject/revise buttons for pending execution plans

For frontend development with hot reload, run `vts serve` in one terminal and
`cd frontend && npm run dev` in another. Vite proxies `/api` requests to port 8000.

## API Reference

All endpoints are under `/api`. The server also serves the built frontend at `/`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/status` | Artifact counts + latest macro stance |
| `GET` | `/api/backtest/rules` | List available signal rules for backtests |
| `POST` | `/api/stages/research/run` | Run Research stage |
| `POST` | `/api/stages/discover/run` | Run Discover stage (body: `ticker`, `thesis`, `key_evidence`, `invalidation`) |
| `POST` | `/api/stages/backtest/run` | Run Backtest stage (body: `ticker`, `rule`, optional `start_date`, `end_date`) |
| `POST` | `/api/stages/viewpoint/run` | Run Viewpoint stage (body: `ticker`) |
| `POST` | `/api/stages/plan/run` | Generate ExecutionPlan (body: `ticker`) |
| `POST` | `/api/plans/{id}/review` | Review a plan (body: `action`: approve/reject/revise, `notes`) |
| `GET` | `/api/artifacts/{type}` | List all artifacts of a type (snapshots/briefs/reports/viewpoints/plans) |
| `GET` | `/api/artifacts/{type}/{id}` | Get a single artifact by ID |

## Project Structure

```
src/vts/
├── api/            # FastAPI server (REST endpoints)
├── artifacts/      # Pydantic schemas + file-based JSON store
├── backtest/       # Engine, metrics, named signal rules
├── cli/            # Click CLI (vts command)
├── loaders/        # yfinance data loader, SEC EDGAR downloader
├── orchestrator/   # Pipeline class wiring stages together
└── stages/         # Five stage modules (research/discover/backtest/viewpoint/plan)

frontend/           # Vite + React + TypeScript + Tailwind v4
├── src/
│   ├── components/ # StageCard, PipelineStages, ArtifactBrowser
│   └── lib/        # Typed API client
└── dist/           # Production build (gitignored)

artifacts/          # JSON artifact storage (gitignored)
├── snapshots/      # MacroSnapshot
├── briefs/         # ResearchBrief
├── reports/        # BacktestReport
├── viewpoints/     # Viewpoint
└── plans/          # ExecutionPlan

docs/stages/        # Per-stage operation guides (Chinese)
tests/              # pytest suite (73 tests)
```

## Boundaries

- No broker API integration. No auto-trading.
- ExecutionPlan requires human approval before manual order placement.
- AI provides frameworks, evidence, and counter-arguments; stage progression and trading decisions are made by the user.

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI / Pydantic v2
- **Data**: yfinance / SEC EDGAR (public APIs, no keys needed)
- **Frontend**: Vite + React + TypeScript + Tailwind CSS v4
- **CLI**: Click
- **Testing**: pytest + ruff
