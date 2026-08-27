from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from mcp_traffic_analysis.campaigns import build_manifest
from mcp_traffic_analysis.experiments import ConditionSpec, run_condition
from mcp_traffic_analysis.measurement.transport_models import (
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


def test_frozen_design_is_balanced_in_randomized_blocks() -> None:
    manifest = build_manifest(
        campaign_id="baseline-v1",
        replicates=20,
        calls_per_run=8,
        seed=20260827,
    )
    assert len(manifest.planned_runs) == 960
    for replicate in range(1, 21):
        block = [item for item in manifest.planned_runs if item.replicate == replicate]
        assert len(block) == 48
        assert len({item.condition.condition_id for item in block}) == 48
    assert len({item.execution_order for item in manifest.planned_runs}) == 960


async def test_in_memory_condition_keeps_bytes_unavailable(tmp_path: Path) -> None:
    artifacts = await run_condition(
        spec=ConditionSpec(
            transport="in_memory",
            payload_target_bytes=64,
            service_time_ms=0,
            concurrency=4,
            calls_per_run=8,
        ),
        output_root=tmp_path,
    )
    assert artifacts.frames_path is None
    calls = artifacts.calls_path.read_text().splitlines()
    assert len(calls) == 8
    assert all('"request_frame_bytes":null' in line for line in calls)


async def test_stdio_condition_correlates_frames_calls_and_server(tmp_path: Path) -> None:
    artifacts = await run_condition(
        spec=ConditionSpec(
            transport="stdio",
            payload_target_bytes=64,
            service_time_ms=0,
            concurrency=4,
            calls_per_run=4,
        ),
        output_root=tmp_path,
    )
    assert artifacts.frames_path is not None
    calls = artifacts.calls_path.read_text().splitlines()
    frames = artifacts.frames_path.read_text().splitlines()
    assert len(calls) == 4
    assert len(frames) >= 10
    assert all('"request_frame_bytes":null' not in line for line in calls)
    assert all('"server_handler_ms":null' not in line for line in calls)
