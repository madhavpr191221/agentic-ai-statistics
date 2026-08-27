"""Pydantic models defining the versioned Phase 1 measurement contract."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

SchemaVersion = Literal["1.0.0"]
SCHEMA_VERSION: SchemaVersion = "1.0.0"
NonNegativeInt = Annotated[int, Field(ge=0)]
NonNegativeFloat = Annotated[float, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Component(StrEnum):
    FIXTURE_RUNNER = "fixture_runner"
    MCP_SERVER = "mcp_server"


class Layer(StrEnum):
    APPLICATION = "application"
    MCP = "mcp"


class Direction(StrEnum):
    INTERNAL = "internal"
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class Transport(StrEnum):
    IN_MEMORY = "in_memory"
    STDIO = "stdio"


class EventKind(StrEnum):
    REQUEST_STARTED = "request_started"
    REQUEST_FINISHED = "request_finished"


class MessageType(StrEnum):
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class Outcome(StrEnum):
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLATION = "cancellation"
    DISCONNECT = "disconnect"


class ErrorType(StrEnum):
    BACKEND_EXCEPTION = "backend_exception"
    TOOL_ERROR = "tool_error"
    TIMEOUT = "timeout"
    CANCELLATION = "cancellation"
    NONEXISTENT_TOOL = "nonexistent_tool"
    PROTOCOL_ERROR = "protocol_error"
    TRANSPORT_DISCONNECT = "transport_disconnect"
    MALFORMED_RESULT = "malformed_result"


class PayloadRecordingPolicy(StrEnum):
    NOT_RECORDED = "not_recorded"
    HASH_ONLY = "hash_only"
    UNAVAILABLE_TRANSPORT_BYPASS = "unavailable_transport_bypass"


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExperimentManifest(StrictFrozenModel):
    """Immutable description of one deterministic experiment run."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    experiment_id: UUID
    condition_id: str
    campaign: str
    run_id: UUID
    scenario_id: str
    scenario_seed: int
    prompt_variant: str | None = None
    task_structure: str
    autonomy_level: str
    agent_architecture: str
    model_id: str | None = None
    model_settings: dict[str, JsonValue] = Field(default_factory=dict)
    agent_sdk_version: str
    mcp_protocol_version: str
    fastmcp_version: str
    transport: Transport
    host_information: dict[str, JsonValue]
    software_versions: dict[str, JsonValue]
    start_time_utc: datetime

    @model_validator(mode="after")
    def validate_start_time(self) -> Self:
        if self.start_time_utc.tzinfo is None:
            raise ValueError("start_time_utc must be timezone-aware")
        if self.start_time_utc.utcoffset() != UTC.utcoffset(self.start_time_utc):
            raise ValueError("start_time_utc must be expressed in UTC")
        return self


class TraceEvent(StrictFrozenModel):
    """One append-only event in an MCP execution trace."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    event_id: UUID
    experiment_id: UUID
    condition_id: str
    run_id: UUID
    turn_id: str | None = None
    trace_id: UUID
    span_id: UUID
    parent_span_id: UUID | None = None
    sequence_number: NonNegativeInt

    wall_time_utc: datetime
    monotonic_time_ns: NonNegativeInt
    process_id: PositiveInt
    component: Component
    layer: Layer
    direction: Direction
    transport: Transport

    event_kind: EventKind
    message_type: MessageType
    jsonrpc_id: str | int | None = None
    mcp_method: str | None = None
    tool_name: str | None = None

    payload_bytes: NonNegativeInt | None = None
    frame_bytes: NonNegativeInt | None = None
    payload_hash: Sha256Hex | None = None
    payload_recording_policy: PayloadRecordingPolicy

    latency_ms: NonNegativeFloat | None = None
    outcome: Outcome
    error_type: ErrorType | None = None
    error_code: str | int | None = None
    tool_is_error: bool | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_event_semantics(self) -> Self:
        if self.wall_time_utc.tzinfo is None:
            raise ValueError("wall_time_utc must be timezone-aware")
        if self.wall_time_utc.utcoffset() != UTC.utcoffset(self.wall_time_utc):
            raise ValueError("wall_time_utc must be expressed in UTC")

        if self.event_kind is EventKind.REQUEST_STARTED:
            if self.outcome is not Outcome.STARTED:
                raise ValueError("request_started events must have outcome=started")
            if self.latency_ms is not None or self.error_type is not None:
                raise ValueError("request_started events cannot contain latency or errors")
        else:
            if self.outcome is Outcome.STARTED:
                raise ValueError("terminal events cannot have outcome=started")
            if self.latency_ms is None:
                raise ValueError("terminal events must contain latency_ms")

        failed = self.outcome in {
            Outcome.FAILURE,
            Outcome.TIMEOUT,
            Outcome.CANCELLATION,
            Outcome.DISCONNECT,
        }
        if failed and self.error_type is None:
            raise ValueError("failed terminal events must contain error_type")
        if self.outcome is Outcome.SUCCESS and self.error_type is not None:
            raise ValueError("successful events cannot contain error_type")

        if self.payload_recording_policy is PayloadRecordingPolicy.HASH_ONLY:
            if self.payload_bytes is None or self.payload_hash is None:
                raise ValueError("hash_only events require payload_bytes and payload_hash")
        if self.payload_recording_policy is PayloadRecordingPolicy.UNAVAILABLE_TRANSPORT_BYPASS:
            if any(
                value is not None
                for value in (self.payload_bytes, self.frame_bytes, self.payload_hash)
            ):
                raise ValueError("transport-bypass events cannot claim byte observations")
        return self
