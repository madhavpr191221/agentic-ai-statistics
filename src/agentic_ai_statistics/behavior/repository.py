"""Read-only access to Phase 4 behavior artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from uuid import UUID

from agentic_ai_statistics.incidents.models import IncidentRunDetail


class BehaviorRepository:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def list_runs(self) -> list[IncidentRunDetail]:
        details = [
            IncidentRunDetail.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self.root.glob("incident-*/detail.json")
        ]
        return sorted(
            (detail for detail in details if detail.behavior is not None),
            key=lambda detail: detail.created_at_utc,
            reverse=True,
        )

    def get(self, run_id: UUID) -> IncidentRunDetail:
        path = self.root / f"incident-{run_id}" / "detail.json"
        if not path.is_file():
            raise KeyError(run_id)
        detail = IncidentRunDetail.model_validate_json(path.read_text(encoding="utf-8"))
        if detail.behavior is None:
            raise KeyError(run_id)
        return detail

    def list_campaigns(self) -> list[dict[str, object]]:
        items = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in self.root.glob("campaign-*/analysis.json")
        ]
        return sorted(items, key=lambda item: str(item.get("created_at_utc", "")))

    def campaign(self, campaign_id: str) -> dict[str, object]:
        if not campaign_id or any(character in campaign_id for character in "/\\.."):
            raise KeyError(campaign_id)
        path = (self.root / f"campaign-{campaign_id}" / "analysis.json").resolve()
        if path.parent.parent != self.root or not path.is_file():
            raise KeyError(campaign_id)
        return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
