# Statistical Data Dictionary

The primary unit is one fresh agent run. Action and MCP-call records are nested within that run.

| Field | Statistical type | Unit | Meaning | Status |
|---|---|---|---|---|
| `run_id` | identifier | run | Unique run identifier | measured metadata |
| `scenario_id` | categorical | run | Synthetic incident family | controlled condition |
| `task_structure` | categorical | run | Sequential, branching, or recovery task structure | controlled condition |
| `batch` | categorical/ordinal | run | Acquisition batch | controlled metadata |
| `execution_order` | discrete count | run | Scheduled order in campaign | controlled metadata |
| `mcp_call_count` | discrete count | run | Number of MCP tool calls | measured |
| `model_call_count` | discrete count | run | Number of model requests | measured |
| `total_latency_ms` | continuous, ratio | run | Client-observed total runtime | measured |
| `model_latency_ms` | continuous, ratio | run | Time inside model requests | measured |
| `mcp_latency_ms` | continuous, ratio | run | Client-observed MCP time | measured |
| `server_handler_latency_ms` | continuous, ratio | run | Time inside server handlers | measured, nested in MCP |
| `orchestration_latency_ms` | continuous, ratio | run | Remaining orchestration time | measured/decomposed |
| `total_tokens` | discrete count | run | Input plus output model tokens | measured |
| `request_frame_bytes` | discrete count | run | Exact local stdio MCP request-frame bytes | measured, not IP packets |
| `response_frame_bytes` | discrete count | run | Exact local stdio MCP response-frame bytes | measured, not IP packets |
| `estimated_cost_usd` | continuous, ratio | run | Estimated model cost | derived from usage/pricing |
| `task_success` | binary | run | Whether deterministic scoring says task succeeded | measured outcome |
| `failure_type` | categorical | run | Failure classification | measured outcome metadata |
| `tool_sequence` | ordered categorical sequence | run | Ordered tool names | measured trace |
| `state_sequence` | ordered categorical sequence | run | Tool plus action outcome states with terminal state | derived from ledger and trace |
| `post_rejection_behavior` | categorical | run | Runbook-first, retried-first, or unclassified | derived observable history |
| `first_oracle_divergence` | discrete position | run | First observable mismatch with oracle | derived |
| `normalized_oracle_distance` | continuous ratio in $[0,1]$ | run | Normalized tool-sequence distance | derived |
| `repeated_tool_count` | discrete count | run | Calls beyond distinct tool names | derived |
| `excess_mcp_calls` | discrete count or undefined | successful run | Calls minus oracle length | derived |
| `source_state` / `target_state` | categorical | nested event | Adjacent states in a run | derived nested measurement |

## Scope limitations

The current recorder does not provide per-tool latency or per-tool bytes. It also does not measure HTTP, TLS, TCP, IP, queue waiting, utilization, or Internet RTT.
