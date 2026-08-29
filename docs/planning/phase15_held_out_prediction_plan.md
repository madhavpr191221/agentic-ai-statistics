# Phase 15: Held-out trajectory prediction

Phase 15 asks whether observable agent behavior can be predicted on genuinely
new runs. The existing 100-run natural-policy campaign is training data. A new
60-run, same-configuration live campaign is the held-out test set, guarded at
`$3.00`.

We compare three fixed models:

1. global-majority successor;
2. add-one-smoothed current-state model,
   \(P(S_{t+1}\mid S_t)\);
3. add-one-smoothed short-history model,
   \(P(S_{t+1}\mid S_{t-1},S_t)\), falling back to model 2 for unseen contexts.

The primary metric is held-out run-level mean log loss. Accuracy and multiclass
Brier score are secondary. Transitions are nested inside runs, so scores are
calculated per run before aggregation. The result is a prediction assessment
under one frozen configuration, not a claim about private reasoning or agents
in general.

The UI reports the training/test campaigns, model definitions, denominators,
scores, and limitations. See the machine-readable contract in
`docs/specs/phase15_held_out_prediction_spec.md`.
