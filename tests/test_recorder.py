from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from mcp_traffic_analysis.fixtures.runner import Scenario, create_manifest
from mcp_traffic_analysis.measurement.clock import ClockSample
from mcp_traffic_analysis.measurement.models import (
    Component,
    Direction,
    EventKind,
    Layer,
    MessageType,
    Outcome,
    PayloadRecordingPolicy,
)
from mcp_traffic_analysis.measurement.recorder import EventRecorder
from mcp_traffic_analysis.measurement.sink import JsonlTraceSink


class IncrementingClock:
    def __init__(self) -> None:
        self._index = 0
        self._start = datetime(2026, 1, 1, tzinfo=UTC)

    def sample(self) -> ClockSample:
        value = self._index
        self._index += 1
        return ClockSample(
            wall_time_utc=self._start + timedelta(microseconds=value),
            monotonic_time_ns=value * 1_000,
        )


def test_sink_refuses_to_overwrite_existing_trace(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    JsonlTraceSink.create(path)

    with pytest.raises(FileExistsError):
        JsonlTraceSink.create(path)


async def test_concurrent_emission_is_file_ordered(tmp_path: Path) -> None:
    sink = JsonlTraceSink.create(tmp_path / "events.jsonl")
    recorder = EventRecorder(
        manifest=create_manifest(scenario=Scenario.CONCURRENT, seed=7),
        sink=sink,
        component=Component.MCP_SERVER,
        clock=IncrementingClock(),
    )

    async def emit_one() -> None:
        await recorder.emit(
            span_id=uuid4(),
            event_kind=EventKind.REQUEST_STARTED,
            message_type=MessageType.REQUEST,
            direction=Direction.INBOUND,
            layer=Layer.MCP,
            outcome=Outcome.STARTED,
            mcp_method="tools/list",
            payload_recording_policy=PayloadRecordingPolicy.UNAVAILABLE_TRANSPORT_BYPASS,
        )

    await asyncio.gather(*(emit_one() for _ in range(20)))

    events = sink.read_events()
    assert [event.sequence_number for event in events] == list(range(20))
    assert len({event.event_id for event in events}) == 20
    assert all(event.payload_bytes is None for event in events)
