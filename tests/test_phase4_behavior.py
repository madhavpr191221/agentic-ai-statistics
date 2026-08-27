from __future__ import annotations

import json
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
import pytest

from mcp_traffic_analysis.api.app import create_app
from mcp_traffic_analysis.behavior.analysis import fit_count_models, fit_success_model
from mcp_traffic_analysis.behavior.campaigns import build_manifest, run_campaign
from mcp_traffic_analysis.behavior.traces import (
    normalized_oracle_distance,
    path_entropy,
    transitions,
)
from mcp_traffic_analysis.incidents.models import IncidentResult, IncidentScenario, TaskStructure
from mcp_traffic_analysis.incidents.runner import run_incident
from mcp_traffic_analysis.incidents.world import (
    SCENARIOS,
    apply_action,
    initial_state,
    load_state,
    observe,
    oracle_sequence,
    save_state,
    score_behavior,
)


@pytest.mark.parametrize("scenario", list(IncidentScenario))
@pytest.mark.parametrize("structure", list(TaskStructure))
async def test_every_behavior_cell_has_a_successful_five_call_oracle(
    tmp_path: Path, scenario: IncidentScenario, structure: TaskStructure
) -> None:
    detail = await run_incident(
        scenario=scenario,
        task_structure=structure,
        output_root=tmp_path,
        mode="deterministic",
    )
    assert detail.score.task_success
    assert detail.behavior is not None
    assert detail.behavior.execution_mode == "scripted_validation"
    assert detail.behavior.oracle_call_count == 5
    assert detail.behavior.observed_sequence == detail.behavior.oracle_sequence
    assert detail.behavior.excess_mcp_calls == 0
    assert detail.behavior.request_frame_bytes is None


def test_recovery_rejection_is_expected_and_retry_resolves(tmp_path: Path) -> None:
    scenario = IncidentScenario.IMAGE_WORKER_DEGRADATION
    definition = SCENARIOS[scenario]
    state_path = tmp_path / "state.json"
    save_state(state_path, initial_state(scenario, TaskStructure.RECOVERY))
    observe(state_path, "get_alert")
    observe(state_path, "search_logs")
    first = apply_action(state_path, definition.required_action, definition.required_target)
    assert first.expected_rejection
    assert not first.accepted
    observe(state_path, "get_runbook")
    second = apply_action(state_path, definition.required_action, definition.required_target)
    assert second.accepted
    assert not second.expected_rejection
    assert load_state(state_path)["resolved"] is True


def test_out_of_order_call_does_not_advance_sequential_world(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    save_state(
        state_path,
        initial_state(IncidentScenario.CHECKOUT_FAILURES, TaskStructure.SEQUENTIAL),
    )
    response = observe(state_path, "get_recent_changes")
    assert response["task_relevance"] == "non_material"
    assert load_state(state_path)["evidence_seen"] == []


def test_early_nonmaterial_runbook_does_not_open_action_gate(tmp_path: Path) -> None:
    scenario = IncidentScenario.CHECKOUT_FAILURES
    definition = SCENARIOS[scenario]
    state_path = tmp_path / "state.json"
    save_state(state_path, initial_state(scenario, TaskStructure.SEQUENTIAL))
    observe(state_path, "get_alert")
    observe(state_path, "get_runbook")
    observe(state_path, "get_metrics")
    observe(state_path, "get_recent_changes")
    action = apply_action(state_path, definition.required_action, definition.required_target)
    assert not action.accepted


def test_oom_is_a_valid_memory_saturation_diagnosis(tmp_path: Path) -> None:
    scenario = IncidentScenario.IMAGE_WORKER_DEGRADATION
    definition = SCENARIOS[scenario]
    state_path = tmp_path / "state.json"
    save_state(state_path, initial_state(scenario, TaskStructure.SEQUENTIAL))
    observe(state_path, "get_alert")
    observe(state_path, "get_metrics")
    observe(state_path, "search_logs")
    observe(state_path, "get_runbook")
    apply_action(state_path, definition.required_action, definition.required_target)
    state = load_state(state_path)
    result = IncidentResult(
        incident_id=scenario.value,
        diagnosis="image-worker-3 is under repeated OOM pressure",
        evidence_ids=list(state["evidence_seen"]),
        selected_action=definition.required_action,
        action_target=definition.required_target,
        resolution_summary="resolved",
    )
    assert score_behavior(state, result).task_success


def test_trace_metrics_have_auditable_small_examples() -> None:
    oracle = oracle_sequence(IncidentScenario.ORDERS_API_OUTAGE, TaskStructure.BRANCHING)
    assert normalized_oracle_distance(oracle, oracle) == 0
    assert normalized_oracle_distance(oracle + ["update_incident"], oracle) == pytest.approx(1 / 6)
    assert path_entropy([tuple(oracle), tuple(oracle)]) == 0
    assert path_entropy([("a",), ("b",)]) == 1
    assert transitions(["a", "b", "c"]) == [("a", "b"), ("b", "c")]


@pytest.mark.parametrize(("stage", "blocks", "runs"), [("pilot", 3, 27), ("main", 10, 90)])
def test_campaign_manifest_is_balanced(stage: str, blocks: int, runs: int) -> None:
    manifest = build_manifest("study-v1", stage)  # type: ignore[arg-type]
    assert manifest["blocks"] == blocks
    assert manifest["planned_runs"] == runs
    schedule = manifest["schedule"]
    for block in range(1, blocks + 1):
        cells = {
            (item["scenario_id"], item["task_structure"])
            for item in schedule
            if item["block"] == block
        }
        assert len(cells) == 9


async def test_deterministic_pilot_is_complete_and_reanalyzable(tmp_path: Path) -> None:
    path = await run_campaign(
        campaign_id="task-structure-pilot-test",
        study_stage="pilot",
        output_root=tmp_path,
        mode="deterministic",
        resume=False,
    )
    assert (path / "analysis.json").is_file()
    assert len(list(path.glob("incident-*/detail.json"))) == 27
    analysis = json.loads((path / "analysis.json").read_text(encoding="utf-8"))
    assert {row["unique_paths"] for row in analysis["condition_summaries"]} == {1}
    assert analysis["success_model"]["available"] is False
    resumed = await run_campaign(
        campaign_id="task-structure-pilot-test",
        study_stage="pilot",
        output_root=tmp_path,
        mode="deterministic",
        resume=True,
    )
    assert resumed == path


def test_poisson_sensitivity_recovers_known_call_ratios() -> None:
    calls = {"sequential": 5, "branching": 10, "recovery": 15}
    randomizer = np.random.default_rng(20260902)
    frame = pd.DataFrame(
        [
            {
                "mcp_call_count": max(1, int(randomizer.poisson(calls[structure]))),
                "task_structure": structure,
                "scenario_id": scenario,
                "block": block,
            }
            for block in range(1, 11)
            for scenario in ("checkout", "images", "orders")
            for structure in calls
        ]
    )
    models = fit_count_models(frame)
    rows = models["primary"]["coefficients"]
    effects = {row["term"]: row["effect_ratio"] for row in rows}
    adjusted = [row["p_value_holm"] for row in rows if "task_structure" in row["term"]]
    assert len(adjusted) == 2
    assert all(value is not None for value in adjusted)
    assert effects[
        "C(task_structure, Treatment(reference='sequential'))[T.branching]"
    ] == pytest.approx(2.0, rel=0.25)
    assert effects[
        "C(task_structure, Treatment(reference='sequential'))[T.recovery]"
    ] == pytest.approx(3.0, rel=0.25)


def test_success_model_accepts_boolean_outcome() -> None:
    scenarios = ("checkout", "images", "orders")
    structures = ("sequential", "branching", "recovery")
    frame = pd.DataFrame(
        [
            {
                "task_success": (block + scenario_index + structure_index) % 3 != 0,
                "task_structure": structure,
                "scenario_id": scenario,
                "block": block,
            }
            for block in range(1, 11)
            for scenario_index, scenario in enumerate(scenarios)
            for structure_index, structure in enumerate(structures)
        ]
    )
    assert fit_success_model(frame)["available"] is True


async def test_behavior_api_exposes_conditions_and_scripted_validation(tmp_path: Path) -> None:
    app = create_app(
        artifact_root=tmp_path / "phase1",
        campaign_root=tmp_path / "phase2",
        agent_root=tmp_path / "phase3",
        behavior_root=tmp_path / "phase4",
        frontend_dist=tmp_path / "missing",
        serve_frontend=False,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        conditions = await client.get("/api/behavior/conditions")
        created = await client.post(
            "/api/behavior/runs",
            json={
                "scenario": "orders_api_outage",
                "task_structure": "recovery",
                "mode": "deterministic",
            },
        )
        listed = await client.get("/api/behavior/runs")
    assert conditions.status_code == 200
    assert len(conditions.json()) == 9
    assert created.status_code == 201
    assert created.json()["behavior"]["execution_mode"] == "scripted_validation"
    assert created.json()["behavior"]["expected_rejections"] == 1
    assert len(listed.json()) == 1
