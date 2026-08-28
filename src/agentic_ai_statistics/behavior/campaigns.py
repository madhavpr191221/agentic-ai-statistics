"""Collect or reanalyze the frozen Phase 4 task-structure campaigns."""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
from uuid import NAMESPACE_URL, uuid5

import pandas as pd  # type: ignore[import-untyped]

from agentic_ai_statistics.behavior.analysis import analyze_campaign
from agentic_ai_statistics.incidents.models import (
    IncidentRunDetail,
    IncidentScenario,
    TaskStructure,
)
from agentic_ai_statistics.incidents.runner import MODEL_ID, run_incident

StudyStage = Literal["pilot", "main"]
BLOCKS: dict[StudyStage, int] = {"pilot": 3, "main": 10}
SEEDS: dict[StudyStage, int] = {"pilot": 20260901, "main": 20260902}


def build_manifest(campaign_id: str, study_stage: StudyStage) -> dict[str, Any]:
    blocks = BLOCKS[study_stage]
    schedule: list[dict[str, Any]] = []
    execution_order = 0
    randomizer = random.Random(SEEDS[study_stage])
    for block in range(1, blocks + 1):
        cells = [
            (scenario, structure)
            for scenario in IncidentScenario
            for structure in TaskStructure
        ]
        randomizer.shuffle(cells)
        for scenario, structure in cells:
            execution_order += 1
            run_id = uuid5(
                NAMESPACE_URL,
                f"agentic-ai-statistics:{campaign_id}:{block}:{scenario.value}:{structure.value}",
            )
            schedule.append(
                {
                    "run_id": str(run_id),
                    "execution_order": execution_order,
                    "block": block,
                    "scenario_id": scenario.value,
                    "task_structure": structure.value,
                }
            )
    return {
        "schema_version": "4.0.0",
        "campaign_id": campaign_id,
        "study_stage": study_stage,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "experimental_unit": "one fresh agent run and MCP session",
        "model_id": MODEL_ID,
        "transport": "stdio",
        "blocks": blocks,
        "planned_runs": len(schedule),
        "seed": SEEDS[study_stage],
        "schedule": schedule,
        "pilot_included_in_main": False,
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def reanalyze(campaign_directory: Path) -> dict[str, Any]:
    manifest = json.loads(
        (campaign_directory / "campaign_manifest.json").read_text(encoding="utf-8")
    )
    details = [
        IncidentRunDetail.model_validate_json(path.read_text(encoding="utf-8"))
        for path in campaign_directory.glob("incident-*/detail.json")
    ]
    details = [detail for detail in details if detail.behavior is not None]
    analysis, tables = analyze_campaign(
        details, str(manifest["campaign_id"]), str(manifest["study_stage"])
    )
    raw_mcp_rows: list[dict[str, Any]] = []
    raw_model_rows: list[dict[str, Any]] = []
    for detail in details:
        if detail.behavior is None:
            continue
        directory = campaign_directory / f"incident-{detail.run_id}"
        common = {
            "run_id": str(detail.run_id),
            "scenario_id": detail.scenario_id.value,
            "task_structure": detail.behavior.task_structure.value,
            "block": detail.behavior.block,
        }
        for name, destination in (
            ("mcp_events.jsonl", raw_mcp_rows),
            ("model_calls.jsonl", raw_model_rows),
        ):
            path = directory / name
            if not path.is_file():
                continue
            for order, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
                if line:
                    destination.append(common | {"call_order": order} | json.loads(line))
    tables["mcp_calls"] = pd.DataFrame(raw_mcp_rows)
    tables["model_calls"] = pd.DataFrame(raw_model_rows)
    _write_json(campaign_directory / "analysis.json", analysis)
    table_directory = campaign_directory / "tables"
    table_directory.mkdir(exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(table_directory / f"{name}.csv", index=False)
        frame.to_parquet(table_directory / f"{name}.parquet", index=False)
    return analysis


async def run_campaign(
    *,
    campaign_id: str,
    study_stage: StudyStage,
    output_root: Path,
    mode: Literal["live", "deterministic"],
    resume: bool,
) -> Path:
    campaign_directory = output_root / f"campaign-{campaign_id}"
    manifest_path = campaign_directory / "campaign_manifest.json"
    if manifest_path.is_file():
        if not resume:
            raise FileExistsError(
                f"campaign already exists: {campaign_directory}; use --resume or --analyze-only"
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["study_stage"] != study_stage:
            raise ValueError("existing campaign stage does not match the requested stage")
    else:
        if campaign_directory.exists() and any(campaign_directory.iterdir()):
            raise FileExistsError(f"non-empty campaign directory: {campaign_directory}")
        campaign_directory.mkdir(parents=True, exist_ok=True)
        manifest = build_manifest(campaign_id, study_stage)
        _write_json(manifest_path, manifest)
    schedule = cast(list[dict[str, Any]], manifest["schedule"])
    completed = 0
    for item in schedule:
        run_id = uuid5(
            NAMESPACE_URL,
            f"agentic-ai-statistics:{campaign_id}:{item['block']}:"
            f"{item['scenario_id']}:{item['task_structure']}",
        )
        detail_path = campaign_directory / f"incident-{run_id}" / "detail.json"
        if not detail_path.is_file():
            await run_incident(
                scenario=IncidentScenario(item["scenario_id"]),
                task_structure=TaskStructure(item["task_structure"]),
                output_root=campaign_directory,
                mode=mode,
                run_id=run_id,
                execution_order=int(item["execution_order"]),
                block=int(item["block"]),
            )
        completed += 1
        _write_json(
            campaign_directory / "progress.json",
            {
                "status": "running" if completed < len(schedule) else "complete",
                "completed_runs": completed,
                "planned_runs": len(schedule),
                "updated_at_utc": datetime.now(UTC).isoformat(),
            },
        )
    reanalyze(campaign_directory)
    return campaign_directory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign_id")
    parser.add_argument("--stage", choices=["pilot", "main"], required=True)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/phase4"))
    parser.add_argument("--mode", choices=["live", "deterministic"], default="live")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    campaign_directory = args.output_root / f"campaign-{args.campaign_id}"
    if args.analyze_only:
        reanalyze(campaign_directory)
        print(campaign_directory.as_posix())
        return 0
    path = asyncio.run(
        run_campaign(
            campaign_id=args.campaign_id,
            study_stage=args.stage,
            output_root=args.output_root,
            mode=args.mode,
            resume=args.resume,
        )
    )
    print(path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
