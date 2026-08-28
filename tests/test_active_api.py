from __future__ import annotations

from pathlib import Path

import httpx

from agentic_ai_statistics.api.app import create_app


async def test_health_describes_active_measurement_boundary(tmp_path: Path) -> None:
    app = create_app(
        agent_root=tmp_path / "phase3",
        behavior_root=tmp_path / "phase4",
        frontend_dist=tmp_path / "missing",
        serve_frontend=False,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["phase"] == "5"
    assert response.json()["measurement_boundary"] == "agent_model_and_stdio_mcp"


async def test_retired_phase_routes_are_absent(tmp_path: Path) -> None:
    app = create_app(
        agent_root=tmp_path / "phase3",
        behavior_root=tmp_path / "phase4",
        frontend_dist=tmp_path / "missing",
        serve_frontend=False,
    )
    retired_routes = (
        "/api/scenarios",
        "/api/runs",
        "/api/analysis/describe",
        "/api/phase2/runs",
        "/api/campaigns",
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        responses = [await client.get(path) for path in retired_routes]

    assert all(response.status_code in {404, 405} for response in responses)
