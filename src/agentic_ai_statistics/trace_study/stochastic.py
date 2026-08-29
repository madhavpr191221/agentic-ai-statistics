"""Small, auditable stochastic-process summaries for observable agent traces."""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np

SUCCESS = "END_SUCCESS"
FAILURE = "END_FAILURE"


def _solve(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray | None:
    try:
        return np.linalg.solve(matrix, vector)
    except np.linalg.LinAlgError:
        return None


def _trace_rows(rows: list[dict[str, Any]], arm: str | None) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if (row.get("intervention_arm") if row.get("intervention_arm") else None) == arm
    ]


def _history_diagnostic(rows: list[dict[str, Any]], states: list[str]) -> dict[str, Any]:
    first = Counter((state, target) for row in rows for state, target in zip(
        row["state_sequence"].split(" > "),
        row["state_sequence"].split(" > ")[1:],
        strict=False,
    ))
    second = Counter(
        (left, middle, target)
        for row in rows
        for left, middle, target in zip(
            row["state_sequence"].split(" > "),
            row["state_sequence"].split(" > ")[1:],
            row["state_sequence"].split(" > ")[2:],
            strict=False,
        )
    )
    prefixes = Counter(
        (left, middle)
        for row in rows
        for left, middle in zip(
            row["state_sequence"].split(" > "),
            row["state_sequence"].split(" > ")[1:],
            strict=False,
        )
    )
    disagreements = 0.0
    comparisons = 0
    for (left, middle, target), count in second.items():
        denominator = prefixes[(left, middle)]
        if denominator == 0:
            continue
        order1_total = sum(
            value for (source, _destination), value in first.items() if source == middle
        )
        order1 = first[(middle, target)] / order1_total if order1_total else 0.0
        order2 = count / denominator
        disagreements += count * abs(order2 - order1)
        comparisons += count
    return {
        "method": (
            "weighted absolute difference between first- and second-order "
            "observed frequencies"
        ),
        "comparisons": comparisons,
        "weighted_absolute_difference": disagreements / comparisons if comparisons else None,
        "interpretation": (
            "Descriptive diagnostic only; it does not prove or disprove the Markov property."
        ),
    }


def fit_absorbing_process(rows: list[dict[str, Any]], *, arm: str | None) -> dict[str, Any]:
    """Fit a compact absorbing-chain summary to complete observable state paths."""
    selected = _trace_rows(rows, arm)
    paths = [str(row["state_sequence"]).split(" > ") for row in selected]
    observed_states = sorted({state for path in paths for state in path})
    transient = [state for state in observed_states if state not in {SUCCESS, FAILURE}]
    states = transient + [SUCCESS, FAILURE]
    counts: Counter[tuple[str, str]] = Counter()
    for path in paths:
        counts.update(zip(path, path[1:], strict=False))
    transition_rows: list[dict[str, Any]] = []
    outgoing: Counter[str] = Counter()
    for (source, _target), count in counts.items():
        outgoing[source] += count
    for (source, target), count in sorted(counts.items()):
        transition_rows.append({
            "source_state": source,
            "target_state": target,
            "count": count,
            "probability": count / outgoing[source],
        })
    success_probability: float | None = None
    failure_probability: float | None = None
    expected_steps: float | None = None
    expected_visits: dict[str, float] = {}
    if paths and "START" in transient:
        q = np.zeros((len(transient), len(transient)))
        success_vector = np.zeros(len(transient))
        for (source, target), count in counts.items():
            if source not in transient:
                continue
            probability = count / outgoing[source]
            source_index = transient.index(source)
            if target in transient:
                q[source_index, transient.index(target)] += probability
            elif target == SUCCESS:
                success_vector[source_index] += probability
        identity = np.eye(len(transient))
        success_values = _solve(identity - q, success_vector)
        visit_matrix = _solve(identity - q, identity)
        if success_values is not None:
            success_probability = float(success_values[transient.index("START")])
            failure_probability = 1.0 - success_probability
        if visit_matrix is not None:
            start_visits = visit_matrix[transient.index("START")]
            expected_steps = float(sum(start_visits))
            expected_visits = {
                state: float(start_visits[index]) for index, state in enumerate(transient)
            }
    return {
        "arm": arm or "observational",
        "n_runs": len(selected),
        "states": states,
        "transient_states": transient,
        "absorbing_states": [SUCCESS, FAILURE],
        "transition_summary": transition_rows,
        "absorption": {
            "success_probability": success_probability,
            "failure_probability": failure_probability,
            "expected_steps_to_absorption": expected_steps,
            "expected_visits_from_start": expected_visits,
        },
        "history_diagnostic": _history_diagnostic(selected, states),
        "holding_times": {
            "available": False,
            "reason": (
                "Current trace artifact contains ordered states but not "
                "per-event timestamps."
            ),
        },
        "uncertainty": {
            "available": False,
            "reason": (
                "Phase 14 first reports the fitted exploratory chain; interval "
                "estimation is deferred until state-level resampling rules are frozen."
            ),
        },
        "limitations": [
            "States are observable summaries, not complete hidden environment states.",
            "The first-order chain is an approximation; history diagnostics must be reviewed.",
            "Observational and randomized-policy traces must not be interpreted as one population.",
        ],
    }


def stochastic_analysis(trace_examples: list[dict[str, Any]]) -> dict[str, Any]:
    """Return separate process summaries for observational and assigned-policy traces."""
    arms = sorted(
        {
            str(row["intervention_arm"])
            for row in trace_examples
            if row.get("intervention_arm")
        }
    )
    subsets = [fit_absorbing_process(trace_examples, arm=None)]
    subsets.extend(fit_absorbing_process(trace_examples, arm=str(arm)) for arm in arms)
    return {
        "schema_version": "14.0.0",
        "analysis": "compact absorbing stochastic process of observable agent trajectories",
        "unit": "one complete run; events are nested within a run",
        "state_definition": "existing compact tool|outcome states plus START and terminal states",
        "subsets": subsets,
        "measurement_status": "derived from measured trace records; model quantities are inferred",
        "timing_status": "holding-time analysis unavailable in the current artifact",
    }
