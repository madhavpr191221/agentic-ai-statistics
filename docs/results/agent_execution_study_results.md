# Agent Execution Study: Main Results

This is the reader-facing summary of the study. It combines the main empirical
findings from Phases 3, 4, 5, 10, and 12. The older phase reports remain
available as technical and audit records.

## What are we studying?

We repeatedly run an AI agent on controlled, synthetic IT incidents and study
how its observable behavior varies.

One fresh agent run is one statistical observation. Tool calls are measurements
inside that run, not independent observations.

For run $r$, the basic scalar outcomes are

$$
N_r=\text{MCP calls},\qquad L_r=\text{total latency},
$$

$$
Y_r=\begin{cases}1,&\text{task succeeds},\\0,&\text{task fails}.
\end{cases}
$$

The richer object is the ordered observable trajectory

$$
\mathbf X_r=(X_{r1},\ldots,X_{rN_r}),
$$

where each $X_{rt}$ is an observed tool/action state.

## Measurement boundary

The system records model and MCP calls, client-observed timing, model tokens,
estimated cost, exact local stdio MCP/JSON-RPC frame bytes, ordered tool traces,
rejected actions, and deterministic success against known synthetic ground
truth.

The current study does **not** measure TCP/IP packets, TLS or HTTP overhead,
Internet RTT, queue waiting time, network retransmissions, or private model
reasoning. The recorded frame bytes are application-layer MCP data.

## Result 1: the agent produces measurable incident traces

The Phase 3 corrected pilot ran 30 model-driven incident executions and all 30
succeeded. The action ledger nevertheless revealed inefficient behavior: the
Orders incident repeatedly attempted an invalid restart before performing the
correct escalation.

This established the study object: a real model-driven execution trace in a
controlled world, with a known objective outcome.

## Result 2: task structure changes workload

Phase 4 used

$$
3\ \text{incidents}\times3\ \text{task structures}\times10\ \text{repetitions}=90\ \text{runs}.
$$

The visible ticket, model, tools, instructions, transport, and scoring rules
were held fixed while hidden task structure varied.

- Recovery structure increased expected MCP calls by about **20.5%** relative to sequential structure.
- Branching showed no detectable call-count difference from sequential structure.
- Overall success was **85/90**.
- All five failures occurred in the Orders recovery condition.

This is the clearest controlled comparison in the current study because task
structure was assigned by the experimental design.

## Result 3: scalar outcomes across 100 repeated runs

The Phase 5B Orders-recovery campaign contained 100 valid runs.

| Quantity | Mean | Median | Main interpretation |
|---|---:|---:|---|
| MCP calls | 9.8 | 10 | About ten tool calls per run |
| Total latency | 20.01 s | 19.57 s | A typical run took about twenty seconds |
| Model latency | 18.75 s | 18.32 s | Model requests dominated runtime |
| MCP latency | 56.6 ms | 57.1 ms | Local MCP communication was small relative to inference |
| Tokens | 10,223 | 10,444 | Moderate run-to-run variation |
| Request frame bytes | 1,832 | 1,835 | Stable local application messages |
| Response frame bytes | 35,325 | 35,949 | Responses were much larger than requests |
| Estimated cost | $0.0360 | $0.0356 | Derived from recorded usage and pricing |
| Task success | 71% | 100% or 0% | 71 successes and 29 failures |

The 95% Wilson interval for the success proportion was **61.5%–79.0%**. The
bootstrap 95% interval for mean MCP calls was **9.71–9.88**; for mean total
latency it was **19.67–20.36 seconds**.

These intervals describe repeated runs under this exact campaign configuration.
They are not guarantees about AI agents generally.

## Result 4: model inference dominated local runtime

Median runtime decomposition was:

| Component | Median |
|---|---:|
| Model | 18.32 s (about 93.7%) |
| MCP client time | 57.1 ms |
| Server handler time | 5.6 ms, nested inside MCP time |
| Orchestration | 1.18 s |

Under this local setup, improving MCP handler speed alone would not materially
change total runtime unless model time also changed.

## Result 5: the agent follows variable paths

Across the 100 Orders-recovery runs there were:

- **22 distinct complete paths**;
- **13 singleton paths** (seen once only);
- one modal path covering **55%** of runs;
- path entropy of **2.700 bits**;
- bootstrap entropy interval of **2.066–2.971 bits**.

The most common successful path was approximately:

```text
inspect evidence → inspect metrics → inspect dependencies → search logs
→ inspect changes → read runbook → attempt restart (rejected)
→ escalate (rejected) → read runbook → escalate → success
```

The common failed path was the same until the rejected escalation, then retried
escalation immediately and failed.

Thus the agent has a dominant behavior, but repeated equivalent runs do not
produce one identical sequence.

## Result 6: success did not mean efficiency

The shortest valid solution contained five calls. Define successful-run excess
work as

$$
E_r=N_r-N_r^*,
$$

where $N_r^*$ is the oracle length.

None of the 71 successful runs exactly followed the oracle. Their median excess
was **five calls**, with an observed range of **four to six**.

The agent generally succeeded after extra investigation and an unnecessary
restart attempt. Therefore reliability and efficiency are separate outcomes.

## Result 7: one observable history separated outcomes

After an escalation was rejected, the observed outcomes were:

| Next observable behavior | Success | Failure |
|---|---:|---:|
| Read the runbook first | 71 | 0 |
| Retried another action first | 0 | 29 |

Therefore,

$$
\widehat P(\text{failure}\mid\text{read runbook first})=0,
$$

while

$$
\widehat P(\text{failure}\mid\text{retry first})=1.
$$

This perfectly separated outcomes in this dataset. However, the agent chose
the next behavior; the experiment did not randomize it. The result is therefore
an extremely strong observed association, not yet proof that reading the
runbook causes success.

## Result 8: early divergence did not explain failure

The first observable divergence from the shortest oracle had median position
2 for both successful and failed runs, with both groups ranging from positions
2 to 3.

So simply departing from the oracle early was not enough to distinguish failure.
The more informative difference appeared later, after the rejected escalation.

## What these results mean statistically

The study uses four levels of claim:

1. **Descriptive:** what happened in these runs?
2. **Inferential:** what might repeated runs under this same setup look like?
3. **Associational:** which observed behaviors occur together?
4. **Causal:** what changes when a behavior is deliberately assigned?

The current results are mostly descriptive and associational. Phase 4 provides a
controlled condition comparison. A future randomized intervention would be
needed for a causal test of the runbook behavior.

The trajectory is the richest object:

$$
\text{trajectory}
\longrightarrow
\text{path summaries}
\longrightarrow
\text{scalar outcomes}.
$$

Transition counts are useful descriptive summaries, but they do not establish a
Markov process. The data also do not reveal private model reasoning.

## Overall conclusion

Under controlled synthetic incident conditions, the agent generated a fairly
stable workload and latency distribution but meaningful variation in its
execution paths. Failures concentrated in one observable post-rejection
behavior, while successful runs were usually inefficient relative to the
shortest valid solution. The next scientifically meaningful step is a small
controlled intervention, not a larger dashboard or an unsupported stochastic
process model.

## Result 9: randomized recovery-policy intervention

The first causal phase assigned 60 fresh Orders-recovery runs to one of two
policies before execution:

- **normal policy:** the agent received the existing instructions;
- **runbook-first policy:** the agent was instructed that, after a rejected
  escalation, its next action must be reading the runbook.

There were 30 valid runs in each arm. The primary outcome was task success.

| Assigned policy | Runs | Successes | Success rate |
|---|---:|---:|---:|
| Normal policy | 30 | 20 | 66.7% |
| Runbook first | 30 | 30 | 100.0% |

The intention-to-treat success-rate difference was

$$
\widehat\Delta=1.000-0.667=0.333.
$$

The Newcombe 95% interval was **0.152–0.512**, and Fisher's two-sided exact
$p$-value was **0.000797**.

In this experiment, assigning the runbook-first recovery policy increased
observed success by **33.3 percentage points**. This is the first causal result
in the project, but its scope is narrow: it applies to this model, prompt,
tool set, synthetic Orders incident, and intervention policy. It is not a
universal production-agent reliability estimate.

The intervention arm also had lower descriptive workload and latency:

| Assigned policy | Mean MCP calls | Mean latency | Mean tokens |
|---|---:|---:|---:|
| Normal policy | 9.87 | 22.35 s | 10,348 |
| Runbook first | 9.23 | 20.53 s | 9,816 |

These secondary differences are descriptive. The primary pre-specified causal
claim concerns task success.

## Technical evidence

- [Phase 3 pilot results](phase3_incident_pilot_results.md)
- [Phase 4 task-structure results](phase4_task_structure_results.md)
- [Phase 5 stochastic-trace results](phase5_stochastic_trace_results.md)
- [Phase 10 workload results](phase10_workload_by_condition_results.md)
- [Statistical analysis specification](../specs/statistical_analysis_spec.md)
- [Analysis contracts](../specs/analysis_contracts.md)
- [Trajectory artifact](../../artifacts/phase5/campaign-trace-orders-recovery-main-v2/q09_q14_trajectory_analysis.json)
- [Randomized intervention artifact](../../artifacts/phase5/campaign-intervention-orders-recovery-v1/q16_randomized_intervention.json)
