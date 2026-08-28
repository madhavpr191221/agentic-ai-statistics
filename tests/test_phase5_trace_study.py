from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

import agentic_ai_statistics.trace_study.campaigns as campaign_module
from agentic_ai_statistics.api.app import create_app
from agentic_ai_statistics.incidents.models import (
    ActionRecord,
    BehaviorMetadata,
    IncidentRunDetail,
    IncidentRunMeasurement,
    IncidentScenario,
    ScoreCard,
    TaskStructure,
)
from agentic_ai_statistics.incidents.world import oracle_sequence
from agentic_ai_statistics.trace_study.analysis import (
    analyze_details,
    bootstrap_entropy_interval,
    bootstrap_interval,
    first_oracle_divergence,
    fisher_exact_two_sided,
    plugin_entropy,
    post_rejection_behavior,
    repeated_tool_count,
    scalar_distributions,
    state_sequence,
    wilson_interval,
)
from agentic_ai_statistics.trace_study.campaigns import (
    analyze_collected_campaign,
    build_manifest,
    configuration_fingerprint,
    cost_limit_reached,
    frozen_configuration,
    is_scientific_observation,
    quarantine_excluded_attempt,
    quarantine_incomplete_run,
    run_campaign,
)


def _detail(*, success: bool, read_runbook_first: bool) -> IncidentRunDetail:
    run_id = uuid4()
    oracle = oracle_sequence(IncidentScenario.ORDERS_API_OUTAGE, TaskStructure.RECOVERY)
    tools = (
        oracle
        if read_runbook_first
        else ["get_alert", "get_dependencies", "escalate_incident", "escalate_incident"]
    )
    now = datetime.now(UTC)
    actions = [
        ActionRecord(
            sequence=0,
            timestamp_utc=now,
            action="escalate_incident",
            target="identity-service-owner",
            accepted=False,
            prohibited=False,
            expected_rejection=True,
            result="consult runbook",
        ),
        ActionRecord(
            sequence=1,
            timestamp_utc=now,
            action="escalate_incident",
            target="identity-service-owner",
            accepted=success,
            prohibited=False,
            expected_rejection=False,
            result="resolved" if success else "rejected",
        ),
    ]
    score = ScoreCard(
        diagnosis_correct=success,
        required_evidence_present=success,
        correct_remediation_executed=success,
        no_prohibited_action_attempted=True,
        final_state_resolved=success,
        task_success=success,
    )
    measurement = IncidentRunMeasurement(
        run_id=run_id,
        scenario_id=IncidentScenario.ORDERS_API_OUTAGE,
        status="success" if success else "failure",
        failure_type=None if success else "task_failure",
        total_latency_ms=100,
        model_latency_ms=80,
        mcp_latency_ms=10,
        server_handler_latency_ms=2,
        orchestration_latency_ms=10,
        decomposition_consistent=True,
        correlation_consistent=True,
        model_call_count=2,
        mcp_call_count=len(tools),
        tool_sequence=tools,
        input_tokens=100,
        cached_input_tokens=0,
        output_tokens=20,
        total_tokens=120,
        request_frame_bytes=400,
        response_frame_bytes=800,
        estimated_cost_usd=0.01,
    )
    behavior = BehaviorMetadata(
        task_structure=TaskStructure.RECOVERY,
        incoming_message="Orders fail",
        oracle_sequence=oracle,
        observed_sequence=tools,
        oracle_call_count=5,
        excess_mcp_calls=0 if success else None,
        normalized_oracle_distance=0 if success else 0.25,
        expected_rejections=1,
        unexpected_rejections=0 if success else 1,
        trace_steps=[],
        execution_mode="live_measurement",
        request_frame_bytes=400,
        response_frame_bytes=800,
        block=1,
        execution_order=1,
    )
    return IncidentRunDetail(
        run_id=run_id,
        scenario_id=IncidentScenario.ORDERS_API_OUTAGE,
        created_at_utc=now,
        model_id="test-model",
        measurement=measurement,
        result=None,
        score=score,
        actions=actions,
        agent_events=[],
        behavior=behavior,
    )


def test_trace_states_keep_action_results_and_terminal_outcome() -> None:
    success = state_sequence(_detail(success=True, read_runbook_first=True))
    failure = state_sequence(_detail(success=False, read_runbook_first=False))
    assert success == [
        "START",
        "get_alert|observed",
        "get_dependencies|observed",
        "escalate_incident|expected_rejection",
        "get_runbook|observed",
        "escalate_incident|accepted",
        "END_SUCCESS",
    ]
    assert failure[-2:] == ["escalate_incident|unexpected_rejection", "END_FAILURE"]
    assert post_rejection_behavior(success) == "read_runbook_first"
    assert post_rejection_behavior(failure) == "retried_first"


def test_trace_state_construction_rejects_action_ledger_mismatch() -> None:
    detail = _detail(success=True, read_runbook_first=True).model_copy(
        update={"actions": []}
    )
    with pytest.raises(ValueError, match="action ledger is missing"):
        state_sequence(detail)


def test_small_trace_statistics_are_hand_checkable() -> None:
    assert first_oracle_divergence(["a", "x"], ["a", "b", "c"]) == 2
    assert first_oracle_divergence(["a", "b"], ["a", "b"]) is None
    assert repeated_tool_count(["a", "b", "a", "a"]) == 2
    assert plugin_entropy(["path-a", "path-b"]) == 1
    assert bootstrap_entropy_interval(["a", "a", "b"], repetitions=100, seed=7) == (
        bootstrap_entropy_interval(["a", "a", "b"], repetitions=100, seed=7)
    )
    interval = wilson_interval(0, 5)
    assert interval is not None
    assert interval[1] == pytest.approx(0.434482, rel=1e-5)
    assert fisher_exact_two_sided(5, 0, 0, 5) == pytest.approx(0.0079365079)


def test_primary_table_connects_behavior_to_failure() -> None:
    details = [
        *[_detail(success=True, read_runbook_first=True) for _ in range(5)],
        *[_detail(success=False, read_runbook_first=False) for _ in range(5)],
    ]
    analysis, tables = analyze_details(
        details, campaign_id="small-example", study_stage="test"
    )
    primary = analysis["post_rejection_analysis"]
    assert primary["counts"]["read_runbook_first"] == {"success": 5, "failure": 0}
    assert primary["counts"]["retried_first"] == {"success": 0, "failure": 5}
    assert primary["failure_risk_difference_retry_minus_read"] == 1
    assert primary["failure_risk_difference_newcombe_95"] == pytest.approx(
        [0.3855490057, 1.0]
    )
    assert len(tables["traces"]) == 10
    assert len(tables["post_rejection_outcomes"]) == 10


def test_secondary_summaries_reconcile_to_run_and_call_totals() -> None:
    details = [
        *[_detail(success=True, read_runbook_first=True) for _ in range(5)],
        *[_detail(success=False, read_runbook_first=False) for _ in range(5)],
    ]
    analysis, tables = analyze_details(
        details, campaign_id="secondary-example", study_stage="test"
    )

    assert sum(row["n_runs"] for row in analysis["prefix_outcomes"]) == 10
    assert sum(row["invocations"] for row in analysis["tool_usage"]) == sum(
        detail.measurement.mcp_call_count for detail in details
    )
    assert {row["outcome"] for row in analysis["divergence_by_outcome"]} == {
        "success",
        "failure",
    }
    assert len(analysis["latency_decomposition"]) == 4
    assert len(tables["tool_usage"]) > 0
    assert len(tables["latency_components"]) == 4
    assert len(tables["prefix_outcomes"]) == 4


def test_frozen_main_manifest_has_ten_batches_of_ten() -> None:
    manifest = build_manifest("trace-main-v1", "main")
    assert manifest["planned_runs"] == 100
    assert manifest["planned_batches"] == 10
    assert len({item["run_id"] for item in manifest["schedule"]}) == 100
    assert {item["batch"] for item in manifest["schedule"]} == set(range(1, 11))
    assert manifest["configuration_fingerprint_sha256"] == configuration_fingerprint()
    assert len(configuration_fingerprint()) == 64
    definition = frozen_configuration()["scenario_definition"]
    assert definition["required_evidence_ids"] == sorted(definition["required_evidence_ids"])


def test_cost_guard_applies_only_to_live_collection() -> None:
    assert cost_limit_reached(5.0, 5.0, "live")
    assert not cost_limit_reached(4.99, 5.0, "live")
    assert not cost_limit_reached(10.0, 5.0, "deterministic")


def test_interrupted_run_is_preserved_before_retry(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    incomplete = campaign / "incident-run-1"
    incomplete.mkdir(parents=True)
    (incomplete / "world_state.json").write_text("{}", encoding="utf-8")
    destination = quarantine_incomplete_run(campaign, "run-1")
    assert destination is not None
    assert not incomplete.exists()
    assert (destination / "world_state.json").is_file()
    assert quarantine_incomplete_run(campaign, "run-1") is None


def test_provider_failure_is_excluded_and_preserved(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign-trace-test"
    failed = _detail(success=False, read_runbook_first=False)
    failed = failed.model_copy(
        update={
            "measurement": failed.measurement.model_copy(
                update={"failure_type": "RateLimitError", "mcp_call_count": 0}
            )
        }
    )
    run_directory = campaign / f"incident-{failed.run_id}"
    run_directory.mkdir(parents=True)
    (run_directory / "detail.json").write_text(
        failed.model_dump_json(), encoding="utf-8"
    )

    assert not is_scientific_observation(failed)
    destination = quarantine_excluded_attempt(campaign, str(failed.run_id))
    assert destination is not None
    assert not run_directory.exists()
    assert (destination / "detail.json").is_file()
    assert quarantine_excluded_attempt(campaign, str(failed.run_id)) is None


def test_campaign_analysis_reports_but_does_not_analyze_provider_failures(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "campaign-trace-test"
    campaign.mkdir()
    manifest = build_manifest("trace-test", "smoke")
    (campaign / "campaign_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    valid = _detail(success=False, read_runbook_first=False)
    excluded = _detail(success=False, read_runbook_first=False)
    excluded = excluded.model_copy(
        update={
            "measurement": excluded.measurement.model_copy(
                update={"failure_type": "RateLimitError"}
            )
        }
    )
    for detail in (valid, excluded):
        run_directory = campaign / f"incident-{detail.run_id}"
        run_directory.mkdir()
        (run_directory / "detail.json").write_text(
            detail.model_dump_json(), encoding="utf-8"
        )

    analysis = analyze_collected_campaign(campaign)

    assert analysis["n_runs"] == 1
    assert analysis["campaign_complete"] is False
    assert analysis["excluded_attempts"] == 1
    assert analysis["excluded_provider_attempts"] == 1
    assert analysis["excluded_measurement_attempts"] == 0
    assert analysis["excluded_provider_failure_types"] == {"RateLimitError": 1}
    assert analysis["scientific_estimated_cost_usd"] == pytest.approx(0.01)
    assert analysis["excluded_attempt_estimated_cost_usd"] == pytest.approx(0.01)
    assert analysis["total_estimated_cost_usd"] == pytest.approx(0.02)


async def test_deterministic_campaign_is_resumable_and_rejects_config_mismatch(
    tmp_path: Path,
) -> None:
    path = await run_campaign(
        campaign_id="trace-smoke-test",
        study_stage="smoke",
        output_root=tmp_path,
        mode="deterministic",
        planned_runs=2,
    )
    analysis = json.loads((path / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["campaign_complete"] is True
    assert analysis["n_runs"] == 2
    resumed = await run_campaign(
        campaign_id="trace-smoke-test",
        study_stage="smoke",
        output_root=tmp_path,
        mode="deterministic",
        resume=True,
    )
    assert resumed == path

    manifest_path = path / "campaign_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["configuration_fingerprint_sha256"] = "changed"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="configuration changed"):
        await run_campaign(
            campaign_id="trace-smoke-test",
            study_stage="smoke",
            output_root=tmp_path,
            mode="deterministic",
            resume=True,
        )


async def test_live_resume_rejects_nonprotocol_sample_size(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign-trace-live-test"
    campaign.mkdir()
    manifest = build_manifest("trace-live-test", "smoke", planned_runs=2, mode="live")
    (campaign / "campaign_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="size differs"):
        await run_campaign(
            campaign_id="trace-live-test",
            study_stage="smoke",
            output_root=tmp_path,
            mode="live",
            resume=True,
        )


async def test_provider_failure_stops_campaign_immediately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    async def fail_once(**kwargs: object) -> IncidentRunDetail:
        nonlocal calls
        calls += 1
        run_id = kwargs["run_id"]
        assert not isinstance(run_id, str)
        detail = _detail(success=False, read_runbook_first=False)
        detail = detail.model_copy(
            update={
                "run_id": run_id,
                "measurement": detail.measurement.model_copy(
                    update={"run_id": run_id, "failure_type": "RateLimitError"}
                ),
            }
        )
        run_directory = tmp_path / "campaign-provider-stop" / f"incident-{run_id}"
        run_directory.mkdir(parents=True)
        (run_directory / "detail.json").write_text(
            detail.model_dump_json(), encoding="utf-8"
        )
        return detail

    monkeypatch.setattr(campaign_module, "run_incident", fail_once)
    path = await run_campaign(
        campaign_id="provider-stop",
        study_stage="smoke",
        output_root=tmp_path,
        mode="live",
    )
    progress = json.loads((path / "progress.json").read_text(encoding="utf-8"))
    analysis = json.loads((path / "analysis.json").read_text(encoding="utf-8"))

    assert calls == 1
    assert progress["status"] == "provider_failure"
    assert progress["completed_runs"] == 0
    assert analysis["n_runs"] == 0
    assert analysis["excluded_provider_attempts"] == 1


async def test_trace_study_api_lists_details_and_allowlisted_tables(tmp_path: Path) -> None:
    root = tmp_path / "phase5"
    campaign = root / "campaign-study-v1"
    tables = campaign / "tables"
    tables.mkdir(parents=True)
    (campaign / "analysis.json").write_text(
        json.dumps({"campaign_id": "study-v1", "created_at_utc": "2026-01-01"}),
        encoding="utf-8",
    )
    (tables / "paths.csv").write_text("count\n1\n", encoding="utf-8")
    (tables / "tool_usage.csv").write_text("tool_name\nget_alert\n", encoding="utf-8")
    (campaign / "q02_scalar_distributions.json").write_text("{}", encoding="utf-8")
    (campaign / "q09_q14_trajectory_analysis.json").write_text("{}", encoding="utf-8")
    app = create_app(
        agent_root=tmp_path / "phase3",
        behavior_root=tmp_path / "phase4",
        trace_study_root=root,
        frontend_dist=tmp_path / "missing",
        serve_frontend=False,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        listed = await client.get("/api/trace-study/campaigns")
        detail = await client.get("/api/trace-study/campaigns/study-v1")
        table = await client.get("/api/trace-study/campaigns/study-v1/tables/paths.csv")
        secondary = await client.get(
            "/api/trace-study/campaigns/study-v1/tables/tool_usage.csv"
        )
        artifact = await client.get(
            "/api/trace-study/campaigns/study-v1/artifacts/q02_scalar_distributions.json"
        )
        trajectory_artifact = await client.get(
            "/api/trace-study/campaigns/study-v1/artifacts/q09_q14_trajectory_analysis.json"
        )
        invalid = await client.get("/api/trace-study/campaigns/study-v1/tables/secret.txt")
        missing = await client.get("/api/trace-study/campaigns/missing")
    assert listed.status_code == 200
    assert detail.json()["campaign_id"] == "study-v1"
    assert table.status_code == 200
    assert secondary.status_code == 200
    assert artifact.status_code == 200
    assert trajectory_artifact.status_code == 200
    assert invalid.status_code == 422
    assert missing.status_code == 404


def test_scalar_distributions_preserve_run_level_unit() -> None:
    rows = [
        {
            "mcp_call_count": 2,
            "model_call_count": 1,
            "total_latency_ms": 10.0,
            "model_latency_ms": 8.0,
            "mcp_latency_ms": 1.0,
            "orchestration_latency_ms": 1.0,
            "total_tokens": 100,
            "request_frame_bytes": 20,
            "response_frame_bytes": 40,
            "estimated_cost_usd": 0.01,
            "task_success": True,
        },
        {
            "mcp_call_count": 4,
            "model_call_count": 2,
            "total_latency_ms": 20.0,
            "model_latency_ms": 16.0,
            "mcp_latency_ms": 2.0,
            "orchestration_latency_ms": 2.0,
            "total_tokens": 200,
            "request_frame_bytes": 30,
            "response_frame_bytes": 50,
            "estimated_cost_usd": 0.02,
            "task_success": False,
        },
    ]
    summaries = scalar_distributions(rows)
    calls = next(item for item in summaries if item["field"] == "mcp_call_count")
    success = next(item for item in summaries if item["field"] == "task_success")
    assert calls["n"] == 2
    assert calls["mean"] == 3.0
    assert success["successes"] == 1
    assert success["failures"] == 1


def test_scalar_bootstrap_intervals_are_reproducible_and_bounded() -> None:
    values = [1.0, 2.0, 4.0, 8.0]
    first = bootstrap_interval(values, "mean", repetitions=200, seed=7)
    second = bootstrap_interval(values, "mean", repetitions=200, seed=7)
    assert first == second
    assert first is not None
    assert first[0] <= sum(values) / len(values) <= first[1]


def test_scalar_bootstrap_handles_single_observation() -> None:
    assert bootstrap_interval([3.5], "median") == [3.5, 3.5]
