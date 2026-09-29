# Glossary

**Run** — one fresh, complete execution from initial task to terminal outcome.

**Invocation** — one request to execute a task; a run may be one invocation or contain nested invocations if the design explicitly says so.

**Event** — one observable occurrence during a run, such as a model call, retrieval, tool call, validation, retry, or terminal outcome.

**State** — an analysis-level representation of the system at a point in the run. States are defined by a specification; they are not automatically identical to raw event types.

**Trajectory** — the ordered sequence of observable states or events:

\[
\mathbf X_r=(X_{r1},\ldots,X_{r\tau_r}).
\]

**Condition** — a controlled configuration under which runs are generated.

**Campaign** — a pre-specified collection of comparable runs with an estimand, stopping rule, and analysis plan.

**Intervention** — a deliberately assigned change to the system or policy.

**Estimand** — the precise quantity the study seeks to learn.

**Terminal outcome** — success, failure, timeout, or cancellation.

**Service time** — time spent receiving service from a specified component.

**Queue wait** — time between entering a queue and beginning service.

**Censoring** — incomplete observation of the event time of interest, for example when a run ends at a timeout.

**Markov assumption** — the claim that the next state depends on the current state and not on the earlier history.

**Semi-Markov process** — a process with state transitions and random holding times that may depend on the transition.
