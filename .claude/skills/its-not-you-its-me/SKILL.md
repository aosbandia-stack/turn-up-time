---
name: its-not-you-its-me
description: Project workflow closeout. Collects rework and process evidence, identifies where the workflow should have prevented it, researches established remedies, proposes a bounded reversible change with a seeded-failure eval, and asks the human to approve, reject, defer, or pilot it. Never edits the upstream workflow automatically.
disable-model-invocation: true
---

# /its-not-you-its-me

Improve the workflow that produced the product. Do not duplicate Easily Irritated's product audit.
Observation systems nominate evidence; they are not policy writers.

## Inputs

Collect from the completed project's ledger and artifacts:

- human corrections and product misunderstandings;
- discovery gaps and premise blockers;
- ticket churn, scope changes, capability failures, and repair attempts;
- integration defects and repeated seams;
- judge REDs, EI findings, runtime incidents, and rollback events;
- wasted or missing spawns, permissions friction, skill conflicts, and controls that never fired;
- elapsed time and evidence of downstream rework where available.

## Improvement loop

1. **Collect:** create candidate observations; do not call them failures yet.
2. **Validate:** separate recurring process defect, high-severity incident, product-specific exception,
   and noise.
3. **Locate:** identify the earliest stage that should have prevented or exposed the issue.
4. **Research:** find applicable established remedies and counterevidence. Do not invent a control from
   the same failure story alone.
5. **Propose:** write the smallest reversible change, expected effect, cost, new risks, rollback, and
   review date.
6. **Seed:** define an eval that is RED before the control and GREEN after it, plus a negative control.
7. **Human decision:** approve, reject, defer, or authorize a project-only pilot.
8. **Implement:** approved change becomes its own Turn Up Time ticket; never patch the constitution as a
   side effect of closeout.
9. **Evaluate:** measure whether the control catches the failure without unacceptable ceremony.
10. **Promote or retire:** global promotion requires the human and a GREEN eval; remove predictions that
    do not prove useful by their review date.

## Artifact contract

Write each proposal under `.claude/improvement-queue/` or the project's `closeout/` directory as JSON
conforming to `improvement-proposal.schema.json`. Use these states only:

```text
OBSERVED → VALIDATED → RESEARCHED → PROPOSED → APPROVED/REJECTED/DEFERRED
→ IMPLEMENTED → EVAL_GREEN/EVAL_RED → RETIRED
```

Record evidence references, root cause, intervention stage, seeded eval, cost, new risk, rollback,
warrant (`incident` or `prediction`), human approval, and review date.

## Promotion gate

A global workflow change requires:

- one high-severity incident or recurrence across more than one project;
- a specific process root cause and earliest intervention stage;
- evidence that an existing control did not already cover it;
- researched remedy and counterevidence;
- seeded-failure and control evals;
- measurable expected benefit and ceremony cost;
- human approval and rollback;
- post-pilot review.

After writing proposals, run `validate_repo.py` for workflow changes and `validate_project.py` for the
project record. No candidate changes the upstream workflow automatically.
