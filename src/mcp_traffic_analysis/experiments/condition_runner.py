"""Run one controlled latency/byte condition through in-memory or stdio MCP."""

from __future__ import annotations

import asyncio
import importlib.metadata
import platform
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic import BaseModel, ConfigDict, Field

from mcp_traffic_analysis.fixtures.server import create_fixture_server
from mcp_traffic_analysis.measurement.models import (
    Component,
    EventKind,
    ExperimentManifest,
    Transport,
)
from mcp_traffic_analysis.measurement.recorder import EventRecorder
from mcp_traffic_analysis.measurement.sink import JsonlTraceSink
from mcp_traffic_analysis.measurement.transport_models import (
    CallMeasurement,
    CallOutcome,
    FrameDirection,
    RunMeasurement,
    TransportFrame,
)
from mcp_traffic_analysis.measurement.validation import validate_completed_trace


class ConditionSpec(BaseModel):
    """Frozen factors for one independent experimental run."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    transport: Literal["in_memory", "stdio"]
    payload_target_bytes: int = Field(ge=0, le=100_000)
    service_time_ms: int = Field(ge=0, le=5_000)
    concurrency: int = Field(gt=0, le=32)
    calls_per_run: int = Field(gt=0, le=1_000)

    @property
    def condition_id(self) -> str:
        return (
            f"phase2:t={self.transport}:b={self.payload_target_bytes}:"
            f"s={self.service_time_ms}:c={self.concurrency}"
        )


@dataclass(frozen=True, slots=True)
class ConditionArtifacts:
    run_directory: Path
    manifest_path: Path
    events_path: Path
    frames_path: Path | None
    calls_path: Path
    run_measurement_path: Path


def _version(distribution: str) -> str:
    return importlib.metadata.version(distribution)


def _manifest(spec: ConditionSpec, seed: int) -> ExperimentManifest:
    return ExperimentManifest(
        experiment_id=uuid4(),
        condition_id=spec.condition_id,
        campaign="phase2_statistical_baseline",
        run_id=uuid4(),
        scenario_id="roundtrip_payload",
        scenario_seed=seed,
        task_structure="controlled_factorial",
        autonomy_level="none",
        agent_architecture="none",
        agent_sdk_version=_version("openai-agents"),
        mcp_protocol_version=_version("mcp"),
        fastmcp_version=_version("fastmcp"),
        transport=Transport(spec.transport),
        host_information={
            "operating_system": platform.system(),
            "operating_system_release": platform.release(),
            "machine": platform.machine(),
        },
        software_versions={
            "python": platform.python_version(),
            "fastmcp": _version("fastmcp"),
            "mcp": _version("mcp"),
            "pydantic": _version("pydantic"),
        },
        start_time_utc=datetime.now(UTC),
    )


def _read_frames(path: Path | None) -> list[TransportFrame]:
    if path is None or not path.is_file():
        return []
    return [
        TransportFrame.model_validate_json(line) for line in path.read_text().splitlines() if line
    ]


def _correlate(
    calls: list[CallMeasurement],
    frames: list[TransportFrame],
    events: list[Any],
) -> list[CallMeasurement]:
    frame_groups: dict[UUID, list[TransportFrame]] = {}
    for frame in frames:
        if frame.call_id is not None:
            frame_groups.setdefault(frame.call_id, []).append(frame)
    handler_by_call: dict[UUID, float] = {}
    for event in events:
        raw_call_id = event.metadata.get("call_id")
        if (
            event.event_kind is EventKind.REQUEST_FINISHED
            and isinstance(raw_call_id, str)
            and event.latency_ms is not None
        ):
            handler_by_call[UUID(raw_call_id)] = event.latency_ms
    enriched: list[CallMeasurement] = []
    for call in calls:
        request = next(
            (
                f
                for f in frame_groups.get(call.call_id, [])
                if f.direction is FrameDirection.CLIENT_TO_SERVER
            ),
            None,
        )
        response = next(
            (
                f
                for f in frame_groups.get(call.call_id, [])
                if f.direction is FrameDirection.SERVER_TO_CLIENT
            ),
            None,
        )
        enriched.append(
            call.model_copy(
                update={
                    "request_payload_bytes": request.payload_bytes if request else None,
                    "request_frame_bytes": request.frame_bytes if request else None,
                    "response_payload_bytes": response.payload_bytes if response else None,
                    "response_frame_bytes": response.frame_bytes if response else None,
                    "server_handler_ms": handler_by_call.get(call.call_id),
                }
            )
        )
    return enriched


async def _measure_call(
    client: Client[Any],
    spec: ConditionSpec,
    manifest: ExperimentManifest,
    call_index: int,
    batch_index: int,
) -> CallMeasurement:
    call_id = uuid4()
    started = time.perf_counter_ns()
    await client.call_tool(
        "roundtrip_payload",
        {"payload": "x" * spec.payload_target_bytes, "delay_ms": spec.service_time_ms},
        meta={
            "call_id": str(call_id),
            "run_id": str(manifest.run_id),
            "trace_id": str(manifest.experiment_id),
        },
    )
    elapsed = (time.perf_counter_ns() - started) / 1_000_000
    return CallMeasurement(
        run_id=manifest.run_id,
        condition_id=manifest.condition_id,
        call_id=call_id,
        call_index=call_index,
        batch_index=batch_index,
        transport=spec.transport,
        payload_target_bytes=spec.payload_target_bytes,
        service_time_ms=spec.service_time_ms,
        concurrency=spec.concurrency,
        is_first_call=call_index == 0,
        client_roundtrip_ms=elapsed,
        outcome=CallOutcome.SUCCESS,
        error_type=None,
    )


async def _execute_calls(
    client: Client[Any], spec: ConditionSpec, manifest: ExperimentManifest
) -> list[CallMeasurement]:
    calls: list[CallMeasurement] = []
    for batch_start in range(0, spec.calls_per_run, spec.concurrency):
        indices = list(range(batch_start, min(batch_start + spec.concurrency, spec.calls_per_run)))
        batch = await asyncio.gather(
            *(
                _measure_call(client, spec, manifest, index, batch_start // spec.concurrency)
                for index in indices
            )
        )
        calls.extend(batch)
    return sorted(calls, key=lambda call: call.call_index)


async def run_condition(
    *,
    spec: ConditionSpec,
    output_root: Path,
    replicate: int = 1,
    execution_order: int = 1,
    seed: int = 0,
) -> ConditionArtifacts:
    manifest = _manifest(spec, seed)
    run_directory = output_root / f"roundtrip-{manifest.run_id}"
    run_directory.mkdir(parents=True, exist_ok=False)
    manifest_path = run_directory / "manifest.json"
    events_path = run_directory / "events.jsonl"
    calls_path = run_directory / "calls.jsonl"
    frames_path = run_directory / "frames.jsonl" if spec.transport == "stdio" else None
    run_path = run_directory / "run_measurement.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")

    start_ns = time.perf_counter_ns()
    if spec.transport == "in_memory":
        sink = JsonlTraceSink.create(events_path)
        recorder = EventRecorder(manifest=manifest, sink=sink, component=Component.MCP_SERVER)
        client: Client[Any] = Client(create_fixture_server(recorder))
    else:
        assert frames_path is not None
        transport = StdioTransport(
            command=sys.executable,
            args=[
                "-m",
                "mcp_traffic_analysis.transport.stdio_relay",
                "--python",
                sys.executable,
                "--run-id",
                str(manifest.run_id),
                "--manifest",
                str(manifest_path.resolve()),
                "--events",
                str(events_path.resolve()),
                "--frames",
                str(frames_path.resolve()),
            ],
            cwd=str(Path.cwd()),
            keep_alive=False,
            log_file=run_directory / "server.stderr.log",
        )
        client = Client(transport)

    session_started = time.perf_counter_ns()
    async with client:
        session_start_ms = (time.perf_counter_ns() - session_started) / 1_000_000
        calls = await _execute_calls(client, spec, manifest)
    run_elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000

    events = JsonlTraceSink(events_path).read_events()
    validate_completed_trace(events)
    calls = _correlate(calls, _read_frames(frames_path), events)
    calls_path.write_text(
        "".join(call.model_dump_json() + "\n" for call in calls), encoding="utf-8"
    )
    measurement = RunMeasurement(
        run_id=manifest.run_id,
        condition_id=manifest.condition_id,
        replicate=replicate,
        execution_order=execution_order,
        transport=spec.transport,
        payload_target_bytes=spec.payload_target_bytes,
        service_time_ms=spec.service_time_ms,
        concurrency=spec.concurrency,
        calls_per_run=spec.calls_per_run,
        session_start_ms=session_start_ms,
        run_elapsed_ms=run_elapsed_ms,
        successful_calls=sum(call.outcome is CallOutcome.SUCCESS for call in calls),
        failed_calls=sum(call.outcome is not CallOutcome.SUCCESS for call in calls),
    )
    run_path.write_text(measurement.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return ConditionArtifacts(
        run_directory, manifest_path, events_path, frames_path, calls_path, run_path
    )
