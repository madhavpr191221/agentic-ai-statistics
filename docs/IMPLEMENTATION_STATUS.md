# Implementation Status

Status date: **2026-08-28**

Release version: **0.8.0**

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

### Phase 5 stochastic trace study

- Tool-and-outcome states with explicit start, terminal-success, and terminal-failure states.
- Direct classification of whether the runbook was read before another post-rejection action.
- Two-by-two outcome counts, Wilson intervals, a Newcombe risk-difference interval, and Fisher's exact test.
- Complete path frequencies, singleton counts, bootstrap entropy intervals, transitions, divergence, repeated tools, and successful-run excess calls.
- Frozen focused campaign with configuration fingerprint, resumability, batches, pilot/main separation, and a USD 5 estimated-cost guard.
- Read-only trace-study API and a practical React trace-dynamics workbench.

Stage 5A has reanalysed all 90 Phase 4 observations without new model calls. Stage 5B is complete with 100 valid runs. Seventeen provider-error attempts from the earlier quota interruption are retained for audit but excluded from scientific analysis.

### Phase 6A credit-free secondary analysis

Phase 6A reuses the completed Phase 5B artifacts without model calls. It adds partial-history outcome tables, tool-usage counts, latency-component summaries, divergence-by-outcome, path concentration, downloadable tables, and corresponding UI sections.

The [Phase 6A statistical analysis roadmap](planning/phase6_statistical_analysis_roadmap.md) documents the small-question learning sequence and interpretation rules.

The specification-driven statistical program is documented in `docs/specs/`: an authoritative specification, question registry, data dictionary, and traceability matrix. These documentation artifacts do not require new model calls.

The reader-facing synthesis of the main empirical findings is
[`results/agent_execution_study_results.md`](results/agent_execution_study_results.md).
Phase-specific result files remain as technical provenance and audit records.

### Phase 12: statistical study layer

Phase 12A is a specification phase with no new model calls. It formalizes the
distinction between an observability measurement layer and this repository's
statistical study layer. The run is the experimental unit; scalar outcomes are
analyzed first, followed by variable-length trajectory distributions and only
then any stochastic-process model. See `docs/specs/analysis_contracts.md` and
`docs/planning/phase12_statistical_study_layer_plan.md`.

Phase 12B adds reproducible bootstrap intervals for scalar means and medians,
Wilson intervals for success proportions, richer per-batch summaries, and
explicit Q01–Q03 artifact contracts. It reuses saved Phase 5 data and makes no
new model calls.

Phase 12C adds an explicit Q09–Q14 trajectory-analysis artifact contract. It
packages complete-path frequencies, entropy/concentration, descriptive
transitions, oracle divergence, excess work, tool usage, and path-family
comparisons while preserving the run-level denominator and the no-Markov/no-
causal-claim limits.

### Phase 8 scalar statistical baseline

Phase 8 implements Q01–Q03 from the specification using only the saved Phase 5 campaign. It adds run-level scalar distributions, an explicit scalar data dictionary, batch-stability summaries, downloadable JSON/CSV artifacts, a read-only artifact route, and a Scalar Baseline section in the React workbench. Q04 and later remain specified but pending.

### Phase 10 workload by task condition

Phase 10 implements Q04 using the saved 90-run Phase 4 main campaign. It publishes workload summaries by sequential, branching, and recovery structure, the pre-specified Poisson count model with HC3 covariance, dispersion diagnostics, downloadable Q04 artifacts, and a workload comparison in the Behavior workbench. No new model calls are required.

## Measurement boundary

The active system measures model activity and local newline-delimited MCP/JSON-RPC frames crossing a stdio relay. Request and response byte counts are exact at that boundary.

It does not measure HTTP, TLS, TCP, IP, Internet RTT, queue waiting, arrival processes, utilization, or production reliability.

## Active software

```text
frontend/src/components/     Phase 3, Phase 4, and Phase 5 workbenches
api/app.py                   active HTTP routes and artifact downloads
incidents/                   agent runner, MCP server, task state, scoring
behavior/                    Phase 4 design, campaigns, traces, models
transport/                   exact stdio relay and frame contract
trace_study/                 Phase 5 analysis and focused campaigns
agent_campaigns.py           Phase 3 repeated campaign
```

The earlier calibration applications and their public routes have been retired. Their commits remain in Git history, but they are not part of the current package or UI.

## Active API prefixes

- `/api/health`
- `/api/agent/*`
- `/api/behavior/*`
- `/api/trace-study/*`

There are no compatibility stubs for the retired routes.

## Artifact policy

Generated run and campaign artifacts remain ignored by Git under `artifacts/phase3/`, `artifacts/phase4/`, and `artifacts/phase5/`. Phase 5 reads but does not rewrite Phase 4 raw observations.

## Validation policy

Every release must pass the Python unit/integration suite, Ruff, strict mypy, React tests, production build, Playwright workflows, uv lock verification, and `git diff --check`.

The transport suite must cross the real relay and incident subprocess without model credit. UI workflows must cover all three active surfaces.

## Documentation

- [`CODE_FLOW.md`](CODE_FLOW.md): active runtime and measurement flow.
- [`DEMO_WORKFLOW.md`](DEMO_WORKFLOW.md): branch, test, and release workflow.
- [`phase3_it_incident_agent.md`](phase3_it_incident_agent.md): Phase 3 protocol.
- [`results/phase3_incident_pilot_results.md`](results/phase3_incident_pilot_results.md): Phase 3 pilot.
- [`phase4_task_structure.md`](phase4_task_structure.md): Phase 4 method.
- [`planning/phase4_task_structure_plan.md`](planning/phase4_task_structure_plan.md): frozen Phase 4 design.
- [`results/phase4_task_structure_results.md`](results/phase4_task_structure_results.md): consolidated Phase 4 results.
- [`phase5_stochastic_traces.md`](phase5_stochastic_traces.md): Phase 5 method in practical language.
- [`planning/phase5_stochastic_trace_plan.md`](planning/phase5_stochastic_trace_plan.md): frozen Phase 5 protocol.
- [`results/phase5_stochastic_trace_results.md`](results/phase5_stochastic_trace_results.md): single Phase 5 result document.
