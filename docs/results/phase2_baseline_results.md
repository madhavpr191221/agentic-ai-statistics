# Phase 2 baseline results

Status: complete local calibration campaign, collected on 2026-08-27.

This is a reproducible result memo for the first controlled MCP performance dataset. It describes one local machine and one implementation, not a general claim about MCP deployments or agentic AI systems.

## Dataset integrity

| Item | Value |
| --- | ---: |
| Treatment cells | 48 |
| Independent runs | 960 |
| Nested tool calls | 7,680 |
| Calls per run | 8 |
| Run replicates per cell | 20 |
| Failed calls | 0 |
| Execution randomization seed | 20260827 |
| Bootstrap iterations | 2,000 |

The frozen campaign manifest has SHA-256 `25B2ACBDC0608EACCFDD04DC0B499C6525CAD9E08A93B418D099E9C66DBEB0BA`. The generated analysis file has SHA-256 `09C93D4F4F19F5D7C1C0B9788BB5E2E098C9D1ABA60315582544BB6599EA5F9B`.

Raw per-run artifacts and analysis tables are local ignored outputs under `artifacts/phase2/baseline-v1/`. The analysis-ready files are in `tables/runs.csv`, `tables/calls.csv`, and their Parquet equivalents.

## Main findings

The primary model uses the log of each run's median client RTT and HC3 robust standard errors:

$$
\log(\widetilde L_r)
\sim \text{transport} * \text{payload}
+ \text{service time}
+ \text{concurrency}
+ \text{transport} * \text{concurrency}.
$$

It has (R^2=0.794) and adjusted (R^2=0.792). The most important controlled effects are expected:

| Contrast against baseline level | Log effect | 95% HC3 interval | Multiplicative RTT ratio |
| --- | ---: | ---: | ---: |
| 20 ms service versus 0 ms | 1.122 | [1.034, 1.210] | 3.07 |
| 100 ms service versus 0 ms | 2.149 | [2.062, 2.237] | 8.58 |
| Concurrency 4 versus 1 | 0.892 | [0.783, 1.000] | 2.44 |
| `stdio` versus in-memory | -0.129 | [-0.267, 0.009] | 0.88 |
| `stdio` × concurrency 4 | -0.246 | [-0.372, -0.119] | 0.78 |

These are conditional model contrasts. The `stdio` coefficient by itself should not be read as a universal claim that subprocess transport is faster: both paths include local runtime effects, and the interaction changes the concurrency contrast. Payload main effects and the tested transport-by-payload interactions had wide intervals containing zero at this local scale.

The fastest observed condition median was 4.78 ms (`in_memory`, 65,536-byte target, 0 ms service, concurrency 1). The slowest was 155.23 ms (`in_memory`, 16,384-byte target, 100 ms service, concurrency 4). These are condition summaries, not estimates of an Internet RTT.

## Nested-call model

The secondary mixed model uses all 7,680 calls with a random intercept for run. It converged, with estimated between-run variance (0.200), within-run variance (0.084), and

$$
\mathrm{ICC}=0.705.
$$

That high ICC is a concrete empirical warning against pseudo-replication: measurements from calls in the same fresh session have substantial shared variation. The model also estimates that the first call in a run is about (1.43\times) later than subsequent calls after the included controls. This is consistent with session/discovery/startup behaviour and is exactly why raw protocol traces are retained alongside the analysis table.

## Byte model

For `stdio` only, actual request and response JSON-RPC frame bytes were captured at the relay. The frame-byte model has (R^2=0.886). Conditional on service and concurrency, doubling the median total frame bytes was associated with a factor of (1.013) in run-median RTT (95% interval [1.003, 1.023]) in this local calibration. This is a small association relative to the programmed service and concurrency effects; it is not a bandwidth benchmark.

## Interpretation and next step

This phase demonstrates three things:

1. the `stdio` recorder observes genuine protocol frames and byte counts rather than estimating Python object size;
2. a frozen, balanced campaign can generate reproducible run- and call-level analysis tables; and
3. the nested data structure has measurable consequences for inference.

It does not yet support queueing theory conclusions. There is no controlled arrival process, queue length, utilization measure, or server resource contention. The next mathematically meaningful phase should introduce an explicit single shared backend with controlled arrival rate and service distribution, then measure waiting time separately from service time. Only then can we test queueing models against this system.
