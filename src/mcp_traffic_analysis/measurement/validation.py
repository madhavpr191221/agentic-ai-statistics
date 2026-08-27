"""Ground-truth invariants for completed Phase 1A traces."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID

from mcp_traffic_analysis.measurement.models import EventKind, Outcome, TraceEvent


class TraceValidationError(ValueError):
    """Raised when a completed trace violates the measurement contract."""


def validate_completed_trace(events: Sequence[TraceEvent]) -> None:
    """Require contiguous ordering and one terminal event per request span."""
    if not events:
        raise TraceValidationError("a completed trace must contain at least one event")

    sequence_numbers = [event.sequence_number for event in events]
    if sequence_numbers != list(range(len(events))):
        raise TraceValidationError("event sequence numbers must be contiguous and file-ordered")

    trace_ids = {event.trace_id for event in events}
    run_ids = {event.run_id for event in events}
    if len(trace_ids) != 1 or len(run_ids) != 1:
        raise TraceValidationError("one trace file must contain exactly one trace and one run")

    spans: dict[UUID, list[TraceEvent]] = defaultdict(list)
    for event in events:
        spans[event.span_id].append(event)

    for span_id, span_events in spans.items():
        if len(span_events) != 2:
            raise TraceValidationError(
                f"span {span_id} must contain one start and one terminal event"
            )
        start, terminal = span_events
        if start.event_kind is not EventKind.REQUEST_STARTED:
            raise TraceValidationError(f"span {span_id} does not begin with request_started")
        if terminal.event_kind is not EventKind.REQUEST_FINISHED:
            raise TraceValidationError(f"span {span_id} does not end with request_finished")
        if terminal.outcome is Outcome.STARTED:
            raise TraceValidationError(f"span {span_id} has no terminal outcome")
        if terminal.monotonic_time_ns < start.monotonic_time_ns:
            raise TraceValidationError(f"span {span_id} moves backwards in monotonic time")
        if (start.mcp_method, start.tool_name) != (terminal.mcp_method, terminal.tool_name):
            raise TraceValidationError(f"span {span_id} changes identity between events")
