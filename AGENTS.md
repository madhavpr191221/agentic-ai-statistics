# Research-engineering working agreement

This repository studies agentic AI systems as stochastic computational systems. It is not an agent-framework tutorial, chatbot, multi-agent demo, or superficial benchmark.

## Scientific rules

- Treat one fresh complete execution as the primary experimental unit.
- Do not treat events nested inside a run as independent replicates.
- State the estimand before collecting or analysing data.
- Distinguish measurement, derivation, association, and causal intervention.
- Do not assume a Markov process because transitions can be counted.
- Do not make queueing claims without measured arrivals, shared resources, and waiting.
- Report uncertainty, practical significance, assumptions, and limitations.
- Do not capture or infer private model reasoning.

## Spec-driven workflow

1. Read `CONSTITUTION.md` and the relevant research documents.
2. Create or revise a feature specification before implementation.
3. Define the statistical object, estimand, assumptions, acceptance criteria, and non-claims.
4. Create a small execution plan.
5. Derive tests from every normative requirement.
6. Implement only the approved feature.
7. Validate the implementation and the scientific interpretation.
8. Record discoveries and update the specification when reality contradicts it.
9. Stop at the feature boundary and review before starting the next feature.

Do not generate a large implementation from a broad roadmap. The human reviews the specification and validation record; the coding agent implements only the approved slice.
