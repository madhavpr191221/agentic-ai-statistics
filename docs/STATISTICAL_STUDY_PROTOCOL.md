# Statistical study protocol

## Objective

Measure and explain the reliability–performance trade-off of a stochastic AI agent solving controlled IT incidents.

The target is a conditional distribution, not one benchmark number. For a specified condition \(Z=z\), we want to learn the distribution of the complete run outcome:

\[
\mathcal L\left(\mathbf X,N,L,B,T,C,Y\mid Z=z\right).
\]

## Experimental unit and random objects

One fresh complete agent execution is one experimental unit, indexed by \(r=1,\ldots,R\). Tool calls and model calls are nested observations, not independent runs.

The scalar random variables are the first analysis objects:

\[
N_r=\text{MCP calls},\quad L_r=\text{total latency},\quad B_r=\text{measured frame bytes},
\]
\[
T_r=\text{tokens},\quad C_r=\text{estimated cost},\quad Y_r\in\{0,1\}=\text{objective success}.
\]

The trajectory is a random finite sequence in a discrete path space:

\[
\mathbf X_r=(X_{r1},\ldots,X_{rN_r})\in\bigcup_{n\ge 1}\mathcal A^n.
\]

At each event we may also observe a timestamp and marks (tool, result, latency, bytes), giving a finite marked event sequence. We do not assume a Markov process merely because transitions can be counted.

## Study A: single-run stochastic behavior

### A1. Scalar baseline

For a fixed incident/model/tool configuration, estimate empirical distributions of \(N,L,B,T,C,Y\). Report center, spread, quantiles, tail probabilities, missingness, and run-level bootstrap intervals. Questions are deliberately small:

- What workload should a fresh run usually generate?
- How variable is runtime and cost?
- What is the repeated-run success probability under this exact condition?

### A2. Controlled comparisons

Change one designed condition at a time (incident structure, autonomy policy, or transport) while holding the rest fixed. Report differences or ratios of run-level distributions with uncertainty. Observed agent choices remain associational unless assigned by randomization.

### A3. Trajectory distribution

Estimate the empirical path law

\[
\widehat P_R(\mathbf X=x)=R^{-1}\sum_{r=1}^R\mathbf 1\{\mathbf X_r=x\}.
\]

Describe unique paths, modal-path coverage, path length, sequence distance, first divergence, transition frequencies, and path entropy. Progress to history-aware prediction, absorbing processes, or semi-Markov holding-time models only when diagnostics and sample size justify them.

### A4. One causal intervention

Pre-specify a practical intervention (for example, randomly assign the next action after a rejected escalation). Compare success and performance between randomized arms. State the estimand and analysis before acquisition; do not turn an agent-generated history into a causal claim.

## Study B: performance under load

Use a shared fixed-worker system and a controlled Poisson arrival process with rate \(\lambda\). For each request record arrival, queue entry, service start, completion, outcome, and the existing MCP/model measurements. Derived quantities include queue wait \(W_q\), total time \(W\), throughput \(X\), utilization \(U\), and queue length.

The first questions are operational and statistical:

- How does waiting time change with offered load?
- At what load does reliability or tail latency deteriorate?
- Does extra work (calls/tokens/cost) trade off against success?
- Does the observed system satisfy the diagnostic relationship \(L\approx\lambda W\) over a stable window?

No queueing model is fitted until arrivals, shared workers, and waiting are truly measured.

## Progressive model ladder

1. Empirical distributions and uncertainty for scalar outcomes.
2. Stratified comparisons and run-level bootstrap.
3. Simple outcome models only when an estimand and design support them (count, latency, or binary success).
4. History-aware trajectory prediction evaluated on held-out runs.
5. Absorbing/semi-Markov models with explicit states and holding times.
6. Queueing models after the load experiment supplies arrival and service data.

## Reporting standard

Every campaign must state the condition, unit, sample size, randomization (if any), primary outcome, estimand, stopping rule, measurement boundary, uncertainty method, and limitations. Results are claims about the tested configuration and environment, not about AI agents in general.
