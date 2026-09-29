# Statistical principles

## Experimental unit

The complete fresh run is the primary experimental unit. If run (r) contains events (X_{r1},\ldots,X_{r\tau_r}), those events are nested measurements. They do not create (	au_r) independent replicates.

## Random variables and random trajectories

Scalar outcomes such as event count, latency, cost, and success are ordinary random variables. The complete trajectory is a random finite sequence:

\[
\mathbf X_r\in\bigcup_{n\geq 1}\mathcal A^n.
\]

The scalar outcomes are usually functionals of the richer trajectory and its environment.

## Description before modeling

Begin with empirical distributions, quantiles, proportions, tail probabilities, and uncertainty intervals. A model is introduced only when it answers a specific question better than an appropriate descriptive analysis.

## Association and causation

An observed history (H_r) can be associated with success (Y_r):

\[
P(Y=1\mid H=h).
\]

This is not automatically a causal effect. A causal comparison requires an assigned intervention (A_r), such as:

\[
P(Y=1\mid A=1)-P(Y=1\mid A=0).
\]

## Dependence and model checking

Runs may be treated as independent only under a documented design and drift assessment. Events within a run are dependent by construction. A Markov model must be checked using held-out prediction and history diagnostics.

## Uncertainty

Report uncertainty for estimates using methods appropriate to the experimental unit. When events are nested, resampling should normally occur at the run level rather than the event level.

## Practical significance

An effect may be statistically detectable but operationally irrelevant. Every result must discuss magnitude, uncertainty, and whether the difference matters for system design.
