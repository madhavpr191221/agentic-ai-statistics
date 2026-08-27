"""FastMCP middleware that records model-free semantic request spans."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

from fastmcp.exceptions import NotFoundError, ToolError
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

from mcp_traffic_analysis.measurement.models import (
    Direction,
    ErrorType,
    EventKind,
    Layer,
    MessageType,
    Outcome,
    PayloadRecordingPolicy,
)
from mcp_traffic_analysis.measurement.recorder import EventRecorder

RECORDED_METHODS = frozenset({"tools/list", "tools/call"})


class FixtureBackendError(RuntimeError):
    """Controlled exception representing a synthetic backend failure."""


def _exception_chain(error: BaseException) -> list[BaseException]:
    chain: list[BaseException] = []
    current: BaseException | None = error
    while current is not None and current not in chain:
        chain.append(current)
        current = current.__cause__ or current.__context__
    return chain


def classify_error(error: BaseException) -> ErrorType:
    """Classify an exception without retaining its potentially sensitive message."""
    chain = _exception_chain(error)
    if isinstance(error, asyncio.CancelledError):
        return ErrorType.CANCELLATION
    if isinstance(error, NotFoundError):
        return ErrorType.NONEXISTENT_TOOL
    if any(isinstance(item, TimeoutError) for item in chain):
        return ErrorType.TIMEOUT
    if any(isinstance(item, FixtureBackendError) for item in chain):
        return ErrorType.BACKEND_EXCEPTION
    if isinstance(error, ToolError):
        return ErrorType.TOOL_ERROR
    return ErrorType.PROTOCOL_ERROR


def _terminal_outcome(error_type: ErrorType) -> Outcome:
    if error_type is ErrorType.TIMEOUT:
        return Outcome.TIMEOUT
    if error_type is ErrorType.CANCELLATION:
        return Outcome.CANCELLATION
    if error_type is ErrorType.TRANSPORT_DISCONNECT:
        return Outcome.DISCONNECT
    return Outcome.FAILURE


class TraceMiddleware(Middleware):
    """Record normalized MCP request spans at the FastMCP server boundary."""

    def __init__(self, recorder: EventRecorder) -> None:
        self.recorder = recorder

    @staticmethod
    def _tool_name(context: MiddlewareContext[Any]) -> str | None:
        if context.method != "tools/call":
            return None
        name = getattr(context.message, "name", None)
        return name if isinstance(name, str) else None

    @staticmethod
    def _metadata(context: MiddlewareContext[Any]) -> dict[str, str]:
        return {
            "measurement_boundary": "fastmcp_server_middleware",
            "byte_measurement": "unavailable_in_memory_transport",
            "source": context.source,
        }

    async def _record_failure(
        self,
        *,
        context: MiddlewareContext[Any],
        span_id: UUID,
        call_start_ns: int,
        error: BaseException,
    ) -> None:
        finish = self.recorder.sample_clock()
        error_type = classify_error(error)
        metadata = self._metadata(context)
        metadata["exception_class"] = type(error).__name__
        await self.recorder.emit(
            span_id=span_id,
            event_kind=EventKind.REQUEST_FINISHED,
            message_type=MessageType.RESPONSE,
            direction=Direction.OUTBOUND,
            layer=Layer.MCP,
            outcome=_terminal_outcome(error_type),
            sample=finish,
            mcp_method=context.method,
            tool_name=self._tool_name(context),
            payload_recording_policy=PayloadRecordingPolicy.UNAVAILABLE_TRANSPORT_BYPASS,
            latency_ms=max(0.0, (finish.monotonic_time_ns - call_start_ns) / 1_000_000),
            error_type=error_type,
            error_code=type(error).__name__,
            tool_is_error=context.method == "tools/call",
            metadata=metadata,
        )

    async def on_message(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        if context.type != "request" or context.method not in RECORDED_METHODS:
            return await call_next(context)

        span_id = uuid4()
        await self.recorder.emit(
            span_id=span_id,
            event_kind=EventKind.REQUEST_STARTED,
            message_type=MessageType.REQUEST,
            direction=Direction.INBOUND,
            layer=Layer.MCP,
            outcome=Outcome.STARTED,
            mcp_method=context.method,
            tool_name=self._tool_name(context),
            payload_recording_policy=PayloadRecordingPolicy.UNAVAILABLE_TRANSPORT_BYPASS,
            metadata=self._metadata(context),
        )

        call_start = self.recorder.sample_clock()
        try:
            result = await call_next(context)
        except asyncio.CancelledError as error:
            await self._record_failure(
                context=context,
                span_id=span_id,
                call_start_ns=call_start.monotonic_time_ns,
                error=error,
            )
            raise
        except Exception as error:
            await self._record_failure(
                context=context,
                span_id=span_id,
                call_start_ns=call_start.monotonic_time_ns,
                error=error,
            )
            raise

        finish = self.recorder.sample_clock()
        await self.recorder.emit(
            span_id=span_id,
            event_kind=EventKind.REQUEST_FINISHED,
            message_type=MessageType.RESPONSE,
            direction=Direction.OUTBOUND,
            layer=Layer.MCP,
            outcome=Outcome.SUCCESS,
            sample=finish,
            mcp_method=context.method,
            tool_name=self._tool_name(context),
            payload_recording_policy=PayloadRecordingPolicy.UNAVAILABLE_TRANSPORT_BYPASS,
            latency_ms=max(
                0.0,
                (finish.monotonic_time_ns - call_start.monotonic_time_ns) / 1_000_000,
            ),
            tool_is_error=False if context.method == "tools/call" else None,
            metadata=self._metadata(context),
        )
        return result
