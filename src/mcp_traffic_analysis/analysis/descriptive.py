"""Explicit descriptive-statistics definitions for experiment metrics."""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
from pydantic import BaseModel, ConfigDict


class AnalysisModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SummaryStatistics(AnalysisModel):
    count: int
    missing_count: int
    minimum: float | None
    maximum: float | None
    mean: float | None
    median: float | None
    sample_standard_deviation: float | None
    interquartile_range: float | None
    p50: float | None
    p90: float | None
    p95: float | None
    p99: float | None
    coefficient_of_variation: float | None


class EcdfPoint(AnalysisModel):
    value: float
    probability: float


class HistogramBin(AnalysisModel):
    left: float
    right: float
    count: int


class DistributionDescription(AnalysisModel):
    summary: SummaryStatistics
    values: list[float]
    ecdf: list[EcdfPoint]
    histogram: list[HistogramBin]
    quantile_method: str = "linear"
    histogram_rule: str


def _finite_values(values: Iterable[float | int | None]) -> tuple[np.ndarray, int]:
    observed: list[float] = []
    missing = 0
    for value in values:
        if value is None or not math.isfinite(float(value)):
            missing += 1
        else:
            observed.append(float(value))
    return np.asarray(observed, dtype=np.float64), missing


def _histogram(values: np.ndarray) -> tuple[list[HistogramBin], str]:
    count = int(values.size)
    if count == 0:
        return [], "unavailable"

    minimum = float(np.min(values))
    maximum = float(np.max(values))
    if minimum == maximum:
        return [HistogramBin(left=minimum - 0.5, right=maximum + 0.5, count=count)], "constant"

    q25, q75 = np.quantile(values, [0.25, 0.75], method="linear")
    iqr = float(q75 - q25)
    if iqr > 0:
        width = 2 * iqr * count ** (-1 / 3)
        bin_count = math.ceil((maximum - minimum) / width)
        rule = "freedman_diaconis"
    else:
        bin_count = math.ceil(math.log2(count) + 1)
        rule = "sturges_zero_iqr"
    bin_count = max(1, min(100, bin_count))

    counts, edges = np.histogram(values, bins=bin_count)
    bins = [
        HistogramBin(left=float(edges[index]), right=float(edges[index + 1]), count=int(value))
        for index, value in enumerate(counts)
    ]
    return bins, rule


def describe_values(values: Iterable[float | int | None]) -> DistributionDescription:
    """Describe finite values using documented sample and quantile conventions."""
    observed, missing_count = _finite_values(values)
    count = int(observed.size)
    sorted_values = np.sort(observed)

    if count == 0:
        summary = SummaryStatistics(
            count=0,
            missing_count=missing_count,
            minimum=None,
            maximum=None,
            mean=None,
            median=None,
            sample_standard_deviation=None,
            interquartile_range=None,
            p50=None,
            p90=None,
            p95=None,
            p99=None,
            coefficient_of_variation=None,
        )
    else:
        q25, p50, q75, p90, p95, p99 = np.quantile(
            observed,
            [0.25, 0.50, 0.75, 0.90, 0.95, 0.99],
            method="linear",
        )
        mean = float(np.mean(observed))
        sample_sd = float(np.std(observed, ddof=1)) if count >= 2 else None
        coefficient = sample_sd / mean if sample_sd is not None and mean != 0 else None
        summary = SummaryStatistics(
            count=count,
            missing_count=missing_count,
            minimum=float(np.min(observed)),
            maximum=float(np.max(observed)),
            mean=mean,
            median=float(p50),
            sample_standard_deviation=sample_sd,
            interquartile_range=float(q75 - q25),
            p50=float(p50),
            p90=float(p90),
            p95=float(p95),
            p99=float(p99),
            coefficient_of_variation=coefficient,
        )

    ecdf = [
        EcdfPoint(value=float(value), probability=(index + 1) / count)
        for index, value in enumerate(sorted_values)
    ]
    histogram, histogram_rule = _histogram(observed)
    return DistributionDescription(
        summary=summary,
        values=[float(value) for value in sorted_values],
        ecdf=ecdf,
        histogram=histogram,
        histogram_rule=histogram_rule,
    )
