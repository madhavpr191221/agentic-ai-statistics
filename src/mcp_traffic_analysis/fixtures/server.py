"""Deterministic FastMCP server used to establish measurement ground truth."""

from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from mcp_traffic_analysis.fixtures.middleware import FixtureBackendError, TraceMiddleware
from mcp_traffic_analysis.measurement.recorder import EventRecorder


class FailureKind(StrEnum):
    BACKEND_EXCEPTION = "backend_exception"
    TOOL_ERROR = "tool_error"
    TIMEOUT = "timeout"


def create_fixture_server(recorder: EventRecorder) -> FastMCP:
    """Build a fresh deterministic server bound to one run recorder."""
    server = FastMCP("Phase 1A deterministic fixture", mask_error_details=False)
    server.add_middleware(TraceMiddleware(recorder))

    @server.tool
    async def echo_bytes(
        n: Annotated[int, Field(ge=0, le=1_000_000)],
    ) -> str:
        """Return exactly n ASCII payload characters."""
        return "x" * n

    @server.tool
    async def sleep_ms(
        delay_ms: Annotated[int, Field(ge=0, le=5_000)],
    ) -> dict[str, int]:
        """Wait for a controlled service time and report the configured delay."""
        await asyncio.sleep(delay_ms / 1_000)
        return {"delay_ms": delay_ms}

    @server.tool
    async def fail_with(kind: FailureKind) -> None:
        """Raise one controlled failure without using external services."""
        if kind is FailureKind.BACKEND_EXCEPTION:
            raise FixtureBackendError("controlled backend failure")
        if kind is FailureKind.TIMEOUT:
            raise TimeoutError("controlled backend timeout")
        raise ToolError("controlled tool error")

    return server
