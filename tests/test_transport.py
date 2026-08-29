from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from agents.mcp import MCPServerStdio
from pydantic import ValidationError

from agentic_ai_statistics.incidents.models import IncidentScenario
from agentic_ai_statistics.incidents.world import initial_state, save_state
from agentic_ai_statistics.transport.models import (
    FrameDirection,
    FrameMessageType,
    TransportFrame,
)


def test_transport_frame_enforces_exact_size_identity() -> None:
    values = {
        "frame_id": uuid4(),
        "run_id": uuid4(),
        "sequence_number": 0,
        "wall_time_utc": datetime.now(UTC),
        "monotonic_time_ns": 1,
        "direction": FrameDirection.CLIENT_TO_SERVER,
        "message_type": FrameMessageType.REQUEST,
        "payload_bytes": 10,
        "frame_bytes": 11,
        "delimiter_bytes": 1,
        "payload_sha256": "0" * 64,
    }
    assert TransportFrame.model_validate(values).frame_bytes == 11
    with pytest.raises(ValidationError, match="frame_bytes"):
        TransportFrame.model_validate({**values, "frame_bytes": 12})


async def test_relay_records_exact_incident_server_frames(tmp_path: Path) -> None:
    run_id = uuid4()
    state_path = tmp_path / "state.json"
    events_path = tmp_path / "events.jsonl"
    frames_path = tmp_path / "frames.jsonl"
    save_state(state_path, initial_state(IncidentScenario.CHECKOUT_FAILURES))
    relay_args = [
        "-m",
        "agentic_ai_statistics.transport.stdio_relay",
        "--python",
        sys.executable,
        "--run-id",
        str(run_id),
        "--frames",
        str(frames_path),
        "--server-module",
        "agentic_ai_statistics.incidents.server",
        "--server-arg=--state",
        f"--server-arg={state_path}",
        "--server-arg=--events",
        f"--server-arg={events_path}",
    ]
    server = MCPServerStdio(
        name="transport regression server",
        params={"command": sys.executable, "args": relay_args, "cwd": str(Path.cwd())},
    )
    async with server:
        tools = await server.list_tools()
        result = await server.call_tool("get_alert", {})

    assert {tool.name for tool in tools} >= {"get_alert", "get_metrics"}
    assert not result.isError
    frames = [
        TransportFrame.model_validate_json(line)
        for line in frames_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert frames
    assert all(frame.run_id == run_id for frame in frames)
    assert [frame.sequence_number for frame in frames] == list(range(len(frames)))
    assert all(frame.frame_bytes == frame.payload_bytes + frame.delimiter_bytes for frame in frames)
    assert all(len(frame.payload_sha256) == 64 for frame in frames)
    assert {frame.direction for frame in frames} == {
        FrameDirection.CLIENT_TO_SERVER,
        FrameDirection.SERVER_TO_CLIENT,
    }
    assert any(frame.mcp_method == "tools/call" for frame in frames)
    assert sum(
        frame.frame_bytes
        for frame in frames
        if frame.direction is FrameDirection.CLIENT_TO_SERVER
    ) > 0
    assert sum(
        frame.frame_bytes
        for frame in frames
        if frame.direction is FrameDirection.SERVER_TO_CLIENT
    ) > 0
