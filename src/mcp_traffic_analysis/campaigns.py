"""Run the frozen Phase 2 statistical baseline campaign."""

# ruff: noqa: ASYNC240 -- local filesystem orchestration is intentionally synchronous.

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import Literal, cast

from mcp_traffic_analysis.analysis.phase2_models import build_tables, fit_phase2_models
from mcp_traffic_analysis.experiments.campaign_models import (
    CampaignManifest,
    CampaignProgress,
    PlannedRun,
)
from mcp_traffic_analysis.experiments.condition_runner import ConditionSpec, run_condition

TRANSPORTS: tuple[Literal["in_memory", "stdio"], ...] = ("in_memory", "stdio")
PAYLOAD_SIZES = (64, 1_024, 16_384, 65_536)
SERVICE_TIMES_MS = (0, 20, 100)
CONCURRENCY_LEVELS = (1, 4)


def build_manifest(
    *,
    campaign_id: str,
    replicates: int,
    calls_per_run: int,
    seed: int,
) -> CampaignManifest:
    rng = random.Random(seed)
    planned: list[PlannedRun] = []
    execution_order = 1
    conditions = [
        ConditionSpec(
            transport=transport,
            payload_target_bytes=payload,
            service_time_ms=service,
            concurrency=concurrency,
            calls_per_run=calls_per_run,
        )
        for transport, payload, service, concurrency in product(
            TRANSPORTS,
            PAYLOAD_SIZES,
            SERVICE_TIMES_MS,
            CONCURRENCY_LEVELS,
        )
    ]
    for replicate in range(1, replicates + 1):
        block = list(conditions)
        rng.shuffle(block)
        for condition in block:
            planned.append(
                PlannedRun(
                    condition=condition,
                    replicate=replicate,
                    execution_order=execution_order,
                    run_seed=seed + execution_order,
                )
            )
            execution_order += 1
    return CampaignManifest(
        campaign_id=campaign_id,
        random_seed=seed,
        replicates=replicates,
        calls_per_run=calls_per_run,
        transports=TRANSPORTS,
        payload_sizes=PAYLOAD_SIZES,
        service_times_ms=SERVICE_TIMES_MS,
        concurrency_levels=CONCURRENCY_LEVELS,
        planned_runs=tuple(planned),
        created_at_utc=datetime.now(UTC),
    )


def _write_progress(path: Path, progress: CampaignProgress) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(progress.model_dump_json(indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _completed_keys(runs_directory: Path) -> set[tuple[str, int]]:
    completed: set[tuple[str, int]] = set()
    for path in runs_directory.glob("*/run_measurement.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        completed.add((str(payload["condition_id"]), int(payload["replicate"])))
    return completed


async def execute_campaign(args: argparse.Namespace) -> Path:
    output_root = cast(Path, args.output_root)
    campaign_id = cast(str, args.campaign_id)
    campaign_directory: Path = output_root / campaign_id
    manifest_path = campaign_directory / "campaign_manifest.json"
    runs_directory = campaign_directory / "runs"
    progress_path = campaign_directory / "progress.json"
    if campaign_directory.exists() and not args.resume:
        raise FileExistsError(f"campaign already exists: {campaign_directory}")
    campaign_directory.mkdir(parents=True, exist_ok=True)
    runs_directory.mkdir(exist_ok=True)
    if manifest_path.is_file():
        manifest = CampaignManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = build_manifest(
            campaign_id=args.campaign_id,
            replicates=args.replicates,
            calls_per_run=args.calls_per_run,
            seed=args.seed,
        )
        manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    completed = _completed_keys(runs_directory)
    planned_count = len(manifest.planned_runs)
    _write_progress(
        progress_path,
        CampaignProgress(
            campaign_id=manifest.campaign_id,
            status="running",
            planned_runs=planned_count,
            completed_runs=len(completed),
            updated_at_utc=datetime.now(UTC),
        ),
    )
    try:
        for planned in manifest.planned_runs:
            key = (planned.condition.condition_id, planned.replicate)
            if key in completed:
                continue
            await run_condition(
                spec=planned.condition,
                output_root=runs_directory,
                replicate=planned.replicate,
                execution_order=planned.execution_order,
                seed=planned.run_seed,
            )
            completed.add(key)
            _write_progress(
                progress_path,
                CampaignProgress(
                    campaign_id=manifest.campaign_id,
                    status="running",
                    planned_runs=planned_count,
                    completed_runs=len(completed),
                    current_execution_order=planned.execution_order,
                    updated_at_utc=datetime.now(UTC),
                ),
            )
    except BaseException as error:
        _write_progress(
            progress_path,
            CampaignProgress(
                campaign_id=manifest.campaign_id,
                status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
                planned_runs=planned_count,
                completed_runs=len(completed),
                error_type=type(error).__name__,
                updated_at_utc=datetime.now(UTC),
            ),
        )
        raise
    runs, calls = build_tables(campaign_directory)
    fit_phase2_models(
        campaign_directory,
        runs,
        calls,
        bootstrap_iterations=args.bootstrap_iterations,
        bootstrap_seed=args.seed,
    )
    _write_progress(
        progress_path,
        CampaignProgress(
            campaign_id=manifest.campaign_id,
            status="complete",
            planned_runs=planned_count,
            completed_runs=len(completed),
            updated_at_utc=datetime.now(UTC),
        ),
    )
    return campaign_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("design", choices=["baseline-v1"])
    parser.add_argument("--campaign-id", default="baseline-v1")
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/phase2"))
    parser.add_argument("--replicates", type=int, default=20)
    parser.add_argument("--calls-per-run", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--bootstrap-iterations", type=int, default=2_000)
    parser.add_argument("--resume", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.replicates < 1 or args.calls_per_run < 1 or args.bootstrap_iterations < 10:
        raise SystemExit(
            "replicates and calls must be positive; bootstrap iterations must be >= 10"
        )
    print(asyncio.run(execute_campaign(args)).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
