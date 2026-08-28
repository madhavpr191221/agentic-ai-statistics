# Implementation Status

Status date: **2026-08-28**

Release version: **0.5.0**

Permanent branches: **`demo`** and **`main`**

## Active capabilities

### Phase 3 incident agent

- Three resettable synthetic incident families with hidden ground truth.
- Ten typed MCP tools for evidence, remediation, escalation, and updates.
- One real model-driven agent per fresh run and MCP session.
- Exact stdio frame metadata, model/tool hooks, tokens, cost, and latency decomposition.
- Deterministic objective scoring and complete action ledgers.
- Resumable repeated campaigns with run, call, action, and trace tables.
- React workbench plus credit-free deterministic API tests.

### Phase 4 task-structure study

- Three incidents crossed with sequential, branching, and recovery structures.
- Five-call shortest valid oracle in every condition.
- Explicit excess calls, oracle distance, expected recovery rejection, trace entropy, and transitions.
- Separate corrected 27-run pilot and 90-run main campaign.
- Poisson log-mean primary analysis with robust uncertainty and frozen sensitivity rules.
- React experiment and campaign-analysis surface.

The main study found approximately 20.5% more expected MCP calls under recovery than sequential structure. Branching showed no detectable call-count difference. Overall success was 85/90.

## Measurement boundary

The active system measures model activity and local newline-delimited MCP/JSON-RPC frames crossing a stdio relay. Request and response byte counts are exact at that boundary.

It does not measure HTTP, TLS, TCP, IP, Internet RTT, queue waiting, arrival processes, utilization, or production reliability.

## Active software

```text
frontend/src/components/     Phase 3 and Phase 4 workbenches
api/app.py                   active HTTP routes and artifact downloads
incidents/                   agent runner, MCP server, task state, scoring
behavior/                    Phase 4 design, campaigns, traces, models
transport/                   exact stdio relay and frame contract
agent_campaigns.py           Phase 3 repeated campaign
```

The earlier calibration applications and their public routes have been retired. Their commits remain in Git history, but they are not part of the current package or UI.

## Active API prefixes

- `/api/health`
- `/api/agent/*`
- `/api/behavior/*`

There are no compatibility stubs for the retired routes.

## Artifact policy

Generated run and campaign artifacts remain ignored by Git under `artifacts/phase3/` and `artifacts/phase4/`. The application does not delete or migrate existing local data during the 0.5.0 cleanup.

## Validation policy

Every release must pass the Python unit/integration suite, Ruff, strict mypy, React tests, production build, Playwright workflows, uv lock verification, and `git diff --check`.

The transport suite must cross the real relay and incident subprocess without model credit. UI workflows must cover both active surfaces.

## Documentation

- [`CODE_FLOW.md`](CODE_FLOW.md): active runtime and measurement flow.
- [`DEMO_WORKFLOW.md`](DEMO_WORKFLOW.md): branch, test, and release workflow.
- [`phase3_it_incident_agent.md`](phase3_it_incident_agent.md): Phase 3 protocol.
- [`results/phase3_incident_pilot_results.md`](results/phase3_incident_pilot_results.md): Phase 3 pilot.
- [`phase4_task_structure.md`](phase4_task_structure.md): Phase 4 method.
- [`planning/phase4_task_structure_plan.md`](planning/phase4_task_structure_plan.md): frozen Phase 4 design.
- [`results/phase4_task_structure_results.md`](results/phase4_task_structure_results.md): consolidated Phase 4 results.
