# Phase 4 Results: Does Task Structure Change Agent Behavior?

For the concise combined study findings, start with
[`agent_execution_study_results.md`](agent_execution_study_results.md).

Status: **complete**

Main campaign: **`task-structure-main-v1`**, completed on 2026-08-27

## The short answer

Yes. We found that the hidden structure of a task changed how the agent behaved.

- A task that required **recovery after a rejected action** generated about **20.5% more MCP tool calls** than a straightforward sequential task.
- A task with ordinary **branching choices** did not produce a clear increase in tool calls.
- The agent completed **85 of 90 runs**.
- All five failures occurred in one recovery condition and followed the same kind of sequencing mistake.
- Repeating the same condition produced different tool-call paths, so agent execution was genuinely variable rather than deterministic.

This phase moved the project beyond collecting traces. We conducted a controlled experiment and found a measurable relationship between task structure and agent workload.

## What did we change?

We used three concrete but simulated IT incidents:

1. checkout failures after a deployment;
2. an image worker suffering memory pressure; and
3. an orders API affected by an identity-service outage.

Each incident had three hidden structures:

- **Sequential:** the useful evidence and actions appear in a mostly direct order.
- **Branching:** the agent must choose between plausible investigative paths.
- **Recovery:** an action is rejected until the agent notices what is missing and changes its approach.

The visible ticket, model, instructions, tools, MCP transport, and scoring rules were otherwise held fixed. Every condition had a shortest valid solution of five tool calls. Therefore, recovery was not given a longer answer by construction.

We ran

$$
3\ \text{incidents}\times3\ \text{structures}\times10\ \text{repetitions}=90\ \text{runs}.
$$

Each run started a fresh agent session and was treated as one experimental observation.

## What did we observe?

| Structure | Runs | Successful runs | Mean MCP calls | Median MCP calls | Median total time | Median model tokens |
|---|---:|---:|---:|---:|---:|---:|
| Sequential | 30 | 30 | 8.13 | 8 | 16.67 s | 7,563.5 |
| Branching | 30 | 30 | 8.23 | 8 | 18.61 s | 7,586.5 |
| Recovery | 30 | 25 | 9.80 | 9 | 20.92 s | 9,130.5 |

Across all runs, the agent succeeded 85 times:

$$
\widehat p=\frac{85}{90}=0.944.
$$

The 95% Wilson interval was $[0.876,0.976]$. In plain language, 94.4% is our observed success rate, while the interval shows the uncertainty caused by having only 90 runs.

At the stdio MCP boundary, the experiment measured exactly:

- 152,164 request bytes;
- 2,827,474 response bytes; and
- no missing or mismatched MCP frames.

These are application-layer MCP/JSON-RPC bytes. They are not TCP or IP packet sizes.

## The main statistical comparison

Our main outcome was a count:

$$
N_{\mathrm{MCP},r}=\text{number of MCP tool calls in run }r.
$$

We used a count regression to compare the expected number of calls. Its equation was

$$
\log(\mu_r)
=\beta_0
+\beta_B I(\text{branching}_r)
+\beta_R I(\text{recovery}_r)
+\gamma_{\text{incident}(r)}
+\delta_{\text{block}(r)},
$$

where $mu_r$ is the model's expected MCP-call count for run $r$.

The variables on the right are called **covariates**. A covariate is simply a recorded characteristic used to make a fair comparison. We included:

- **task structure**, which was the variable we cared about;
- **incident identity**, because checkout, image, and orders incidents may naturally differ; and
- **randomized block**, which identifies the group of nine conditions run around the same time and helps account for time-related drift.

### Variable types, values, and model coding

| Variable | Role | Statistical type | Possible values in this study | How it entered the model |
|---|---|---|---|---|
| $N_{\mathrm{MCP},r}$ | Outcome being explained | Discrete count | Any non-negative integer in principle; observed values were 7, 8, 9, 10, and 11 | Used directly as the response variable |
| Task structure | Main explanatory variable | Nominal categorical | `sequential`, `branching`, `recovery` | Converted into two binary indicators, with `sequential` as the reference |
| Incident identity | Adjustment variable | Nominal categorical | `checkout_failures`, `image_worker_degradation`, `orders_api_outage` | Converted into two binary indicators, with `checkout_failures` as the reference |
| Randomized block | Adjustment variable | Categorical blocking factor | Block labels 1 through 10 | Converted into nine binary indicators, with block 1 as the reference |
| $\mu_r$ | Model-produced expected call count | Positive continuous quantity | Any value greater than zero | Not observed directly; calculated by the fitted model |

**Nominal categorical** means that the values name different groups but have no natural numerical order. For example, recovery is not â€œlarger thanâ€ branching in the way that 20 seconds is larger than 10 seconds.

Although blocks are labelled 1 to 10, block was **not** treated as a continuous number. The model did not assume that moving from block 1 to block 2 had the same effect as moving from block 8 to block 9. Each block was treated as its own category.

The two task-structure indicators were

$$
I(\text{branching}_r)=
\begin{cases}
1,&\text{if run }r\text{ used branching},\\
0,&\text{otherwise},
\end{cases}
$$

and

$$
I(\text{recovery}_r)=
\begin{cases}
1,&\text{if run }r\text{ used recovery},\\
0,&\text{otherwise}.
\end{cases}
$$

A sequential run has zero for both indicators. The incident and block categories were represented by the same reference-category idea. Therefore, this primary model contained **no continuous observed covariates**.

Sequential structure was the reference level. Exponentiating a structure coefficient gives an expected call ratio.

| Comparison with sequential | Expected call ratio | 95% confidence interval | Conclusion |
|---|---:|---:|---|
| Branching | 1.012 | $[0.976,1.050]$ | No clear difference was detected. |
| Recovery | 1.205 | $[1.167,1.244]$ | Recovery generated about 20.5% more expected calls. |

The recovery interval is entirely above 1. The branching interval includes 1. We adjusted the two planned comparisons together so that making two comparisons did not artificially strengthen the evidence.

## Why did we consider a negative-binomial model?

Count data are often more variable than a basic Poisson model expects. An agent might sometimes finish directly and sometimes get stuck in a long sequence of repeated calls. This extra variability is called **overdispersion**.

A negative-binomial model is useful when

$$
\operatorname{Var}(N\mid X)>\operatorname{E}(N\mid X).
$$

We therefore considered it before collecting the main data.

The pilot and main experiment showed the opposite: call counts were tightly concentrated around a small range. This is called **underdispersion**. The main dispersion estimate was approximately

$$
\widehat\phi=0.047,
$$

which is far below 1. A negative-binomial model adds extra variance and was therefore unsuitable here.

We used a Poisson model to estimate the average call ratios and **HC3 robust standard errors** for uncertainty. â€œRobust standard errorsâ€ means that the confidence intervals were calculated in a way that does not require the observed variance to match the Poisson variance exactly. The frozen rule said to fit a negative-binomial sensitivity model only if the dispersion estimate exceeded 1.25. It did not, so that model was not fitted.

## What happened in the five failed runs?

Sequential and branching runs succeeded 30/30 times. Recovery runs succeeded 25/30 times. All five failures occurred in the orders/recovery condition.

The common pattern was:

1. the agent diagnosed the identity-service dependency correctly;
2. it read the recovery runbook before that information was useful;
3. it attempted an invalid restart;
4. the system rejected escalation because a requirement was missing; and
5. the agent tried escalation again without rereading the runbook after the task state had changed.

The agent largely understood the incident but mishandled the order of actions. A final-answer-only evaluation would probably miss this distinction.

We did not report a logistic-regression coefficient for success. All failures were concentrated in one condition, while several groups had no failures. This creates **quasi-complete separation**: the available data cannot produce a stable, trustworthy coefficient. Reporting the raw success counts and intervals is more honest.

## How inefficient were successful traces?

Every shortest valid path contained five calls. For a successful run, we defined

$$
N_{\mathrm{excess},r}=N_{\mathrm{MCP},r}-5.
$$

| Structure | Mean excess calls | Median excess calls |
|---|---:|---:|
| Sequential | 3.13 | 3 |
| Branching | 3.23 | 3 |
| Recovery | 4.84 | 5 |

An excess call is a call beyond the shortest valid path. It is not automatically useless: it may represent sensible extra investigation.

## What else became larger?

Compared with sequential runs, the fitted recovery ratios were approximately:

- 1.20 for total time;
- 1.16 for request bytes;
- 1.19 for response bytes;
- 1.30 for model tokens; and
- 1.08 for estimated model cost.

These were secondary analyses. We did not correct them as a family of multiple tests, so they are supporting observations rather than the main confirmatory result.

## Did repeated runs follow the same path?

No. Within the same incident and structure, repeated agents sometimes called tools in different orders.

Across the nine experimental conditions, ten repetitions produced between two and eight distinct complete paths. The orders/recovery condition had eight different paths and was also the only condition containing failures.

We summarized path diversity using **entropy**. Entropy is larger when execution is spread across many paths and smaller when most runs follow the same path. Observed path entropy ranged from 0.722 to 2.846 bits.

This establishes that traces vary. It does not yet prove that the traces form a Markov process, that the transition probabilities are stable over time, or that high entropy causes failure.

## What did the pilot contribute?

The valid pilot contained 27 runs: one complete set of nine conditions repeated in three blocks. All 27 succeeded. Its purpose was to test the experiment before spending money on the main campaign.

An earlier pilot version was declared invalid because its image-worker scorer accepted the literal word `memory` but rejected the equally correct phrase `OOM pressure`. We fixed the scoring rule, added a regression test, and reran the pilot. The invalid artifacts were retained with an audit note and were never combined with the valid pilot or the main data.

The valid pilot also revealed underdispersion. That allowed us to freeze the Poisson-with-robust-uncertainty rule before collecting the separate 90-run main dataset.

## What have we established?

For these three tasks, using one fixed model and policy:

1. recovery structure increased MCP work;
2. ordinary branching did not clearly increase call count;
3. recovery traces were longer and more expensive on several measured dimensions;
4. identical conditions could produce different execution paths; and
5. trace ordering exposed a repeatable reliability problem.

We have not shown that the numerical effect applies to all models, agents, or real production incidents. We also have not measured queue waiting, arrival rates, utilization, HTTP/TLS/TCP/IP behavior, or Internet latency.

## Reproducing the saved analysis

The main analysis can be rebuilt without making new model calls:

```powershell
uv --cache-dir .uv-cache run --all-groups python -m agentic_ai_statistics.behavior.campaigns task-structure-main-v1 --stage main --analyze-only
```

The analyzed local artifacts had these SHA-256 checksums:

| Artifact | SHA-256 |
|---|---|
| `campaign_manifest.json` | `60e0cb8d8658427f62226724d02e929cf2de902fe381850f38aaf5596ffe2233` |
| `analysis.json` | `f4f8edfa67726de7884ef8fd12dbe37f4cfe61d3c8b94e91fc0c98aade81aaaa` |
| `tables/runs.csv` | `b9552bfbc1f68904452cda52db73db1daf1f333120249c16339a281f7f0b56a4` |
