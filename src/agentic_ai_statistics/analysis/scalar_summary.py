"""Descriptive summaries for complete agent runs.

The complete run is the experimental unit. This module intentionally does not
fit a model or treat nested tool calls as independent observations.
"""

from __future__ import annotations

from collections.abc import Callable
from statistics import mean, median, quantiles

from pydantic import BaseModel, ConfigDict

from agentic_ai_statistics.incidents.models import IncidentRunDetail


class ScalarSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    label: str
    kind: str
    unit: str
    status: str
    n: int
    missing: int
    mean: float | None
    median: float | None
    q1: float | None
    q3: float | None
    minimum: float | None
    maximum: float | None
    proportion: float | None = None


def _quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return float(quantiles(values, n=100, method="inclusive")[int(probability * 100) - 1])


def _numeric_summary(
    field: str, label: str, unit: str, values: list[float], missing: int
) -> ScalarSummary:
    return ScalarSummary(
        field=field,
        label=label,
        kind="continuous" if field in {"total_latency_ms", "estimated_cost_usd"} else "count",
        unit=unit,
        status="measured",
        n=len(values),
        missing=missing,
        mean=float(mean(values)) if values else None,
        median=float(median(values)) if values else None,
        q1=_quantile(values, 0.25),
        q3=_quantile(values, 0.75),
        minimum=min(values) if values else None,
        maximum=max(values) if values else None,
    )


def _binary_summary(field: str, label: str, values: list[float], missing: int) -> ScalarSummary:
    successes = sum(values)
    return ScalarSummary(
        field=field,
        label=label,
        kind="binary",
        unit="proportion",
        status="derived from objective score",
        n=len(values),
        missing=missing,
        mean=float(mean(values)) if values else None,
        median=float(median(values)) if values else None,
        q1=_quantile(values, 0.25),
        q3=_quantile(values, 0.75),
        minimum=min(values) if values else None,
        maximum=max(values) if values else None,
        proportion=(successes / len(values)) if values else None,
    )


def summarize_runs(runs: list[IncidentRunDetail]) -> list[ScalarSummary]:
    """Summarize scalar outcomes across complete runs."""

    numeric: list[tuple[str, str, str, Callable[[IncidentRunDetail], float | None]]] = [
        ("mcp_call_count", "MCP call count", "calls", lambda r: r.measurement.mcp_call_count),
        ("model_call_count", "Model call count", "calls", lambda r: r.measurement.model_call_count),
        ("total_latency_ms", "Total latency", "ms", lambda r: r.measurement.total_latency_ms),
        ("total_tokens", "Total tokens", "tokens", lambda r: r.measurement.total_tokens),
        (
            "request_frame_bytes",
            "Request frame bytes",
            "bytes",
            lambda r: r.measurement.request_frame_bytes,
        ),
        (
            "response_frame_bytes",
            "Response frame bytes",
            "bytes",
            lambda r: r.measurement.response_frame_bytes,
        ),
        ("estimated_cost_usd", "Estimated cost", "USD", lambda r: r.measurement.estimated_cost_usd),
    ]
    summaries: list[ScalarSummary] = []
    for field, label, unit, getter in numeric:
        values = [value for run in runs if (value := getter(run)) is not None]
        summaries.append(_numeric_summary(field, label, unit, values, len(runs) - len(values)))
    successes = [1.0 if run.score.task_success else 0.0 for run in runs]
    summaries.append(_binary_summary("task_success", "Task success", successes, 0))
    return summaries
