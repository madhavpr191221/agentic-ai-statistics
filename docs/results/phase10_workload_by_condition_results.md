# Phase 10 Results: Workload by Task Condition

For the concise combined study findings, start with
[`agent_execution_study_results.md`](agent_execution_study_results.md).

## Question

Does changing the hidden task structure change the amount of MCP work performed by the agent?

## Data

We reused the completed Phase 4 main campaign: 90 valid fresh runs, consisting of three incidents, three task structures, and ten repetitions per condition. No new model calls were made.

## Result

Recovery runs had the highest observed MCP-call workload. Their adjusted expected call ratio relative to sequential runs was approximately $1.205$ (about 20.5% higher). The adjusted branching ratio was approximately $1.012$, with no clear difference from sequential structure.

The model adjusted for incident identity and randomized block. These are comparisons within this controlled synthetic campaign; they are not universal causal claims about agentic AI systems.

See the downloadable Q04 artifacts in the Phase 4 campaign directory for the exact summaries and model coefficients.
