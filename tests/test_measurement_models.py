from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from mcp_traffic_analysis.measurement.models import (
    Component,
    Direction,
    EventKind,
    Layer,
    MessageType,
    Outcome,
    PayloadRecordingPolicy,
    TraceEvent,
    Transport,
)


def valid_event_data() -> dict[str, object]:
    return {
        "event_id": uuid4(),
        "experiment_id": uuid4(),
        "condition_id": "phase1a:test",
        "run_id": uuid4(),
        "trace_id": uuid4(),
        "span_id": uuid4(),
        "sequence_number": 0,
        "wall_time_utc": datetime.now(UTC),
        "monotonic_time_ns": 100,
        "process_id": 1,
        "component": Component.MCP_SERVER,
        "layer": Layer.MCP,
        "direction": Direction.INBOUND,
        "transport": Transport.IN_MEMORY,
        "event_kind": EventKind.REQUEST_STARTED,
        "message_type": MessageType.REQUEST,
        "mcp_method": "tools/list",
        "payload_recording_policy": PayloadRecordingPolicy.UNAVAILABLE_TRANSPORT_BYPASS,
        "outcome": Outcome.STARTED,
    }


def test_trace_event_is_strict_and_frozen() -> None:
    event = TraceEvent.model_validate(valid_event_data())

    with pytest.raises(ValidationError):
        TraceEvent.model_validate({**valid_event_data(), "unexpected": "field"})
    with pytest.raises(ValidationError):
        event.outcome = Outcome.SUCCESS  # type: ignore[misc]


def test_trace_event_requires_utc() -> None:
    values = valid_event_data()
    values["wall_time_utc"] = datetime(2026, 1, 1)

    with pytest.raises(ValidationError, match="timezone-aware"):
        TraceEvent.model_validate(values)


def test_in_memory_event_cannot_claim_observed_bytes() -> None:
    values = valid_event_data()
    values["payload_bytes"] = 12

    with pytest.raises(ValidationError, match="cannot claim byte observations"):
        TraceEvent.model_validate(values)


def test_terminal_event_requires_latency() -> None:
    values = valid_event_data()
    values.update(
        event_kind=EventKind.REQUEST_FINISHED,
        message_type=MessageType.RESPONSE,
        outcome=Outcome.SUCCESS,
        direction=Direction.OUTBOUND,
    )

    with pytest.raises(ValidationError, match="latency_ms"):
        TraceEvent.model_validate(values)
