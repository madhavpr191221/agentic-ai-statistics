from __future__ import annotations

from pathlib import Path

import pytest

from mcp_traffic_analysis.fixtures.runner import Scenario, run_fixture
from mcp_traffic_analysis.measurement.models import ErrorType, EventKind, Outcome, TraceEvent

TRIAL_MATRIX = [
    Scenario.LIST_TOOLS,
    *([Scenario.ECHO] * 4),
    *([Scenario.SLEEP] * 3),
    *([Scenario.BACKEND_EXCEPTION] * 2),
    *([Scenario.TOOL_ERROR] * 2),
    *([Scenario.TIMEOUT] * 2),
    *([Scenario.NONEXISTENT_TOOL] * 2),
    *([Scenario.CONCURRENT] * 2),
    *([Scenario.CANCELLATION] * 2),
]

EXPECTED_ERROR = {
    Scenario.BACKEND_EXCEPTION: ErrorType.BACKEND_EXCEPTION,
    Scenario.TOOL_ERROR: ErrorType.TOOL_ERROR,
    Scenario.TIMEOUT: ErrorType.TIMEOUT,
    Scenario.NONEXISTENT_TOOL: ErrorType.NONEXISTENT_TOOL,
    Scenario.CANCELLATION: ErrorType.CANCELLATION,
}


def read_events(path: Path) -> list[TraceEvent]:
    return [
        TraceEvent.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


@pytest.mark.parametrize(
    ("scenario", "trial_number"),
    [(scenario, index) for index, scenario in enumerate(TRIAL_MATRIX)],
)
async def test_twenty_trial_in_memory_matrix(
    tmp_path: Path,
    scenario: Scenario,
    trial_number: int,
) -> None:
    artifacts = await run_fixture(
        scenario=scenario,
        output_root=tmp_path / str(trial_number),
        seed=trial_number,
    )
    events = read_events(artifacts.events_path)

    assert events
    assert all(event.payload_bytes is None for event in events)
    assert all(event.frame_bytes is None for event in events)
    assert all(event.payload_hash is None for event in events)

    terminal_tool_events = [
        event
        for event in events
        if event.event_kind is EventKind.REQUEST_FINISHED and event.mcp_method == "tools/call"
    ]
    if scenario in EXPECTED_ERROR:
        assert any(event.error_type is EXPECTED_ERROR[scenario] for event in terminal_tool_events)
    elif scenario is not Scenario.LIST_TOOLS:
        assert terminal_tool_events
        assert all(event.outcome is Outcome.SUCCESS for event in terminal_tool_events)

    serialized = artifacts.events_path.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" not in serialized
    assert "controlled backend failure" not in serialized
    assert '"arguments"' not in serialized


async def test_sleep_latency_respects_controlled_service_time(tmp_path: Path) -> None:
    artifacts = await run_fixture(scenario=Scenario.SLEEP, output_root=tmp_path)
    terminal = [
        event
        for event in read_events(artifacts.events_path)
        if event.event_kind is EventKind.REQUEST_FINISHED and event.tool_name == "sleep_ms"
    ]

    assert len(terminal) == 1
    assert terminal[0].latency_ms is not None
    assert terminal[0].latency_ms >= 15


async def test_concurrent_calls_overlap_without_false_sequential_order(tmp_path: Path) -> None:
    artifacts = await run_fixture(scenario=Scenario.CONCURRENT, output_root=tmp_path)
    tool_events = [
        event for event in read_events(artifacts.events_path) if event.tool_name == "sleep_ms"
    ]
    starts = [event for event in tool_events if event.event_kind is EventKind.REQUEST_STARTED]
    terminals = [event for event in tool_events if event.event_kind is EventKind.REQUEST_FINISHED]

    assert len(starts) == len(terminals) == 3
    assert max(event.sequence_number for event in starts) < min(
        event.sequence_number for event in terminals
    )
