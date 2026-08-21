---
name: grill-me
description: Resolve only human-owned product ambiguity before discovery. Ask one decision at a time, recommend a path and its tradeoff, record the answer in the Intake Readiness Card, and stop when the card is ready, deferred with risk, or blocked.
disable-model-invocation: true
---

# /grill-me

This is an intake control, not a general interview ritual.

## Preconditions

Turn Up Time has already inspected the repository/conversation and identified a required answer that
cannot be resolved by current-state evidence or research.

## Human-owned questions

Use only when the answer changes:

- primary user, job, or product boundary;
- what users may do;
- sensitive data or external/model egress;
- cost/risk posture;
- irreversible behavior;
- a material tradeoff among different product outcomes.

Do not ask about framework choice, current code, official standards, or facts research can establish.

## Loop

1. Name the unresolved field and why it is load-bearing.
2. Ask exactly one question.
3. Give a recommended answer, the strongest alternative, and the consequence of each.
4. Record the human answer in `intake-readiness.json` and the decision in the project ledger.
5. Validate the Intake Card.
6. Repeat only while a required human-owned decision remains open.

After six questions in one intake, summarize remaining forks and ask the human to continue, defer with
named risk, or block. Do not exhaust the human into arbitrary answers.

## Exit

- `INTAKE_READY`
- `INTAKE_READY_WITH_DEFERRED_RISK`
- `BLOCKED_BY_PRODUCT_DECISION`

## Boundaries

Do not conduct discovery, choose architecture, write code, or silently answer the human's side of a
fork. A deferred risk must be visible in both intake and ledger.
