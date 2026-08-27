"""Subprocess entry point for the deterministic FastMCP stdio fixture."""

from __future__ import annotations

import argparse
from pathlib import Path

from mcp_traffic_analysis.fixtures.server import create_fixture_server
from mcp_traffic_analysis.measurement.models import Component, ExperimentManifest
from mcp_traffic_analysis.measurement.recorder import EventRecorder
from mcp_traffic_analysis.measurement.sink import JsonlTraceSink


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    args = parser.parse_args()
    manifest = ExperimentManifest.model_validate_json(args.manifest.read_text(encoding="utf-8"))
    recorder = EventRecorder(
        manifest=manifest,
        sink=JsonlTraceSink.create(args.events),
        component=Component.MCP_SERVER,
    )
    create_fixture_server(recorder).run(transport="stdio", show_banner=False, log_level="WARNING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
