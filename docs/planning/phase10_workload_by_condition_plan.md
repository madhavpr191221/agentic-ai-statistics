# Phase 10 Plan: Workload by Task Condition

## Practical question

> Does the structure of an incident task change how much work the agent performs?

This phase reuses the completed 90-run Phase 4 main campaign. It makes no new model calls.

## Statistical specification

The primary run-level outcome is

$$
N_r=\text{number of MCP calls in run }r.
$$

We first describe the distributions by task structure:

$$
E[N\mid Z=z],\qquad \operatorname{Var}(N\mid Z=z),\qquad P(N\ge k\mid Z=z).
$$

The three structures are sequential, branching, and recovery. Incident identity and randomized block are recorded categorical adjustment variables. One fresh run and MCP session is one observation; calls inside it are nested measurements.

After distribution checks, the pre-specified count model is

$$
\log(\mu_r)=\beta_0+\beta_BB_r+\beta_RR_r+\gamma_{\mathrm{incident}(r)}+\delta_{\mathrm{block}(r)},
$$

where sequential is the reference structure. Exponentiated structure coefficients are expected MCP-call ratios. A Poisson log-mean GLM with HC3 robust covariance is primary. A negative-binomial sensitivity model is fitted only if Pearson dispersion exceeds 1.25.

Latency, tokens, cost, and success are secondary outcomes. Results are associational unless an intervention has been assigned.

## Outputs

- `q04_workload_by_condition.json`
- `q04_count_model.json`
- `q04_workload_by_condition.csv`
- `q04_distribution_data.csv`
- UI workload comparison and downloads

## Limitations

The study covers three synthetic incidents and three designed task structures. It does not establish production-wide agent reliability, network performance, queueing behaviour, or a causal effect for every possible task.
