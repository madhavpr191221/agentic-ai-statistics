"""Versioned transport and call measurements for Phase 2."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonNegativeInt = Annotated[int, Field(ge=0)]
NonNegativeFloat = Annotated[float, Field(ge=0)]
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FrameDirection(StrEnum):
    CLIENT_TO_SERVER = "client_to_server"
    SERVER_TO_CLIENT = "server_to_client"


class FrameMessageType(StrEnum):
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    MALFORMED = "malformed"


class TransportFrame(FrozenModel):
    """One exact newline-delimited frame observed by the stdio relay."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    frame_id: UUID
    run_id: UUID
    sequence_number: NonNegativeInt
    wall_time_utc: datetime
    monotonic_time_ns: NonNegativeInt
    direction: FrameDirection
    message_type: FrameMessageType
    jsonrpc_id: str | int | None = None
    mcp_method: str | None = None
    call_id: UUID | None = None
    payload_bytes: NonNegativeInt
    frame_bytes: NonNegativeInt
    delimiter_bytes: NonNegativeInt
    payload_sha256: Sha256Hex

    @model_validator(mode="after")
    def validate_frame(self) -> Self:
        if self.wall_time_utc.tzinfo is None or self.wall_time_utc.utcoffset() != UTC.utcoffset(
            self.wall_time_utc
        ):
            raise ValueError("wall_time_utc must be expressed in UTC")
        if self.frame_bytes != self.payload_bytes + self.delimiter_bytes:
            raise ValueError("frame_bytes must equal payload_bytes plus delimiter_bytes")
        return self


class CallOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLATION = "cancellation"


class CallMeasurement(FrozenModel):
    """One client-observed synthetic tool call used in statistical tables."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    run_id: UUID
    condition_id: str
    call_id: UUID
    call_index: NonNegativeInt
    batch_index: NonNegativeInt
    transport: Literal["in_memory", "stdio"]
    payload_target_bytes: NonNegativeInt
    service_time_ms: NonNegativeInt
    concurrency: Annotated[int, Field(gt=0)]
    is_first_call: bool
    client_roundtrip_ms: NonNegativeFloat
    outcome: CallOutcome
    error_type: str | None = None
    request_payload_bytes: NonNegativeInt | None = None
    request_frame_bytes: NonNegativeInt | None = None
    response_payload_bytes: NonNegativeInt | None = None
    response_frame_bytes: NonNegativeInt | None = None
    server_handler_ms: NonNegativeFloat | None = None

    @property
    def total_frame_bytes(self) -> int | None:
        if self.request_frame_bytes is None or self.response_frame_bytes is None:
            return None
        return self.request_frame_bytes + self.response_frame_bytes

    @property
    def nonhandler_residual_ms(self) -> float | None:
        if self.server_handler_ms is None:
            return None
        return self.client_roundtrip_ms - self.server_handler_ms


class RunMeasurement(FrozenModel):
    """Run-level experimental factors and session timing."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    run_id: UUID
    condition_id: str
    replicate: Annotated[int, Field(gt=0)]
    execution_order: Annotated[int, Field(gt=0)]
    transport: Literal["in_memory", "stdio"]
    payload_target_bytes: NonNegativeInt
    service_time_ms: NonNegativeInt
    concurrency: Annotated[int, Field(gt=0)]
    calls_per_run: Annotated[int, Field(gt=0)]
    session_start_ms: NonNegativeFloat
    run_elapsed_ms: NonNegativeFloat
    successful_calls: NonNegativeInt
    failed_calls: NonNegativeInt
