# Phase 1A: Model-Free Measurement Core

Phase 1A answers a narrow question:

> Can the project reconstruct the semantic execution of deterministic MCP requests before introducing transport framing or a language model?

It uses a real FastMCP client and server connected through FastMCP's in-memory transport. This exercises MCP initialization, tool discovery, tool dispatch, validation, and error handling in one Python process.

## What is measured

Server middleware records `tools/list` and `tools/call` spans. Each span has one start event and one terminal event joined by `span_id`. All events in a run share `run_id` and `trace_id`.

The terminal latency measures the FastMCP server handler around `call_next`. Recorder file I/O is excluded from this duration. Both UTC wall time and monotonic nanoseconds are retained because they answer different questions:

- UTC time locates an event in calendar time and supports cross-system correlation.
- monotonic time measures durations without being affected by wall-clock adjustments.

Sequence numbers describe the order in which one component committed events to its JSONL stream. They do not claim that concurrent tool calls executed sequentially.

## What is not measured yet

In-memory transport bypasses actual `stdio` or HTTP serialization. Therefore Phase 1A cannot observe:

- JSON-RPC request or response byte counts;
- transport frame sizes;
- JSON-RPC wire identifiers;
- network or subprocess overhead.

Those fields remain null and use the `unavailable_transport_bypass` recording policy. Estimating them from Python object sizes would create a misleading metric.

## Deterministic fixture

The server exposes three tools:

- `echo_bytes(n)` returns exactly `n` ASCII characters.
- `sleep_ms(delay_ms)` creates a controlled service time.
- `fail_with(kind)` produces a backend exception, explicit tool error, or timeout.

The runner also invokes nonexistent tools, executes concurrent calls, and cancels in-flight work. No external service, random backend, model, or API key is involved.

## Run a trial

```powershell
uv --cache-dir .uv-cache run python -m mcp_traffic_analysis.fixtures.runner concurrent
```

Choose a different output root or repeat the same operation within one run:

```powershell
uv --cache-dir .uv-cache run python -m mcp_traffic_analysis.fixtures.runner sleep --repeat 5 --seed 42 --output-dir artifacts/phase1a
```

The command prints the new run directory. It contains:

```text
manifest.json
events.jsonl
```

The manifest records the condition, scenario seed, transport, host characteristics, and software versions. The JSONL file is canonical append-only data: one validated trace event per line.

## Privacy boundary

The runner does not load `.env` or inspect `os.environ`. It records no request arguments, payload bodies, exception messages, authorization data, or private model content. Only synthetic identifiers, timing, method and tool names, classified outcomes, package versions, and non-identifying host characteristics are retained.

## Exit condition

Phase 1A is complete when the deterministic tests prove:

- every recorded request has exactly one terminal event;
- event sequence numbers match JSONL order;
- concurrent requests overlap without false serialization;
- controlled failures map to distinct error classes;
- timing respects known service delays;
- no unobserved byte measurement is reported;
- no payload or secret content enters the trace.
- the React/TypeScript workbench can run scenarios, inspect artifacts, and reproduce descriptive summaries from the canonical events;
- the complete successful, concurrent, failure, and persistence flows pass in Chromium.

Phase 1B will cross a subprocess `stdio` boundary and validate exact serialized payload and frame bytes over the full 200-trial recorder-validation campaign.
