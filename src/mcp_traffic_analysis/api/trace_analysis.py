"""Derive UI-facing run summaries and descriptive analyses from raw events."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Literal

from mcp_traffic_analysis.analysis.descriptive import describe_values
from mcp_traffic_analysis.api.models import (
    AnalysisResponse,
    NamedDistribution,
    RunSummary,
    TimelineSpan,
)
from mcp_traffic_analysis.api.repository import ArtifactRecord
from mcp_traffic_analysis.measurement.models import EventKind, Outcome, TraceEvent


def _terminal_events(events: Iterable[TraceEvent]) -> list[TraceEvent]:
    return [event for event in events if event.event_kind is EventKind.REQUEST_FINISHED]


def _trace_window_ms(events: Iterable[TraceEvent]) -> float | None:
    event_list = list(events)
    if not event_list:
        return None
    first = min(event.monotonic_time_ns for event in event_list)
    last = max(event.monotonic_time_ns for event in event_list)
    return max(0.0, (last - first) / 1_000_000)


def summarize_record(record: ArtifactRecord) -> RunSummary:
    starts = [event for event in record.events if event.event_kind is EventKind.REQUEST_STARTED]
    terminals = _terminal_events(record.events)
    successful = [event for event in terminals if event.outcome is Outcome.SUCCESS]
    failed = [event for event in terminals if event.outcome is not Outcome.SUCCESS]
    latencies = [event.latency_ms for event in terminals if event.latency_ms is not None]
    failure_proportion = len(failed) / len(terminals) if terminals else None
    return RunSummary(
        run_id=record.manifest.run_id,
        scenario_id=record.manifest.scenario_id,
        start_time_utc=record.manifest.start_time_utc,
        transport=record.manifest.transport,
        event_count=len(record.events),
        span_count=len({event.span_id for event in record.events}),
        mcp_request_count=len(starts),
        discovery_call_count=sum(event.mcp_method == "tools/list" for event in starts),
        tool_call_count=sum(event.mcp_method == "tools/call" for event in starts),
        successful_span_count=len(successful),
        failed_span_count=len(failed),
        failure_proportion=failure_proportion,
        observed_trace_window_ms=_trace_window_ms(record.events),
        mean_handler_latency_ms=(sum(latencies) / len(latencies) if latencies else None),
    )


def _named_distributions(
    events: Iterable[TraceEvent],
    key: str,
) -> list[NamedDistribution]:
    grouped: dict[str, list[float | None]] = defaultdict(list)
    for event in events:
        if key == "method":
            group = event.mcp_method or "unavailable"
        elif key == "tool":
            group = event.tool_name or "no_tool"
        else:
            group = event.outcome.value
        grouped[group].append(event.latency_ms)
    return [
        NamedDistribution(key=group, distribution=describe_values(values))
        for group, values in sorted(grouped.items())
    ]


def _timeline(records: Iterable[ArtifactRecord]) -> list[TimelineSpan]:
    spans: list[TimelineSpan] = []
    for record in records:
        start_time = min(event.monotonic_time_ns for event in record.events)
        grouped: dict[object, list[TraceEvent]] = defaultdict(list)
        for event in record.events:
            grouped[event.span_id].append(event)
        for span_events in grouped.values():
            start = next(
                event for event in span_events if event.event_kind is EventKind.REQUEST_STARTED
            )
            terminal = next(
                event for event in span_events if event.event_kind is EventKind.REQUEST_FINISHED
            )
            spans.append(
                TimelineSpan(
                    run_id=record.manifest.run_id,
                    span_id=start.span_id,
                    method=start.mcp_method or "unknown",
                    tool_name=start.tool_name,
                    outcome=terminal.outcome.value,
                    error_type=terminal.error_type.value if terminal.error_type else None,
                    start_offset_ms=(start.monotonic_time_ns - start_time) / 1_000_000,
                    event_window_ms=max(
                        0.0,
                        (terminal.monotonic_time_ns - start.monotonic_time_ns) / 1_000_000,
                    ),
                    handler_latency_ms=terminal.latency_ms or 0.0,
                )
            )
    return sorted(spans, key=lambda span: (str(span.run_id), span.start_offset_ms))


def analyze_records(
    records: list[ArtifactRecord],
    unit: Literal["call", "run"],
) -> AnalysisResponse:
    terminals = [event for record in records for event in _terminal_events(record.events)]
    if unit == "run":
        values = [_trace_window_ms(record.events) for record in records]
        metric = "observed_trace_window_ms"
        by_method: list[NamedDistribution] = []
        by_tool: list[NamedDistribution] = []
        by_outcome: list[NamedDistribution] = []
        notes = [
            "The run-level metric is the window between the first and last recorded MCP event.",
            "It is not full agent latency and does not sum overlapping span durations.",
        ]
    else:
        values = [event.latency_ms for event in terminals]
        metric = "server_handler_latency_ms"
        by_method = _named_distributions(terminals, "method")
        by_tool = _named_distributions(terminals, "tool")
        by_outcome = _named_distributions(terminals, "outcome")
        notes = [
            "Calls are nested observations within runs and are not independent experimental units.",
            "These summaries are descriptive calibration results, not inferential claims.",
        ]

    errors = Counter(event.error_type.value for event in terminals if event.error_type is not None)
    return AnalysisResponse(
        unit="run" if unit == "run" else "call",
        metric=metric,
        selected_run_count=len(records),
        distribution=describe_values(values),
        by_method=by_method,
        by_tool=by_tool,
        by_outcome=by_outcome,
        error_counts=dict(sorted(errors.items())),
        timeline=_timeline(records),
        notes=notes,
    )
