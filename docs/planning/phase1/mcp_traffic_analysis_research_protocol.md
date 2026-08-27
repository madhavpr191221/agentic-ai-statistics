# Agentic AI and MCP Performance Analysis Study

## Summary

This project will build a reproducible performance-analysis laboratory for agentic AI systems, giving equal attention to:

- **Agent behaviour:** model calls, tool decisions, retries, handoffs, concurrency, and completion.
- **MCP communication:** methods, messages, sizes, latency, errors, ordering, and transport.
- **System performance:** end-to-end latency, throughput, cost, variability, reliability, and scaling.

The study will use a synthetic but realistic enterprise IT incident-response application. MCP provides the observable protocol boundary; statistics, probability, stochastic processes, and later queueing theory provide the analytical framework.

The central research question is:

> How do task structure, agent autonomy, system load, orchestration architecture, and MCP transport affect the performance and reliability of agentic AI systems?

## What is a campaign?

A **campaign** is one organized series of experimental runs designed to answer one main question.

It contains:

- one factor deliberately changed
- quantities held fixed
- repeated runs
- predefined measurements
- a statistical analysis
- a stopping or completion rule

For example, in the task-structure campaign:

- **Changed factor:** single-step, sequential, branching, parallel, or recovery task.
- **Held constant:** model, agent policy, tools, timeout, and transport.
- **Measured:** latency, calls, bytes, trace depth, and success.
- **Repeated:** multiple scenarios and repetitions.
- **Question:** does task structure affect system performance?

The planned campaigns are:

| Campaign | Factor changed | Main question |
|---|---|---|
| A | Task structure | Are complicated tasks slower or less reliable? |
| B | Agent autonomy | Does decision latitude create more variable traces? |
| C | Agent architecture | What is the cost and benefit of multiple agents? |
| D | System load | What happens as concurrent demand increases? |
| E | MCP transport | What overhead comes from local, HTTP, or remote communication? |

The campaigns are separated so that an observed change can be attributed to a particular factor. If model, autonomy, concurrency, and transport were changed simultaneously, the cause of a performance difference would be unclear.

## How queueing theory helps

Queueing theory studies systems in which **jobs arrive, wait for limited resources, receive service, and depart**.

In this study, possible jobs include:

- user requests
- agent runs
- model inference requests
- MCP requests
- tool calls
- backend operations

Possible service stations include:

- hosted model API
- agent runtime
- MCP server worker
- enterprise-tool backend
- network connection

```text
Arrivals              Waiting                 Service
Agent requests ---> [ MCP request queue ] ---> Tool worker ---> Responses
```

The basic quantities are:

$$
\lambda=\text{average arrival rate}
$$

$$
S=\text{service time}
$$

$$
W_q=\text{time waiting in the queue}
$$

$$
R=W_q+S=\text{total response time}
$$

$$
\rho=\text{resource utilization}
$$

$$
L=\text{average number of jobs in the system}.
$$

Queueing theory helps separate two different reasons why an operation is slow:

1. The operation itself takes a long time.
2. The operation is fast but waits behind other work.

That distinction is central to performance analysis.

### A numerical example

Suppose an MCP tool can process ten requests per second:

$$
\mu=10\text{ requests/second}.
$$

Its mean service time is therefore:

$$
\mathbb{E}[S]=\frac{1}{\mu}=0.1\text{ seconds}.
$$

Under a simple $M/M/1$ model, mean response time is:

$$
\mathbb{E}[R]=\frac{1}{\mu-\lambda}.
$$

If five requests arrive per second:

$$
\lambda=5,\qquad \rho=\frac{5}{10}=0.5,
$$

then:

$$
\mathbb{E}[R]=\frac{1}{10-5}=0.2\text{ seconds}.
$$

The tool performs 100 milliseconds of actual work, but the average response takes 200 milliseconds because of waiting.

Now increase arrivals to nine per second:

$$
\lambda=9,\qquad \rho=0.9.
$$

Then:

$$
\mathbb{E}[R]=\frac{1}{10-9}=1\text{ second}.
$$

The tool still needs only 100 milliseconds to do the work. The other 900 milliseconds are queueing delay.

This is the **utilization knee**: as utilization approaches capacity, latency can grow dramatically before throughput improves much further.

### How it helps the campaigns

#### Task structure

A single user request can generate several tool requests.

A sequential task might generate:

```text
model -> tool -> model -> tool -> model -> tool
```

A parallel task might generate a burst:

```text
             -> metrics tool
model ------> logs tool
             -> dependency tool
```

Both might contain three calls, but their queueing and critical-path behaviour will differ.

#### Agent autonomy

A more autonomous agent might make additional investigative calls, retry uncertain results, call several tools concurrently, revisit the same tool, or generate bursts. Autonomy therefore changes the workload arriving at the MCP servers.

#### Single-agent versus multi-agent

Multiple agents can produce concurrent calls and additional model requests. Queueing theory helps determine whether multi-agent decomposition creates useful parallelism or merely adds congestion.

#### System load

This is the most direct queueing campaign. Concurrent agent jobs are increased while observing:

- throughput
- waiting time
- response time
- in-flight work
- timeouts
- failure rate
- the point where the system saturates

#### Local versus remote MCP

Queueing theory helps separate backend waiting from transport delay. A remote request might be slow because of network latency, server congestion, or both.

### Little's Law

One of the first relationships to test is:

$$
L=\lambda R.
$$

If the system completes five requests per second and each request spends an average of two seconds in the system, then the average number of requests present should be:

$$
L=5\times2=10.
$$

Little's Law is useful because it does not require exponential arrivals or service times. It also provides a consistency check for the measurements.

### Where agentic systems become interesting

Agent traffic will probably violate simple textbook assumptions:

- arrivals may be bursty rather than Poisson
- service times may be heavy-tailed
- retries create correlated arrivals
- tool results influence future requests
- parallel tool calls arrive together
- hosted model APIs may batch or rate-limit requests
- the workload may change over time

This does not make queueing theory useless. A simple queueing model becomes a baseline prediction:

> If the system behaved like this model, latency should look like $X$. We observed $Y$. Which assumption explains the difference?

That comparison is where the statistical research begins.

Queueing theory is not the entire project. It is a family of mathematical models that helps explain how agent-generated work interacts with limited computational and communication resources.

## Experimental system

### Enterprise application

Create a fake enterprise incident-resolution system with seeded, resettable scenarios and no real side effects.

Three FastMCP servers will represent enterprise services:

- **Observability server:** alert details, metrics, logs, and health checks.
- **Operations server:** service ownership, dependencies, recent changes, and runbooks.
- **Action server:** restart, rollback, escalation, incident updates, and notifications.

Scenario families will include resource saturation, bad deployment, dependency outage, expired credentials or certificates, and configuration drift.

Every scenario will define:

- hidden root cause
- available evidence
- correct and prohibited actions
- deterministic final state
- controlled response sizes, delays, and injected failures

The agent must return structured results containing:

```text
incident_id
diagnosis
evidence_ids
selected_action
resolution_summary
```

Success will be scored automatically against scenario state and the action ledger. An LLM judge will not be used.

### Agent configurations

Use Python, FastMCP, the OpenAI Agents SDK, and one explicitly pinned hosted model. The baseline model configuration will use `gpt-5.5` with low reasoning effort and low verbosity.

Within each campaign, hold these quantities fixed unless they are the named experimental factor:

- model identifier and model settings
- tool names and descriptions
- output schema
- turn and timeout limits
- scenario state
- synthetic service-time schedule

Compare two orchestration architectures:

- **Single agent:** one incident-resolution agent with access to every tool.
- **Multi-agent:** supervisor, diagnostician, and remediation agents using the same model, with scoped tool access and explicit handoffs.

Autonomy means decision latitude:

- **Low:** an explicit ordered investigation plan is supplied.
- **Medium:** investigation stages are prescribed, but tool selection is free.
- **High:** only the goal, safety constraints, and success criteria are supplied.

All autonomy conditions retain the same tools, model, turn limit, scenario evidence, and scoring rules.

## Packet hierarchy

The word *packet* must be qualified by layer:

- **Agent event:** model request, model response, tool decision, retry, handoff, or final answer.
- **MCP message:** one JSON-RPC request, response, or notification.
- **Transport unit:** one newline-delimited `stdio` frame, HTTP request or response, or SSE event.
- **Network packet:** one TCP/IP packet, deferred to a later networking phase.

The initial transport progression is:

$$
\text{local stdio}
\rightarrow
\text{localhost Streamable HTTP}
\rightarrow
\text{controlled remote Streamable HTTP}.
$$

The remote deployment will use HTTPS on one fixed-region, fixed-resource Linux VM with no scale-to-zero behaviour.

The later networking progression is:

$$
\text{agent event}
\rightarrow
\text{MCP message}
\rightarrow
\text{HTTP or stdio unit}
\rightarrow
\text{TLS record}
\rightarrow
\text{TCP segment}
\rightarrow
\text{IP packet}.
$$

## Measurement contract

### Experiment manifest

The versioned experiment manifest records:

```text
schema_version
experiment_id
condition_id
campaign
run_id
scenario_id
scenario_seed
prompt_variant
task_structure
autonomy_level
agent_architecture
model_id
model_settings
agent_sdk_version
mcp_protocol_version
fastmcp_version
transport
host_information
software_versions
start_time_utc
```

### Trace event

Each versioned trace event records:

```text
schema_version
event_id
experiment_id
condition_id
run_id
turn_id
trace_id
span_id
parent_span_id
sequence_number

wall_time_utc
monotonic_time_ns
process_id
component
layer
direction
transport

event_kind
message_type
jsonrpc_id
mcp_method
tool_name

payload_bytes
frame_bytes
payload_hash
payload_recording_policy

latency_ms
outcome
error_type
error_code
tool_is_error
metadata
```

### Scenario definition

Each versioned scenario definition records:

```text
scenario_id
family
initial_state
evidence_graph
root_cause
correct_actions
prohibited_actions
failure_schedule
service_time_configuration
response_size_configuration
scoring_rules
```

### Storage and privacy

Store canonical raw events as append-only JSONL. Produce derived tables for runs, model calls, MCP messages, tool executions, state transitions, failures, and action outcomes.

Synthetic payloads may be retained. Credentials, API keys, authorization headers, private reasoning content, and unrelated environment data must never be recorded.

### Correlation and timing

Each independent run receives an experiment ID, condition ID, run ID, trace ID, turn ID, span and parent-span IDs, and per-component sequence numbers.

Record both UTC wall time and monotonic nanoseconds. Propagate W3C trace context through MCP `_meta` where supported.

Measure:

- end-to-end run latency
- model-call latency and token usage
- MCP client-observed round-trip latency
- server dispatch and backend execution latency
- critical-path latency
- request and response payload bytes
- transport-frame and HTTP-body bytes
- call, retry, handoff, and notification counts
- trace depth, width, branching, and concurrency
- task success, timeout, protocol error, tool error, and recovery

For a local request:

$$
\begin{aligned}
L_{\text{MCP observed}}
={}& L_{\text{serialization}}
+ L_{\text{transport}}
+ L_{\text{server queue}} \\
&+ L_{\text{backend}}
+ L_{\text{return}}.
\end{aligned}
$$

For remote MCP, report client round-trip time and server execution time separately. Derive only a combined transport, serialization, scheduling, and clock-uncertainty residual. Do not claim one-way network latency from unsynchronized clocks.

### Trace representation

Represent each run as a causal graph:

$$
T_r=(V_r,E_r),
$$

where nodes are agent, protocol, transport, and backend events, and edges describe causality, correlation, ordering, concurrency, retry, or handoff.

Initial quantities include:

$$
N_{\text{tool}},\quad
N_{\text{MCP}},\quad
D_{\text{trace}},\quad
B_{\text{request}},\quad
B_{\text{response}},\quad
L_{\text{total}},\quad
P(\text{failure}).
$$

Use these operational definitions:

$$
N_{\text{tool}}=\#(\texttt{tools/call})
$$

$$
N_{\text{MCP}}=\#(\text{all MCP requests})
$$

$$
D_{\text{trace}}=\text{longest causal path through the trace}
$$

$$
B_{\text{request}}=\text{exact serialized request payload bytes}
$$

$$
B_{\text{response}}=\text{exact serialized response payload bytes}.
$$

For concurrent calls, calculate end-to-end contribution from spans and the critical path. Do not add overlapping durations.

### Failure taxonomy

Keep these outcomes distinct:

- JSON-RPC protocol error
- MCP tool result with `isError=true`
- backend exception
- timeout
- cancellation
- malformed result
- transport disconnect
- model-selected nonexistent tool
- exhausted agent turn limit
- incorrect diagnosis
- unsafe or prohibited action
- incomplete final answer

## Workload structure

The task suite will contain five controlled structures:

1. **Single lookup:** retrieve one known fact such as service ownership or incident severity.
2. **Sequential chain:** each tool result supplies information required by the next tool.
3. **Conditional branch:** the correct next tool depends on observed evidence.
4. **Parallel fan-out and fan-in:** independent evidence sources can be queried concurrently before synthesis.
5. **Failure recovery:** one primary path fails or times out, requiring a safe fallback.

Each task has a deterministic success condition independent of the exact valid path chosen by the agent.

## Research campaigns

Run campaigns sequentially with exit gates. Do not cross every factor in one full factorial design.

### Campaign 0: recorder validation

Run 200 deterministic, model-free trials covering known payload sizes, fixed delays, discovery, tool calls, notifications, concurrency, errors, timeouts, cancellations, malformed responses, and transport termination.

Exit only when byte counts, message pairing, event ordering, timing, and error classification agree with ground truth.

### Pilot

Run 50 hosted-agent trials: ten examples from each task structure.

Use the pilot to validate task difficulty, automatic scoring, model access, run limits, trace completeness, expected API usage and cost, and main-study variance estimates.

Freeze scenarios, prompts, dependency versions, exclusions, and scoring rules after the pilot. Do not mix pilot observations with confirmatory results.

### Campaign A: task structure

Use one single agent at medium autonomy:

$$
5\text{ structures}
\times5\text{ scenarios}
\times2\text{ prompt variants}
\times3\text{ repetitions}
=150\text{ runs}.
$$

Primary question:

> How does task structure affect end-to-end latency and task success?

Secondary outcomes are model calls, MCP calls, bytes, tokens, trace depth and width, concurrency, and failure type.

### Campaign B: agent autonomy

Use low, medium, and high decision latitude on the sequential, branching, and recovery workloads:

$$
3\text{ policies}
\times3\text{ structures}
\times5\text{ scenarios}
\times3\text{ repetitions}
=135\text{ runs}.
$$

Primary question:

> Does decision latitude change between-run execution-trace variability?

Secondary outcomes are success, latency, upper-tail cost, redundant calls, retries, and tool-sequence diversity.

### Campaign C: single-agent versus multi-agent

Compare matched single-agent and supervisor-specialist architectures:

$$
2\text{ architectures}
\times3\text{ structures}
\times5\text{ scenarios}
\times3\text{ repetitions}
=90\text{ runs}.
$$

Primary question:

> Does multi-agent decomposition improve task success enough to justify its handoff, model-call, traffic, and latency overhead?

### Campaign D: system load

Run 25 completed agent jobs at concurrency levels 1, 2, 4, and 8:

$$
4\text{ concurrency levels}\times25\text{ jobs}=100\text{ jobs}.
$$

Use one fixed task mixture and agent policy. Measure throughput, response-time distribution, tail latency, in-flight work, queue accumulation where observable, provider rate limits, timeouts, and failures.

Treat this as a finite-concurrency performance experiment. Open-loop arrival-process experiments belong to the later queueing phase.

### Campaign E: transport and remote MCP

Replay identical MCP call traces without a model:

$$
3\text{ transports}
\times5\text{ traces}
\times6\text{ repetitions}
=90\text{ replay runs}.
$$

The transports are local `stdio`, localhost Streamable HTTP, and controlled remote Streamable HTTP.

Follow this with ten end-to-end agent runs per transport:

$$
3\text{ transports}\times10\text{ runs}=30\text{ confirmation runs}.
$$

Primary question:

> How much latency and byte overhead does each transport introduce when logical work is held constant?

The complete staged study contains approximately 845 runs, including about 555 hosted-model runs.

## Statistical analysis

The independent experimental unit is the agent run. Calls within a run are clustered observations.

Use:

- empirical cumulative distribution functions
- medians and interquartile ranges
- p90, p95, and p99 estimates with explicit uncertainty
- bootstrap confidence intervals
- mixed-effects models with scenario as a random effect
- logistic mixed models for task success and failure
- survival analysis for timed-out or censored runs
- clustered bootstrap resampling at run or scenario level
- Holm correction for planned multiple comparisons
- effect sizes and confidence intervals alongside p-values
- variance decomposition across scenario, prompt variant, policy, and repetition
- normalized tool-sequence edit distance
- tool-set Jaccard similarity
- transition matrices and dwell times
- sequence entropy
- critical-path analysis for concurrent traces

Markov or semi-Markov models may be fitted later, but only after checking whether transition behaviour and dwell times support those assumptions.

Claims of heavy-tailed behaviour require tail diagnostics and comparison with competing distributions. A log-log plot alone is insufficient.

Pre-register the primary outcome, model formula, planned contrasts, exclusions, timeout treatment, multiple-comparison family, and stopping rule before each confirmatory campaign.

## Hypotheses

1. More complex task structures increase trace depth, latency, traffic, and failure probability.
2. Greater decision latitude increases trace variability and upper-tail cost, with an uncertain effect on success.
3. Multi-agent orchestration adds model and communication overhead and is beneficial only when its success improvement compensates for that overhead.
4. Increasing concurrency raises throughput initially, then produces latency growth, rate limiting, and failures.
5. Remote transport increases MCP latency and byte overhead without changing the intended logical trace, although timeouts or retries may alter actual agent behaviour.
6. Backend service-time variability and bursty agent calls provide the later bridge to stochastic-process and queueing analysis.

## Reproducibility rules

- Pin dependencies, model IDs, prompts, scenarios, manifests, and protocol versions.
- Begin every run with fresh conversation state and a reset scenario.
- Randomize run order within scenario blocks.
- Seed synthetic timing and failure schedules.
- Keep a canonical, immutable raw-event dataset.
- Record software and host configuration with every run.
- Record token usage rather than depending only on a changing currency price.
- Keep exploratory analyses separate from confirmatory analyses.
- Report negative and null results.

## Acceptance criteria

- Every MCP request has exactly one correlated terminal outcome or a documented cancellation or disconnect.
- Fixture payload byte counts match exact serialized bytes.
- Concurrent events preserve causal order without being forced into false sequential order.
- The recorder distinguishes protocol errors, tool errors, backend exceptions, cancellations, timeouts, and incorrect agent outcomes.
- Automatic scoring passes all hand-written positive and negative fixtures.
- Derived tables reproduce raw-event counts exactly.
- A saved manifest reproduces scenario state and synthetic backend behaviour, though not identical hosted-model output.
- Each campaign produces a methods note, validated dataset, analysis artifact, plots, and formal result memo.
- The final report separates confirmatory results, exploratory findings, limitations, and negative results.

## Phase exit gates

| Phase | Exit gate |
|---|---|
| Measurement contract | Every field and metric has one operational definition |
| Recorder validation | All deterministic ground-truth checks pass |
| Agent pilot | Tasks, scoring, traces, run limits, and expected cost are acceptable |
| Task structure | Confirmatory dataset and result memo complete |
| Autonomy | Policy contrasts complete without changing other factors |
| Architecture | Matched single-agent and multi-agent comparison complete |
| Load | Throughput, latency, and failure curves complete |
| Transport | Logical replay comparison and agent confirmation complete |

## Deferred work

The first release excludes dashboards, real enterprise credentials or systems, adversarial-security benchmarking, multiple model providers, raw TLS decryption, TCP/IP packet capture, and formal queueing-theory claims.

The recorder must nevertheless preserve arrival, departure, service, waiting, concurrency, and queue-depth observations where available so later work can study:

$$
\lambda,\qquad S,\qquad W_q,\qquad R,\qquad L,\qquad\rho.
$$

Queueing theory will be learned and applied after the measurement system produces trustworthy data.
