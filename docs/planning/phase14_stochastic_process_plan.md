# Phase 14: Statistical Audit and Small Stochastic-Process Model

Phase 14 asks whether the recorded agent traces can be summarized by a small
absorbing stochastic process. It uses existing saved traces first; no paid
model calls are required.

## Statistical question

For one complete run, the observable state path is

\[
S_0,S_1,\ldots,S_{\tau},
\]

where `START` begins the run and `END_SUCCESS` or `END_FAILURE` terminates it.
The analysis estimates observed movements between compact tool-and-outcome
states and asks how much of the path can be explained by the current state.

Scalar run variables remain primary outcomes: calls, latency, bytes, tokens,
cost, and success are not replaced by the process model.

## Model and limits

For each separately analyzed subset (natural-policy observations and randomized
policy arms), estimate

\[
P_{ij}=P(S_{t+1}=j\mid S_t=i).
\]

Success and failure are absorbing states. From the transient matrix \(Q\),
report the fundamental matrix \((I-Q)^{-1}\), eventual absorption
probabilities, expected steps, and expected state visits when estimable.

The first-order model is a hypothesis to check, not a fact. Compare it with
selected second-order/history-conditioned frequencies. Holding-time analysis is
unavailable until the trace artifact contains valid per-event timestamps.

## User-facing outputs

The UI shows separate subset summaries, transition counts and percentages,
eventual success/failure probabilities, expected steps, model-status warnings,
and a downloadable `q17_absorbing_process.json` artifact. All process values
are labeled derived/inferred from measured traces.

## Acceptance criteria

- one run remains the experimental unit;
- observational and assigned-policy traces are not silently pooled;
- terminal states are absorbing and row probabilities are valid;
- sparse or singular systems are reported as not estimable;
- scalar baseline results remain visible;
- no claims are made about private reasoning, network packets, queueing, or a
  universal Markov model;
- the full repository test/build/browser gate passes.
