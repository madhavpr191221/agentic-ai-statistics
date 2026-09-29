# Working with ChatGPT and Codex

This project deliberately separates understanding from implementation.

The aim is not to let an AI coding agent silently invent a research project. The human should understand the statistical object, the assumptions, and the interpretation before code is written.

## ChatGPT: thinking, learning, and research design

Use ChatGPT primarily for questions such as:

- What is the right mathematical object?
- What is random in this experiment?
- What is the experimental unit?
- What is the estimand?
- Which assumptions are required?
- Is a proposed quantity identifiable?
- Is an observed relationship associative or causal?
- Is a Markov, semi-Markov, survival, queueing, or simulation model justified?
- What uncertainty method is appropriate?
- How should a result be interpreted in plain language?
- What are the threats to validity?
- What should be learned from a textbook before implementation?

ChatGPT should help produce:

- explanations of probability and statistics;
- notation and derivations;
- examples and counterexamples;
- research questions;
- estimands;
- assumptions;
- model-comparison arguments;
- experiment designs;
- specification drafts;
- interpretation of results;
- limitations and future questions.

ChatGPT should not be used to hide an unexamined decision behind a large code generation request.

## Codex: repository execution and evidence

Use Codex primarily for tasks that change or validate the repository:

- create or update specification files;
- implement an approved feature;
- write tests derived from acceptance criteria;
- create deterministic fixtures and replay data;
- modify schemas and typed interfaces;
- build the API, CLI, or UI;
- run tests, type checks, lint, and builds;
- inspect actual failures;
- produce validation records;
- update implementation documentation;
- create commits and push approved changes.

Codex should not decide the scientific meaning of a metric silently. If implementation exposes an ambiguity, Codex should stop at the feature boundary, describe the discovery, and update the specification or ask for a decision.

## The collaboration loop

```text
ChatGPT: understand the question
    ↓
ChatGPT: define the statistical object and estimand
    ↓
ChatGPT + human: review the specification
    ↓
Codex: create the execution plan
    ↓
Codex: implement one bounded feature
    ↓
Codex: test and demonstrate it
    ↓
ChatGPT + human: interpret evidence and limitations
    ↓
Update the specification if needed
```

## What a good request looks like

### Learning request to ChatGPT

> Explain the difference between an event sequence, a Markov chain, and a semi-Markov process using our agent-run example. Do not write code. State the assumptions and show where each model could fail.

### Design request to ChatGPT

> Draft the estimand and acceptance criteria for measuring time to terminal success or failure. Include censoring and non-claims.

### Implementation request to Codex

> Implement `SPEC-001-observable-run-event-schema.md`. Read the constitution first. Do not add stochastic models or live provider calls. Derive tests from every MUST requirement and stop after validation.

### Interpretation request after implementation

> Here is the validation record and the observed data. Explain what we learned, what we did not learn, and whether the next feature is justified.

## The boundary in one sentence

ChatGPT helps us decide what the system means; Codex makes the approved meaning executable and testable.

Both roles require human review. The human owns the research question, scientific judgment, and final interpretation.

## Current next step

The next bounded feature is `SPEC-001-observable-run-event-schema.md`. Before asking Codex to implement it, use ChatGPT to understand:

- what an event is;
- what a state is;
- whether state and event should be separate in the first schema;
- which timestamps are needed;
- which fields are necessary for later statistical analysis;
- which quantities should explicitly be unavailable.
