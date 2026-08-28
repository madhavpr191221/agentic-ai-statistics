"""Run the frozen Phase 3 repeated-measures incident campaign."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from agentic_ai_statistics.incidents.models import IncidentRunDetail, IncidentScenario
from agentic_ai_statistics.incidents.runner import run_incident


def distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "median": None, "iqr": None, "p90": None, "p95": None}
    series = pd.Series(values, dtype="float64")
    return {
        "n": len(values),
        "median": float(series.median()),
        "iqr": float(series.quantile(0.75) - series.quantile(0.25)),
        "p90": float(series.quantile(0.90)),
        "p95": float(series.quantile(0.95)),
    }


def wilson(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return center - half, center + half


def normalized_edit_distance(left: list[str], right: list[str]) -> float:
    if not left and not right:
        return 0.0
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1] / max(len(left), len(right))


def analyze(details: list[IncidentRunDetail], campaign_id: str) -> dict[str, Any]:
    rows = [
        item.measurement.model_dump(mode="json")
        | {
            "task_success": item.score.task_success,
            "created_at_utc": item.created_at_utc.isoformat(),
        }
        for item in details
    ]
    success = sum(bool(row["task_success"]) for row in rows)
    low, high = wilson(success, len(rows))
    sequences = [tuple(item.measurement.tool_sequence) for item in details]
    within_scenario_distances: list[float] = []
    by_scenario: dict[str, Any] = {}
    for scenario in IncidentScenario:
        group = [item for item in details if item.scenario_id is scenario]
        wins = sum(item.score.task_success for item in group)
        lo, hi = wilson(wins, len(group))
        latencies = [item.measurement.total_latency_ms for item in group]
        group_sequences = [tuple(item.measurement.tool_sequence) for item in group]
        group_distances = [
            normalized_edit_distance(list(left), list(right))
            for index, left in enumerate(group_sequences)
            for right in group_sequences[index + 1 :]
        ]
        within_scenario_distances.extend(group_distances)
        group_modal = Counter(group_sequences).most_common(1)
        by_scenario[scenario.value] = {
            "n": len(group),
            "successes": wins,
            "success_rate": wins / len(group) if group else None,
            "wilson_95": [lo, hi],
            "latency_ms": distribution(latencies),
            "tokens": distribution([float(item.measurement.total_tokens) for item in group]),
            "unique_tool_sequences": len(set(group_sequences)),
            "modal_sequence_fraction": group_modal[0][1] / len(group) if group_modal else None,
            "mean_pairwise_normalized_edit_distance": (
                sum(group_distances) / len(group_distances) if group_distances else 0.0
            ),
            "runs_with_rejected_action": sum(
                any(not action.accepted for action in item.actions) for item in group
            ),
        }
    modal = Counter(sequences).most_common(1)
    return {
        "campaign_id": campaign_id,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "experimental_unit": "one fresh agent run and MCP session",
        "n_runs": len(details),
        "successes": success,
        "success_rate": success / len(details) if details else None,
        "success_rate_wilson_95": [low, high],
        "by_scenario": by_scenario,
        "failure_types": dict(Counter(item.measurement.failure_type or "none" for item in details)),
        "runs_with_rejected_action": sum(
            any(not action.accepted for action in item.actions) for item in details
        ),
        "total_latency_ms": distribution([item.measurement.total_latency_ms for item in details]),
        "total_tokens": distribution([float(item.measurement.total_tokens) for item in details]),
        "request_frame_bytes": distribution(
            [float(item.measurement.request_frame_bytes) for item in details]
        ),
        "response_frame_bytes": distribution(
            [float(item.measurement.response_frame_bytes) for item in details]
        ),
        "model_calls": distribution([float(item.measurement.model_call_count) for item in details]),
        "mcp_calls": distribution([float(item.measurement.mcp_call_count) for item in details]),
        "total_estimated_cost_usd": sum(item.measurement.estimated_cost_usd for item in details),
        "unique_tool_sequences": len(set(sequences)),
        "modal_sequence": list(modal[0][0]) if modal else [],
        "modal_sequence_fraction": modal[0][1] / len(sequences) if modal else None,
        "mean_within_scenario_pairwise_normalized_edit_distance": (
            sum(within_scenario_distances) / len(within_scenario_distances)
            if within_scenario_distances
            else 0.0
        ),
        "notes": [
            "Scenario comparisons are exploratory.",
            "p90 and p95 are descriptive at n=10 per scenario.",
        ],
        "runs": rows,
    }


def reanalyze_campaign(campaign_dir: Path, campaign_id: str) -> dict[str, Any]:
    details = [
        IncidentRunDetail.model_validate_json(path.read_text(encoding="utf-8"))
        for path in campaign_dir.glob("incident-*/detail.json")
    ]
    analysis = analyze(details, campaign_id)
    model_latencies: list[tuple[int, float]] = []
    for detail in details:
        path = campaign_dir / f"incident-{detail.run_id}" / "model_calls.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            if item["latency_ms"] is not None:
                model_latencies.append((int(item["call_index"]), float(item["latency_ms"])))
    analysis["model_call_latency_ms"] = {
        "first": distribution([value for index, value in model_latencies if index == 0]),
        "later": distribution([value for index, value in model_latencies if index > 0]),
    }
    (campaign_dir / "analysis.json").write_text(
        json.dumps(analysis, indent=2) + "\n", encoding="utf-8"
    )
    return analysis


async def run_campaign(campaign_id: str, output_root: Path, mode: str) -> Path:
    campaign_dir = output_root / f"campaign-{campaign_id}"
    campaign_dir.mkdir(parents=True, exist_ok=False)
    schedule = [(block, scenario) for block in range(1, 11) for scenario in IncidentScenario]
    random.Random(20260828).shuffle(schedule)
    manifest = {
        "campaign_id": campaign_id,
        "seed": 20260828,
        "blocks": 10,
        "planned_runs": len(schedule),
        "schedule": [{"block": b, "scenario": s.value} for b, s in schedule],
    }
    (campaign_dir / "campaign_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    details: list[IncidentRunDetail] = []
    for order, (block, scenario) in enumerate(schedule, 1):
        detail = await run_incident(
            scenario=scenario,
            output_root=campaign_dir,
            mode=mode,
            execution_order=order,
            block=block,
        )
        details.append(detail)
        (campaign_dir / "progress.json").write_text(
            json.dumps({"completed": order, "planned": len(schedule)}, indent=2) + "\n",
            encoding="utf-8",
        )
    analysis = reanalyze_campaign(campaign_dir, campaign_id)
    tables = campaign_dir / "tables"
    tables.mkdir()
    frame = pd.DataFrame(analysis["runs"])
    frame.to_csv(tables / "runs.csv", index=False)
    frame.to_parquet(tables / "runs.parquet", index=False)
    model_rows: list[dict[str, Any]] = []
    mcp_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    for detail in details:
        directory = campaign_dir / f"incident-{detail.run_id}"
        for line in (directory / "model_calls.jsonl").read_text(encoding="utf-8").splitlines():
            model_rows.append(
                {"run_id": str(detail.run_id), "scenario_id": detail.scenario_id.value}
                | json.loads(line)
            )
        mcp_events_path = directory / "mcp_events.jsonl"
        mcp_lines = (
            mcp_events_path.read_text(encoding="utf-8").splitlines()
            if mcp_events_path.is_file()
            else []
        )
        for order, line in enumerate(mcp_lines):
            mcp_rows.append(
                {
                    "run_id": str(detail.run_id),
                    "scenario_id": detail.scenario_id.value,
                    "call_order": order,
                }
                | json.loads(line)
            )
        for action in detail.actions:
            action_rows.append(
                {"run_id": str(detail.run_id), "scenario_id": detail.scenario_id.value}
                | action.model_dump(mode="json")
            )
        trace_rows.append(
            {
                "run_id": str(detail.run_id),
                "scenario_id": detail.scenario_id.value,
                "task_success": detail.score.task_success,
                "n_calls": detail.measurement.mcp_call_count,
                "tool_sequence": " > ".join(detail.measurement.tool_sequence),
            }
        )
    for name, rows in {
        "model_calls": model_rows,
        "mcp_calls": mcp_rows,
        "actions": action_rows,
        "traces": trace_rows,
    }.items():
        table = pd.DataFrame(rows)
        table.to_csv(tables / f"{name}.csv", index=False)
        table.to_parquet(tables / f"{name}.parquet", index=False)
    return campaign_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign_id", nargs="?", default="incident-pilot-v2")
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/phase3"))
    parser.add_argument("--mode", choices=["live", "deterministic"], default="live")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    if args.analyze_only:
        path = args.output_root / f"campaign-{args.campaign_id}"
        reanalyze_campaign(path, args.campaign_id)
        print(path)
        return 0
    path = asyncio.run(run_campaign(args.campaign_id, args.output_root, args.mode))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
