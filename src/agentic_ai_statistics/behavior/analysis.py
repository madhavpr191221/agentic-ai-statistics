"""Run-level statistical summaries for the Phase 4 task-structure campaign."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import statsmodels.api as sm  # type: ignore[import-untyped]
import statsmodels.formula.api as smf  # type: ignore[import-untyped]
from statsmodels.stats.multitest import multipletests  # type: ignore[import-untyped]

from agentic_ai_statistics.behavior.traces import path_entropy, transitions
from agentic_ai_statistics.incidents.models import IncidentRunDetail


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    proportion = successes / total
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


def _coefficient_rows(result: Any, *, exponentiate: bool) -> list[dict[str, Any]]:
    intervals = result.conf_int()
    rows: list[dict[str, Any]] = []
    for term, estimate in result.params.items():
        low, high = intervals.loc[term]
        rows.append(
            {
                "term": str(term),
                "estimate": float(estimate),
                "standard_error": float(result.bse[term]),
                "ci_low": float(low),
                "ci_high": float(high),
                "p_value": float(result.pvalues[term]),
                "effect_ratio": (
                    float(math.exp(estimate)) if exponentiate and term != "alpha" else None
                ),
                "effect_ratio_ci": (
                    [float(math.exp(low)), float(math.exp(high))]
                    if exponentiate and term != "alpha"
                    else None
                ),
                "p_value_holm": None,
            }
        )
    return rows


def _holm_structure_contrasts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [row for row in rows if "task_structure" in row["term"]]
    if len(selected) == 2:
        adjusted = multipletests([row["p_value"] for row in selected], method="holm")[1]
        for row, value in zip(selected, adjusted, strict=True):
            row["p_value_holm"] = float(value)
    return rows


def fit_count_models(frame: pd.DataFrame) -> dict[str, Any]:
    formula = (
        "mcp_call_count ~ C(task_structure, Treatment(reference='sequential')) "
        "+ C(scenario_id) + C(block)"
    )
    if len(frame) < 9 or frame["mcp_call_count"].nunique() < 2:
        return {
            "formula": formula,
            "primary": None,
            "negative_binomial_sensitivity": None,
            "note": "Model unavailable: the dataset has insufficient call-count variation.",
        }
    output: dict[str, Any] = {"formula": formula}
    poisson = smf.glm(formula, data=frame, family=sm.families.Poisson()).fit(
        cov_type="HC3"
    )
    dispersion = float(poisson.pearson_chi2 / poisson.df_resid)
    output["primary"] = {
        "model_type": "Poisson log-mean GLM with HC3 robust covariance",
        "coefficients": _holm_structure_contrasts(
            _coefficient_rows(poisson, exponentiate=True)
        ),
        "pearson_dispersion": dispersion,
    }
    if dispersion > 1.25:
        try:
            negative_binomial = smf.negativebinomial(formula, data=frame).fit(
                disp=False, cov_type="HC3"
            )
            output["negative_binomial_sensitivity"] = {
                "fitted": True,
                "converged": bool(negative_binomial.mle_retvals.get("converged", False)),
                "coefficients": _holm_structure_contrasts(
                    _coefficient_rows(negative_binomial, exponentiate=True)
                ),
                "aic": float(negative_binomial.aic),
            }
        except Exception as error:
            output["negative_binomial_sensitivity"] = {
                "fitted": False,
                "error_type": type(error).__name__,
            }
    else:
        output["negative_binomial_sensitivity"] = {
            "fitted": False,
            "note": "Not fitted because Pearson dispersion did not exceed 1.25.",
        }
    return output


def _log_model(frame: pd.DataFrame, outcome: str) -> dict[str, Any] | None:
    subset = frame.loc[frame[outcome] > 0].copy()
    if len(subset) < 9 or subset[outcome].nunique() < 2:
        return None
    subset["log_outcome"] = subset[outcome].map(math.log)
    formula = (
        "log_outcome ~ C(task_structure, Treatment(reference='sequential')) "
        "+ C(scenario_id) + C(block)"
    )
    result = smf.ols(formula, data=subset).fit(cov_type="HC3")
    return {
        "outcome": outcome,
        "formula": formula,
        "n_runs": int(len(subset)),
        "coefficients": _coefficient_rows(result, exponentiate=True),
    }


def fit_success_model(frame: pd.DataFrame) -> dict[str, Any]:
    formula = (
        "task_success ~ C(task_structure, Treatment(reference='sequential')) "
        "+ C(scenario_id) + C(block)"
    )
    if frame["task_success"].nunique() < 2:
        return {
            "available": False,
            "formula": formula,
            "note": "Logistic regression is unavailable because task success is constant.",
        }
    separated_factors = [
        factor
        for factor in ("task_structure", "scenario_id", "block")
        if any(rate in {0.0, 1.0} for rate in frame.groupby(factor)["task_success"].mean())
    ]
    if separated_factors:
        return {
            "available": False,
            "formula": formula,
            "error_type": "quasi_complete_separation",
            "note": (
                "Logistic regression was not reported because one or more fixed-effect "
                f"levels had a constant outcome: {', '.join(separated_factors)}."
            ),
        }
    try:
        model_frame = frame.copy()
        model_frame["task_success"] = model_frame["task_success"].astype(int)
        result = smf.logit(formula, data=model_frame).fit(disp=False, cov_type="HC3")
        return {
            "available": True,
            "formula": formula,
            "coefficients": _holm_structure_contrasts(
                _coefficient_rows(result, exponentiate=True)
            ),
        }
    except Exception as error:
        return {
            "available": False,
            "formula": formula,
            "error_type": type(error).__name__,
            "note": "Logistic regression was not reported because estimation failed.",
        }


def analyze_campaign(
    details: list[IncidentRunDetail], campaign_id: str, study_stage: str
) -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    run_rows: list[dict[str, Any]] = []
    transition_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    mcp_rows: list[dict[str, Any]] = []
    model_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    sequences_by_condition: dict[tuple[str, str], list[tuple[str, ...]]] = defaultdict(list)
    for detail in details:
        if detail.behavior is None:
            continue
        behavior = detail.behavior
        block = behavior.block or 0
        row = detail.measurement.model_dump(mode="json") | {
            "task_structure": behavior.task_structure.value,
            "task_success": detail.score.task_success,
            "block": block,
            "oracle_call_count": behavior.oracle_call_count,
            "excess_mcp_calls": behavior.excess_mcp_calls,
            "normalized_oracle_distance": behavior.normalized_oracle_distance,
            "expected_rejections": behavior.expected_rejections,
            "unexpected_rejections": behavior.unexpected_rejections,
        }
        run_rows.append(row)
        condition = (detail.scenario_id.value, behavior.task_structure.value)
        sequence = tuple(behavior.observed_sequence)
        sequences_by_condition[condition].append(sequence)
        trace_rows.append(
            {
                "run_id": str(detail.run_id),
                "scenario_id": detail.scenario_id.value,
                "task_structure": behavior.task_structure.value,
                "task_success": detail.score.task_success,
                "tool_sequence": " > ".join(sequence),
                "oracle_sequence": " > ".join(behavior.oracle_sequence),
                "normalized_oracle_distance": behavior.normalized_oracle_distance,
            }
        )
        for order, (source, target) in enumerate(transitions(list(sequence))):
            transition_rows.append(
                {
                    "run_id": str(detail.run_id),
                    "scenario_id": detail.scenario_id.value,
                    "task_structure": behavior.task_structure.value,
                    "transition_order": order,
                    "source_tool": source,
                    "target_tool": target,
                }
            )
        for action in detail.actions:
            action_rows.append(
                {
                    "run_id": str(detail.run_id),
                    "scenario_id": detail.scenario_id.value,
                    "task_structure": behavior.task_structure.value,
                }
                | action.model_dump(mode="json")
            )
        for event in detail.agent_events:
            if event.event == "tool_finished":
                mcp_rows.append(
                    {
                        "run_id": str(detail.run_id),
                        "scenario_id": detail.scenario_id.value,
                        "task_structure": behavior.task_structure.value,
                        "tool_name": event.tool_name,
                        "elapsed_ms": event.elapsed_ms,
                    }
                )
            if event.event == "model_finished":
                model_rows.append(
                    {
                        "run_id": str(detail.run_id),
                        "scenario_id": detail.scenario_id.value,
                        "task_structure": behavior.task_structure.value,
                        "elapsed_ms": event.elapsed_ms,
                    }
                )
    runs = pd.DataFrame(run_rows)
    if runs.empty:
        analysis = {
            "campaign_id": campaign_id,
            "study_stage": study_stage,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "experimental_unit": "one fresh agent run and MCP session",
            "n_runs": 0,
            "note": "No Phase 4 runs were available.",
        }
    else:
        condition_summaries: list[dict[str, Any]] = []
        for (scenario, structure), group in runs.groupby(["scenario_id", "task_structure"]):
            successes = int(group["task_success"].sum())
            condition_summaries.append(
                {
                    "scenario_id": scenario,
                    "task_structure": structure,
                    "n_runs": int(len(group)),
                    "successes": successes,
                    "success_rate": successes / len(group),
                    "success_wilson_95": wilson(successes, len(group)),
                    "median_mcp_calls": float(group["mcp_call_count"].median()),
                    "median_latency_ms": float(group["total_latency_ms"].median()),
                    "median_oracle_distance": float(
                        group["normalized_oracle_distance"].median()
                    ),
                    "unique_paths": len(set(sequences_by_condition[(scenario, structure)])),
                    "path_entropy_bits": path_entropy(
                        sequences_by_condition[(scenario, structure)]
                    ),
                }
            )
        transition_counts = Counter(
            (row["task_structure"], row["source_tool"], row["target_tool"])
            for row in transition_rows
        )
        source_totals = Counter(
            (row["task_structure"], row["source_tool"]) for row in transition_rows
        )
        transition_summary = [
            {
                "task_structure": structure,
                "source_tool": source,
                "target_tool": target,
                "count": count,
                "probability": count / source_totals[(structure, source)],
            }
            for (structure, source, target), count in sorted(transition_counts.items())
        ]
        successes = int(runs["task_success"].sum())
        call_distributions = []
        for structure, group in runs.groupby("task_structure"):
            values = sorted(int(value) for value in group["mcp_call_count"])
            call_distributions.append(
                {
                    "task_structure": structure,
                    "values": values,
                    "ecdf": [
                        {"value": value, "probability": (index + 1) / len(values)}
                        for index, value in enumerate(values)
                    ],
                }
            )
        analysis = {
            "campaign_id": campaign_id,
            "study_stage": study_stage,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "experimental_unit": "one fresh agent run and MCP session",
            "n_runs": int(len(runs)),
            "successes": successes,
            "success_rate": successes / len(runs),
            "success_wilson_95": wilson(successes, len(runs)),
            "primary_outcome": "mcp_call_count",
            "primary_model": fit_count_models(runs),
            "success_model": fit_success_model(runs),
            "secondary_models": {
                outcome: _log_model(runs, outcome)
                for outcome in (
                    "total_latency_ms",
                    "request_frame_bytes",
                    "response_frame_bytes",
                    "total_tokens",
                    "estimated_cost_usd",
                )
            },
            "condition_summaries": condition_summaries,
            "mcp_call_distributions": call_distributions,
            "transition_summary": transition_summary,
            "notes": [
                "Pilot observations are not combined with the main study.",
                "Path entropy and transition probabilities are descriptive, not Markov claims.",
                "The three task scenarios are fixed; inference does not cover all IT incidents.",
            ],
        }
    tables = {
        "runs": runs,
        "traces": pd.DataFrame(trace_rows),
        "transitions": pd.DataFrame(transition_rows),
        "actions": pd.DataFrame(action_rows),
        "mcp_calls": pd.DataFrame(mcp_rows),
        "model_calls": pd.DataFrame(model_rows),
    }
    return analysis, tables
