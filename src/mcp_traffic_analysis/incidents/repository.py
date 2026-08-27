"""Read Phase 3 run and campaign artifacts without a database."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from uuid import UUID

from mcp_traffic_analysis.incidents.models import IncidentRunDetail


class IncidentRepository:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def list_runs(self) -> list[IncidentRunDetail]:
        results: list[IncidentRunDetail] = []
        for path in self.root.glob("incident-*/detail.json"):
            try:
                results.append(
                    IncidentRunDetail.model_validate_json(path.read_text(encoding="utf-8"))
                )
            except (ValueError, OSError):
                continue
        return sorted(results, key=lambda item: item.created_at_utc, reverse=True)

    def get(self, run_id: UUID) -> IncidentRunDetail:
        path = self.root / f"incident-{run_id}" / "detail.json"
        if not path.is_file():
            raise KeyError(str(run_id))
        return IncidentRunDetail.model_validate_json(path.read_text(encoding="utf-8"))

    def list_campaigns(self) -> list[dict[str, object]]:
        values = []
        for path in self.root.glob("campaign-*/analysis.json"):
            values.append(json.loads(path.read_text(encoding="utf-8")))
        return sorted(values, key=lambda item: str(item.get("created_at_utc", "")), reverse=True)

    def campaign(self, campaign_id: str) -> dict[str, object]:
        path = self.root / f"campaign-{campaign_id}" / "analysis.json"
        if not path.is_file():
            raise KeyError(campaign_id)
        return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
