"""FastAPI application for the local Phase 1A experiment workbench."""

from __future__ import annotations

from pathlib import Path
from statistics import median
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from mcp_traffic_analysis.api.campaign_repository import CampaignNotFoundError, CampaignRepository
from mcp_traffic_analysis.api.models import (
    AnalysisRequest,
    AnalysisResponse,
    CampaignDetail,
    CampaignListResponse,
    CampaignSummary,
    EventListResponse,
    HealthResponse,
    Phase2RunRequest,
    Phase2RunResponse,
    RunDetail,
    RunListResponse,
    RunRequest,
    ScenarioDescriptor,
)
from mcp_traffic_analysis.api.repository import (
    ArtifactRecord,
    ArtifactRepository,
    RunNotFoundError,
)
from mcp_traffic_analysis.api.trace_analysis import analyze_records, summarize_record
from mcp_traffic_analysis.experiments.condition_runner import run_condition
from mcp_traffic_analysis.fixtures.runner import Scenario, run_fixture
from mcp_traffic_analysis.measurement.transport_models import CallMeasurement, RunMeasurement

SCENARIOS = [
    ScenarioDescriptor(
        id=Scenario.LIST_TOOLS,
        label="Tool discovery",
        description="List the deterministic tools exposed by the FastMCP server.",
        expected_outcome="success",
    ),
    ScenarioDescriptor(
        id=Scenario.ECHO,
        label="Controlled output",
        description="Call echo_bytes with a fixed 64-character synthetic output.",
        expected_outcome="success",
    ),
    ScenarioDescriptor(
        id=Scenario.SLEEP,
        label="Controlled service time",
        description="Call sleep_ms with a configured 20 ms delay.",
        expected_outcome="success",
    ),
    ScenarioDescriptor(
        id=Scenario.BACKEND_EXCEPTION,
        label="Backend exception",
        description="Raise and classify a controlled synthetic backend exception.",
        expected_outcome="backend_exception",
    ),
    ScenarioDescriptor(
        id=Scenario.TOOL_ERROR,
        label="Tool error",
        description="Raise and classify an explicit FastMCP tool error.",
        expected_outcome="tool_error",
    ),
    ScenarioDescriptor(
        id=Scenario.TIMEOUT,
        label="Timeout",
        description="Raise and classify a controlled timeout cause.",
        expected_outcome="timeout",
    ),
    ScenarioDescriptor(
        id=Scenario.NONEXISTENT_TOOL,
        label="Missing tool",
        description="Call a nonexistent tool and retain the protocol outcome.",
        expected_outcome="nonexistent_tool",
    ),
    ScenarioDescriptor(
        id=Scenario.CONCURRENT,
        label="Concurrent calls",
        description="Run three controlled service times concurrently.",
        expected_outcome="success",
    ),
    ScenarioDescriptor(
        id=Scenario.CANCELLATION,
        label="Cancellation",
        description="Cancel an in-flight controlled service operation.",
        expected_outcome="cancellation",
    ),
]


def create_app(
    *,
    artifact_root: Path = Path("artifacts/phase1a"),
    campaign_root: Path = Path("artifacts/phase2"),
    frontend_dist: Path = Path("frontend/dist"),
    serve_frontend: bool = True,
) -> FastAPI:
    repository = ArtifactRepository(artifact_root)
    campaigns_repository = CampaignRepository(campaign_root)
    api = FastAPI(
        title="MCP Traffic Analysis",
        version="0.2.0",
        description="Local API for deterministic MCP performance experiments.",
    )
    api.state.repository = repository
    api.state.campaign_repository = campaigns_repository
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    def get_record(run_id: UUID) -> ArtifactRecord:
        try:
            return repository.get(run_id)
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="run not found") from error

    @api.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @api.get("/api/scenarios", response_model=list[ScenarioDescriptor])
    async def scenarios() -> list[ScenarioDescriptor]:
        return SCENARIOS

    @api.post("/api/runs", response_model=RunDetail, status_code=201)
    async def create_run(request: RunRequest) -> RunDetail:
        artifacts = await run_fixture(
            scenario=request.scenario,
            output_root=repository.root,
            repeat=request.repeat,
            seed=request.seed,
        )
        record = repository.read_directory(artifacts.run_directory)
        return RunDetail(manifest=record.manifest, summary=summarize_record(record))

    @api.get("/api/runs", response_model=RunListResponse)
    async def list_runs() -> RunListResponse:
        return RunListResponse(
            runs=[summarize_record(record) for record in repository.list_records()]
        )

    @api.get("/api/runs/{run_id}", response_model=RunDetail)
    async def run_detail(run_id: UUID) -> RunDetail:
        record = get_record(run_id)
        return RunDetail(manifest=record.manifest, summary=summarize_record(record))

    @api.get("/api/runs/{run_id}/events", response_model=EventListResponse)
    async def run_events(run_id: UUID) -> EventListResponse:
        record = get_record(run_id)
        return EventListResponse(run_id=run_id, events=list(record.events))

    @api.post("/api/analysis/describe", response_model=AnalysisResponse)
    async def describe(request: AnalysisRequest) -> AnalysisResponse:
        records = [get_record(run_id) for run_id in request.run_ids]
        return analyze_records(records, request.unit)

    @api.post("/api/phase2/runs", response_model=Phase2RunResponse, status_code=201)
    async def create_phase2_run(request: Phase2RunRequest) -> Phase2RunResponse:
        artifacts = await run_condition(
            spec=request.condition(),
            output_root=repository.root,
            seed=request.seed,
        )
        manifest = repository.read_directory(artifacts.run_directory).manifest
        calls = [
            CallMeasurement.model_validate_json(line)
            for line in artifacts.calls_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        run = RunMeasurement.model_validate_json(
            artifacts.run_measurement_path.read_text(encoding="utf-8")
        )
        handler = [call.server_handler_ms for call in calls if call.server_handler_ms is not None]
        residual = [value for call in calls if (value := call.nonhandler_residual_ms) is not None]
        request_bytes = [
            call.request_frame_bytes for call in calls if call.request_frame_bytes is not None
        ]
        response_bytes = [
            call.response_frame_bytes for call in calls if call.response_frame_bytes is not None
        ]
        return Phase2RunResponse(
            run_id=manifest.run_id,
            condition_id=manifest.condition_id,
            transport=request.transport,
            session_start_ms=run.session_start_ms,
            run_elapsed_ms=run.run_elapsed_ms,
            median_client_roundtrip_ms=median(call.client_roundtrip_ms for call in calls),
            median_server_handler_ms=median(handler) if handler else None,
            median_nonhandler_residual_ms=median(residual) if residual else None,
            total_request_frame_bytes=sum(request_bytes) if request_bytes else None,
            total_response_frame_bytes=sum(response_bytes) if response_bytes else None,
            calls=calls,
        )

    @api.get("/api/campaigns", response_model=CampaignListResponse)
    async def list_campaigns() -> CampaignListResponse:
        return CampaignListResponse(
            campaigns=[
                CampaignSummary(
                    campaign_id=manifest.campaign_id,
                    design_name=manifest.design_name,
                    status=progress.status,
                    planned_runs=progress.planned_runs,
                    completed_runs=progress.completed_runs,
                    created_at_utc=manifest.created_at_utc,
                )
                for manifest, progress in campaigns_repository.list()
            ]
        )

    @api.get("/api/campaigns/{campaign_id}", response_model=CampaignDetail)
    async def campaign_detail(campaign_id: str) -> CampaignDetail:
        try:
            manifest, progress, analysis = campaigns_repository.get(campaign_id)
        except CampaignNotFoundError as error:
            raise HTTPException(status_code=404, detail="campaign not found") from error
        return CampaignDetail(manifest=manifest, progress=progress, analysis=analysis)

    @api.get("/api/campaigns/{campaign_id}/tables/{table_name}")
    async def campaign_table(
        campaign_id: str,
        table_name: Literal["runs.csv", "calls.csv", "runs.parquet", "calls.parquet"],
    ) -> FileResponse:
        try:
            path = campaigns_repository.directory(campaign_id) / "tables" / table_name
        except CampaignNotFoundError as error:
            raise HTTPException(status_code=404, detail="campaign not found") from error
        if not path.is_file():
            raise HTTPException(status_code=404, detail="table not found")
        return FileResponse(path, filename=table_name)

    resolved_dist = frontend_dist.resolve()
    index_path = resolved_dist / "index.html"
    assets_path = resolved_dist / "assets"
    if serve_frontend and index_path.is_file():
        if assets_path.is_dir():
            api.mount("/assets", StaticFiles(directory=assets_path), name="frontend-assets")

        @api.get("/", include_in_schema=False)
        async def frontend() -> FileResponse:
            return FileResponse(index_path)

    else:

        @api.get("/", include_in_schema=False)
        async def api_root() -> dict[str, str]:
            return {
                "name": "MCP Traffic Analysis API",
                "docs": "/docs",
                "health": "/api/health",
            }

    return api


app = create_app()
