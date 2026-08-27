"""Local FastMCP server for the synthetic incident environment."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from mcp_traffic_analysis.incidents.world import apply_action, load_state, observe, save_state


def _append(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, default=str) + "\n")


def create_incident_server(state_path: Path, event_path: Path) -> FastMCP:
    server = FastMCP("Synthetic IT incident operations", mask_error_details=False)

    def observed(
        name: str, function: Callable[..., Coroutine[Any, Any, Any]]
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        @wraps(function)
        async def wrapper(**kwargs: Any) -> Any:
            started = time.perf_counter_ns()
            outcome = "success"
            error_type = None
            try:
                return await function(**kwargs)
            except Exception as error:
                outcome, error_type = "failure", type(error).__name__
                raise
            finally:
                _append(
                    event_path,
                    {
                        "timestamp_utc": datetime.now(UTC).isoformat(),
                        "tool_name": name,
                        "arguments": kwargs,
                        "handler_latency_ms": (time.perf_counter_ns() - started) / 1_000_000,
                        "outcome": outcome,
                        "error_type": error_type,
                    },
                )

        wrapper.__name__ = name
        return wrapper

    async def alert() -> dict[str, Any]:
        return observe(state_path, "get_alert")

    async def metrics() -> dict[str, Any]:
        return observe(state_path, "get_metrics")

    async def logs(query: str = "") -> dict[str, Any]:
        return observe(state_path, "search_logs", query)

    async def dependencies() -> dict[str, Any]:
        return observe(state_path, "get_dependencies")

    async def changes() -> dict[str, Any]:
        return observe(state_path, "get_recent_changes")

    async def runbook() -> dict[str, Any]:
        return observe(state_path, "get_runbook")

    async def restart(target: str) -> dict[str, Any]:
        return apply_action(state_path, "restart_service", target).model_dump(mode="json")

    async def rollback(deployment: str) -> dict[str, Any]:
        return apply_action(state_path, "rollback_deployment", deployment).model_dump(mode="json")

    async def escalate(owner: str) -> dict[str, Any]:
        return apply_action(state_path, "escalate_incident", owner).model_dump(mode="json")

    async def update(status: str) -> dict[str, str]:
        state = load_state(state_path)
        state["updates"].append(status)
        save_state(state_path, state)
        return {"recorded": status}

    tools: list[tuple[str, Callable[..., Coroutine[Any, Any, Any]], str]] = [
        ("get_alert", alert, "Read the active incident alert."),
        ("get_metrics", metrics, "Inspect relevant service metrics and return evidence IDs."),
        ("search_logs", logs, "Search incident logs and return evidence IDs."),
        ("get_dependencies", dependencies, "Inspect service dependency health."),
        ("get_recent_changes", changes, "Inspect recent production changes."),
        ("get_runbook", runbook, "Read safe-response guidance."),
        ("restart_service", restart, "Restart one synthetic service or worker."),
        ("rollback_deployment", rollback, "Roll back one synthetic deployment."),
        ("escalate_incident", escalate, "Escalate to a synthetic service owner."),
        ("update_incident", update, "Record a synthetic incident status update."),
    ]
    for name, function, description in tools:
        server.tool(name=name, description=description)(observed(name, function))
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    args = parser.parse_args()
    create_incident_server(args.state, args.events).run(
        transport="stdio", show_banner=False, log_level="WARNING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
