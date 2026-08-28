from __future__ import annotations

import sys
from pathlib import Path

import httpx
from agents.mcp import MCPServerStdio

from mcp_traffic_analysis.agent_campaigns import normalized_edit_distance, wilson
from mcp_traffic_analysis.api.app import create_app
from mcp_traffic_analysis.incidents.models import IncidentResult, IncidentScenario
from mcp_traffic_analysis.incidents.runner import run_incident
from mcp_traffic_analysis.incidents.world import (
    SCENARIOS,
    apply_action,
    initial_state,
    load_state,
    save_state,
    score,
)


def test_each_world_resets_and_requires_exact_remediation(tmp_path: Path) -> None:
    for scenario, definition in SCENARIOS.items():
        path = tmp_path / f"{scenario}.json"
        save_state(path, initial_state(scenario))
        wrong = apply_action(path, definition.required_action, "wrong-target")
        assert not wrong.accepted
        correct = apply_action(path, definition.required_action, definition.required_target)
        assert correct.accepted
        assert load_state(path)["resolved"] is True


def test_prohibited_action_is_not_erased_by_later_success(tmp_path: Path) -> None:
    scenario = IncidentScenario.ORDERS_API_OUTAGE
    definition = SCENARIOS[scenario]
    path = tmp_path / "state.json"
    save_state(path, initial_state(scenario))
    apply_action(path, "restart_service", "orders-api")
    apply_action(path, definition.required_action, definition.required_target)
    result = IncidentResult(
        incident_id=scenario.value,
        diagnosis=definition.hidden_cause,
        evidence_ids=list(definition.required_evidence_ids),
        selected_action=definition.required_action,
        action_target=definition.required_target,
        resolution_summary="resolved",
    )
    card = score(load_state(path), result)
    assert card.final_state_resolved
    assert not card.no_prohibited_action_attempted
    assert not card.task_success


async def test_deterministic_agent_path_writes_scored_artifact(tmp_path: Path) -> None:
    detail = await run_incident(
        scenario=IncidentScenario.CHECKOUT_FAILURES,
        output_root=tmp_path,
        mode="deterministic",
    )
    assert detail.score.task_success
    assert detail.measurement.status == "success"
    assert (tmp_path / f"incident-{detail.run_id}" / "detail.json").is_file()


async def test_incident_api_supports_credit_free_test_run(tmp_path: Path) -> None:
    app = create_app(
        agent_root=tmp_path / "phase3",
        frontend_dist=tmp_path / "missing",
        serve_frontend=False,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        scenarios = await client.get("/api/agent/scenarios")
        created = await client.post(
            "/api/agent/runs",
            json={"scenario": "image_worker_degradation", "mode": "deterministic"},
        )
        listed = await client.get("/api/agent/runs")
    assert scenarios.status_code == 200
    assert len(scenarios.json()) == 3
    assert created.status_code == 201
    assert created.json()["score"]["task_success"] is True
    assert len(listed.json()) == 1


def test_wilson_interval_and_trace_distance() -> None:
    low, high = wilson(8, 10)
    assert low < 0.8 < high
    assert normalized_edit_distance(["a", "b"], ["a", "c"]) == 0.5


async def test_incident_stdio_server_exposes_typed_tools(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    events = tmp_path / "events.jsonl"
    save_state(state, initial_state(IncidentScenario.CHECKOUT_FAILURES))
    server = MCPServerStdio(
        params={
            "command": sys.executable,
            "args": [
                "-m",
                "mcp_traffic_analysis.incidents.server",
                "--state",
                str(state),
                "--events",
                str(events),
            ],
        }
    )
    async with server:
        tools = await server.list_tools()
    names = {tool.name for tool in tools}
    assert names == {
        "get_alert",
        "get_metrics",
        "search_logs",
        "get_dependencies",
        "get_recent_changes",
        "get_runbook",
        "restart_service",
        "rollback_deployment",
        "escalate_incident",
        "update_incident",
    }
    restart = next(tool for tool in tools if tool.name == "restart_service")
    assert "target" in restart.inputSchema["properties"]
