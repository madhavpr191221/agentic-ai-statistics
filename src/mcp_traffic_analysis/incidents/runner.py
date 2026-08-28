"""Run and measure one real or deterministic synthetic incident agent."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agents import Agent, ModelSettings, RunConfig, RunHooks, Runner
from agents.mcp import MCPServerStdio
from agents.models.openai_responses import OpenAIResponsesModel
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.shared import Reasoning

from mcp_traffic_analysis.behavior.traces import classify_trace, normalized_oracle_distance
from mcp_traffic_analysis.incidents.models import (
    ActionRecord,
    AgentEvent,
    BehaviorMetadata,
    IncidentResult,
    IncidentRunDetail,
    IncidentRunMeasurement,
    IncidentScenario,
    ModelCallMeasurement,
    TaskStructure,
)
from mcp_traffic_analysis.incidents.world import (
    ACTION_TOOL,
    INCOMING_MESSAGES,
    SCENARIOS,
    apply_action,
    evidence,
    initial_state,
    load_state,
    observe,
    oracle_sequence,
    save_state,
    score,
    score_behavior,
)
from mcp_traffic_analysis.transport.models import FrameDirection, TransportFrame

MODEL_ID = "gpt-5.6-sol"
INPUT_USD_PER_MILLION = 4.0
CACHED_INPUT_USD_PER_MILLION = 0.40
OUTPUT_USD_PER_MILLION = 20.0


class MeasurementHooks(RunHooks[Any]):
    def __init__(self) -> None:
        self.events: list[AgentEvent] = []
        self.model_calls: list[ModelCallMeasurement] = []
        self._model_starts: list[int] = []
        self._tool_starts: dict[str, int] = {}

    def _event(self, event: str, started: int, **kwargs: Any) -> None:
        self.events.append(
            AgentEvent(
                sequence=len(self.events),
                event=event,
                started_ns=started,
                elapsed_ms=(time.perf_counter_ns() - started) / 1_000_000,
                tool_name=kwargs.pop("tool_name", None),
                metadata=kwargs,
            )
        )

    async def on_llm_start(
        self, context: Any, agent: Any, system_prompt: Any, input_items: Any
    ) -> None:
        del context, agent, system_prompt, input_items  # Required RunHooks signature.
        started = time.perf_counter_ns()
        self._model_starts.append(started)
        self.events.append(
            AgentEvent(sequence=len(self.events), event="model_started", started_ns=started)
        )

    async def on_llm_end(self, context: Any, agent: Any, response: Any) -> None:
        del context, agent  # Required RunHooks signature.
        started = self._model_starts[-1]
        usage = getattr(response, "usage", None)
        details = getattr(usage, "input_tokens_details", None)
        measurement = ModelCallMeasurement(
            call_index=len(self.model_calls),
            latency_ms=(time.perf_counter_ns() - started) / 1_000_000,
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            cached_input_tokens=int(getattr(details, "cached_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            total_tokens=int(getattr(usage, "total_tokens", 0) or 0),
        )
        self.model_calls.append(measurement)
        self._event("model_finished", started, call_index=measurement.call_index)

    async def on_tool_start(self, context: Any, agent: Any, tool: Any) -> None:
        del context, agent  # Required RunHooks signature.
        name = str(getattr(tool, "name", "unknown"))
        started = time.perf_counter_ns()
        self._tool_starts[name] = started
        self.events.append(
            AgentEvent(
                sequence=len(self.events), event="tool_started", started_ns=started, tool_name=name
            )
        )

    async def on_tool_end(self, context: Any, agent: Any, tool: Any, result: str) -> None:
        del context, agent, result  # Required RunHooks signature.
        name = str(getattr(tool, "name", "unknown"))
        self._event(
            "tool_finished", self._tool_starts.pop(name, time.perf_counter_ns()), tool_name=name
        )


def _write_json(path: Path, value: Any) -> None:
    if hasattr(value, "model_dump_json"):
        path.write_text(value.model_dump_json(indent=2) + "\n", encoding="utf-8")
    else:
        path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, values: list[Any]) -> None:
    path.write_text(
        "".join(
            (
                value.model_dump_json()
                if hasattr(value, "model_dump_json")
                else json.dumps(value, default=str)
            )
            + "\n"
            for value in values
        ),
        encoding="utf-8",
    )


def _frames(path: Path) -> list[TransportFrame]:
    if not path.is_file():
        return []
    return [
        TransportFrame.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _deterministic_result(scenario: IncidentScenario, state_path: Path) -> IncidentResult:
    definition = SCENARIOS[scenario]
    facts = evidence(scenario)
    evidence_ids = [facts[key]["id"] for key in ("metrics", "logs", "dependencies", "changes")]
    apply_action(state_path, definition.required_action, definition.required_target)
    return IncidentResult(
        incident_id=scenario.value,
        diagnosis=definition.hidden_cause,
        evidence_ids=evidence_ids,
        selected_action=definition.required_action,
        action_target=definition.required_target,
        resolution_summary="Synthetic incident resolved.",
    )


def _required_action(scenario: IncidentScenario, state_path: Path) -> ActionRecord:
    definition = SCENARIOS[scenario]
    return apply_action(state_path, definition.required_action, definition.required_target)


def _deterministic_behavior_result(
    scenario: IncidentScenario, structure: TaskStructure, state_path: Path
) -> tuple[IncidentResult, list[str]]:
    sequence = oracle_sequence(scenario, structure)
    for tool_name in sequence:
        if tool_name == ACTION_TOOL[scenario]:
            _required_action(scenario, state_path)
        else:
            observe(state_path, tool_name)
    definition = SCENARIOS[scenario]
    state = load_state(state_path)
    return (
        IncidentResult(
            incident_id=scenario.value,
            diagnosis=definition.hidden_cause,
            evidence_ids=list(dict.fromkeys(state["evidence_seen"])),
            selected_action=definition.required_action,
            action_target=definition.required_target,
            resolution_summary="Synthetic incident resolved through the oracle path.",
        ),
        sequence,
    )


async def run_incident(
    *,
    scenario: IncidentScenario,
    output_root: Path,
    mode: str = "live",
    run_id: UUID | None = None,
    execution_order: int | None = None,
    block: int | None = None,
    task_structure: TaskStructure | None = None,
) -> IncidentRunDetail:
    load_dotenv()
    run_id = run_id or uuid4()
    created = datetime.now(UTC)
    run_directory = output_root / f"incident-{run_id}"
    run_directory.mkdir(parents=True, exist_ok=False)
    state_path, frames_path = run_directory / "world_state.json", run_directory / "frames.jsonl"
    mcp_events_path = run_directory / "mcp_events.jsonl"
    save_state(state_path, initial_state(scenario, task_structure))
    hooks = MeasurementHooks()
    result: IncidentResult | None = None
    failure_type: str | None = None
    failure_detail: str | None = None
    started = time.perf_counter_ns()
    scripted_sequence: list[str] = []
    if mode == "deterministic":
        if task_structure:
            result, scripted_sequence = _deterministic_behavior_result(
                scenario, task_structure, state_path
            )
        else:
            result = _deterministic_result(scenario, state_path)
    else:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is missing. Add it to .env before a live incident run."
            )
        relay_args = [
            "-m",
            "mcp_traffic_analysis.transport.stdio_relay",
            "--python",
            sys.executable,
            "--run-id",
            str(run_id),
            "--frames",
            str(frames_path.resolve()),
            "--server-module",
            "mcp_traffic_analysis.incidents.server",
            "--server-arg=--state",
            f"--server-arg={state_path.resolve()}",
            "--server-arg=--events",
            f"--server-arg={mcp_events_path.resolve()}",
        ]
        server = MCPServerStdio(
            name="measured incident MCP server",
            params={"command": sys.executable, "args": relay_args, "cwd": str(Path.cwd())},
            client_session_timeout_seconds=5,
            max_retry_attempts=0,
        )
        definition = SCENARIOS[scenario]
        instructions = (
            "Resolve the synthetic IT incident using only MCP evidence and actions. "
            "Gather evidence before acting. Never invent evidence IDs. Return every material "
            "evidence ID. Do not claim resolution unless an action "
            "tool accepted the exact target. The orders-api must not be restarted."
        )
        client = AsyncOpenAI(max_retries=0, timeout=120.0)
        model = OpenAIResponsesModel(model=MODEL_ID, openai_client=client)
        try:
            async with server:
                agent: Agent[Any] = Agent(
                    name="IT incident responder",
                    instructions=instructions,
                    model=model,
                    mcp_servers=[server],
                    output_type=IncidentResult,
                    model_settings=ModelSettings(
                        reasoning=Reasoning(effort="low"),
                        verbosity="low",
                        parallel_tool_calls=False,
                        store=False,
                        include_usage=True,
                    ),
                )
                run = await asyncio.wait_for(
                    Runner.run(
                        agent,
                        (
                            INCOMING_MESSAGES[scenario]
                            if task_structure
                            else f"Investigate incident {scenario.value}. Alert: {definition.alert}"
                        ),
                        max_turns=12,
                        hooks=hooks,
                        run_config=RunConfig(
                            tracing_disabled=True,
                            workflow_name=(
                                "phase4-task-structure"
                                if task_structure
                                else "phase3-incident-agent"
                            ),
                        ),
                    ),
                    timeout=300,
                )
                result = IncidentResult.model_validate(run.final_output)
        except TimeoutError:
            failure_type = "run_timeout"
        except Exception as error:
            failure_type = type(error).__name__
            failure_detail = str(error)
        finally:
            await client.close()

    total_ms = (time.perf_counter_ns() - started) / 1_000_000
    state = load_state(state_path)
    actions = [ActionRecord.model_validate(item) for item in state["actions"]]
    score_card = score_behavior(state, result) if task_structure else score(state, result)
    frames = _frames(frames_path)
    mcp_events = (
        [json.loads(line) for line in mcp_events_path.read_text(encoding="utf-8").splitlines()]
        if mcp_events_path.is_file()
        else []
    )
    model_ms = sum(item.latency_ms or 0 for item in hooks.model_calls)
    handler_ms = sum(float(item["handler_latency_ms"]) for item in mcp_events)
    tool_events = [item for item in hooks.events if item.event == "tool_finished"]
    mcp_ms = sum(item.elapsed_ms or 0.0 for item in tool_events)
    orchestration_ms = total_ms - model_ms - mcp_ms
    usage_input = sum(item.input_tokens for item in hooks.model_calls)
    cached = sum(item.cached_input_tokens for item in hooks.model_calls)
    output = sum(item.output_tokens for item in hooks.model_calls)
    cost = (
        (usage_input - cached) * INPUT_USD_PER_MILLION
        + cached * CACHED_INPUT_USD_PER_MILLION
        + output * OUTPUT_USD_PER_MILLION
    ) / 1_000_000
    tool_sequence = (
        scripted_sequence
        if mode == "deterministic" and task_structure
        else [str(item["tool_name"]) for item in mcp_events]
    )
    sdk_tool_sequence = [item.tool_name or "unknown" for item in tool_events]
    correlation_consistent = (
        True
        if mode == "deterministic" and task_structure
        else sdk_tool_sequence == tool_sequence
    )
    measurement = IncidentRunMeasurement(
        run_id=run_id,
        scenario_id=scenario,
        status="success" if score_card.task_success and correlation_consistent else "failure",
        failure_type=failure_type
        if failure_type
        else (
            "correlation_mismatch"
            if not correlation_consistent
            else (None if score_card.task_success else "task_failure")
        ),
        total_latency_ms=total_ms,
        model_latency_ms=model_ms,
        mcp_latency_ms=mcp_ms,
        server_handler_latency_ms=handler_ms,
        orchestration_latency_ms=orchestration_ms,
        decomposition_consistent=orchestration_ms >= -1,
        correlation_consistent=correlation_consistent,
        model_call_count=len(hooks.model_calls),
        mcp_call_count=len(tool_sequence),
        tool_sequence=tool_sequence,
        input_tokens=usage_input,
        cached_input_tokens=cached,
        output_tokens=output,
        total_tokens=usage_input + output,
        request_frame_bytes=sum(
            f.frame_bytes for f in frames if f.direction is FrameDirection.CLIENT_TO_SERVER
        ),
        response_frame_bytes=sum(
            f.frame_bytes for f in frames if f.direction is FrameDirection.SERVER_TO_CLIENT
        ),
        estimated_cost_usd=cost,
    )
    behavior: BehaviorMetadata | None = None
    if task_structure:
        oracle = oracle_sequence(scenario, task_structure)
        trace_steps = classify_trace(tool_sequence, oracle, actions)
        behavior = BehaviorMetadata(
            task_structure=task_structure,
            incoming_message=INCOMING_MESSAGES[scenario],
            oracle_sequence=oracle,
            observed_sequence=tool_sequence,
            oracle_call_count=len(oracle),
            excess_mcp_calls=(
                len(tool_sequence) - len(oracle) if score_card.task_success else None
            ),
            normalized_oracle_distance=normalized_oracle_distance(tool_sequence, oracle),
            expected_rejections=sum(action.expected_rejection for action in actions),
            unexpected_rejections=sum(
                not action.accepted and not action.expected_rejection and not action.prohibited
                for action in actions
            ),
            trace_steps=trace_steps,
            execution_mode=(
                "scripted_validation" if mode == "deterministic" else "live_measurement"
            ),
            request_frame_bytes=(
                None
                if mode == "deterministic"
                else sum(
                    frame.frame_bytes
                    for frame in frames
                    if frame.direction is FrameDirection.CLIENT_TO_SERVER
                )
            ),
            response_frame_bytes=(
                None
                if mode == "deterministic"
                else sum(
                    frame.frame_bytes
                    for frame in frames
                    if frame.direction is FrameDirection.SERVER_TO_CLIENT
                )
            ),
            block=block,
            execution_order=execution_order,
        )
    detail = IncidentRunDetail(
        run_id=run_id,
        scenario_id=scenario,
        created_at_utc=created,
        model_id=MODEL_ID,
        measurement=measurement,
        result=result,
        score=score_card,
        actions=actions,
        agent_events=hooks.events,
        behavior=behavior,
    )
    manifest = {
        "schema_version": "4.0.0" if task_structure else "3.0.0",
        "run_id": str(run_id),
        "scenario_id": scenario.value,
        "created_at_utc": created.isoformat(),
        "model_id": MODEL_ID,
        "mode": mode,
        "execution_order": execution_order,
        "block": block,
        "task_structure": task_structure.value if task_structure else None,
        "incoming_message": INCOMING_MESSAGES[scenario] if task_structure else None,
        "transport": "stdio",
        "model_settings": {
            "reasoning_effort": "low",
            "verbosity": "low",
            "parallel_tool_calls": False,
            "store": False,
        },
        "price_snapshot": {
            "date": "2026-08-27",
            "input_usd_per_million": INPUT_USD_PER_MILLION,
            "cached_input_usd_per_million": CACHED_INPUT_USD_PER_MILLION,
            "output_usd_per_million": OUTPUT_USD_PER_MILLION,
            "source": "https://developers.openai.com/api/docs/models/gpt-5.6-sol",
        },
    }
    _write_json(run_directory / "manifest.json", manifest)
    _write_jsonl(run_directory / "agent_events.jsonl", hooks.events)
    _write_jsonl(run_directory / "model_calls.jsonl", hooks.model_calls)
    _write_jsonl(run_directory / "action_ledger.jsonl", actions)
    _write_json(
        run_directory / "final_output.json", result.model_dump(mode="json") if result else None
    )
    _write_json(run_directory / "score.json", score_card)
    _write_json(run_directory / "run_measurement.json", measurement)
    _write_json(run_directory / "detail.json", detail)
    if failure_type:
        _write_json(
            run_directory / "terminal_error.json",
            {"error_type": failure_type, "detail": failure_detail},
        )
    return detail
