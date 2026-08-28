# Phase 6A Statistical Analysis Roadmap

This is a credit-free learning and analysis roadmap. It uses only the completed 100-run Phase 5 campaign. No model calls, new incidents, new providers, or new agent behaviour are introduced.

## What statistical analysis means here

Each fresh agent run is one observation. We use repeated observations to describe variation, compare groups, quantify uncertainty, and build limited explanations of why runs differ.

The basic chain is:

$$
\text{task condition}
\rightarrow
\text{agent actions}
\rightarrow
\text{MCP trace}
\rightarrow
\text{latency and cost}
\rightarrow
\text{success or failure}.
$$

Actions inside one run are nested measurements, not independent experimental units.

## Small questions, in learning order

### 1. What is one observation?

Identify the run-level unit and classify every variable as numeric, binary, categorical, count, or ordered sequence. Record its meaning, unit, range, and whether it is measured or derived.

### 2. How much MCP work does a run perform?

For

$$
N_r=\text{MCP calls in run }r,
$$

calculate the mean, median, quartiles, standard deviation, range, empirical distribution, and unusually large or small values.

### 3. How long does a run take?

For total runtime $L_r$, report its distribution and compare successful and failed runs. Then examine the observed relationship

$$
L_r=\beta_0+\beta_1N_r+\varepsilon_r.
$$

Here $\beta_1$ is an association with one additional MCP call, not automatically a causal effect.

### 4. Where does runtime go?

Use the measured decomposition

$$
L_{\mathrm{total},r}
=
L_{\mathrm{model},r}
+L_{\mathrm{MCP},r}
+L_{\mathrm{orchestration},r}.
$$

Report component medians, shares, ranges, and correlations with total runtime. Server-handler time remains a nested MCP component.

### 5. What explains tokens and cost?

For token count $T_r$ and estimated cost $C_r$, compare cost with call count, runtime, and trace length using plots and rank correlations before considering regression.

### 6. Which observable histories are associated with failure?

Define success as

$$
Y_r=1\text{ for success},\qquad Y_r=0\text{ for failure}.
$$

For an observed history $H$, calculate

$$
\widehat P(Y_r=0\mid H).
$$

Use counts, percentages, and Wilson intervals. Do not call this an out-of-sample prediction model.

### 7. How variable are complete paths?

Represent each trace as

$$
X_r=(X_{r1},X_{r2},\ldots,X_{rN_r}).
$$

Count unique paths, singleton paths, modal-path coverage, cumulative coverage, and entropy:

$$
H(X)=-\sum_xP(X=x)\log_2P(X=x).
$$

Bootstrap intervals describe uncertainty in the entropy estimate.

### 8. What actions follow other actions?

Calculate observed transition counts and row-normalized proportions:

$$
\widehat p_{ij}=\frac{n_{ij}}{\sum_j n_{ij}}.
$$

These are descriptive transition summaries. A Markov assumption is not made.

### 9. How much extra work occurs?

For successful runs, compare observed calls $N_r$ with the shortest valid oracle length $N_r^*$:

$$
E_r=N_r-N_r^*.
$$

Report exact-oracle successes, excess-call summaries, repeated tools, unexpected actions, and oracle distance.

### 10. Did behaviour drift across batches?

Compare success rate, runbook-first rate, call count, runtime, and path entropy across acquisition batches. Treat this as a drift diagnostic, not a new confirmatory hypothesis test.

## Interpretation rules

- Report effect sizes and intervals, not isolated $p$-values.
- Label exploratory questions separately from the predeclared primary comparison.
- Do not treat actions within one run as independent replicates.
- Do not infer private model reasoning from observable traces.
- Do not convert local stdio frame bytes into network-packet claims.
- Do not use causal language for the non-randomized runbook comparison.

Every result must answer four things: what happened, how precisely it was estimated, what it might mean, and what it does not establish.

## Completion criteria

The roadmap is complete when every question has a reproducible table or plot, a plain-language explanation, an uncertainty statement where appropriate, an explicit limitation, and passing Python, API, UI, browser, and repository-gate tests.
