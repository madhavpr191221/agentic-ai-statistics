# Phase 4 Task-Structure Pilot Results

Status: valid pilot completed on 2026-08-27.

Valid campaign: **`task-structure-pilot-v2`**

Experimental unit: one fresh agent run and one fresh MCP session.

## What was tested

The pilot crossed three concrete incident tickets with sequential, conditional-branching, and recovery task graphs. It used three randomized complete blocks:

$$
3\ \text{tickets}\times3\ \text{structures}\times3\ \text{blocks}=27\ \text{runs}.
$$

The visible ticket, model, prompt policy, tools, stdio transport, timeouts, and scoring mechanism were held fixed. Pilot data will not be combined with the 90-run main study.

## Calibration defect found before v2

`task-structure-pilot-v1` is invalid calibration evidence. Its image-worker scorer required the literal word `memory`. Three agents correctly diagnosed `image-worker-3` as suffering `OOM pressure`, executed the accepted restart, and resolved the world, but were marked as diagnosis failures.

The rubric was corrected to require `image-worker-3` plus either `memory` or `oom`. A regression test freezes that equivalence. The v1 raw artifacts were retained with an explicit invalid-calibration note; they were not silently edited, rescored, or combined with v2.

This is exactly what the pilot was meant to catch.

## Valid v2 observations

| Quantity | Observed value |
|---|---:|
| Runs and fresh sessions | 27 |
| Successful tasks | 27/27 |
| Wilson 95% interval | $[0.875,1.000]$ |
| Median MCP calls per run | 9 |
| Median total latency | 18.557 s |
| Median total tokens | 8,803 |
| Exact request-frame bytes | 45,213 |
| Exact response-frame bytes | 843,641 |
| Correlation mismatches | 0 |
| Estimated model cost | $0.9065 |

### By task structure

| Structure | Runs | Successes | Mean MCP calls | Median MCP calls | Median latency | Estimated cost |
|---|---:|---:|---:|---:|---:|---:|
| Sequential | 9 | 9 | 8.000 | 8 | 16.808 s | $0.2922 |
| Branching | 9 | 9 | 8.444 | 8 | 19.087 s | $0.3006 |
| Recovery | 9 | 9 | 9.556 | 9 | 20.261 s | $0.3138 |

All shortest valid traces contain five calls. The agent usually used more because it gathered additional evidence, repeated calls, posted updates, or deviated from the shortest order.

## Pilot model diagnostics

The pilot Pearson dispersion estimate for the Poisson log-mean model was approximately

$$
\widehat\phi=0.056.
$$

This is underdispersion, not overdispersion. The originally planned negative-binomial primary model was therefore replaced before the main study by a Poisson log-mean GLM with HC3 robust covariance. The robust covariance does not require the empirical conditional variance to equal the conditional mean.

The now-frozen main-study rule is:

- primary: Poisson log-mean GLM with HC3 covariance;
- planned structure contrasts: branching versus sequential and recovery versus sequential;
- Holm adjustment across those two contrasts;
- negative-binomial sensitivity model only if Pearson dispersion exceeds 1.25.

The pilot call-ratio coefficients are design diagnostics, not confirmatory estimates. They must not be reported as the main scientific result.

Task success was constant in v2, so logistic regression was correctly marked unavailable. Wilson intervals remain reportable.

## Stochastic trace evidence

Repeated runs under the same condition did not always follow the same tool sequence. Six of the nine cells produced at least two distinct paths in only three repetitions; four cells produced three distinct paths. Observed cell-level path entropy ranged from 0 to approximately 1.585 bits.

These values establish that repeated agent traces can vary. They do not establish a Markov process, stationary transition law, or population entropy for all IT tasks.

## Pilot decision

The corrected task world is fit to freeze for the main study because:

1. all nine conditions produced terminal artifacts;
2. every condition was solvable;
3. exact stdio bytes were present for every live run;
4. SDK and MCP tool sequences correlated for every run;
5. the primary call count varied across runs and structures;
6. the scoring defect was corrected before confirmatory collection; and
7. the final statistical rule was fixed using pilot diagnostics.

The main campaign remains a separate 90-run dataset. No pilot observation is eligible for it.
