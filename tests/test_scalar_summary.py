from uuid import uuid4

from agentic_ai_statistics.analysis.scalar_summary import summarize_runs
from agentic_ai_statistics.incidents.models import (
    IncidentRunDetail,
    IncidentRunMeasurement,
    IncidentScenario,
    ScoreCard,
)


def _run(calls: int, latency: float, success: bool) -> IncidentRunDetail:
    measurement = IncidentRunMeasurement(
        run_id=uuid4(), scenario_id=IncidentScenario.CHECKOUT_FAILURES,
        status="success" if success else "failure", failure_type=None,
        total_latency_ms=latency, model_latency_ms=0, mcp_latency_ms=0,
        server_handler_latency_ms=0, orchestration_latency_ms=latency,
        decomposition_consistent=True, correlation_consistent=True,
        model_call_count=1, mcp_call_count=calls, tool_sequence=[],
        input_tokens=10, cached_input_tokens=0, output_tokens=5, total_tokens=15,
        request_frame_bytes=10, response_frame_bytes=20, estimated_cost_usd=0.01,
    )
    score = ScoreCard(
        diagnosis_correct=success, required_evidence_present=success,
        correct_remediation_executed=success, no_prohibited_action_attempted=True,
        final_state_resolved=success, task_success=success,
    )
    return IncidentRunDetail(
        run_id=measurement.run_id, scenario_id=measurement.scenario_id,
        created_at_utc="2026-09-15T00:00:00Z", model_id="test",
        measurement=measurement, result=None, score=score, actions=[], agent_events=[],
    )


def test_summary_uses_complete_runs_and_reports_binary_proportion() -> None:
    summaries = summarize_runs([_run(2, 10, True), _run(4, 30, False)])
    by_field = {item.field: item for item in summaries}
    assert by_field["mcp_call_count"].n == 2
    assert by_field["mcp_call_count"].median == 3
    assert by_field["total_latency_ms"].mean == 20
    assert by_field["task_success"].proportion == 0.5
