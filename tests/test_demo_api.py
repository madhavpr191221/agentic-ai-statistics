from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx

from mcp_traffic_analysis.api.app import create_app


@asynccontextmanager
async def make_client(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(
        artifact_root=tmp_path / "runs",
        campaign_root=tmp_path / "campaigns",
        frontend_dist=tmp_path / "missing-frontend",
        serve_frontend=False,
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_health_and_scenario_catalog(tmp_path: Path) -> None:
    async with make_client(tmp_path) as client:
        health = await client.get("/api/health")
        scenarios = await client.get("/api/scenarios")

    assert health.status_code == 200
    assert health.json()["measurement_boundary"] == "application_and_stdio_transport"
    assert len(scenarios.json()) == 9
    assert {item["id"] for item in scenarios.json()} >= {"echo", "concurrent", "timeout"}


async def test_create_list_inspect_and_analyze_run(tmp_path: Path) -> None:
    async with make_client(tmp_path) as client:
        created = await client.post(
            "/api/runs",
            json={"scenario": "echo", "repeat": 2, "seed": 42},
        )
        run_id = created.json()["manifest"]["run_id"]
        listed = await client.get("/api/runs")
        detail = await client.get(f"/api/runs/{run_id}")
        events = await client.get(f"/api/runs/{run_id}/events")
        analysis = await client.post(
            "/api/analysis/describe",
            json={"run_ids": [run_id], "unit": "call"},
        )

    assert created.status_code == 201
    assert created.json()["summary"]["tool_call_count"] == 2
    assert len(listed.json()["runs"]) == 1
    assert detail.status_code == 200
    assert len(events.json()["events"]) == 8
    body = analysis.json()
    assert analysis.status_code == 200
    assert body["metric"] == "server_handler_latency_ms"
    assert body["distribution"]["summary"]["count"] == 4
    assert sum(item["count"] for item in body["distribution"]["histogram"]) == 4
    assert "Calls are nested observations within runs" in body["notes"][0]


async def test_failure_classification_reaches_analysis(tmp_path: Path) -> None:
    async with make_client(tmp_path) as client:
        created = await client.post(
            "/api/runs",
            json={"scenario": "backend_exception", "repeat": 1, "seed": 1},
        )
        run_id = created.json()["manifest"]["run_id"]
        analysis = await client.post(
            "/api/analysis/describe",
            json={"run_ids": [run_id], "unit": "call"},
        )

    assert created.status_code == 201
    assert created.json()["summary"]["failed_span_count"] == 1
    assert analysis.json()["error_counts"] == {"backend_exception": 1}


async def test_run_level_analysis_does_not_sum_overlapping_spans(tmp_path: Path) -> None:
    async with make_client(tmp_path) as client:
        created = await client.post(
            "/api/runs",
            json={"scenario": "concurrent", "repeat": 1, "seed": 2},
        )
        run_id = created.json()["manifest"]["run_id"]
        analysis = await client.post(
            "/api/analysis/describe",
            json={"run_ids": [run_id], "unit": "run"},
        )

    body = analysis.json()
    assert body["metric"] == "observed_trace_window_ms"
    assert body["distribution"]["summary"]["count"] == 1
    assert "does not sum overlapping span durations" in body["notes"][1]


async def test_unknown_and_malformed_run_identifiers_are_rejected(tmp_path: Path) -> None:
    async with make_client(tmp_path) as client:
        missing = await client.get(f"/api/runs/{uuid4()}")
        malformed = await client.get("/api/runs/../../.env")

    assert missing.status_code == 404
    assert malformed.status_code in {404, 422}


async def test_phase2_stdio_run_exposes_exact_frame_measurements(tmp_path: Path) -> None:
    async with make_client(tmp_path) as client:
        response = await client.post(
            "/api/phase2/runs",
            json={
                "transport": "stdio",
                "payload_target_bytes": 64,
                "service_time_ms": 0,
                "concurrency": 1,
                "calls_per_run": 2,
                "seed": 9,
            },
        )
    assert response.status_code == 201
    body = response.json()
    assert len(body["calls"]) == 2
    assert body["total_request_frame_bytes"] > 128
    assert body["total_response_frame_bytes"] > 128
    assert all(call["server_handler_ms"] is not None for call in body["calls"])


async def test_campaign_catalog_reads_persisted_results(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from mcp_traffic_analysis.campaigns import build_manifest
    from mcp_traffic_analysis.experiments.campaign_models import CampaignProgress

    campaign = tmp_path / "campaigns" / "tiny"
    campaign.mkdir(parents=True)
    manifest = build_manifest(campaign_id="tiny", replicates=1, calls_per_run=1, seed=1)
    progress = CampaignProgress(
        campaign_id="tiny",
        status="complete",
        planned_runs=48,
        completed_runs=48,
        updated_at_utc=datetime.now(UTC),
    )
    (campaign / "campaign_manifest.json").write_text(manifest.model_dump_json())
    (campaign / "progress.json").write_text(progress.model_dump_json())
    (campaign / "analysis.json").write_text('{"experimental_unit":"run"}')
    async with make_client(tmp_path) as client:
        listed = await client.get("/api/campaigns")
        detail = await client.get("/api/campaigns/tiny")
    assert listed.json()["campaigns"][0]["completed_runs"] == 48
    assert detail.json()["analysis"]["experimental_unit"] == "run"
