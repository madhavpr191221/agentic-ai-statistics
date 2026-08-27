"""Append-only JSONL storage for canonical trace events."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from mcp_traffic_analysis.measurement.models import TraceEvent


class JsonlTraceSink:
    """Write validated events to a newly created append-only JSONL file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()

    @classmethod
    def create(cls, path: Path) -> JsonlTraceSink:
        """Create a new empty trace file, refusing to overwrite an existing run."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=False)
        return cls(path)

    async def write(self, event: TraceEvent) -> None:
        """Append one durable JSON object followed by exactly one newline."""
        line = event.model_dump_json() + "\n"
        async with self._lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(line)
                stream.flush()
                os.fsync(stream.fileno())

    def read_events(self) -> list[TraceEvent]:
        """Read and validate all events currently stored in the sink."""
        return [
            TraceEvent.model_validate_json(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line
        ]
