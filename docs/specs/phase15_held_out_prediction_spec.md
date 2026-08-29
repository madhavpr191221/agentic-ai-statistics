# Phase 15 Statistical Specification

## Unit

One complete run is the resampling and reporting unit. State transitions inside
one run are nested observations.

## Primary estimand

For model \(m\), a test run with path
\(S_0,\ldots,S_{\tau}\) has

\[
\bar\ell_{r,m}= -\frac{1}{\tau}
\sum_{t=0}^{\tau-1}\log\widehat P_m(S_{t+1}\mid\mathcal H_t).
\]

The primary comparison is the difference in mean run log loss between the
current-state model and the global-majority baseline. A negative difference
means the current-state model predicts better.

Secondary estimands are next-state accuracy, multiclass Brier score, and
per-transition/path log likelihood. All are evaluated only on the held-out
campaign.

## Models and fallback

The state vocabulary is fixed from training states plus terminal states and an
`UNKNOWN` bucket. Add-one smoothing gives unseen transitions nonzero mass. An
unseen second-order context falls back to the current-state model, then the
global baseline.

## Interpretation limits

The comparison is predictive, not causal. It describes observable state
sequences, not private model reasoning. A single held-out campaign cannot
establish universal generalization. Uncertainty intervals are deferred until a
run-level resampling rule is frozen after acquisition.
