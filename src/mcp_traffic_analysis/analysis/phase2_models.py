"""Phase 2 table construction, bootstrap summaries, and regression models."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import statsmodels.formula.api as smf  # type: ignore[import-untyped]
from scipy import stats  # type: ignore[import-untyped]

from mcp_traffic_analysis.measurement.transport_models import (
    CallMeasurement,
    RunMeasurement,
)

PRIMARY_FORMULA = (
    "log_median_rtt ~ C(transport) * C(payload_target_bytes) "
    "+ C(service_time_ms) + C(concurrency) + C(transport):C(concurrency)"
)
MIXED_FORMULA = (
    "log_client_roundtrip ~ C(transport) * C(payload_target_bytes) "
    "+ C(service_time_ms) + C(concurrency) + C(transport):C(concurrency) + is_first_call"
)


def _json_ready(value: Any) -> Any:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def build_tables(campaign_directory: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build one run table and one correlated call table from canonical JSON artifacts."""
    run_rows: list[dict[str, Any]] = []
    call_rows: list[dict[str, Any]] = []
    for run_path in campaign_directory.glob("runs/*/run_measurement.json"):
        run = RunMeasurement.model_validate_json(run_path.read_text(encoding="utf-8"))
        run_rows.append(run.model_dump(mode="json"))
        calls_path = run_path.parent / "calls.jsonl"
        for line in calls_path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            call = CallMeasurement.model_validate_json(line)
            row = call.model_dump(mode="json")
            row["total_frame_bytes"] = call.total_frame_bytes
            row["nonhandler_residual_ms"] = call.nonhandler_residual_ms
            call_rows.append(row)
    runs = pd.DataFrame(run_rows).sort_values("execution_order").reset_index(drop=True)
    calls = pd.DataFrame(call_rows).sort_values(["run_id", "call_index"]).reset_index(drop=True)
    tables = campaign_directory / "tables"
    tables.mkdir(exist_ok=True)
    runs.to_parquet(tables / "runs.parquet", index=False)
    calls.to_parquet(tables / "calls.parquet", index=False)
    runs.to_csv(tables / "runs.csv", index=False)
    calls.to_csv(tables / "calls.csv", index=False)
    return runs, calls


def _coefficient_table(result: Any) -> list[dict[str, Any]]:
    intervals = result.conf_int()
    return [
        {
            "term": str(term),
            "estimate": float(result.params[term]),
            "standard_error": float(result.bse[term]),
            "ci_low": float(intervals.loc[term, 0]),
            "ci_high": float(intervals.loc[term, 1]),
            "p_value": float(result.pvalues[term]),
            "latency_ratio": float(math.exp(result.params[term])),
        }
        for term in result.params.index
    ]


def _cluster_bootstrap(
    group: pd.DataFrame,
    *,
    iterations: int,
    rng: np.random.Generator,
) -> dict[str, float | int]:
    run_ids = group["run_id"].unique()
    medians = np.empty(iterations)
    p95s = np.empty(iterations)
    by_run = {
        run_id: group.loc[group["run_id"] == run_id, "client_roundtrip_ms"].to_numpy()
        for run_id in run_ids
    }
    for index in range(iterations):
        selected = rng.choice(run_ids, size=len(run_ids), replace=True)
        sample = np.concatenate([by_run[run_id] for run_id in selected])
        medians[index] = np.median(sample)
        p95s[index] = np.quantile(sample, 0.95, method="linear")
    values = group["client_roundtrip_ms"].to_numpy()
    return {
        "n_runs": int(len(run_ids)),
        "n_calls": int(len(values)),
        "median_ms": float(np.median(values)),
        "median_ci_low": float(np.quantile(medians, 0.025)),
        "median_ci_high": float(np.quantile(medians, 0.975)),
        "p90_ms": float(np.quantile(values, 0.90)),
        "p95_ms": float(np.quantile(values, 0.95)),
        "p95_ci_low": float(np.quantile(p95s, 0.025)),
        "p95_ci_high": float(np.quantile(p95s, 0.975)),
        "iqr_ms": float(np.quantile(values, 0.75) - np.quantile(values, 0.25)),
    }


def fit_phase2_models(
    campaign_directory: Path,
    runs: pd.DataFrame,
    calls: pd.DataFrame,
    *,
    bootstrap_iterations: int = 2_000,
    bootstrap_seed: int = 20260827,
) -> dict[str, Any]:
    """Fit the preregistered run OLS and secondary call-level mixed model."""
    successful = calls.loc[calls["outcome"] == "success"].copy()
    run_medians = successful.groupby("run_id", as_index=False).agg(
        median_rtt_ms=("client_roundtrip_ms", "median"),
        transport=("transport", "first"),
        payload_target_bytes=("payload_target_bytes", "first"),
        service_time_ms=("service_time_ms", "first"),
        concurrency=("concurrency", "first"),
    )
    run_medians["log_median_rtt"] = np.log(run_medians["median_rtt_ms"])
    primary = smf.ols(PRIMARY_FORMULA, data=run_medians).fit(cov_type="HC3")

    successful["log_client_roundtrip"] = np.log(successful["client_roundtrip_ms"])
    mixed_error: str | None = None
    mixed_summary: dict[str, Any]
    try:
        mixed = smf.mixedlm(
            MIXED_FORMULA,
            successful,
            groups=successful["run_id"],
            re_formula="1",
        ).fit(reml=True, method="lbfgs", maxiter=300)
        between_variance = float(mixed.cov_re.iloc[0, 0])
        within_variance = float(mixed.scale)
        mixed_summary = {
            "formula": MIXED_FORMULA,
            "converged": bool(mixed.converged),
            "coefficients": _coefficient_table(mixed),
            "between_run_variance": between_variance,
            "within_run_variance": within_variance,
            "icc": between_variance / (between_variance + within_variance),
        }
    except Exception as error:
        mixed_error = type(error).__name__
        mixed_summary = {"formula": MIXED_FORMULA, "converged": False, "error_type": mixed_error}

    stdio = successful.dropna(subset=["total_frame_bytes"]).copy()
    byte_summary: dict[str, Any] | None = None
    if len(stdio) >= 8:
        stdio_runs = stdio.groupby("run_id", as_index=False).agg(
            median_rtt_ms=("client_roundtrip_ms", "median"),
            median_total_frame_bytes=("total_frame_bytes", "median"),
            service_time_ms=("service_time_ms", "first"),
            concurrency=("concurrency", "first"),
        )
        stdio_runs["log_median_rtt"] = np.log(stdio_runs["median_rtt_ms"])
        byte = smf.ols(
            "log_median_rtt ~ np.log2(median_total_frame_bytes) "
            "+ C(service_time_ms) + C(concurrency)",
            data=stdio_runs,
        ).fit(cov_type="HC3")
        byte_summary = {
            "formula": "log_median_rtt ~ log2(measured_total_frame_bytes) + service + concurrency",
            "coefficients": _coefficient_table(byte),
            "r_squared": float(byte.rsquared),
        }

    rng = np.random.default_rng(bootstrap_seed)
    summaries: list[dict[str, Any]] = []
    group_columns = ["transport", "payload_target_bytes", "service_time_ms", "concurrency"]
    for keys, group in successful.groupby(group_columns, sort=True):
        summary = dict(zip(group_columns, keys, strict=True))
        summary.update(_cluster_bootstrap(group, iterations=bootstrap_iterations, rng=rng))
        summaries.append(summary)

    ordered_residuals = np.sort(np.asarray(primary.resid))
    probabilities = (np.arange(len(ordered_residuals)) + 0.5) / len(ordered_residuals)
    theoretical = stats.norm.ppf(probabilities)
    result = {
        "schema_version": "1.0.0",
        "experimental_unit": "run",
        "primary_model": {
            "model_type": "OLS with HC3 robust covariance",
            "formula": PRIMARY_FORMULA,
            "n_runs": int(primary.nobs),
            "r_squared": float(primary.rsquared),
            "adjusted_r_squared": float(primary.rsquared_adj),
            "coefficients": _coefficient_table(primary),
        },
        "mixed_model": mixed_summary,
        "byte_model": byte_summary,
        "condition_summaries": summaries,
        "diagnostics": {
            "fitted": [float(value) for value in primary.fittedvalues],
            "residuals": [float(value) for value in primary.resid],
            "qq_theoretical": [float(value) for value in theoretical],
            "qq_observed": [float(value) for value in ordered_residuals],
        },
        "counts": {
            "runs": int(len(runs)),
            "successful_calls": int(len(successful)),
            "failed_calls": int(len(calls) - len(successful)),
            "mixed_model_error_type": mixed_error,
        },
        "bootstrap": {
            "iterations": bootstrap_iterations,
            "seed": bootstrap_seed,
            "unit": "run cluster",
        },
        "notes": [
            "Calls are nested within independent runs.",
            "Discovery traffic is retained in raw traces but excluded from modeled tool calls.",
            "Timeouts are not treated as completed latency observations.",
        ],
    }
    analysis_path = campaign_directory / "analysis.json"
    analysis_path.write_text(
        json.dumps(result, indent=2, default=_json_ready) + "\n",
        encoding="utf-8",
    )
    return result
