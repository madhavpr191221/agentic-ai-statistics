"""FastAPI application for the measured Phase 3 and Phase 4 agent studies."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from mcp_traffic_analysis.behavior.repository import BehaviorRepository
from mcp_traffic_analysis.incidents.models import (
    BehaviorRunRequest,
    IncidentRunDetail,
    IncidentRunRequest,
    TaskStructure,
)
from mcp_traffic_analysis.incidents.repository import IncidentRepository
from mcp_traffic_analysis.incidents.runner import run_incident
from mcp_traffic_analysis.incidents.world import INCOMING_MESSAGES, oracle_sequence
from mcp_traffic_analysis.incidents.world import SCENARIOS as INCIDENT_SCENARIOS

AgentTable = Literal[
    "runs.csv",
    "runs.parquet",
    "model_calls.csv",
    "model_calls.parquet",
    "mcp_calls.csv",
    "mcp_calls.parquet",
    "actions.csv",
    "actions.parquet",
    "traces.csv",
    "traces.parquet",
]
BehaviorTable = Literal[
    "runs.csv",
    "runs.parquet",
    "traces.csv",
    "traces.parquet",
    "transitions.csv",
    "transitions.parquet",
    "actions.csv",
    "actions.parquet",
    "mcp_calls.csv",
    "mcp_calls.parquet",
    "model_calls.csv",
    "model_calls.parquet",
]


def _campaign_table(root: Path, campaign_id: str, table_name: str) -> Path:
    if not campaign_id or any(character in campaign_id for character in "/\\.."):
        raise HTTPException(status_code=404, detail="campaign not found")
    resolved_root = root.resolve()
    campaign_directory = (resolved_root / f"campaign-{campaign_id}").resolve()
    if campaign_directory.parent != resolved_root:
        raise HTTPException(status_code=404, detail="campaign not found")
    path = campaign_directory / "tables" / table_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="campaign table not found")
    return path


def create_app(
    *,
    agent_root: Path = Path("artifacts/phase3"),
    behavior_root: Path = Path("artifacts/phase4"),
    frontend_dist: Path = Path("frontend/dist"),
    serve_frontend: bool = True,
) -> FastAPI:
    incident_repository = IncidentRepository(agent_root)
    behavior_repository = BehaviorRepository(behavior_root)
    agent_available = bool(os.getenv("OPENAI_API_KEY") or Path(".env").is_file())
    api = FastAPI(
        title="MCP Traffic Analysis",
        version="0.5.0",
        description="Local API for measured IT-incident agent experiments.",
    )
    api.state.incident_repository = incident_repository
    api.state.behavior_repository = behavior_repository
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @api.get("/api/health")
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "phase": "4",
            "measurement_boundary": "agent_model_and_stdio_mcp",
            "agent_available": agent_available,
        }

    @api.get("/api/behavior/conditions")
    async def behavior_conditions() -> list[dict[str, object]]:
        return [
            {
                "scenario_id": scenario.value,
                "label": INCIDENT_SCENARIOS[scenario].label,
                "incoming_message": INCOMING_MESSAGES[scenario],
                "task_structure": structure.value,
                "oracle_sequence": oracle_sequence(scenario, structure),
            }
            for scenario in INCIDENT_SCENARIOS
            for structure in TaskStructure
        ]

    @api.post("/api/behavior/runs", response_model=IncidentRunDetail, status_code=201)
    async def create_behavior_run(request: BehaviorRunRequest) -> IncidentRunDetail:
        if request.mode == "live" and not agent_available:
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY is missing. Add it to .env and restart the API.",
            )
        try:
            return await run_incident(
                scenario=request.scenario,
                task_structure=request.task_structure,
                output_root=behavior_repository.root,
                mode=request.mode,
            )
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @api.get("/api/behavior/runs", response_model=list[IncidentRunDetail])
    async def list_behavior_runs() -> list[IncidentRunDetail]:
        return behavior_repository.list_runs()

    @api.get("/api/behavior/runs/{run_id}", response_model=IncidentRunDetail)
    async def get_behavior_run(run_id: UUID) -> IncidentRunDetail:
        try:
            return behavior_repository.get(run_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="behavior run not found") from error

    @api.get("/api/behavior/campaigns")
    async def list_behavior_campaigns() -> list[dict[str, object]]:
        return behavior_repository.list_campaigns()

    @api.get("/api/behavior/campaigns/{campaign_id}")
    async def get_behavior_campaign(campaign_id: str) -> dict[str, object]:
        try:
            return behavior_repository.campaign(campaign_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="behavior campaign not found") from error

    @api.get("/api/behavior/campaigns/{campaign_id}/tables/{table_name}")
    async def behavior_campaign_table(
        campaign_id: str, table_name: BehaviorTable
    ) -> FileResponse:
        path = _campaign_table(behavior_repository.root, campaign_id, table_name)
        return FileResponse(path, filename=table_name)

    @api.get("/api/agent/scenarios")
    async def agent_scenarios() -> list[dict[str, object]]:
        return [
            {"id": item.id.value, "label": item.label, "alert": item.alert}
            for item in INCIDENT_SCENARIOS.values()
        ]

    @api.post("/api/agent/runs", response_model=IncidentRunDetail, status_code=201)
    async def create_agent_run(request: IncidentRunRequest) -> IncidentRunDetail:
        if request.mode == "live" and not agent_available:
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY is missing. Add it to .env and restart the API.",
            )
        try:
            return await run_incident(
                scenario=request.scenario,
                output_root=incident_repository.root,
                mode=request.mode,
            )
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @api.get("/api/agent/runs", response_model=list[IncidentRunDetail])
    async def list_agent_runs() -> list[IncidentRunDetail]:
        return incident_repository.list_runs()

    @api.get("/api/agent/runs/{run_id}", response_model=IncidentRunDetail)
    async def get_agent_run(run_id: UUID) -> IncidentRunDetail:
        try:
            return incident_repository.get(run_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="agent run not found") from error

    @api.get("/api/agent/campaigns")
    async def list_agent_campaigns() -> list[dict[str, object]]:
        return incident_repository.list_campaigns()

    @api.get("/api/agent/campaigns/{campaign_id}")
    async def get_agent_campaign(campaign_id: str) -> dict[str, object]:
        if not campaign_id or any(character in campaign_id for character in "/\\.."):
            raise HTTPException(status_code=404, detail="agent campaign not found")
        try:
            return incident_repository.campaign(campaign_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="agent campaign not found") from error

    @api.get("/api/agent/campaigns/{campaign_id}/tables/{table_name}")
    async def agent_campaign_table(campaign_id: str, table_name: AgentTable) -> FileResponse:
        path = _campaign_table(incident_repository.root, campaign_id, table_name)
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
