"""Frozen Phase 2 campaign design and progress contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mcp_traffic_analysis.experiments.condition_runner import ConditionSpec


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlannedRun(FrozenModel):
    condition: ConditionSpec
    replicate: int = Field(gt=0)
    execution_order: int = Field(gt=0)
    run_seed: int


class CampaignManifest(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    campaign_id: str
    design_name: Literal["baseline-v1"] = "baseline-v1"
    random_seed: int
    replicates: int = Field(gt=0)
    calls_per_run: int = Field(gt=0)
    transports: tuple[Literal["in_memory", "stdio"], ...]
    payload_sizes: tuple[int, ...]
    service_times_ms: tuple[int, ...]
    concurrency_levels: tuple[int, ...]
    planned_runs: tuple[PlannedRun, ...]
    created_at_utc: datetime

    @model_validator(mode="after")
    def validate_design(self) -> Self:
        if self.created_at_utc.tzinfo is None or self.created_at_utc.utcoffset() != UTC.utcoffset(
            self.created_at_utc
        ):
            raise ValueError("created_at_utc must be UTC")
        expected = (
            len(self.transports)
            * len(self.payload_sizes)
            * len(self.service_times_ms)
            * len(self.concurrency_levels)
            * self.replicates
        )
        if len(self.planned_runs) != expected:
            raise ValueError("planned run count does not match the factorial design")
        return self


class CampaignProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campaign_id: str
    status: Literal["created", "running", "complete", "failed", "interrupted"]
    planned_runs: int
    completed_runs: int
    current_execution_order: int | None = None
    error_type: str | None = None
    updated_at_utc: datetime
