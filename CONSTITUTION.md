# Scientific constitution

## Mission

Build a public, reproducible research-engineering project that measures and models agentic AI executions using probability, statistics, stochastic processes, and performance engineering.

## Primary object

The primary observation is one complete execution:

\[
\mathcal R_r=(Z_r,\mathbf X_r,N_r,L_r,C_r,Y_r),
\]

where (Z_r) is the controlled condition, (mathbf X_r) is the observable trajectory, (N_r) is work or event count, (L_r) is elapsed time, (C_r) is cost, and (Y_r) is terminal success or failure.

## Non-negotiable principles

1. The experimental unit is a fresh complete run.
2. Nested events are measurements within a run, not independent observations.
3. Every feature has a research question and an estimand.
4. Association is not causation. Causal claims require randomized assignment or a defensible alternative design.
5. A stochastic-process model must emerge from observed behavior; it must not be imposed for prestige.
6. Model adequacy is assessed with prediction, diagnostics, uncertainty, and sensitivity analysis.
7. Queueing theory is used only after arrivals, shared resources, service, and waiting are measured.
8. The project reports what the instrumentation can support and labels unavailable quantities honestly.
9. Reproducible synthetic data must support every public analysis.
10. Proprietary traces must never be required for public builds or tests.

## Development principles

- Specifications precede code.
- Acceptance criteria precede implementation.
- Tests are derived from requirements.
- One feature is implemented at a time.
- Deterministic replay precedes live model execution.
- The UI is an inspection surface for the scientific object, not the scientific object itself.
- Documentation records failed assumptions and negative results, not only successes.

## Evidence hierarchy

1. Directly measured event or run data.
2. Transparent deterministic transformations of measured data.
3. Descriptive statistical estimates with uncertainty.
4. Predictive stochastic models validated on held-out data.
5. Causal effects from randomized interventions.
6. Queueing or simulation conclusions validated against observed system behavior.

Higher-level claims cannot silently replace lower-level evidence.
