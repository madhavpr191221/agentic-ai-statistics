# UI guide

The UI is a small laboratory console, not a generic observability dashboard.

1. Select a controlled IT incident.
2. Choose deterministic mode for a no-cost measurement smoke test, or live mode for a real model execution.
3. Inspect the newest run as one observation: success, latency, call counts, cost, measured bytes, and ordered actions.
4. Read the timing decomposition and objective score. The decomposition is a measurement reconciliation, not a claim about hidden model computation.
5. Compare saved runs only after deciding what repeated-run question they answer.

The UI distinguishes:

- **Measured:** directly recorded at the application boundary.
- **Derived:** calculated from recorded fields, such as cost or an excess-action count.
- **Unavailable:** not supported by the current instrumentation, such as Internet packet sizes or queue waiting in a single-worker run.
