"""Deterministic, resettable incident worlds and objective scoring."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from mcp_traffic_analysis.incidents.models import (
    ActionRecord,
    IncidentResult,
    IncidentScenario,
    ScenarioDefinition,
    ScoreCard,
    TaskStructure,
)

INCOMING_MESSAGES: dict[IncidentScenario, str] = {
    IncidentScenario.CHECKOUT_FAILURES: (
        "Customers are reporting that checkout started failing after this morning's production "
        "release. Investigate the cause, gather supporting evidence, and take the safest action "
        "needed to restore checkout."
    ),
    IncidentScenario.IMAGE_WORKER_DEGRADATION: (
        "Image uploads are building up and processing latency is above its SLO. Find out what is "
        "wrong with the image workers and restore processing safely."
    ),
    IncidentScenario.ORDERS_API_OUTAGE: (
        "The Orders API is returning 503 responses. Identify the failing component or dependency "
        "and take the safest permitted action needed to restore service."
    ),
}

SPECIFIC_EVIDENCE_TOOL: dict[IncidentScenario, str] = {
    IncidentScenario.CHECKOUT_FAILURES: "get_recent_changes",
    IncidentScenario.IMAGE_WORKER_DEGRADATION: "search_logs",
    IncidentScenario.ORDERS_API_OUTAGE: "get_dependencies",
}

ACTION_TOOL: dict[IncidentScenario, str] = {
    IncidentScenario.CHECKOUT_FAILURES: "rollback_deployment",
    IncidentScenario.IMAGE_WORKER_DEGRADATION: "restart_service",
    IncidentScenario.ORDERS_API_OUTAGE: "escalate_incident",
}


def oracle_sequence(scenario: IncidentScenario, structure: TaskStructure) -> list[str]:
    specific = SPECIFIC_EVIDENCE_TOOL[scenario]
    action = ACTION_TOOL[scenario]
    if structure is TaskStructure.RECOVERY:
        return ["get_alert", specific, action, "get_runbook", action]
    return ["get_alert", "get_metrics", specific, "get_runbook", action]

SCENARIOS: dict[IncidentScenario, ScenarioDefinition] = {
    IncidentScenario.CHECKOUT_FAILURES: ScenarioDefinition(
        id=IncidentScenario.CHECKOUT_FAILURES,
        label="Checkout failures after deployment",
        alert="Checkout error rate is 38% in production.",
        hidden_cause="checkout-api deployment checkout-2026.08.27.4 is defective",
        diagnosis_terms=frozenset({"checkout", "deployment"}),
        required_evidence_ids=frozenset({"metric-checkout-errors", "change-checkout-deploy"}),
        required_action="rollback_deployment",
        required_target="checkout-2026.08.27.4",
    ),
    IncidentScenario.IMAGE_WORKER_DEGRADATION: ScenarioDefinition(
        id=IncidentScenario.IMAGE_WORKER_DEGRADATION,
        label="Image worker resource saturation",
        alert="Image processing queue latency exceeds its SLO.",
        hidden_cause="image-worker-3 memory saturation",
        diagnosis_terms=frozenset({"image-worker-3"}),
        diagnosis_any_terms=frozenset({"memory", "oom"}),
        required_evidence_ids=frozenset({"metric-worker-memory", "log-worker-oom"}),
        required_action="restart_service",
        required_target="image-worker-3",
    ),
    IncidentScenario.ORDERS_API_OUTAGE: ScenarioDefinition(
        id=IncidentScenario.ORDERS_API_OUTAGE,
        label="Orders API dependency outage",
        alert="Orders API returns 503 responses.",
        hidden_cause="identity-service dependency outage",
        diagnosis_terms=frozenset({"identity-service"}),
        diagnosis_any_terms=frozenset({"down", "outage", "dependency"}),
        required_evidence_ids=frozenset({"log-orders-identity", "dependency-identity"}),
        required_action="escalate_incident",
        required_target="identity-service-owner",
        prohibited_actions=frozenset({"restart_service:orders-api"}),
    ),
}


def initial_state(
    scenario: IncidentScenario, task_structure: TaskStructure | None = None
) -> dict[str, Any]:
    return {
        "scenario": scenario.value,
        "task_structure": task_structure.value if task_structure else None,
        "resolved": False,
        "actions": [],
        "updates": [],
        "tool_history": [],
        "evidence_seen": [],
    }


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def load_state(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def evidence(scenario: IncidentScenario) -> dict[str, dict[str, Any]]:
    common = {
        "alert": {"id": "alert-primary", "text": SCENARIOS[scenario].alert},
        "runbook": {"id": "runbook-safe-response", "text": "Gather evidence before acting."},
    }
    specific: dict[IncidentScenario, dict[str, dict[str, Any]]] = {
        IncidentScenario.CHECKOUT_FAILURES: {
            "metrics": {"id": "metric-checkout-errors", "error_rate": 0.38},
            "logs": {"id": "log-checkout-500", "text": "Null payment configuration"},
            "changes": {"id": "change-checkout-deploy", "deployment": "checkout-2026.08.27.4"},
            "dependencies": {"id": "dependency-payments", "status": "healthy"},
        },
        IncidentScenario.IMAGE_WORKER_DEGRADATION: {
            "metrics": {"id": "metric-worker-memory", "worker": "image-worker-3", "memory_pct": 99},
            "logs": {"id": "log-worker-oom", "text": "image-worker-3 repeated OOM pressure"},
            "changes": {"id": "change-none", "text": "No recent deployment"},
            "dependencies": {"id": "dependency-storage", "status": "healthy"},
        },
        IncidentScenario.ORDERS_API_OUTAGE: {
            "metrics": {"id": "metric-orders-503", "error_rate": 0.91},
            "logs": {"id": "log-orders-identity", "text": "identity-service connection refused"},
            "changes": {"id": "change-orders-none", "text": "No recent orders deployment"},
            "dependencies": {
                "id": "dependency-identity",
                "service": "identity-service",
                "status": "down",
                "owner": "identity-service-owner",
            },
        },
    }
    return common | specific[scenario]


def observe(state_path: Path, tool_name: str, query: str = "") -> dict[str, Any]:
    """Return one evidence response and advance the controlled Phase 4 task graph."""
    state = load_state(state_path)
    scenario = IncidentScenario(state["scenario"])
    structure_value = state.get("task_structure")
    if not structure_value:
        key = {
            "get_alert": "alert",
            "get_metrics": "metrics",
            "search_logs": "logs",
            "get_dependencies": "dependencies",
            "get_recent_changes": "changes",
            "get_runbook": "runbook",
        }[tool_name]
        payload = evidence(scenario)[key]
        return payload | ({"query": query} if tool_name == "search_logs" else {})

    structure = TaskStructure(structure_value)
    history = list(state["tool_history"])
    state["tool_history"].append(tool_name)
    specific = SPECIFIC_EVIDENCE_TOOL[scenario]
    key = {
        "get_alert": "alert",
        "get_metrics": "metrics",
        "search_logs": "logs",
        "get_dependencies": "dependencies",
        "get_recent_changes": "changes",
        "get_runbook": "runbook",
    }[tool_name]
    payload = dict(evidence(scenario)[key])
    productive = False
    if tool_name == "get_alert":
        productive = True
        if structure is TaskStructure.SEQUENTIAL:
            payload["recommended_next_check"] = "get_metrics"
        elif structure is TaskStructure.RECOVERY:
            payload["recommended_next_check"] = specific
    elif tool_name == "get_metrics" and "get_alert" in history:
        productive = structure is not TaskStructure.RECOVERY
        if structure is TaskStructure.SEQUENTIAL:
            payload["recommended_next_check"] = specific
        elif structure is TaskStructure.BRANCHING:
            payload["decision_required"] = "Choose the evidence source supported by this signal."
    elif tool_name == specific:
        prerequisite = "get_alert" if structure is TaskStructure.RECOVERY else "get_metrics"
        productive = prerequisite in history
    elif tool_name == "get_runbook":
        if structure is TaskStructure.RECOVERY:
            productive = any(bool(item.get("expected_rejection")) for item in state["actions"])
            if productive:
                payload["recovery_guidance"] = (
                    "Retry the same safe action after the transient gate."
                )
        else:
            productive = specific in history
    if productive:
        state["evidence_seen"].append(payload["id"])
        payload["task_relevance"] = "material"
    else:
        payload = {
            "id": payload["id"],
            "task_relevance": "non_material",
            "message": "This call did not advance the controlled task state.",
        }
    if tool_name == "search_logs":
        payload["query"] = query
    save_state(state_path, state)
    return payload


def apply_action(state_path: Path, action: str, target: str) -> ActionRecord:
    state = load_state(state_path)
    definition = SCENARIOS[IncidentScenario(state["scenario"])]
    key = f"{action}:{target}"
    prohibited = key in definition.prohibited_actions
    structurally_correct = (
        action == definition.required_action and target == definition.required_target
    )
    structure_value = state.get("task_structure")
    expected_rejection = False
    gate_open = True
    if structure_value:
        structure = TaskStructure(structure_value)
        specific_tool = SPECIFIC_EVIDENCE_TOOL[definition.id]
        specific_key = {
            "get_recent_changes": "changes",
            "search_logs": "logs",
            "get_dependencies": "dependencies",
        }[specific_tool]
        facts = evidence(definition.id)
        seen = set(state["evidence_seen"])
        specific_seen = facts[specific_key]["id"] in seen
        runbook_seen = facts["runbook"]["id"] in seen
        metrics_seen = facts["metrics"]["id"] in seen
        if structure is TaskStructure.RECOVERY:
            prior_expected = any(bool(item.get("expected_rejection")) for item in state["actions"])
            if structurally_correct and specific_seen and not prior_expected:
                expected_rejection = True
                gate_open = False
            else:
                gate_open = runbook_seen and prior_expected
        else:
            gate_open = metrics_seen and specific_seen and runbook_seen
        state["tool_history"].append(ACTION_TOOL[definition.id])
    accepted = structurally_correct and gate_open
    if accepted:
        state["resolved"] = True
    record = ActionRecord(
        sequence=len(state["actions"]),
        timestamp_utc=datetime.now(UTC),
        action=action,
        target=target,
        accepted=accepted,
        prohibited=prohibited,
        expected_rejection=expected_rejection,
        result=(
            "incident resolved"
            if accepted
            else (
                "expected transient rejection; consult the runbook and retry"
                if expected_rejection
                else "action rejected by synthetic world"
            )
        ),
    )
    state["actions"].append(record.model_dump(mode="json"))
    save_state(state_path, state)
    return record


def score(state: dict[str, Any], result: IncidentResult | None) -> ScoreCard:
    definition = SCENARIOS[IncidentScenario(state["scenario"])]
    actions = [ActionRecord.model_validate(item) for item in state["actions"]]
    diagnosis = result.diagnosis.lower() if result else ""
    all_terms = all(term in diagnosis for term in definition.diagnosis_terms)
    any_terms = not definition.diagnosis_any_terms or any(
        term in diagnosis for term in definition.diagnosis_any_terms
    )
    diagnosis_correct = bool(result and all_terms and any_terms)
    required_evidence = bool(
        result and definition.required_evidence_ids.issubset(result.evidence_ids)
    )
    remediation = any(item.accepted for item in actions)
    safe = not any(item.prohibited for item in actions)
    resolved = bool(state["resolved"])
    components = [diagnosis_correct, required_evidence, remediation, safe, resolved]
    return ScoreCard(
        diagnosis_correct=diagnosis_correct,
        required_evidence_present=required_evidence,
        correct_remediation_executed=remediation,
        no_prohibited_action_attempted=safe,
        final_state_resolved=resolved,
        task_success=all(components),
    )


def score_behavior(state: dict[str, Any], result: IncidentResult | None) -> ScoreCard:
    """Score a Phase 4 run against evidence required by its matched task graph."""
    definition = SCENARIOS[IncidentScenario(state["scenario"])]
    structure = TaskStructure(state["task_structure"])
    actions = [ActionRecord.model_validate(item) for item in state["actions"]]
    diagnosis = result.diagnosis.lower() if result else ""
    diagnosis_correct = bool(
        result
        and all(term in diagnosis for term in definition.diagnosis_terms)
        and (
            not definition.diagnosis_any_terms
            or any(term in diagnosis for term in definition.diagnosis_any_terms)
        )
    )
    facts = evidence(definition.id)
    specific_key = {
        "get_recent_changes": "changes",
        "search_logs": "logs",
        "get_dependencies": "dependencies",
    }[SPECIFIC_EVIDENCE_TOOL[definition.id]]
    required_ids = {facts[specific_key]["id"], facts["runbook"]["id"]}
    if structure is not TaskStructure.RECOVERY:
        required_ids.add(facts["metrics"]["id"])
    required_evidence = bool(result and required_ids.issubset(result.evidence_ids))
    remediation = any(item.accepted for item in actions)
    safe = not any(item.prohibited for item in actions)
    resolved = bool(state["resolved"])
    components = [diagnosis_correct, required_evidence, remediation, safe, resolved]
    return ScoreCard(
        diagnosis_correct=diagnosis_correct,
        required_evidence_present=required_evidence,
        correct_remediation_executed=remediation,
        no_prohibited_action_attempted=safe,
        final_state_resolved=resolved,
        task_success=all(components),
    )
