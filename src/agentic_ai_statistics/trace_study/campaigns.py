"""Reanalyse Phase 4 traces or collect the frozen Phase 5 repetition campaign."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
from uuid import NAMESPACE_URL, uuid5

import pandas as pd  # type: ignore[import-untyped]

from agentic_ai_statistics.incidents.models import (
    IncidentRunDetail,
    IncidentScenario,
    TaskStructure,
)
from agentic_ai_statistics.incidents.runner import (
    AGENT_INSTRUCTIONS,
    MODEL_ID,
    run_incident,
)
from agentic_ai_statistics.incidents.world import INCOMING_MESSAGES, SCENARIOS, oracle_sequence
from agentic_ai_statistics.trace_study.analysis import analyze_details

StudyStage = Literal["exploratory", "smoke", "main"]
FOCUSED_SCENARIO = IncidentScenario.ORDERS_API_OUTAGE
FOCUSED_STRUCTURE = TaskStructure.RECOVERY
DEFAULT_RUNS: dict[StudyStage, int] = {"exploratory": 0, "smoke": 3, "main": 100}
DEFAULT_COST_LIMIT_USD = 5.0
PROVIDER_FAILURE_TYPES = frozenset(
    {
        "APIConnectionError",
        "APITimeoutError",
        "AuthenticationError",
        "BadRequestError",
        "InternalServerError",
        "NotFoundError",
        "PermissionDeniedError",
        "RateLimitError",
        "UnprocessableEntityError",
    }
)


def cost_limit_reached(
    accumulated_cost_usd: float,
    limit_usd: float,
    mode: Literal["live", "deterministic"],
) -> bool:
    return mode == "live" and accumulated_cost_usd >= limit_usd


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def _write_tables(directory: Path, tables: dict[str, pd.DataFrame]) -> None:
    table_directory = directory / "tables"
    table_directory.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(table_directory / f"{name}.csv", index=False)
        frame.to_parquet(table_directory / f"{name}.parquet", index=False)


def _write_scalar_artifacts(directory: Path, analysis: dict[str, Any]) -> None:
    """Write auditable scalar artifacts with their statistical contracts."""
    _write_json(directory / "q01_data_dictionary.json", {
        "schema_version": "12.0.0",
        "question_id": "Q01",
        "campaign_id": analysis["campaign_id"],
        "unit": "run",
        "measurement_status": "measured_metadata",
        "n_runs": analysis["n_runs"],
        "variables": analysis["scalar_data_dictionary"],
    })
    _write_json(directory / "q02_scalar_distributions.json", {
        "schema_version": "12.0.0",
        "question_id": "Q02",
        "campaign_id": analysis["campaign_id"],
        "unit": "run",
        "estimand": "marginal empirical distributions of run-level scalar outcomes",
        "method": "summary statistics, empirical CDF, and reproducible bootstrap intervals",
        "uncertainty": "percentile bootstrap for means and medians; Wilson interval for success",
        "n_runs": analysis["n_runs"],
        "distributions": analysis["scalar_distributions"],
        "limitations": ["Results describe repeated runs under this campaign configuration."],
    })
    _write_json(directory / "q03_batch_stability.json", {
        "schema_version": "12.0.0",
        "question_id": "Q03",
        "campaign_id": analysis["campaign_id"],
        "unit": "run",
        "estimand": "descriptive outcome summaries by acquisition batch",
        "method": "ordered batch table with Wilson intervals for proportions",
        "uncertainty": "descriptive intervals; no time-series model",
        "n_runs": analysis["n_runs"],
        "batches": analysis["batch_summaries"],
        "limitations": ["Batch comparisons diagnose possible drift but do not prove it."],
    })


def frozen_configuration() -> dict[str, Any]:
    scenario_definition = SCENARIOS[FOCUSED_SCENARIO].model_dump(mode="json")
    for field in (
        "diagnosis_terms",
        "diagnosis_any_terms",
        "required_evidence_ids",
        "prohibited_actions",
    ):
        scenario_definition[field] = sorted(scenario_definition[field])
    return {
        "scenario_id": FOCUSED_SCENARIO.value,
        "task_structure": FOCUSED_STRUCTURE.value,
        "incoming_message": INCOMING_MESSAGES[FOCUSED_SCENARIO],
        "oracle_sequence": oracle_sequence(FOCUSED_SCENARIO, FOCUSED_STRUCTURE),
        "scenario_definition": scenario_definition,
        "agent_instructions": AGENT_INSTRUCTIONS,
        "tool_names": [
            "get_alert",
            "get_metrics",
            "search_logs",
            "get_dependencies",
            "get_recent_changes",
            "get_runbook",
            "restart_service",
            "rollback_deployment",
            "escalate_incident",
            "update_incident",
        ],
        "model_id": MODEL_ID,
        "transport": "stdio",
        "reasoning_effort": "low",
        "verbosity": "low",
        "parallel_tool_calls": False,
        "max_turns": 12,
    }


def configuration_fingerprint() -> str:
    payload = json.dumps(frozen_configuration(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_manifest(
    campaign_id: str,
    study_stage: StudyStage,
    *,
    planned_runs: int | None = None,
    mode: Literal["live", "deterministic"] = "live",
) -> dict[str, Any]:
    count = DEFAULT_RUNS[study_stage] if planned_runs is None else planned_runs
    if study_stage == "exploratory" or count < 1:
        raise ValueError("collected campaigns require smoke or main stage and positive runs")
    schedule = []
    for execution_order in range(1, count + 1):
        batch = (execution_order - 1) // 10 + 1
        run_id = uuid5(
            NAMESPACE_URL,
            f"agentic-ai-statistics:phase5:{campaign_id}:{execution_order}",
        )
        schedule.append(
            {
                "run_id": str(run_id),
                "execution_order": execution_order,
                "batch": batch,
                "scenario_id": FOCUSED_SCENARIO.value,
                "task_structure": FOCUSED_STRUCTURE.value,
            }
        )
    return {
        "schema_version": "5.0.0",
        "campaign_id": campaign_id,
        "study_stage": study_stage,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "experimental_unit": "one fresh agent run and MCP session",
        "planned_runs": count,
        "planned_batches": (count - 1) // 10 + 1,
        "mode": mode,
        "pilot_included_in_main": False,
        "smoke_included_in_main": False,
        "configuration": frozen_configuration(),
        "configuration_fingerprint_sha256": configuration_fingerprint(),
        "schedule": schedule,
    }


def _load_details(campaign_directory: Path) -> list[IncidentRunDetail]:
    return [
        IncidentRunDetail.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(campaign_directory.glob("incident-*/detail.json"))
    ]


def _load_quarantined_details(campaign_directory: Path) -> list[IncidentRunDetail]:
    return [
        IncidentRunDetail.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(campaign_directory.glob("excluded_attempts/*/detail.json"))
    ]


def is_scientific_observation(detail: IncidentRunDetail) -> bool:
    return (
        detail.measurement.correlation_consistent
        and detail.measurement.failure_type not in PROVIDER_FAILURE_TYPES
    )


def quarantine_incomplete_run(campaign_directory: Path, run_id: str) -> Path | None:
    run_directory = campaign_directory / f"incident-{run_id}"
    if not run_directory.exists() or (run_directory / "detail.json").is_file():
        return None
    quarantine_root = campaign_directory / "incomplete_runs"
    quarantine_root.mkdir(exist_ok=True)
    suffix = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = quarantine_root / f"incident-{run_id}-{suffix}"
    run_directory.rename(destination)
    return destination


def quarantine_excluded_attempt(campaign_directory: Path, run_id: str) -> Path | None:
    run_directory = campaign_directory / f"incident-{run_id}"
    detail_path = run_directory / "detail.json"
    if not detail_path.is_file():
        return None
    detail = IncidentRunDetail.model_validate_json(detail_path.read_text(encoding="utf-8"))
    if is_scientific_observation(detail):
        return None
    quarantine_root = campaign_directory / "excluded_attempts"
    quarantine_root.mkdir(exist_ok=True)
    suffix = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = quarantine_root / f"incident-{run_id}-{suffix}"
    run_directory.rename(destination)
    return destination


def analyze_collected_campaign(campaign_directory: Path) -> dict[str, Any]:
    manifest = json.loads(
        (campaign_directory / "campaign_manifest.json").read_text(encoding="utf-8")
    )
    attempted_details = _load_details(campaign_directory)
    details = [detail for detail in attempted_details if is_scientific_observation(detail)]
    excluded_details = [
        detail for detail in attempted_details if not is_scientific_observation(detail)
    ]
    excluded_details.extend(_load_quarantined_details(campaign_directory))
    analysis, tables = analyze_details(
        details,
        campaign_id=str(manifest["campaign_id"]),
        study_stage=str(manifest["study_stage"]),
    )
    analysis["planned_runs"] = int(manifest["planned_runs"])
    analysis["campaign_complete"] = len(details) == int(manifest["planned_runs"])
    analysis["configuration_fingerprint_sha256"] = manifest[
        "configuration_fingerprint_sha256"
    ]
    scientific_cost = sum(
        detail.measurement.estimated_cost_usd for detail in details
    )
    excluded_cost = sum(
        detail.measurement.estimated_cost_usd for detail in excluded_details
    )
    analysis["scientific_estimated_cost_usd"] = scientific_cost
    analysis["excluded_attempt_estimated_cost_usd"] = excluded_cost
    analysis["total_estimated_cost_usd"] = scientific_cost + excluded_cost
    analysis["excluded_attempts"] = len(excluded_details)
    analysis["excluded_provider_attempts"] = sum(
        detail.measurement.failure_type in PROVIDER_FAILURE_TYPES
        for detail in excluded_details
    )
    analysis["excluded_measurement_attempts"] = sum(
        not detail.measurement.correlation_consistent for detail in excluded_details
    )
    analysis["excluded_provider_failure_types"] = dict(
        sorted(
            Counter(
                detail.measurement.failure_type or "unknown" for detail in excluded_details
            ).items()
        )
    )
    _write_json(campaign_directory / "analysis.json", analysis)
    _write_tables(campaign_directory, tables)
    _write_scalar_artifacts(campaign_directory, analysis)
    return analysis


def reanalyze_phase4(
    source_campaign: Path,
    *,
    output_root: Path,
    campaign_id: str = "phase4-main-reanalysis-v1",
) -> Path:
    source_manifest = json.loads(
        (source_campaign / "campaign_manifest.json").read_text(encoding="utf-8")
    )
    details = _load_details(source_campaign)
    if len(details) != 90 or str(source_manifest.get("study_stage")) != "main":
        raise ValueError("Phase 5A requires the complete 90-run Phase 4 main campaign")
    campaign_directory = output_root / f"campaign-{campaign_id}"
    campaign_directory.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "5.0.0",
        "campaign_id": campaign_id,
        "study_stage": "exploratory",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_campaign_id": source_manifest["campaign_id"],
        "source_run_count": len(details),
        "new_model_calls": 0,
        "pilot_included_in_main": False,
    }
    analysis, tables = analyze_details(
        details, campaign_id=campaign_id, study_stage="exploratory"
    )
    analysis["source_campaign_id"] = source_manifest["campaign_id"]
    analysis["campaign_complete"] = True
    analysis["new_model_calls"] = 0
    _write_json(campaign_directory / "campaign_manifest.json", manifest)
    _write_json(campaign_directory / "analysis.json", analysis)
    _write_tables(campaign_directory, tables)
    _write_scalar_artifacts(campaign_directory, analysis)
    return campaign_directory


async def run_campaign(
    *,
    campaign_id: str,
    study_stage: Literal["smoke", "main"],
    output_root: Path,
    mode: Literal["live", "deterministic"] = "live",
    resume: bool = False,
    max_estimated_cost_usd: float = DEFAULT_COST_LIMIT_USD,
    planned_runs: int | None = None,
) -> Path:
    campaign_directory = output_root / f"campaign-{campaign_id}"
    manifest_path = campaign_directory / "campaign_manifest.json"
    if manifest_path.is_file():
        if not resume:
            raise FileExistsError(
                f"campaign already exists: {campaign_directory}; use --resume or --analyze-only"
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if mode == "live" and int(manifest["planned_runs"]) != DEFAULT_RUNS[study_stage]:
            raise ValueError("live Phase 5 campaign size differs from the frozen protocol")
        expected = build_manifest(
            campaign_id,
            study_stage,
            planned_runs=int(manifest["planned_runs"]),
            mode=mode,
        )
        if manifest.get("configuration_fingerprint_sha256") != configuration_fingerprint():
            raise ValueError("frozen Phase 5 configuration changed; start a new campaign")
        for field in ("campaign_id", "study_stage", "planned_runs", "mode", "schedule"):
            if manifest.get(field) != expected.get(field):
                raise ValueError(f"existing campaign {field} does not match the request")
    else:
        if campaign_directory.exists() and any(campaign_directory.iterdir()):
            raise FileExistsError(f"non-empty campaign directory: {campaign_directory}")
        campaign_directory.mkdir(parents=True, exist_ok=True)
        manifest = build_manifest(
            campaign_id, study_stage, planned_runs=planned_runs, mode=mode
        )
        _write_json(manifest_path, manifest)

    schedule = cast(list[dict[str, Any]], manifest["schedule"])
    attempted = _load_details(campaign_directory)
    all_attempts = [*attempted, *_load_quarantined_details(campaign_directory)]
    completed = [detail for detail in attempted if is_scientific_observation(detail)]
    accumulated_cost = sum(
        item.measurement.estimated_cost_usd for item in all_attempts
    )
    completed_ids = {str(item.run_id) for item in completed}
    stopped_for_cost = False
    for item in schedule:
        if str(item["run_id"]) in completed_ids:
            continue
        if cost_limit_reached(accumulated_cost, max_estimated_cost_usd, mode):
            stopped_for_cost = True
            break
        quarantine_excluded_attempt(campaign_directory, str(item["run_id"]))
        quarantine_incomplete_run(campaign_directory, str(item["run_id"]))
        detail = await run_incident(
            scenario=FOCUSED_SCENARIO,
            task_structure=FOCUSED_STRUCTURE,
            output_root=campaign_directory,
            mode=mode,
            run_id=uuid5(
                NAMESPACE_URL,
                f"agentic-ai-statistics:phase5:{campaign_id}:{item['execution_order']}",
            ),
            execution_order=int(item["execution_order"]),
            block=int(item["batch"]),
        )
        completed_ids.add(str(detail.run_id))
        accumulated_cost += detail.measurement.estimated_cost_usd
        if not is_scientific_observation(detail):
            completed_ids.remove(str(detail.run_id))
            _write_json(
                campaign_directory / "progress.json",
                {
                    "status": "provider_failure",
                    "completed_runs": len(completed_ids),
                    "planned_runs": len(schedule),
                    "failed_execution_order": item["execution_order"],
                    "failure_type": detail.measurement.failure_type,
                    "estimated_cost_usd": accumulated_cost,
                    "cost_limit_usd": max_estimated_cost_usd,
                    "updated_at_utc": datetime.now(UTC).isoformat(),
                },
            )
            break
        _write_json(
            campaign_directory / "progress.json",
            {
                "status": (
                    "complete" if len(completed_ids) == len(schedule) else "running"
                ),
                "completed_runs": len(completed_ids),
                "planned_runs": len(schedule),
                "estimated_cost_usd": accumulated_cost,
                "cost_limit_usd": max_estimated_cost_usd,
                "updated_at_utc": datetime.now(UTC).isoformat(),
            },
        )
    if stopped_for_cost:
        _write_json(
            campaign_directory / "progress.json",
            {
                "status": "cost_limit_reached",
                "completed_runs": len(completed_ids),
                "planned_runs": len(schedule),
                "estimated_cost_usd": accumulated_cost,
                "cost_limit_usd": max_estimated_cost_usd,
                "updated_at_utc": datetime.now(UTC).isoformat(),
            },
        )
    analyze_collected_campaign(campaign_directory)
    return campaign_directory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    reuse = subparsers.add_parser("reanalyze-phase4")
    reuse.add_argument(
        "--source-campaign",
        type=Path,
        default=Path("artifacts/phase4/campaign-task-structure-main-v1"),
    )
    reuse.add_argument("--output-root", type=Path, default=Path("artifacts/phase5"))
    reuse.add_argument("--campaign-id", default="phase4-main-reanalysis-v1")

    collect = subparsers.add_parser("collect")
    collect.add_argument("campaign_id")
    collect.add_argument("--stage", choices=["smoke", "main"], required=True)
    collect.add_argument("--output-root", type=Path, default=Path("artifacts/phase5"))
    collect.add_argument("--mode", choices=["live", "deterministic"], default="live")
    collect.add_argument("--resume", action="store_true")
    collect.add_argument("--analyze-only", action="store_true")
    collect.add_argument(
        "--max-estimated-cost-usd", type=float, default=DEFAULT_COST_LIMIT_USD
    )
    args = parser.parse_args()
    if args.command == "reanalyze-phase4":
        path = reanalyze_phase4(
            args.source_campaign,
            output_root=args.output_root,
            campaign_id=args.campaign_id,
        )
    else:
        campaign_directory = args.output_root / f"campaign-{args.campaign_id}"
        if args.analyze_only:
            analyze_collected_campaign(campaign_directory)
            path = campaign_directory
        else:
            path = asyncio.run(
                run_campaign(
                    campaign_id=args.campaign_id,
                    study_stage=args.stage,
                    output_root=args.output_root,
                    mode=args.mode,
                    resume=args.resume,
                    max_estimated_cost_usd=args.max_estimated_cost_usd,
                )
            )
    print(path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
