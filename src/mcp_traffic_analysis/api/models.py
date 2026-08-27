"""Public request and response models for the local demo API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from mcp_traffic_analysis.analysis.descriptive import DistributionDescription
from mcp_traffic_analysis.fixtures.runner import Scenario
from mcp_traffic_analysis.measurement.models import ExperimentManifest, TraceEvent, Transport


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"
    phase: str = "1A"
    measurement_boundary: str = "fastmcp_server_middleware"


class ScenarioDescriptor(ApiModel):
    id: Scenario
    label: str
    description: str
    expected_outcome: str


class RunRequest(ApiModel):
    scenario: Scenario
    repeat: Annotated[int, Field(ge=1, le=100)] = 1
    seed: int = 0


class RunSummary(ApiModel):
    run_id: UUID
    scenario_id: str
    start_time_utc: datetime
    transport: Transport
    event_count: int
    span_count: int
    mcp_request_count: int
    discovery_call_count: int
    tool_call_count: int
    successful_span_count: int
    failed_span_count: int
    failure_proportion: float | None
    observed_trace_window_ms: float | None
    mean_handler_latency_ms: float | None


class RunDetail(ApiModel):
    manifest: ExperimentManifest
    summary: RunSummary


class RunListResponse(ApiModel):
    runs: list[RunSummary]


class EventListResponse(ApiModel):
    run_id: UUID
    events: list[TraceEvent]


class AnalysisRequest(ApiModel):
    run_ids: Annotated[list[UUID], Field(min_length=1, max_length=200)]
    unit: Literal["call", "run"] = "call"


class NamedDistribution(ApiModel):
    key: str
    distribution: DistributionDescription


class TimelineSpan(ApiModel):
    run_id: UUID
    span_id: UUID
    method: str
    tool_name: str | None
    outcome: str
    error_type: str | None
    start_offset_ms: float
    event_window_ms: float
    handler_latency_ms: float


class AnalysisResponse(ApiModel):
    unit: Literal["call", "run"]
    metric: str
    selected_run_count: int
    distribution: DistributionDescription
    by_method: list[NamedDistribution]
    by_tool: list[NamedDistribution]
    by_outcome: list[NamedDistribution]
    error_counts: dict[str, int]
    timeline: list[TimelineSpan]
    notes: list[str]
