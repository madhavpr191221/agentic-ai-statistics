"""Frozen data contracts for Phase 3 incident runs."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IncidentScenario(StrEnum):
    CHECKOUT_FAILURES = "checkout_failures"
    IMAGE_WORKER_DEGRADATION = "image_worker_degradation"
    ORDERS_API_OUTAGE = "orders_api_outage"


class ScenarioDefinition(StrictModel):
    id: IncidentScenario
    label: str
    alert: str
    hidden_cause: str
    diagnosis_terms: frozenset[str]
    diagnosis_any_terms: frozenset[str] = frozenset()
    required_evidence_ids: frozenset[str]
    required_action: str
    required_target: str
    prohibited_actions: frozenset[str] = frozenset()


class IncidentResult(StrictModel):
    incident_id: str
    diagnosis: str
    evidence_ids: list[str]
    selected_action: str
    action_target: str
    resolution_summary: str


class ActionRecord(StrictModel):
    sequence: int
    timestamp_utc: datetime
    action: str
    target: str
    accepted: bool
    prohibited: bool
    result: str


class ScoreCard(StrictModel):
    diagnosis_correct: bool
    required_evidence_present: bool
    correct_remediation_executed: bool
    no_prohibited_action_attempted: bool
    final_state_resolved: bool
    task_success: bool


class AgentEvent(StrictModel):
    sequence: int
    event: str
    started_ns: int
    elapsed_ms: float | None = None
    tool_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelCallMeasurement(StrictModel):
    call_index: int
    latency_ms: float | None
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    total_tokens: int


class IncidentRunMeasurement(StrictModel):
    run_id: UUID
    scenario_id: IncidentScenario
    status: Literal["success", "failure"]
    failure_type: str | None
    total_latency_ms: float
    model_latency_ms: float
    mcp_latency_ms: float
    server_handler_latency_ms: float
    orchestration_latency_ms: float
    decomposition_consistent: bool
    correlation_consistent: bool
    model_call_count: int
    mcp_call_count: int
    tool_sequence: list[str]
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    total_tokens: int
    request_frame_bytes: int
    response_frame_bytes: int
    estimated_cost_usd: float


class IncidentRunDetail(StrictModel):
    run_id: UUID
    scenario_id: IncidentScenario
    created_at_utc: datetime
    model_id: str
    measurement: IncidentRunMeasurement
    result: IncidentResult | None
    score: ScoreCard
    actions: list[ActionRecord]
    agent_events: list[AgentEvent]


class IncidentRunRequest(StrictModel):
    scenario: IncidentScenario
    mode: Literal["live", "deterministic"] = "live"
