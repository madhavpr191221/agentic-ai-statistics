"""Command-line and Python runner for model-free in-memory MCP trials."""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import platform
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastmcp import Client

from mcp_traffic_analysis.fixtures.server import FailureKind, create_fixture_server
from mcp_traffic_analysis.measurement.models import Component, ExperimentManifest, Transport
from mcp_traffic_analysis.measurement.recorder import EventRecorder
from mcp_traffic_analysis.measurement.sink import JsonlTraceSink
from mcp_traffic_analysis.measurement.validation import validate_completed_trace


class Scenario(StrEnum):
    LIST_TOOLS = "list_tools"
    ECHO = "echo"
    SLEEP = "sleep"
    BACKEND_EXCEPTION = "backend_exception"
    TOOL_ERROR = "tool_error"
    TIMEOUT = "timeout"
    NONEXISTENT_TOOL = "nonexistent_tool"
    CONCURRENT = "concurrent"
    CANCELLATION = "cancellation"


@dataclass(frozen=True, slots=True)
class RunArtifacts:
    run_directory: Path
    manifest_path: Path
    events_path: Path


def _package_version(distribution: str) -> str:
    return importlib.metadata.version(distribution)


def create_manifest(*, scenario: Scenario, seed: int) -> ExperimentManifest:
    """Create a privacy-safe manifest without reading environment variables."""
    return ExperimentManifest(
        experiment_id=uuid4(),
        condition_id=f"phase1a:{scenario.value}",
        campaign="recorder_validation",
        run_id=uuid4(),
        scenario_id=scenario.value,
        scenario_seed=seed,
        task_structure="deterministic_fixture",
        autonomy_level="none",
        agent_architecture="none",
        agent_sdk_version=_package_version("openai-agents"),
        mcp_protocol_version=_package_version("mcp"),
        fastmcp_version=_package_version("fastmcp"),
        transport=Transport.IN_MEMORY,
        host_information={
            "operating_system": platform.system(),
            "operating_system_release": platform.release(),
            "machine": platform.machine(),
        },
        software_versions={
            "python": platform.python_version(),
            "fastmcp": _package_version("fastmcp"),
            "mcp": _package_version("mcp"),
            "openai_agents": _package_version("openai-agents"),
            "pydantic": _package_version("pydantic"),
        },
        start_time_utc=datetime.now(UTC),
    )


async def _expect_failure(
    client: Client[Any],
    name: str,
    arguments: dict[str, object],
) -> None:
    try:
        await client.call_tool(name, arguments, raise_on_error=True)
    except Exception:
        return
    raise RuntimeError(f"expected tool {name!r} to fail")


async def execute_scenario(client: Client[Any], scenario: Scenario) -> None:
    """Execute one deterministic scenario against an initialized client."""
    if scenario is Scenario.LIST_TOOLS:
        tools = await client.list_tools()
        if {tool.name for tool in tools} != {
            "echo_bytes",
            "sleep_ms",
            "roundtrip_payload",
            "fail_with",
        }:
            raise RuntimeError("fixture tool discovery did not match the ground truth")
    elif scenario is Scenario.ECHO:
        await client.call_tool("echo_bytes", {"n": 64})
    elif scenario is Scenario.SLEEP:
        await client.call_tool("sleep_ms", {"delay_ms": 20})
    elif scenario is Scenario.BACKEND_EXCEPTION:
        await _expect_failure(
            client,
            "fail_with",
            {"kind": FailureKind.BACKEND_EXCEPTION.value},
        )
    elif scenario is Scenario.TOOL_ERROR:
        await _expect_failure(client, "fail_with", {"kind": FailureKind.TOOL_ERROR.value})
    elif scenario is Scenario.TIMEOUT:
        await _expect_failure(client, "fail_with", {"kind": FailureKind.TIMEOUT.value})
    elif scenario is Scenario.NONEXISTENT_TOOL:
        await _expect_failure(client, "tool_does_not_exist", {})
    elif scenario is Scenario.CONCURRENT:
        await asyncio.gather(
            client.call_tool("sleep_ms", {"delay_ms": 30}),
            client.call_tool("sleep_ms", {"delay_ms": 20}),
            client.call_tool("sleep_ms", {"delay_ms": 10}),
        )
    elif scenario is Scenario.CANCELLATION:
        task = asyncio.create_task(client.call_tool("sleep_ms", {"delay_ms": 250}))
        await asyncio.sleep(0.02)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def run_fixture(
    *,
    scenario: Scenario,
    output_root: Path,
    repeat: int = 1,
    seed: int = 0,
) -> RunArtifacts:
    """Run one model-free trial and persist its manifest and canonical events."""
    if repeat < 1:
        raise ValueError("repeat must be at least one")

    manifest = create_manifest(scenario=scenario, seed=seed)
    run_directory = output_root / f"{scenario.value}-{manifest.run_id}"
    run_directory.mkdir(parents=True, exist_ok=False)
    manifest_path = run_directory / "manifest.json"
    events_path = run_directory / "events.jsonl"
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")

    sink = JsonlTraceSink.create(events_path)
    recorder = EventRecorder(
        manifest=manifest,
        sink=sink,
        component=Component.MCP_SERVER,
    )
    server = create_fixture_server(recorder)

    async with Client(server) as client:
        for _ in range(repeat):
            await execute_scenario(client, scenario)

    validate_completed_trace(sink.read_events())
    return RunArtifacts(
        run_directory=run_directory,
        manifest_path=manifest_path,
        events_path=events_path,
    )


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be at least one")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Scenario, choices=list(Scenario))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/phase1a"))
    parser.add_argument("--repeat", type=_positive_integer, default=1)
    parser.add_argument("--seed", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    artifacts = asyncio.run(
        run_fixture(
            scenario=args.scenario,
            output_root=args.output_dir,
            repeat=args.repeat,
            seed=args.seed,
        )
    )
    print(artifacts.run_directory.as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
