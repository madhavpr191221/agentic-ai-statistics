"""Auditable Phase 5 trace summaries built from complete agent runs."""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict, deque
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from mcp_traffic_analysis.incidents.models import ActionRecord, IncidentRunDetail

ACTION_TOOLS = frozenset(
    {"restart_service", "rollback_deployment", "escalate_incident"}
)
FOCUSED_SCENARIO = "orders_api_outage"
FOCUSED_STRUCTURE = "recovery"


def wilson_interval(events: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total == 0:
        return None
    proportion = events / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    half = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / total + z * z / (4 * total * total)
        )
        / denominator
    )
    return [center - half, center + half]


def newcombe_difference_interval(
    events_a: int, total_a: int, events_b: int, total_b: int
) -> list[float] | None:
    """Newcombe score interval for p_a - p_b without pooled variance."""
    interval_a = wilson_interval(events_a, total_a)
    interval_b = wilson_interval(events_b, total_b)
    if interval_a is None or interval_b is None:
        return None
    proportion_a = events_a / total_a
    proportion_b = events_b / total_b
    lower = (proportion_a - proportion_b) - math.sqrt(
        (proportion_a - interval_a[0]) ** 2 + (interval_b[1] - proportion_b) ** 2
    )
    upper = (proportion_a - proportion_b) + math.sqrt(
        (interval_a[1] - proportion_a) ** 2 + (proportion_b - interval_b[0]) ** 2
    )
    return [max(-1.0, lower), min(1.0, upper)]


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p-value for [[a, b], [c, d]]."""
    row_one = a + b
    row_two = c + d
    column_one = a + c
    total = row_one + row_two
    if total == 0:
        return 1.0

    def probability(value: int) -> float:
        return (
            math.comb(row_one, value)
            * math.comb(row_two, column_one - value)
            / math.comb(total, column_one)
        )

    minimum = max(0, column_one - row_two)
    maximum = min(row_one, column_one)
    observed = probability(a)
    return min(
        1.0,
        sum(
            probability(value)
            for value in range(minimum, maximum + 1)
            if probability(value) <= observed + 1e-12
        ),
    )


def action_outcome(action: ActionRecord) -> str:
    if action.accepted:
        return "accepted"
    if action.prohibited:
        return "prohibited"
    if action.expected_rejection:
        return "expected_rejection"
    return "unexpected_rejection"


def state_sequence(detail: IncidentRunDetail) -> list[str]:
    action_queues: dict[str, deque[ActionRecord]] = defaultdict(deque)
    for action in detail.actions:
        action_queues[action.action].append(action)
    states = ["START"]
    for tool in detail.measurement.tool_sequence:
        queue = action_queues.get(tool)
        if tool in ACTION_TOOLS and not queue:
            raise ValueError(f"action ledger is missing recorded outcome for {tool}")
        outcome = action_outcome(queue.popleft()) if queue else "observed"
        states.append(f"{tool}|{outcome}")
    unmatched = sum(len(queue) for queue in action_queues.values())
    if unmatched:
        raise ValueError(f"action ledger has {unmatched} outcome(s) absent from the tool trace")
    states.append("END_SUCCESS" if detail.score.task_success else "END_FAILURE")
    return states


def post_rejection_behavior(states: list[str]) -> str:
    rejected = "escalate_incident|expected_rejection"
    try:
        start = states.index(rejected) + 1
    except ValueError:
        return "no_expected_rejection"
    for state in states[start:]:
        tool = state.split("|", maxsplit=1)[0]
        if tool == "get_runbook":
            return "read_runbook_first"
        if tool in ACTION_TOOLS:
            return "retried_first"
        if state.startswith("END_"):
            break
    return "no_follow_up_action"


def first_oracle_divergence(observed: list[str], oracle: list[str]) -> int | None:
    for index, (left, right) in enumerate(zip(observed, oracle, strict=False), start=1):
        if left != right:
            return index
    if len(observed) != len(oracle):
        return min(len(observed), len(oracle)) + 1
    return None


def repeated_tool_count(sequence: list[str]) -> int:
    return len(sequence) - len(set(sequence))


def plugin_entropy(paths: Iterable[str]) -> float:
    counts = Counter(paths)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def bootstrap_entropy_interval(
    paths: list[str], *, repetitions: int = 2000, seed: int = 20260905
) -> list[float] | None:
    if not paths:
        return None
    randomizer = random.Random(seed)
    estimates = sorted(
        plugin_entropy(randomizer.choices(paths, k=len(paths))) for _ in range(repetitions)
    )
    return [
        estimates[int(0.025 * (repetitions - 1))],
        estimates[int(0.975 * (repetitions - 1))],
    ]


def _quantile(values: Sequence[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _numeric_summary(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = [float(row[field]) for row in rows if row[field] is not None]
    return {
        "n": len(values),
        "median": _quantile(values, 0.5),
        "q1": _quantile(values, 0.25),
        "q3": _quantile(values, 0.75),
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
    }


def _post_rejection_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    focused = [
        row
        for row in rows
        if row["scenario_id"] == FOCUSED_SCENARIO
        and row["task_structure"] == FOCUSED_STRUCTURE
    ]
    counts: dict[str, dict[str, int]] = {
        "read_runbook_first": {"success": 0, "failure": 0},
        "retried_first": {"success": 0, "failure": 0},
    }
    for row in focused:
        behavior = str(row["post_rejection_behavior"])
        if behavior in counts:
            outcome = "success" if bool(row["task_success"]) else "failure"
            counts[behavior][outcome] += 1
    classified = sum(sum(outcomes.values()) for outcomes in counts.values())
    read = counts["read_runbook_first"]
    retry = counts["retried_first"]
    read_total = read["success"] + read["failure"]
    retry_total = retry["success"] + retry["failure"]
    read_rate = read["failure"] / read_total if read_total else None
    retry_rate = retry["failure"] / retry_total if retry_total else None
    difference = (
        retry_rate - read_rate if retry_rate is not None and read_rate is not None else None
    )
    return {
        "focused_runs": len(focused),
        "classified_runs": classified,
        "unclassified_runs": len(focused) - classified,
        "counts": counts,
        "failure_rate_read_runbook_first": read_rate,
        "failure_rate_read_runbook_first_wilson_95": wilson_interval(
            read["failure"], read_total
        ),
        "failure_rate_retried_first": retry_rate,
        "failure_rate_retried_first_wilson_95": wilson_interval(
            retry["failure"], retry_total
        ),
        "failure_risk_difference_retry_minus_read": difference,
        "failure_risk_difference_newcombe_95": newcombe_difference_interval(
            retry["failure"], retry_total, read["failure"], read_total
        ),
        "fisher_exact_two_sided_p": (
            fisher_exact_two_sided(
                retry["failure"], retry["success"], read["failure"], read["success"]
            )
            if retry_total and read_total
            else None
        ),
        "interpretation_limit": (
            "Observed association in a synthetic world; the agent behavior was not randomized."
        ),
    }


def analyze_details(
    details: list[IncidentRunDetail], *, campaign_id: str, study_stage: str
) -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    run_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    transition_rows: list[dict[str, Any]] = []
    post_rows: list[dict[str, Any]] = []
    path_counts: Counter[tuple[str, str, str]] = Counter()

    for detail in details:
        if detail.behavior is None:
            continue
        behavior = detail.behavior
        tools = detail.measurement.tool_sequence
        states = state_sequence(detail)
        state_path = " > ".join(states)
        raw_path = " > ".join(tools)
        post_behavior = post_rejection_behavior(states)
        extra_steps = sum(
            step.classification in {"extra", "unexpected_rejection", "prohibited"}
            for step in behavior.trace_steps
        )
        common: dict[str, Any] = {
            "run_id": str(detail.run_id),
            "scenario_id": detail.scenario_id.value,
            "task_structure": behavior.task_structure.value,
            "task_success": detail.score.task_success,
            "batch": behavior.block,
            "execution_order": behavior.execution_order,
        }
        row = common | {
            "mcp_call_count": detail.measurement.mcp_call_count,
            "excess_mcp_calls": behavior.excess_mcp_calls,
            "repeated_tool_count": repeated_tool_count(tools),
            "nonoracle_step_count": extra_steps,
            "first_oracle_divergence": first_oracle_divergence(
                tools, behavior.oracle_sequence
            ),
            "normalized_oracle_distance": behavior.normalized_oracle_distance,
            "exact_oracle_path": tools == behavior.oracle_sequence,
            "post_rejection_behavior": post_behavior,
            "total_latency_ms": detail.measurement.total_latency_ms,
            "total_tokens": detail.measurement.total_tokens,
            "request_frame_bytes": behavior.request_frame_bytes,
            "response_frame_bytes": behavior.response_frame_bytes,
            "estimated_cost_usd": detail.measurement.estimated_cost_usd,
        }
        run_rows.append(row)
        trace_rows.append(
            common
            | {
                "tool_sequence": raw_path,
                "state_sequence": state_path,
                "oracle_sequence": " > ".join(behavior.oracle_sequence),
                "post_rejection_behavior": post_behavior,
                "first_oracle_divergence": row["first_oracle_divergence"],
            }
        )
        post_rows.append(
            common
            | {
                "post_rejection_behavior": post_behavior,
                "failure": not detail.score.task_success,
            }
        )
        path_counts[(detail.scenario_id.value, behavior.task_structure.value, state_path)] += 1
        for order, (source, target) in enumerate(zip(states, states[1:], strict=False), start=1):
            transition_rows.append(
                common
                | {
                    "transition_order": order,
                    "source_state": source,
                    "target_state": target,
                }
            )

    path_rows: list[dict[str, Any]] = []
    condition_totals = Counter((row["scenario_id"], row["task_structure"]) for row in run_rows)
    for (scenario, structure, path), count in sorted(path_counts.items()):
        path_rows.append(
            {
                "scenario_id": scenario,
                "task_structure": structure,
                "state_sequence": path,
                "count": count,
                "proportion": count / condition_totals[(scenario, structure)],
            }
        )

    transition_counts = Counter(
        (row["scenario_id"], row["task_structure"], row["source_state"], row["target_state"])
        for row in transition_rows
    )
    source_totals = Counter(
        (row["scenario_id"], row["task_structure"], row["source_state"])
        for row in transition_rows
    )
    transition_summary = [
        {
            "scenario_id": scenario,
            "task_structure": structure,
            "source_state": source,
            "target_state": target,
            "count": count,
            "probability": count / source_totals[(scenario, structure, source)],
        }
        for (scenario, structure, source, target), count in sorted(transition_counts.items())
    ]

    condition_summaries: list[dict[str, Any]] = []
    grouped_paths: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in trace_rows:
        grouped_paths[(str(row["scenario_id"]), str(row["task_structure"]))].append(
            str(row["state_sequence"])
        )
    for condition_index, ((scenario, structure), paths) in enumerate(sorted(grouped_paths.items())):
        group = [
            row
            for row in run_rows
            if row["scenario_id"] == scenario and row["task_structure"] == structure
        ]
        counts = Counter(paths)
        successful_excess = [
            int(row["excess_mcp_calls"])
            for row in group
            if row["excess_mcp_calls"] is not None
        ]
        condition_summaries.append(
            {
                "scenario_id": scenario,
                "task_structure": structure,
                "n_runs": len(group),
                "successes": sum(bool(row["task_success"]) for row in group),
                "unique_paths": len(counts),
                "singleton_paths": sum(count == 1 for count in counts.values()),
                "modal_path_count": max(counts.values()),
                "modal_path_proportion": max(counts.values()) / len(group),
                "path_entropy_bits": plugin_entropy(paths),
                "path_entropy_bootstrap_95": bootstrap_entropy_interval(
                    paths, seed=20260905 + condition_index
                ),
                "exact_oracle_successes": sum(
                    row["task_success"] and row["exact_oracle_path"] for row in group
                ),
                "successful_excess_calls": {
                    "n": len(successful_excess),
                    "mean": (
                        sum(successful_excess) / len(successful_excess)
                        if successful_excess
                        else None
                    ),
                    "median": _quantile(successful_excess, 0.5),
                    "q1": _quantile(successful_excess, 0.25),
                    "q3": _quantile(successful_excess, 0.75),
                    "minimum": min(successful_excess) if successful_excess else None,
                    "maximum": max(successful_excess) if successful_excess else None,
                },
            }
        )

    batch_summaries: list[dict[str, Any]] = []
    focused_run_rows = [
        row
        for row in run_rows
        if row["scenario_id"] == FOCUSED_SCENARIO
        and row["task_structure"] == FOCUSED_STRUCTURE
    ]
    batches = sorted(
        {int(row["batch"]) for row in focused_run_rows if row["batch"] is not None}
    )
    for batch in batches:
        group = [row for row in focused_run_rows if row["batch"] == batch]
        batch_summaries.append(
            {
                "batch": batch,
                "n_runs": len(group),
                "success_rate": sum(bool(row["task_success"]) for row in group) / len(group),
                "read_runbook_first_rate": sum(
                    row["post_rejection_behavior"] == "read_runbook_first" for row in group
                )
                / len(group),
                "mean_mcp_calls": sum(int(row["mcp_call_count"]) for row in group)
                / len(group),
            }
        )

    analysis: dict[str, Any] = {
        "schema_version": "5.0.0",
        "campaign_id": campaign_id,
        "study_stage": study_stage,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "experimental_unit": "one fresh agent run and MCP session",
        "n_runs": len(run_rows),
        "focused_condition": {
            "scenario_id": FOCUSED_SCENARIO,
            "task_structure": FOCUSED_STRUCTURE,
        },
        "primary_question": (
            "After expected escalation rejection, is failure associated with retrying "
            "before rereading the runbook?"
        ),
        "post_rejection_analysis": _post_rejection_summary(run_rows),
        "focused_measurements": {
            field: _numeric_summary(focused_run_rows, field)
            for field in (
                "mcp_call_count",
                "total_latency_ms",
                "total_tokens",
                "request_frame_bytes",
                "response_frame_bytes",
                "estimated_cost_usd",
            )
        },
        "measurement_boundary": (
            "Latency is client-observed agent runtime; bytes are exact local stdio "
            "MCP frame bytes, not HTTP, TLS, TCP, or IP traffic."
        ),
        "condition_summaries": condition_summaries,
        "path_summary": path_rows,
        "transition_summary": transition_summary,
        "batch_summaries": batch_summaries,
        "trace_examples": trace_rows,
        "notes": [
            "Counts and percentages are shown before statistical summaries.",
            "Entropy and transition probabilities are descriptive.",
            "The behavior-outcome comparison is observational within a synthetic world.",
            "No Markov property is assumed or fitted.",
        ],
    }
    return analysis, {
        "runs": pd.DataFrame(run_rows),
        "traces": pd.DataFrame(trace_rows),
        "paths": pd.DataFrame(path_rows),
        "transitions": pd.DataFrame(transition_rows),
        "post_rejection_outcomes": pd.DataFrame(post_rows),
    }
