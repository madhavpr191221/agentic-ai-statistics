"""FastAPI application for the local Phase 1A experiment workbench."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from mcp_traffic_analysis.api.models import (
    AnalysisRequest,
    AnalysisResponse,
    EventListResponse,
    HealthResponse,
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
from mcp_traffic_analysis.fixtures.runner import Scenario, run_fixture

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
    frontend_dist: Path = Path("frontend/dist"),
    serve_frontend: bool = True,
) -> FastAPI:
    repository = ArtifactRepository(artifact_root)
    api = FastAPI(
        title="MCP Traffic Analysis",
        version="0.1.0",
        description="Local API for deterministic MCP performance experiments.",
    )
    api.state.repository = repository
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
