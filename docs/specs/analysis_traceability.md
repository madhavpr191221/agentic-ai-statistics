# Statistical Analysis Traceability

This matrix is the review checklist for the specification. A question is complete only when its practical wording, estimand, artifact, UI representation, test, and result paragraph agree.

## Foundational principles

| ID | Principle | Documentation evidence | Verification |
|---|---|---|---|
| F01 | Scalar random variables are the first analysis objects | statistical specification; data dictionary | scalar distributions are reported before path summaries |
| F02 | Trajectories have random finite length | statistical specification | length or terminal state is included in path probability |
| F03 | Path frequencies do not imply a Markov model | statistical specification; roadmap | transitions are labeled descriptive unless separately justified |
| F04 | Scalars are functionals of richer run objects | statistical specification; Phase 5 results | scalar summaries remain primary outcomes and are not replaced by paths |

| ID | Practical object | Primary artifact | UI surface | Verification |
|---|---|---|---|---|
| Q01 | Run and variable definitions | data dictionary and `q01_data_dictionary.json` | Scalar baseline | schema/range reconciliation |
| Q02 | Run-level distributions | `q02_scalar_distributions.json` and CSV | Scalar baseline | aggregate totals and summary tests |
| Q03 | Batch stability | `q03_batch_stability.json` and CSV | Batch stability | batch-manifest test |
| Q04 | Workload by condition | Q04 workload summaries and count model | workload analysis | count-model and dispersion checks |
| Q05 | Calls and runtime | latency association table | runtime section | correlation/regression test |
| Q06 | Runtime components | latency components | where-runtime-goes section | decomposition accounting |
| Q07 | Tokens and cost | token/cost summaries | performance section | unit and missing-value tests |
| Q08 | Histories and failure | prefix outcomes | partial-history table | Wilson/Newcombe/Fisher tests |
| Q09 | Complete paths | paths/path concentration | path variability section | path-count reconciliation |
| Q10 | Adjacent events | transitions | transition section | row-normalization test |
| Q11 | Extra work | runs/excess summaries | efficiency section | oracle/excess test |
| Q12 | First divergence | divergence table | divergence section | position-by-outcome test |
| Q13 | Tool dominance | tool usage table | tool-traffic section | invocation reconciliation |
| Q14 | Path/workload/failure | grouped run summaries | trace dynamics | nested-unit test |
| Q15 | Causal intervention design | design note only | limitations | no Phase 5 causal claim |

## Review questions

- Does every percentage name its denominator?
- Is the unit of analysis a run unless explicitly labeled nested event?
- Is the quantity measured, derived, or unavailable?
- Is the uncertainty method appropriate for the sample and outcome?
- Is an association being described as an association rather than a cause?
- Does the artifact reconcile to the 100 valid Phase 5 runs?
- Does the UI explain the result before showing a technical statistic?
