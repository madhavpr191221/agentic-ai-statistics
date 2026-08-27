"""Read-only access to persisted Phase 2 campaign artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp_traffic_analysis.experiments.campaign_models import CampaignManifest, CampaignProgress


class CampaignNotFoundError(LookupError):
    pass


class CampaignRepository:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def directory(self, campaign_id: str) -> Path:
        if not campaign_id or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789-_"
            for character in campaign_id.lower()
        ):
            raise CampaignNotFoundError(campaign_id)
        directory = (self.root / campaign_id).resolve()
        if directory.parent != self.root or not (directory / "campaign_manifest.json").is_file():
            raise CampaignNotFoundError(campaign_id)
        return directory

    def list(self) -> list[tuple[CampaignManifest, CampaignProgress]]:
        records: list[tuple[CampaignManifest, CampaignProgress]] = []
        for path in self.root.glob("*/campaign_manifest.json"):
            progress_path = path.parent / "progress.json"
            if not progress_path.is_file():
                continue
            records.append(
                (
                    CampaignManifest.model_validate_json(path.read_text(encoding="utf-8")),
                    CampaignProgress.model_validate_json(progress_path.read_text(encoding="utf-8")),
                )
            )
        return sorted(records, key=lambda item: item[0].created_at_utc, reverse=True)

    def get(
        self, campaign_id: str
    ) -> tuple[CampaignManifest, CampaignProgress, dict[str, Any] | None]:
        directory = self.directory(campaign_id)
        manifest = CampaignManifest.model_validate_json(
            (directory / "campaign_manifest.json").read_text(encoding="utf-8")
        )
        progress = CampaignProgress.model_validate_json(
            (directory / "progress.json").read_text(encoding="utf-8")
        )
        analysis_path = directory / "analysis.json"
        analysis = (
            json.loads(analysis_path.read_text(encoding="utf-8"))
            if analysis_path.is_file()
            else None
        )
        return manifest, progress, analysis
