---
name: easily-irritated
description: Bounded independent product closeout. Tests the assembled build against the approved Definition of Good and critical journeys, validates friction with evidence, routes repairs to separate engineers, verifies tickets independently, and returns an explicit product-closeout verdict.
disable-model-invocation: true
argument-hint: 'project="<id>" mode=lite|standard|full max_rounds=4 repairs=off|authorized'
---

# /easily-irritated

This stage checks whether the finished product consistently delivers the researched and approved
outcome. It does not discover a new product or reopen architecture because an auditor has a preference.

## Entry gate

Require:

- ledger stage `CLOSEOUT`;
- approved Definition of Good and critical journeys;
- all tickets `TICKET_EVIDENCE_GREEN`;
- `integration/postbuild-verdict.json` with `SEAMS_SOUND`;
- exact runnable build identity;
- safe test data, environment, known risks, and deferred human decisions.

Run `validate_project.py` before the first audit round.

## Audit profiles

- **Lite:** irritated domain user + functional QA; add UX/accessibility when a user interface changed.
- **Standard:** irritated domain user + functional QA + UX/accessibility reviewer; add security/performance
  when the approved contract or change surface warrants it.
- **Full:** Standard plus justified specialist lenses. Do not add a lens merely to spend the budget.

All auditors are fresh and read-only. They receive persona, journeys, Definition of Good, build
identity, and permitted evidence—not prior findings or engineer rationale before their first pass.

## Round contract

For each round up to `max_rounds`:

1. Run independent audit roles.
2. Collect raw candidate findings tied to requirements and journey steps.
3. Dispatch `triage-lead` after independent submissions are complete.
4. Validate, reject, deduplicate, classify, assign severity/owner, and write observable acceptance
   criteria using `finding.schema.json`.
5. If repairs are unauthorized, stop with `AUDIT_ONLY_COMPLETE`.
6. If authorized, assign each non-overlapping validated repair to a fresh `implementation-engineer`.
7. Dispatch a fresh `ticket-verifier` for every material repair. Builders cannot close their own
   findings.
8. Reassemble, record the new build identity, and rerun the locked critical journey with a fresh team.
9. Evaluate the stop contract.

A new round requires a changed build or genuinely new evidence. Repeating the same team against the
same artifact is not a valid loop.

## Finding and repair rules

- Only VALIDATED findings may enter repair.
- S0/S1 functional, safety, and workflow blockers precede craft.
- Business-rule, permission, data, architecture, and risk-policy questions go to the human.
- Visual polish begins only after critical journeys are stable. For dashboards and product interfaces,
  request capability `frontend-operate`; do not load marketing Taste rules.
- Visual polish uses one batched desktop/mobile pass and at most one confirmation pass.

Store round artifacts under `closeout/` and hash material outputs in the ledger.

## Stop contract

A materially clean round introduces no new validated S0, S1, or S2. S3/S4 findings remain visible and
must be dispositioned but do not automatically restart the full engineering loop.

Terminal states:

- `RELEASE_READY`
- `YELLOW_ACCEPTANCE_REQUIRED`
- `BLOCKED_BY_DECISION`
- `BLOCKED_BY_ENVIRONMENT`
- `MAX_ROUNDS_REACHED`
- `AUDIT_ONLY_COMPLETE`

Write `closeout/verdict.json` conforming to `stage-verdict.schema.json` with kind
`product-closeout`, exact build identity, evidence, blockers, accepted risks, reviewer, and timestamp.
Validated findings are stored as JSON records conforming to `finding.schema.json`.

## Handoff

Only `RELEASE_READY` or human-accepted `YELLOW_ACCEPTANCE_REQUIRED` may advance to RELEASE. The next
stage is `/production-audit`, which must test the same build identity. Easily Irritated does not deploy
or issue the final release judgment.
