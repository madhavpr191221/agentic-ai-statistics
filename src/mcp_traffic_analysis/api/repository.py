"""Safe access to completed experiment artifacts below one configured root."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from mcp_traffic_analysis.measurement.models import ExperimentManifest, TraceEvent
from mcp_traffic_analysis.measurement.validation import validate_completed_trace


class RunNotFoundError(LookupError):
    """Raised when a run identifier does not exist below the artifact root."""


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    directory: Path
    manifest: ExperimentManifest
    events: tuple[TraceEvent, ...]


class ArtifactRepository:
    """Discover and validate run artifacts without accepting user-controlled paths."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def read_directory(directory: Path) -> ArtifactRecord:
        manifest = ExperimentManifest.model_validate_json(
            (directory / "manifest.json").read_text(encoding="utf-8")
        )
        events = tuple(
            TraceEvent.model_validate_json(line)
            for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()
            if line
        )
        validate_completed_trace(events)
        return ArtifactRecord(directory=directory, manifest=manifest, events=events)

    def list_records(self) -> list[ArtifactRecord]:
        records = [
            self.read_directory(manifest_path.parent)
            for manifest_path in self.root.glob("*/manifest.json")
            if (manifest_path.parent / "events.jsonl").is_file()
        ]
        return sorted(records, key=lambda record: record.manifest.start_time_utc, reverse=True)

    def get(self, run_id: UUID) -> ArtifactRecord:
        for record in self.list_records():
            if record.manifest.run_id == run_id:
                return record
        raise RunNotFoundError(str(run_id))
