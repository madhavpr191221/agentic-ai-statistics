# Phase 6A Plan: Credit-Free Statistical Deepening

Phase 6A reuses the completed 100-run Phase 5 main campaign. It makes no model calls and does not change the agent, scenario, transport, or experimental unit.

## Questions

1. Where in an observed trace does failure become visible?
2. Which tools account for most observed actions?
3. How is measured runtime divided between model, MCP, handler, and orchestration time?
4. How concentrated or variable are complete paths?
5. Did the observed behaviour change across acquisition batches?
6. How much extra MCP work did successful runs perform?

## Statistical rules

- A run is the primary experimental unit; actions inside a run are nested observations.
- Prefix and transition tables are empirical conditional summaries, not Markov-model estimates.
- Bootstrap intervals are used for path entropy and other descriptive run-level summaries.
- Exact local stdio frame bytes remain distinct from network packet measurements.
- No causal claim is made about runbook reading because the behaviour was observed rather than randomized.

## Deliverables

- Extended JSON, CSV, and Parquet summaries in the existing Phase 5 artifact directory.
- Additional Trace Dynamics UI sections for prefix risk, tool usage, latency decomposition, divergence, and path concentration.
- Updated single canonical results document and implementation documentation.
- Unit, API, React, browser, and full repository-gate verification.
