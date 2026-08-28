# Phase 5 Plan: Why Do Identical Agent Runs Follow Different Paths?

## Question

> When the same Orders recovery incident is repeated, which observable execution paths are associated with failure, how variable are those paths, and how much extra work does the agent perform?

Phase 5 connects three practical questions directly to three statistical analyses:

| Practical question | Recorded data | Statistical answer |
|---|---|---|
| What happens after escalation is rejected? | Whether the agent reads the runbook before retrying | Conditional failure percentages |
| Does the agent follow the same path every time? | Complete ordered tool sequences | Path frequencies and entropy |
| How much unnecessary work does it perform? | Calls beyond the five-call valid path | Distribution of excess calls |

The study identifies observable histories associated with outcomes. It does not claim to recover the model's internal reason for choosing an action.

## Design

### Stage 5A: existing observations

Reanalyse the 90 Phase 4 main-study runs without making model calls. Use them to validate event extraction, describe all nine conditions, and confirm that `orders_api_outage` with recovery structure is the focused condition. The existing ten focused runs are pilot evidence and are not pooled with the new main sample.

### Stage 5B: focused repetition

Collect 100 new live runs with the incident, recovery structure, incoming message, instructions, tools, simulated world, model identifier, scoring, and stdio MCP transport held fixed. Every observation uses a fresh agent and MCP session. Acquisition uses ten resumable batches of ten runs and records batch, execution order, timestamps, configuration fingerprint, calls, actions, latency, tokens, bytes, cost, and outcome.

Before collection, validate the five-call oracle without model cost and collect three paid smoke observations that are excluded from analysis. Refuse to resume a campaign if the frozen configuration changes. Apply a $5 estimated-cost guard; an interrupted campaign remains explicitly incomplete.

## Primary reliability analysis

After the first expected rejection of `escalate_incident`, define

$$
H_r=
\begin{cases}
1, & \text{runbook read before another remediation attempt},\\
0, & \text{another remediation attempted first},
\end{cases}
$$

and

$$
F_r=
\begin{cases}
1, & \text{task failed},\\
0, & \text{task succeeded}.
\end{cases}
$$

Estimate

$$
q_1=P(F_r=1\mid H_r=1),
\qquad
q_0=P(F_r=1\mid H_r=0),
$$

and the risk difference

$$
\Delta=q_0-q_1.
$$

Report the underlying two-by-two counts, Wilson 95% intervals for each conditional failure proportion, a Newcombe 95% interval for $\Delta$, and Fisher's exact test as a secondary test. If either behaviour is too rare for a useful comparison, report the sparse support rather than fit an unstable model.

## Trace variability and efficiency

Represent run $r$ as

$$
X_r=(X_{r1},X_{r2},\ldots,X_{rN_r}),
$$

where each state contains the tool name and observed result. Include `START`, `END_SUCCESS`, and `END_FAILURE`. Report complete path counts and percentages, the modal path, singleton paths, and plug-in path entropy with a run-level bootstrap interval:

$$
\widehat H=-\sum_k \widehat p_k\log_2(\widehat p_k).
$$

Report empirical one-step transition counts and probabilities,

$$
\widehat P(X_{t+1}=j\mid X_t=i)
=
\frac{N(i\rightarrow j)}{\sum_k N(i\rightarrow k)},
$$

without claiming that the trace is a Markov chain.

For successful runs, define excess calls relative to the five-call oracle:

$$
E_r=N_r-5.
$$

Report the exact-oracle proportion and the mean, median, interquartile range, and observed range of $E_r$. Failed runs retain their observed call counts, but successful-path excess is undefined. Also report repeated tools, extra or unexpected actions, first oracle divergence, normalized oracle edit distance, latency, tokens, exact stdio bytes, estimated cost, and acquisition-batch diagnostics.

## Delivery

Write auditable JSON, CSV, and Parquet artifacts under `artifacts/phase5/`. Add read-only `/api/trace-study/` campaign and table endpoints. Paid repeated collection remains CLI-controlled.

Add a React/TypeScript **Trace dynamics** page that begins with the practical incident, then shows the two-by-two outcome table, conditional failure estimates, aligned success and failure traces, first divergence, path frequencies, transition counts and probabilities, excess-call distributions, batch diagnostics, individual traces, and raw downloads. It must distinguish reused pilot evidence, new main evidence, measured values, calculated summaries, and unavailable quantities.

Maintain one canonical result document at `docs/results/phase5_stochastic_trace_results.md`, starting with plain language before mathematical definitions, variable types and ranges, results, a Mermaid trace diagram, and limitations. Update the README, code flow, implementation status, and demo instructions without creating duplicate Phase 5 result memos.

## Acceptance

Test trace construction, action-result reconciliation, terminal states, post-rejection classification, confidence intervals, zero cells, path summaries, transitions, excess-call rules, pilot/main separation, resumability, configuration mismatch, the cost guard, API allow-lists, React explanations, and the browser workflow. Run the repository's complete acceptance gate before a `--no-ff` merge into `demo`. Preserve `phase/05-stochastic-traces`; do not merge to `main` without explicit direction.

## Limits

The results apply to the frozen synthetic incident, agent, model, configuration, and acquisition period. Fresh sessions define the experimental unit, while provider-side and temporal dependence remain possible. Phase 5 excludes queueing, controlled load, HTTP/TLS/TCP/IP traffic, multi-agent systems, causal interventions, and formal Markov-chain claims.
