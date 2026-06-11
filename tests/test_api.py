import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from vts.api.server import create_app
from vts.artifacts.schemas import ViewpointDirection, Confidence


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=250, freq="B")
    prices = 100 + np.cumsum(np.random.randn(250) * 1.5)
    ohlcv = pd.DataFrame(
        {
            "open": prices, "high": prices + 1, "low": prices - 1,
            "close": prices, "volume": [1_000_000] * 250,
        },
        index=dates,
    )
    loader.fetch_macro_indicators.return_value = {
        "treasury_10y": {"latest": 4.28, "data": ohlcv},
        "vix": {"latest": 15.0, "data": ohlcv},
        "dxy": {"latest": 104.0, "data": ohlcv},
        "spy": {"latest": 540.0, "data": ohlcv},
        "qqq": {"latest": 470.0, "data": ohlcv},
        "hyg": {"latest": 78.0, "data": ohlcv},
    }
    loader.compute_ma_status.return_value = {50: True, 200: True}
    loader.fetch_ohlcv.return_value = ohlcv
    return loader


@pytest.fixture
def client(store, mock_loader):
    app = create_app(store=store, loader=mock_loader)
    return TestClient(app)


def test_status_empty(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["counts"] == {
        "snapshots": 0, "briefs": 0, "reports": 0, "viewpoints": 0, "plans": 0,
    }
    assert body["latest_stance"] is None


def test_run_research(client):
    resp = client.post("/api/stages/research/run")
    assert resp.status_code == 200
    body = resp.json()
    assert body["artifact_type"] == "snapshots"
    assert body["artifact"]["vix"] == 15.0
    # OFFENSIVE: vix < 18 and both above 50d MA
    assert body["artifact"]["stance"] == "进攻"


def test_run_discover(client):
    resp = client.post("/api/stages/discover/run", json={
        "ticker": "TSLA",
        "thesis": "EV leader",
        "key_evidence": ["deliveries beat", "margin expansion"],
        "invalidation": "two consecutive delivery misses",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["artifact_id"] == "TSLA"
    assert body["artifact"]["thesis"] == "EV leader"


def test_discover_validation_error(client):
    resp = client.post("/api/stages/discover/run", json={"ticker": "TSLA"})
    assert resp.status_code == 422


def test_list_backtest_rules(client):
    resp = client.get("/api/backtest/rules")
    assert resp.status_code == 200
    rules = resp.json()
    names = [r["name"] for r in rules]
    assert "ma_cross_20_60" in names
    for r in rules:
        assert r["entry_rule"]
        assert r["exit_rule"]


def test_run_backtest_with_named_rule(client):
    resp = client.post("/api/stages/backtest/run", json={
        "ticker": "TSLA",
        "rule": "ma_cross_20_60",
        "start_date": "2024-01-01",
        "end_date": "2025-01-01",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["artifact_id"] == "TSLA-ma_cross_20_60"
    assert "sample_count" in body["artifact"]


def test_run_backtest_unknown_rule(client):
    resp = client.post("/api/stages/backtest/run", json={
        "ticker": "TSLA", "rule": "nonexistent",
    })
    assert resp.status_code == 400


def test_run_viewpoint_requires_brief(client):
    resp = client.post("/api/stages/viewpoint/run", json={"ticker": "TSLA"})
    assert resp.status_code == 409


def test_full_pipeline_via_api(client):
    client.post("/api/stages/research/run")
    client.post("/api/stages/discover/run", json={
        "ticker": "TSLA",
        "thesis": "EV leader",
        "key_evidence": ["deliveries beat"],
        "invalidation": "delivery misses",
    })
    resp = client.post("/api/stages/viewpoint/run", json={"ticker": "TSLA"})
    assert resp.status_code == 200
    assert resp.json()["artifact"]["ticker"] == "TSLA"


def test_run_plan_and_review(client, store, sample_viewpoint):
    vp = sample_viewpoint.model_copy(update={
        "ticker": "TSLA",
        "direction": ViewpointDirection.BULLISH,
        "confidence": Confidence.MEDIUM,
    })
    store.save(vp, "viewpoints", "TSLA")

    resp = client.post("/api/stages/plan/run", json={"ticker": "TSLA"})
    assert resp.status_code == 200
    assert resp.json()["artifact"]["approval_status"] == "pending_review"

    resp = client.post("/api/plans/TSLA/review", json={
        "action": "approve", "notes": "looks good",
    })
    assert resp.status_code == 200
    assert resp.json()["artifact"]["approval_status"] == "approved"
    assert resp.json()["artifact"]["approved_at"] is not None


def test_plan_rejected_for_low_confidence(client, store, sample_viewpoint):
    vp = sample_viewpoint.model_copy(update={
        "ticker": "TSLA", "confidence": Confidence.LOW,
    })
    store.save(vp, "viewpoints", "TSLA")
    resp = client.post("/api/stages/plan/run", json={"ticker": "TSLA"})
    assert resp.status_code == 409


def test_review_invalid_action(client, store, sample_plan):
    store.save(sample_plan, "plans", "TSLA")
    resp = client.post("/api/plans/TSLA/review", json={"action": "destroy"})
    assert resp.status_code == 422


def test_list_artifacts(client, store, sample_brief):
    store.save(sample_brief, "briefs", "TSLA.US")
    resp = client.get("/api/artifacts/briefs")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == "TSLA.US"
    assert items[0]["data"]["ticker"] == "TSLA.US"


def test_get_artifact_not_found(client):
    resp = client.get("/api/artifacts/briefs/NOPE")
    assert resp.status_code == 404


def test_unknown_artifact_type(client):
    resp = client.get("/api/artifacts/bogus")
    assert resp.status_code == 404


def test_cli_has_serve_command():
    from click.testing import CliRunner

    from vts.cli.main import cli

    result = CliRunner().invoke(cli, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output
