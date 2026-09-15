# Agentic AI Statistics

An empirical statistical study of how a stochastic AI agent behaves while solving controlled IT incidents.

## The goal

We repeat the same incident task under controlled conditions and learn the distribution of what happens:

\[
\text{condition} \longrightarrow \text{agent trajectory} \longrightarrow
\text{work, time, cost, reliability}.
\]

The project is not trying to build a general-purpose agent or to claim that a local MCP measurement is an Internet packet capture. MCP/JSON-RPC is the application measurement boundary. The scientific object is the repeated execution of an agent.

For run \(r\), the primary scalar observations are

\[
N_r,\; L_r,\; B_r,\; T_r,\; C_r,\; Y_r,
\]

where these mean MCP-call count, total latency, measured frame bytes, token usage, estimated cost, and objective success. The complete ordered action sequence is also retained:

\[
\mathbf X_r=(X_{r1},\ldots,X_{rN_r}).
\]

Scalar outcomes are the first/basic analysis. Trajectories are richer random objects studied only after the run-level data are understood.

## Two linked study layers

1. **Single-run stochastic behavior.** Describe and explain variation in incident executions: workload, latency, cost, success, and action paths. Use a progressive model ladder: empirical distributions first, then justified dependence or state-process models.
2. **System performance under load.** Deliberately generate incident arrivals to a shared fixed-worker system. Measure queue waiting, service time, throughput, utilization, reliability, and cost. This is where queueing theory becomes relevant; no queueing claim is made without actual arrivals and waiting measurements.

The primary trade-off is reliability versus performance: how much time, work, and cost are required to achieve a given probability of resolving the incident.

## Current implementation

The repository contains a controlled synthetic incident world, a real OpenAI Agents SDK incident agent, a FastMCP server, stdio MCP frame instrumentation, objective scoring, and a React/TypeScript UI. A deterministic mode is available for measurement smoke tests without model spend; live mode requires `OPENAI_API_KEY` in `.env`.

The active branch is a clean restart of the study. Earlier phase work is preserved in the Git branch `archive/pre-reset-2026-09-15` and is not treated as current evidence.

## Run locally

```powershell
uv sync
npm install
npm run dev
```

Open the UI at `http://127.0.0.1:5173`. Choose an incident and run it. The UI reports measured values and explicitly labels quantities that are unavailable at the current instrumentation boundary.

## Scientific guardrails

- A fresh complete run is the experimental unit; tool calls nested inside a run are not independent replicates.
- Descriptive associations are not causal effects. Causal claims require randomized interventions.
- We do not infer private model reasoning.
- We do not report TCP/IP/TLS packet quantities, Internet RTT, queue waiting, or independent-arrival results unless those quantities are actually instrumented.
- Expensive campaigns are specified before execution and reported with uncertainty and limitations.

See [`docs/STATISTICAL_STUDY_PROTOCOL.md`](docs/STATISTICAL_STUDY_PROTOCOL.md) for the complete protocol and [`docs/CODE_FLOW.md`](docs/CODE_FLOW.md) for the implementation map.
