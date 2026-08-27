# Phase 2: controlled statistical baseline

Phase 2 is the first dataset-producing experiment in this project. It does **not** build an AI agent. It measures a small, deterministic MCP client/server system so that the statistical meaning of each observation is clear before agent decisions, model latency, retries, and real backends are introduced.

The question is deliberately narrow:

> How do transport, payload size, programmed service time, and client concurrency change the observed latency and byte volume of a controlled MCP tool call?

## What one observation means

One **run** is the independent experimental unit. A run creates a fresh MCP client/server session under one fixed treatment combination and makes eight calls to `roundtrip_payload`.

One **call** is a nested observation within that run. Calls are useful for inspecting within-run variation, but they must not be treated as eight independent replications.

```mermaid
flowchart LR
    C[Chosen condition] --> R[Fresh run]
    R --> S[Fresh MCP session]
    S --> C1[Call 1]
    S --> C2[Call 2]
    S --> C8[Call 8]
    C1 --> M[Call-level measurements]
    C2 --> M
    C8 --> M
    M --> A[Run-level summaries and models]
```

The tool returns a deterministic ASCII payload of the requested size after an optional, programmed delay. There is no model inference, no external API, no database, and no hidden workload.

## Experimental design

The baseline is a balanced factorial experiment:

| Factor | Levels |
| --- | --- |
| MCP transport | `in_memory`, `stdio` |
| Target payload bytes | 64, 1,024, 16,384, 65,536 |
| Programmed server service time | 0, 20, 100 ms |
| Client concurrency | 1, 4 |
| Independent run replicates per cell | 20 |
| Calls per run | 8 |

There are

$$
2 \times 4 \times 3 \times 2 = 48
$$

treatment cells, giving

$$
48 \times 20 = 960 \text{ runs},
\qquad
960 \times 8 = 7{,}680 \text{ calls}.
$$

Runs are randomly ordered inside each of 20 complete replicate blocks, using seed `20260827`. This prevents a simple time trend from always being confounded with a particular factor level. The frozen `manifest.json` records every planned run before collection begins.

## Measurement boundary

The outcome is the client-observed round-trip time

$$
L_{\mathrm{RTT}} = t_{\mathrm{client\ receives\ response}} - t_{\mathrm{client\ sends\ request}}.
$$

For each call we also preserve the server handler duration,

$$
L_{\mathrm{handler}},
$$

so the residual

$$
L_{\mathrm{nonhandler}} = L_{\mathrm{RTT}} - L_{\mathrm{handler}}
$$

is an observed remainder. It includes serialization, scheduling, protocol processing, and client-side effects; it is **not** automatically a network delay or queueing delay.

`in_memory` measures application/handler behaviour but deliberately leaves byte fields unavailable. It does not cross a serialized wire boundary.

`stdio` starts a separate FastMCP server process. A relay copies every newline-delimited JSON-RPC frame unchanged between the client and child process. It records the actual payload and frame byte counts (including the line delimiter), SHA-256 checksum, direction, JSON-RPC identifier, and correlated call identifier. This is application/protocol-frame measurement, not an IP packet capture.

```mermaid
sequenceDiagram
    participant Client as MCP client
    participant Relay as stdio relay
    participant Server as FastMCP server
    Client->>Relay: JSON-RPC request frame
    Note over Relay: exact request bytes, hash, ID
    Relay->>Server: unchanged frame
    Server->>Server: roundtrip_payload + programmed delay
    Server-->>Relay: JSON-RPC response frame
    Note over Relay: exact response bytes, hash, ID
    Relay-->>Client: unchanged frame
    Note over Client: client RTT
```

## Analysis plan

The primary response is each run's median call RTT, analyzed on the log scale:

$$
\log\!\left(\widetilde L_{r}\right)
= \beta_0
+ \beta_T T_r
+ \beta_P P_r
+ \beta_S S_r
+ \beta_C C_r
+ \beta_{TP}(T_r P_r)
+ \beta_{TC}(T_r C_r)
+ \varepsilon_r.
$$

This is ordinary least squares with HC3 heteroskedasticity-robust standard errors. It is a controlled descriptive/explanatory model, not a claim about a population of arbitrary MCP servers.

The call-level secondary model accounts for calls being nested within runs:

$$
\log(L_{rj}) = X_r\beta + \gamma\,\mathrm{first}_{rj} + b_r + \epsilon_{rj},
\qquad b_r \sim \mathcal N(0, \tau^2).
$$

The random intercept (b_r) represents persistent run-to-run differences. The reported intra-class correlation is

$$
\mathrm{ICC} = \frac{\tau^2}{\tau^2 + \sigma^2}.
$$

For `stdio` runs, a separate byte model uses the run median of total request-plus-response frame bytes. Condition-level uncertainty is summarized by a bootstrap that resamples **runs within treatment cells**, never individual calls.

The workbench provides the model coefficients with HC3 intervals, residual-versus-fitted and QQ diagnostics, empirical summaries, and downloadable `runs` and `calls` tables. Treat diagnostics as checks on the model's usefulness, not as an automatic proof that a model is correct.

## Artifacts and reproducibility

Run the frozen baseline from the command line:

```powershell
uv run python -m mcp_traffic_analysis.campaigns baseline-v1 `
  --output-root artifacts/phase2 `
  --replicates 20 --calls-per-run 8 --seed 20260827 `
  --bootstrap-iterations 2000
```

The campaign writes ignored artifacts under `artifacts/phase2/baseline-v1/`:

- `manifest.json`: frozen treatment schedule and analysis specification;
- `progress.json`: resumable collection state;
- `tables/runs.csv` / `tables/runs.parquet`: one row per independent run;
- `tables/calls.csv` / `tables/calls.parquet`: one row per nested call;
- `analysis.json`: model outputs, diagnostics, and bootstrap summaries;
- `runs/<run_id>/`: original event, frame, call, and server-stderr artifacts.

The UI is intentionally a reader of these saved artifacts. It can run a small one-condition calibration trial, but the full campaign is launched by the reproducible command above. This keeps the scientific protocol separate from the convenience interface.

## What Phase 2 does and does not establish

It establishes a validated baseline for how known factors affect measurements in one local implementation and one machine. It also validates the trace/byte recording pipeline that later phases will rely on.

It does **not** measure Internet network packets, production queues, model inference, agent autonomy, tool selection, external backend behavior, or general MCP performance. Those are later hypotheses. Queueing theory becomes useful once we introduce controlled offered load and a resource whose queue is measured; it should not be retrofitted onto these local residuals.
