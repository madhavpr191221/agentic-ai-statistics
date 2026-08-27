"""Public request and response models for the local demo API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from mcp_traffic_analysis.analysis.descriptive import DistributionDescription
from mcp_traffic_analysis.experiments.campaign_models import CampaignManifest, CampaignProgress
from mcp_traffic_analysis.experiments.condition_runner import ConditionSpec
from mcp_traffic_analysis.fixtures.runner import Scenario
from mcp_traffic_analysis.measurement.models import ExperimentManifest, TraceEvent, Transport
from mcp_traffic_analysis.measurement.transport_models import CallMeasurement


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"
    phase: str = "2"
    measurement_boundary: str = "application_and_stdio_transport"
    agent_available: bool = False


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


class Phase2RunRequest(ApiModel):
    transport: Literal["in_memory", "stdio"] = "stdio"
    payload_target_bytes: Annotated[int, Field(ge=0, le=100_000)] = 1_024
    service_time_ms: Annotated[int, Field(ge=0, le=5_000)] = 20
    concurrency: Annotated[int, Field(gt=0, le=8)] = 1
    calls_per_run: Annotated[int, Field(gt=0, le=100)] = 8
    seed: int = 0

    def condition(self) -> ConditionSpec:
        return ConditionSpec(
            transport=self.transport,
            payload_target_bytes=self.payload_target_bytes,
            service_time_ms=self.service_time_ms,
            concurrency=self.concurrency,
            calls_per_run=self.calls_per_run,
        )


class Phase2RunResponse(ApiModel):
    run_id: UUID
    condition_id: str
    transport: Literal["in_memory", "stdio"]
    session_start_ms: float
    run_elapsed_ms: float
    median_client_roundtrip_ms: float
    median_server_handler_ms: float | None
    median_nonhandler_residual_ms: float | None
    total_request_frame_bytes: int | None
    total_response_frame_bytes: int | None
    calls: list[CallMeasurement]


class CampaignSummary(ApiModel):
    campaign_id: str
    design_name: str
    status: str
    planned_runs: int
    completed_runs: int
    created_at_utc: datetime


class CampaignListResponse(ApiModel):
    campaigns: list[CampaignSummary]


class CampaignDetail(ApiModel):
    manifest: CampaignManifest
    progress: CampaignProgress
    analysis: dict[str, JsonValue] | None
