# Phase 4 Task-Structure Main Results

Status: completed on 2026-08-27.

Campaign: **`task-structure-main-v1`**

Frozen implementation commit: **`600409f`**

Experimental unit: one fresh agent run with one fresh MCP session.

## The question in plain language

We gave the same model the same three visible IT-incident tickets, the same ten tools, and the same operating rules. What changed was the hidden structure of the task world:

- **sequential:** evidence and actions become useful in a mostly linear order;
- **branching:** the agent must choose between plausible diagnostic branches; and
- **recovery:** a correct-looking action is deliberately rejected until the agent obtains the required evidence or instruction.

The shortest valid solution always contained five MCP calls. This makes the comparison interpretable: a longer observed trace reflects additional investigation, repetition, recovery, or deviation rather than a longer built-in oracle.

The balanced main design was

$$
3\ \text{tickets}\times3\ \text{structures}\times10\ \text{blocks}=90\ \text{independent runs}.
$$

Pilot observations were not included.

## Primary outcome: MCP call count

For run $r$, let $N_{\mathrm{MCP},r}$ be the number of MCP tool calls. The preregistered main model after pilot diagnostics was

$$
N_{\mathrm{MCP},r}\mid X_r \sim \operatorname{Poisson}(\mu_r),
$$

$$
\log(\mu_r)
=\beta_0
+\beta_B I(\text{branching}_r)
+\beta_R I(\text{recovery}_r)
+\gamma_{\text{ticket}(r)}
+\delta_{\text{block}(r)}.
$$

HC3 robust standard errors were used. The two planned structure contrasts were adjusted together by the Holm method.

| Planned contrast | Expected call ratio | 95% HC3 interval | Holm-adjusted $p$ | Interpretation |
|---|---:|---:|---:|---|
| Branching versus sequential | 1.012 | $[0.976,1.050]$ | 0.517 | No detectable call-count difference in this study. |
| Recovery versus sequential | 1.205 | $[1.167,1.244]$ | $4.52\times10^{-30}$ | Recovery tasks generated about 20.5% more expected MCP calls. |

The Pearson dispersion estimate was

$$
\widehat\phi=0.0469.
$$

This is strong underdispersion, so the prespecified negative-binomial sensitivity model was not fitted. Its trigger required $\widehat\phi>1.25$.

## Descriptive results

| Structure | Runs | Successful | Mean MCP calls | Median MCP calls | Median total latency | Median tokens | Estimated cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sequential | 30 | 30 | 8.133 | 8 | 16.673 s | 7,563.5 | $0.9874 |
| Branching | 30 | 30 | 8.233 | 8 | 18.609 s | 7,586.5 | $0.9984 |
| Recovery | 30 | 25 | 9.800 | 9 | 20.916 s | 9,130.5 | $1.0643 |
| **All runs** | **90** | **85** | — | **8** | — | — | **$3.0501** |

The overall success estimate was

$$
\widehat p=\frac{85}{90}=0.944,
\qquad
\text{Wilson 95% interval}=[0.876,0.976].
$$

The campaign recorded exactly 152,164 request-frame bytes and 2,827,474 response-frame bytes at the stdio MCP boundary. All 90 runs had complete frame-byte measurements and consistent SDK-to-MCP tool correlation.

## Success and the five failures

Sequential and branching runs succeeded 30/30 times. Recovery runs succeeded 25/30 times. All five failures occurred in the orders-API recovery condition, which succeeded 5/10 times.

A logistic success model was not estimable because task structure, ticket, and block produced quasi-complete separation: some groups had no failures, while one cell contained every failure. Reporting a large unstable coefficient would create false precision, so the analysis reports the model as unavailable. Wilson intervals and cell counts remain valid descriptive summaries.

The five failures shared a concrete mechanism:

1. the agent found the correct dependency diagnosis;
2. it read the recovery runbook too early;
3. it attempted an invalid restart;
4. the world produced the expected rejection when escalation prerequisites were absent; and
5. the agent retried escalation without rereading the now-relevant runbook, so escalation was rejected again.

This is a path-dependent failure. The final diagnosis alone would not reveal it; the ordered trace does.

## Efficiency relative to the oracle

Every oracle contains five calls. Among successful runs, excess calls were therefore

$$
E_r=N_{\mathrm{MCP},r}-5.
$$

| Structure | Successful runs | Mean excess calls | Median excess calls |
|---|---:|---:|---:|
| Sequential | 30 | 3.133 | 3 |
| Branching | 30 | 3.233 | 3 |
| Recovery | 25 | 4.840 | 5 |

This is an action-efficiency measure, not monetary regret and not proof that every non-oracle call was useless.

## Exploratory secondary outcomes

These log-linear HC3 contrasts were specified as secondary analyses. Their raw $p$-values are descriptive and were not multiplicity-adjusted, so they should not be treated like the primary confirmatory contrast.

| Outcome | Branching/sequential ratio (95% CI) | Recovery/sequential ratio (95% CI) |
|---|---:|---:|
| Total latency | 1.097 $[1.020,1.180]$ | 1.198 $[1.122,1.279]$ |
| Request bytes | 1.014 $[0.970,1.060]$ | 1.162 $[1.113,1.213]$ |
| Response bytes | 1.010 $[0.972,1.050]$ | 1.195 $[1.155,1.236]$ |
| Model tokens | 1.016 $[0.958,1.077]$ | 1.298 $[1.231,1.368]$ |
| Estimated cost | 1.011 $[0.985,1.037]$ | 1.078 $[1.053,1.103]$ |

The recovery condition was consistently larger on these measured outcomes. Because model time dominates total time and the traces contain extra model decisions as well as extra MCP calls, these ratios are system-level consequences of the controlled task structure—not estimates of network delay.

## Stochastic trace variability

Repeated runs in the same experimental cell did not always follow the same tool sequence. Across the nine cells, the number of distinct observed paths among ten repetitions ranged from two to eight. Empirical path entropy ranged from approximately 0.722 to 2.846 bits.

The most variable cell was orders/recovery: eight paths in ten runs and 2.846 bits of empirical entropy. This was also the only failure-bearing cell. That association is scientifically interesting, but one cell is not enough to claim that higher entropy causes failure.

Transition probabilities and path entropy are empirical summaries of these 90 traces. They do not establish stationarity, a Markov property, or a general stochastic law for agent behavior.

## What this phase establishes

Within these three synthetic but concrete IT tasks, and under one fixed model and policy:

1. hidden recovery structure increased MCP call count relative to matched sequential tasks;
2. ordinary branching did not produce a detectable call-count increase;
3. recovery also produced longer, larger, and more token-intensive traces descriptively;
4. repeated prompts generated multiple valid execution paths; and
5. ordered trace analysis exposed a repeatable path-dependent reliability failure.

It does **not** establish that all recovery tasks have these effect sizes, that trace entropy predicts production failure, or that any measured latency is Internet RTT or queue waiting time.

## Reproducibility record

The raw campaign directory is ignored by Git because it contains large generated artifacts. The derived analysis can be rebuilt without model calls using:

```powershell
uv --cache-dir .uv-cache run --all-groups python -m mcp_traffic_analysis.behavior.campaigns task-structure-main-v1 --stage main --analyze-only
```

SHA-256 checksums for the analyzed local artifacts are:

| Artifact | SHA-256 |
|---|---|
| `campaign_manifest.json` | `60e0cb8d8658427f62226724d02e929cf2de902fe381850f38aaf5596ffe2233` |
| `analysis.json` | `f4f8edfa67726de7884ef8fd12dbe37f4cfe61d3c8b94e91fc0c98aade81aaaa` |
| `tables/runs.csv` | `b9552bfbc1f68904452cda52db73db1daf1f333120249c16339a281f7f0b56a4` |

