"""Correlation, sequencing, and event emission for one experiment run."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID, uuid4

from pydantic import JsonValue

from mcp_traffic_analysis.measurement.clock import Clock, ClockSample, SystemClock
from mcp_traffic_analysis.measurement.models import (
    Component,
    Direction,
    ErrorType,
    EventKind,
    ExperimentManifest,
    Layer,
    MessageType,
    Outcome,
    PayloadRecordingPolicy,
    TraceEvent,
)
from mcp_traffic_analysis.measurement.sink import JsonlTraceSink


@dataclass(frozen=True, slots=True)
class TraceIdentity:
    """Identifiers shared by all events emitted by one recorder."""

    trace_id: UUID
    turn_id: str | None = None


class EventRecorder:
    """Create valid, ordered events and append them to a trace sink."""

    def __init__(
        self,
        *,
        manifest: ExperimentManifest,
        sink: JsonlTraceSink,
        component: Component,
        identity: TraceIdentity | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.manifest = manifest
        self.sink = sink
        self.component = component
        self.identity = identity or TraceIdentity(trace_id=uuid4())
        self.clock = clock or SystemClock()
        self._next_sequence = 0
        self._emit_lock = asyncio.Lock()

    def sample_clock(self) -> ClockSample:
        return self.clock.sample()

    async def emit(
        self,
        *,
        span_id: UUID,
        event_kind: EventKind,
        message_type: MessageType,
        direction: Direction,
        layer: Layer,
        outcome: Outcome,
        sample: ClockSample | None = None,
        parent_span_id: UUID | None = None,
        jsonrpc_id: str | int | None = None,
        mcp_method: str | None = None,
        tool_name: str | None = None,
        payload_bytes: int | None = None,
        frame_bytes: int | None = None,
        payload_hash: str | None = None,
        payload_recording_policy: PayloadRecordingPolicy = (PayloadRecordingPolicy.NOT_RECORDED),
        latency_ms: float | None = None,
        error_type: ErrorType | None = None,
        error_code: str | int | None = None,
        tool_is_error: bool | None = None,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> TraceEvent:
        """Build and durably append one event with an atomic sequence number."""
        observation = sample or self.clock.sample()
        async with self._emit_lock:
            event = TraceEvent(
                event_id=uuid4(),
                experiment_id=self.manifest.experiment_id,
                condition_id=self.manifest.condition_id,
                run_id=self.manifest.run_id,
                turn_id=self.identity.turn_id,
                trace_id=self.identity.trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                sequence_number=self._next_sequence,
                wall_time_utc=observation.wall_time_utc,
                monotonic_time_ns=observation.monotonic_time_ns,
                process_id=os.getpid(),
                component=self.component,
                layer=layer,
                direction=direction,
                transport=self.manifest.transport,
                event_kind=event_kind,
                message_type=message_type,
                jsonrpc_id=jsonrpc_id,
                mcp_method=mcp_method,
                tool_name=tool_name,
                payload_bytes=payload_bytes,
                frame_bytes=frame_bytes,
                payload_hash=payload_hash,
                payload_recording_policy=payload_recording_policy,
                latency_ms=latency_ms,
                outcome=outcome,
                error_type=error_type,
                error_code=error_code,
                tool_is_error=tool_is_error,
                metadata=dict(metadata or {}),
            )
            await self.sink.write(event)
            self._next_sequence += 1
            return event
