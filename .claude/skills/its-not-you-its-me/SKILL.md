---
name: its-not-you-its-me
description: Project workflow closeout. Collects rework and process evidence, identifies where the workflow should have prevented it, researches established remedies, proposes a bounded reversible change with a seeded-failure eval, and asks the human to approve, reject, defer, or pilot it. Never edits the upstream workflow automatically.
disable-model-invocation: true
---

# /its-not-you-its-me

Improve the workflow that produced the product. Do not duplicate Easily Irritated's product audit.

## Sources

Collect candidates from human corrections, discovery gaps, ticket churn, integration defects, judge
REDs, EI findings, runtime incidents, wasted spawns, repeated permissions, skill conflicts, and controls
that never fired.

## Loop

1. **Collect** candidate evidence.
2. **Validate** recurring process defect versus one-off noise.
3. **Locate** the earliest stage that should have prevented it.
4. **Research** established remedies and counterevidence.
5. **Propose** the smallest reversible workflow change.
6. **Human decides:** approve, reject, defer, or project-only pilot.
7. **Implement** approved change as its own ticket.
8. **Seed and run** the original failure as an eval.
9. **Promote or retire** based on measured benefit and ceremony cost.

## Promotion gate

A global workflow change requires a high-severity incident or recurrence across more than one project,
a named root cause, seeded-failure eval, expected benefit, cost, new risks, rollback, human approval,
and a review date.

Observation or continuous-learning systems may nominate candidates only. They are not policy writers.

Store proposals under `.claude/improvement-queue/` using `improvement-proposal.schema.json`.
