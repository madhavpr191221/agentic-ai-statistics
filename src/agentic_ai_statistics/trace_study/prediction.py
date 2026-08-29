"""Held-out prediction of observable agent state trajectories."""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from typing import Any


def _paths(analysis: dict[str, Any]) -> list[tuple[str, list[str]]]:
    return [
        (str(row["run_id"]), str(row["state_sequence"]).split(" > "))
        for row in analysis.get("trace_examples", [])
    ]


def _probability(counts: Counter[str], vocabulary: list[str], target: str) -> float:
    denominator = sum(counts.values()) + len(vocabulary)
    return (counts[target] + 1) / denominator if denominator else 1.0 / len(vocabulary)


def _models(training: list[tuple[str, list[str]]], vocabulary: list[str]) -> dict[str, Any]:
    global_counts: Counter[str] = Counter()
    state_counts: dict[str, Counter[str]] = defaultdict(Counter)
    history_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for _, path in training:
        for previous, target in zip(path, path[1:], strict=False):
            global_counts[target] += 1
            state_counts[previous][target] += 1
        for previous, current, target in zip(path, path[1:], path[2:], strict=False):
            history_counts[(previous, current)][target] += 1
    global_target = global_counts.most_common(1)[0][0] if global_counts else "END_FAILURE"

    def distribution(model: str, previous: str, current: str) -> dict[str, float]:
        if model == "global_majority":
            return {state: 1.0 if state == global_target else 0.0 for state in vocabulary}
        if model == "current_state":
            counts = state_counts.get(current, Counter())
        else:
            counts = history_counts.get((previous, current)) or state_counts.get(current, Counter())
        return {state: _probability(counts, vocabulary, state) for state in vocabulary}

    return {"distribution": distribution, "global_target": global_target}


def _run_metrics(
    path: list[str], model_name: str, model: dict[str, Any], vocabulary: list[str]
) -> dict[str, float]:
    log_loss = 0.0
    accuracy = 0
    brier = 0.0
    transitions = max(0, len(path) - 1)
    for index, (current, target) in enumerate(zip(path, path[1:], strict=False)):
        previous = path[index - 1] if index else "<NONE>"
        distribution = model["distribution"](model_name, previous, current)
        observed = target if target in vocabulary else "UNKNOWN"
        probability = distribution.get(observed, 1e-12)
        log_loss -= math.log(max(probability, 1e-12))
        predicted = max(distribution, key=distribution.get)
        accuracy += int(predicted == observed)
        brier += sum(
            (value - float(state == observed)) ** 2 for state, value in distribution.items()
        )
    return {
        "transitions": float(transitions),
        "log_loss": log_loss / transitions if transitions else 0.0,
        "accuracy": accuracy / transitions if transitions else 0.0,
        "brier_score": brier / transitions if transitions else 0.0,
    }


def _bootstrap_interval(values: list[float], *, seed: int) -> list[float] | None:
    if not values:
        return None
    if len(values) == 1:
        return [values[0], values[0]]
    generator = random.Random(seed)
    estimates = sorted(
        sum(generator.choices(values, k=len(values))) / len(values)
        for _ in range(2000)
    )
    return [estimates[49], estimates[1949]]


def evaluate_prediction(
    training_analysis: dict[str, Any], test_analysis: dict[str, Any]
) -> dict[str, Any]:
    training = _paths(training_analysis)
    test = _paths(test_analysis)
    known = {state for _, path in training for state in path}
    vocabulary = sorted(known | {"UNKNOWN", "END_SUCCESS", "END_FAILURE"})
    model = _models(training, vocabulary)
    model_names = ("global_majority", "current_state", "history_aware")
    per_run: list[dict[str, Any]] = []
    for run_id, path in test:
        for model_name in model_names:
            per_run.append(
                {
                    "run_id": run_id,
                    "model": model_name,
                    **_run_metrics(path, model_name, model, vocabulary),
                }
            )
    comparison: list[dict[str, Any]] = []
    for model_name in model_names:
        rows = [row for row in per_run if row["model"] == model_name]
        comparison.append(
            {
                "model": model_name,
                "n_runs": len(rows),
                "n_transitions": int(sum(row["transitions"] for row in rows)),
                "mean_run_log_loss": sum(row["log_loss"] for row in rows) / len(rows)
                if rows
                else None,
                "mean_run_accuracy": sum(row["accuracy"] for row in rows) / len(rows)
                if rows
                else None,
                "mean_run_brier_score": sum(row["brier_score"] for row in rows) / len(rows)
                if rows
                else None,
                "mean_run_log_loss_bootstrap_95": _bootstrap_interval(
                    [row["log_loss"] for row in rows], seed=20261500
                ),
                "mean_run_accuracy_bootstrap_95": _bootstrap_interval(
                    [row["accuracy"] for row in rows], seed=20261501
                ),
                "mean_run_brier_score_bootstrap_95": _bootstrap_interval(
                    [row["brier_score"] for row in rows], seed=20261502
                ),
            }
        )
    by_run = {
        run_id: {row["model"]: row for row in per_run if row["run_id"] == run_id}
        for run_id, _ in test
    }
    paired: list[dict[str, Any]] = []
    for left, right in (("current_state", "global_majority"), ("history_aware", "current_state")):
        differences = [
            by_run[run][left]["log_loss"] - by_run[run][right]["log_loss"] for run in by_run
        ]
        paired.append(
            {
                "better_model": left,
                "baseline_model": right,
                "mean_log_loss_difference": sum(differences) / len(differences)
                if differences
                else None,
                "mean_log_loss_difference_bootstrap_95": _bootstrap_interval(
                    differences, seed=20261510 + len(paired)
                ),
            }
        )
    return {
        "schema_version": "15.0.0",
        "analysis": "held-out prediction of observable state trajectories",
        "training_campaign_id": training_analysis.get("campaign_id"),
        "test_campaign_id": test_analysis.get("campaign_id"),
        "training_runs": len(training),
        "test_runs": len(test),
        "state_vocabulary": vocabulary,
        "models": [
            {"name": "global_majority", "definition": "always predict the most common successor"},
            {
                "name": "current_state",
                "definition": "add-one-smoothed P(next state | current state)",
            },
            {
                "name": "history_aware",
                "definition": (
                    "add-one-smoothed P(next state | previous and current state), "
                    "falling back to current state"
                ),
            },
        ],
        "model_comparison": comparison,
        "paired_log_loss_comparisons": paired,
        "per_run_metrics": per_run,
        "limitations": [
            (
                "Metrics are evaluated on one held-out campaign and do not "
                "establish universal agent predictability."
            ),
            (
                "Transitions remain nested within runs; reported model "
                "comparisons aggregate run-level metrics."
            ),
            "The model predicts observable states, not private reasoning.",
            (
                "Uncertainty intervals are deferred until the held-out campaign "
                "is complete and resampling rules are frozen."
            ),
        ],
    }
