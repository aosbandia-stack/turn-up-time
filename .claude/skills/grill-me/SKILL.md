---
name: grill-me
description: Resolve human-owned product ambiguity before research. Ask one decision at a time, recommend an answer, and stop when the Intake Readiness Card is complete, explicitly deferred, or blocked. Do not ask questions the repository or research can answer.
disable-model-invocation: true
---

# /grill-me

Use only from `/turn-up-time` or by explicit user request.

## Input

Read `.claude/projects/<project-id>/intake-readiness.json`, the current repository evidence, and the
conversation. Validate the card against `intake-readiness.schema.json` before asking anything.

## Human-owned unknowns

Ask only when the answer changes:

- primary user or job;
- desired user outcome or product boundary;
- permitted behavior;
- sensitive data, external/model egress, cost, or risk posture;
- a material tradeoff among different products;
- an explicit non-goal.

Do not ask about framework selection, current code, official standards, existing behavior, or facts that
research can resolve.

## Question loop

1. Name the unresolved decision ID and explain why it changes the project.
2. Ask exactly one question.
3. Offer a recommended answer grounded in known evidence and explain the consequence of alternatives.
4. Record the answer in `human_owned_decisions` with owner `human`, status, and decision.
5. Update the relevant intake field and validate the JSON.
6. Continue only while a required human-owned field remains unresolved.

After six questions in one intake, summarize remaining forks and ask whether to continue, defer with
risk, or block. Do not turn the cap into an automatic default choice.

## Exit contract

- `INTAKE_READY`: every required product field is resolved and no human decision remains OPEN/BLOCKED.
- `INTAKE_READY_WITH_DEFERRED_RISK`: all required fields are present and every deferred decision has a
  named risk accepted by the human.
- `BLOCKED_BY_PRODUCT_DECISION`: a material human decision is still unresolved.

The root session writes the validated card and records it in the project ledger. `/grill-me` does not
advance stages itself.
