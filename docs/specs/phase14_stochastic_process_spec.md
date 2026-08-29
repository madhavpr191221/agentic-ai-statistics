# Phase 14 Statistical Specification

## Unit and data

The unit is one fresh run. Each run contributes one finite ordered state path;
events within it are nested observations. The state path reuses the existing
`START`, `tool|outcome`, `END_SUCCESS`, and `END_FAILURE` representation.

## Estimands

For each analysis subset:

- observed transition count \(n_{ij}\);
- row frequency \(\hat p_{ij}=n_{ij}/\sum_j n_{ij}\);
- eventual success and failure absorption probabilities;
- expected steps to absorption;
- expected visits to each transient state;
- a weighted diagnostic comparing first- and second-order history summaries.

The holding-time estimand is registered as unavailable because the current
artifact contains ordering but not event timestamps.

## Interpretation

Transition frequencies describe this sample. A fitted first-order chain is an
approximation to the observable process, not a statement about the model's
private computation. Observational and randomized-policy subsets have different
scientific meanings and are reported separately.
