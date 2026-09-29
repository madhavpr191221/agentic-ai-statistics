# Feature: Research constitution and workflow

## Overview

Establish the scientific and engineering rules that govern this repository before any agent implementation or data collection.

## Research question

What principles and review gates are required to study agent executions as stochastic computational systems without turning the project into framework-driven coding?

## Requirements

- The repository MUST define the complete run as the primary experimental unit.
- The repository MUST distinguish measured, derived, associative, causal, predictive, and unavailable quantities.
- The repository MUST require an estimand before an experiment or analysis is implemented.
- The repository MUST prohibit unsupported Markov and queueing claims.
- The repository MUST require uncertainty and limitations in reported results.
- The repository MUST require deterministic replay before live model campaigns.
- The repository MUST support public synthetic or anonymized data without proprietary dependencies.
- The repository MUST require a specification, plan, tests, and validation record for each feature.
- The workflow SHOULD keep each implementation slice small enough for human review.
- The workflow MAY use a UI as an inspection surface when it improves understanding.

## Design

The constitution is expressed in `CONSTITUTION.md`. Persistent agent instructions are expressed in `AGENTS.md`. Research definitions are separated into objective, glossary, and statistical-principles documents. Later features will have their own specification, execution plan, and validation record.

## Acceptance criteria

- A reader can identify the research objective and initial workload.
- A reader can identify the experimental unit and primary random objects.
- A reader can distinguish a campaign from a run and a feature from an analysis.
- A reader can identify the non-goals and measurement limitations.
- The workflow defines review points before implementation and after validation.
- The documents state that nested events are not independent replicates.

## Non-claims

This feature does not define an event schema, implement an agent, collect traces, fit a stochastic model, or establish any empirical result.

## Cost and safety

This feature is documentation-only and must not invoke a model provider or spend API credits.
