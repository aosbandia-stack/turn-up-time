---
name: grill-me
description: Resolve human-owned product ambiguity before research. Ask one decision at a time, recommend an answer, and stop when the Intake Readiness Card is complete, deferred, or blocked. Do not ask questions the repository or research can answer.
disable-model-invocation: true
---

# /grill-me

## Use only for human-owned unknowns

Ask when the answer changes product scope, intended user, permitted behavior, accepted risk, sensitive
data, or a material product tradeoff.

Do not ask about facts the codebase, official documentation, or external research can resolve.

## Method

1. State the unresolved field and why it changes the project.
2. Ask exactly one question.
3. Offer a recommended answer and the consequence of alternatives.
4. Record the human answer in `intake-readiness.yaml`.
5. Continue only while a required human-owned field remains unresolved.

After six questions in one intake, summarize remaining ambiguity and ask whether to continue, defer,
or block.

## Exit

- `INTAKE_READY`
- `INTAKE_READY_WITH_DEFERRED_RISK`
- `BLOCKED_BY_PRODUCT_DECISION`
