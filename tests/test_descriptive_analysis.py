from __future__ import annotations

import math

import pytest

from mcp_traffic_analysis.analysis.descriptive import describe_values


def test_known_sample_uses_sample_statistics_and_linear_quantiles() -> None:
    result = describe_values([1, 2, 3, 4, None, math.nan])

    assert result.summary.count == 4
    assert result.summary.missing_count == 2
    assert result.summary.mean == pytest.approx(2.5)
    assert result.summary.median == pytest.approx(2.5)
    assert result.summary.sample_standard_deviation == pytest.approx(math.sqrt(5 / 3))
    assert result.summary.interquartile_range == pytest.approx(1.5)
    assert result.summary.p90 == pytest.approx(3.7)
    assert result.quantile_method == "linear"
    assert sum(item.count for item in result.histogram) == 4
    assert [point.probability for point in result.ecdf] == [0.25, 0.5, 0.75, 1.0]


def test_empty_sample_reports_unavailable_statistics() -> None:
    result = describe_values([None, math.inf])

    assert result.summary.count == 0
    assert result.summary.missing_count == 2
    assert result.summary.mean is None
    assert result.summary.sample_standard_deviation is None
    assert result.ecdf == []
    assert result.histogram == []
    assert result.histogram_rule == "unavailable"


def test_singleton_has_no_sample_standard_deviation() -> None:
    result = describe_values([7])

    assert result.summary.count == 1
    assert result.summary.sample_standard_deviation is None
    assert result.summary.coefficient_of_variation is None
    assert result.histogram_rule == "constant"


def test_zero_iqr_uses_documented_histogram_fallback() -> None:
    result = describe_values([0, 0, 0, 0, 1])

    assert result.histogram_rule == "sturges_zero_iqr"
    assert sum(item.count for item in result.histogram) == 5
