# Statistical Analysis Contracts

This document defines what an analysis is allowed to claim. The question registry supplies the question IDs; this document supplies the common contract used by implementations and the UI.

## Common input contract

An analysis consumes a validated campaign artifact with:

- one row or record per fresh run;
- a stable run identifier and experimental condition;
- nested event records linked to that run;
- a complete ordered trajectory when available;
- explicit missingness and measurement-status fields;
- campaign metadata describing model, prompt, tools, transport, seed, and acquisition order.

The run is the default denominator. Event-level counts are aggregated to runs before they are used as experimental outcomes.

## Common output contract

Each analysis artifact must include:

| Field | Meaning |
|---|---|
| `question_id` | Registered question, for example `Q02` |
| `dataset_id` | Exact campaign used |
| `unit` | `run`, `nested_event`, or `future_run` |
| `estimand` | Quantity being described or compared |
| `method` | Calculation or model used |
| `n_valid` / `n_missing` | Denominator and excluded records |
| `estimate` | Point estimate or distribution summary |
| `uncertainty` | Interval or explicit `descriptive_only` status |
| `measurement_status` | `measured`, `derived`, `inferred`, or `unavailable` |
| `interpretation` | Plain-language reading of the result |
| `limitations` | Dependence, transport, causality, or generalization limits |

## Analysis families

### Scalar distributions (Q01–Q03)

The first outputs describe run-level random variables such as

$$
N_r,\quad L_r,\quad T_r,\quad C_r,\quad Y_r.
$$

Required summaries include valid count, missing count, mean, median, spread, quantiles, an empirical distribution, and a documented uncertainty interval where estimable. Scalar means and medians use a fixed-seed percentile bootstrap; binary success uses a Wilson interval. A scalar result describes repeated runs under the recorded setup; it is not a claim about all agents.

### Controlled comparisons (Q04)

The condition is recorded by design. Group differences may be estimated with an appropriate count or continuous-outcome model only after checking the outcome distribution and dispersion. The report must state reference levels, covariates, uncertainty method, and whether the condition was actually manipulated.

### Associations (Q05–Q08, Q14)

These analyses compare observed quantities or histories. They may report

$$
P(Y=1\mid H=h)
$$

or an observed runtime difference, but must not call it a causal effect unless the predictor was assigned by design. Perfect separation is reported directly rather than hidden behind an unstable model.

### Trajectory distributions (Q09–Q13)

The complete path is a variable-length random object:

$$
\mathbf X_r=(X_{r1},\ldots,X_{rN_r}).
$$

Path frequencies, entropy, sequence distance, divergence, and transition frequencies are summaries of observed paths. Adjacent transition frequencies are not automatically Markov transition probabilities.

### Intervention design (Q15)

An intervention analysis requires a deliberately assigned behavior, a preserved comparison condition, and a pre-specified outcome. Only then may an intervention contrast such as

$$
P(Y=1\mid A=1)-P(Y=1\mid A=0)
$$

be interpreted causally, subject to the design limits.

## Trajectory artifact

The Q09–Q14 artifact is `q09_q14_trajectory_analysis.json`. It is derived from
measured run and nested-event records and mirrors the downloadable path tables.
Its transition values are descriptive row-normalized frequencies; its path
family comparisons are observational. It must not be interpreted as a fitted
Markov model or as evidence that an observed path choice caused an outcome.

## Measurement-status rules

- **Measured:** directly recorded by instrumentation, such as local stdio frame bytes or timestamps.
- **Derived:** calculated from measured records, such as medians, entropy, or path distance.
- **Inferred:** produced by a statistical model; model assumptions must be stated.
- **Unavailable:** not recorded at the current boundary, such as TCP packet sizes, TLS overhead, queue waiting time, or private reasoning.

The UI must never silently convert unavailable quantities into estimates.
