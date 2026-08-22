---
name: its-not-you-its-me
description: Project workflow closeout. Collects rework and process evidence, identifies the earliest stage that should have prevented it, researches established remedies, proposes the smallest reversible change with a seeded-failure eval, and requires human approval before any workflow mutation.
disable-model-invocation: true
---

# /its-not-you-its-me

Improve the workflow that produced the product. Do not duplicate Easily Irritated's product audit.

## Inputs

Collect from:

- human corrections and abandoned approaches;
- discovery gaps and invalid sources;
- ticket rewrites, scope churn, and repeated acceptance failures;
- integration seam defects;
- closeout and final-judge findings;
- runtime/release incidents;
- wasted spawns, permission friction, provider conflicts, and controls that never fired;
- project ledger timing, stage receipts, and budget usage.

Observation and continuous-learning systems may nominate candidates. They are evidence collectors, not
policy writers.

## Loop

1. **Collect** candidate evidence linked to project/build/stage.
2. **Validate** a workflow defect versus product defect, one-off noise, or operator choice.
3. **Locate** the earliest stage that could have prevented or cheaply detected it.
4. **Research** established remedies, counterevidence, and applicability.
5. **Propose** the smallest reversible change using `improvement-proposal.schema.json`.
6. **Human decides:** approve, reject, defer, or project-only pilot.
7. **Implement** an approved change as its own Turn Up Time project/ticket.
8. **Seed and run** the original failure; require RED-before and GREEN-after.
9. **Measure** quality benefit, spawn/time cost, false positives, and new failure modes.
10. **Promote or retire** at the review date.

## Promotion policy

A project-level pilot may follow one credible incident. A global change requires either a high-severity
incident or recurrence across more than one project, a named root cause, external/practice evidence,
seeded eval, expected effect, ceremony cost, new risks, rollback, human approval, and review date.

No proposal changes `CLAUDE.md`, core skills, hooks, schemas, or registry automatically.

## Outputs

- schema-valid proposals under `.claude/improvement-queue/` or project `improvements/`;
- dispositions for every candidate;
- `NO_WORKFLOW_CHANGE_PROPOSED` when evidence does not justify a change;
- measured pilot/eval result and promotion/retirement decision.

## Stop and escalate

Stop when evidence is insufficient, the remedy is broader than the observed failure, or no measurement
can distinguish improvement from added ceremony. Ask the human rather than auto-promoting.

## Boundaries

Do not rewrite product code, retroactively change a project's success contract, or treat every reviewer
complaint as a workflow defect. The workflow improves by evidence, not accumulation.
