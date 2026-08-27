"""Auditable trace metrics for the Phase 4 behavior study."""

from __future__ import annotations

import math
from collections import Counter
from typing import Literal

from mcp_traffic_analysis.incidents.models import ActionRecord, BehaviorTraceStep


def edit_distance(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for index, left_item in enumerate(left, 1):
        current = [index]
        for right_index, right_item in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_item != right_item),
                )
            )
        previous = current
    return previous[-1]


def normalized_oracle_distance(observed: list[str], oracle: list[str]) -> float:
    denominator = max(len(observed), len(oracle))
    return edit_distance(observed, oracle) / denominator if denominator else 0.0


def classify_trace(
    observed: list[str], oracle: list[str], actions: list[ActionRecord]
) -> list[BehaviorTraceStep]:
    """Classify calls without pretending that all rejected actions are failures."""
    action_by_tool: dict[str, list[ActionRecord]] = {}
    for recorded_action in actions:
        tool = {
            "restart_service": "restart_service",
            "rollback_deployment": "rollback_deployment",
            "escalate_incident": "escalate_incident",
        }[recorded_action.action]
        action_by_tool.setdefault(tool, []).append(recorded_action)
    action_offsets: Counter[str] = Counter()
    oracle_cursor = 0
    steps: list[BehaviorTraceStep] = []
    for sequence, tool in enumerate(observed):
        matched_action: ActionRecord | None = None
        if tool in action_by_tool:
            offset = action_offsets[tool]
            if offset < len(action_by_tool[tool]):
                matched_action = action_by_tool[tool][offset]
            action_offsets[tool] += 1
        classification: Literal[
            "oracle", "expected_rejection", "extra", "unexpected_rejection", "prohibited"
        ]
        if matched_action and matched_action.prohibited:
            classification = "prohibited"
        elif matched_action and matched_action.expected_rejection:
            classification = "expected_rejection"
        elif matched_action and not matched_action.accepted:
            classification = "unexpected_rejection"
        else:
            classification = (
                "oracle"
                if oracle_cursor < len(oracle) and tool == oracle[oracle_cursor]
                else "extra"
            )
        if oracle_cursor < len(oracle) and tool == oracle[oracle_cursor]:
            oracle_cursor += 1
        steps.append(
            BehaviorTraceStep(
                sequence=sequence, tool_name=tool, classification=classification
            )
        )
    return steps


def path_entropy(sequences: list[tuple[str, ...]]) -> float:
    """Plug-in path entropy in bits; descriptive at the Phase 4 sample size."""
    if not sequences:
        return 0.0
    counts = Counter(sequences)
    total = len(sequences)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def transitions(sequence: list[str]) -> list[tuple[str, str]]:
    return list(zip(sequence, sequence[1:], strict=False))
