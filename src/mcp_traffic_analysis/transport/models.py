"""Exact stdio frame measurements used by the active agent studies."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonNegativeInt = Annotated[int, Field(ge=0)]
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
