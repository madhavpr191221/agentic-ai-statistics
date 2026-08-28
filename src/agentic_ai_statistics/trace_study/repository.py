"""Read-only access to Phase 5 stochastic-trace artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast


class TraceStudyRepository:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def list_campaigns(self) -> list[dict[str, object]]:
        values = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in self.root.glob("campaign-*/analysis.json")
        ]
        return sorted(values, key=lambda item: str(item.get("created_at_utc", "")))

    def campaign(self, campaign_id: str) -> dict[str, object]:
        if not campaign_id or any(character in campaign_id for character in "/\\.."):
            raise KeyError(campaign_id)
        path = (self.root / f"campaign-{campaign_id}" / "analysis.json").resolve()
        if path.parent.parent != self.root or not path.is_file():
            raise KeyError(campaign_id)
        return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
