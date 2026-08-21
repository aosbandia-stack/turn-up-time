---
name: omnidex
description: Evidence compiler and ticket factory. Consumes approved discovery packs and current-state receipts, produces one Definition of Good, a coherent architecture, a traceability matrix, and executable tickets. It does not conduct discovery, build code, or converge by multi-round consensus.
disable-model-invocation: true
---

# /omnidex

OmniDex begins only after the Premise Auditor returns `EVIDENCE_READY` or the human explicitly accepts
a named deferred risk.

## Inputs

- validated `intake-readiness.json`;
- current-state receipts and artifact hashes;
- validated product, frontend/backend or lite engineering, and security evidence packs;
- `evidence/premise-verdict.json`;
- authoritative project ledger;
- existing architecture and tickets when this is a revision.

If any required artifact is missing, stale, or invalid, return `DEFINITION_BLOCKED`. Do not fill a gap
with first-principles confidence.

## 1. Compile `definition-of-good.json`

Validate against `definition-of-good.schema.json`. Each requirement contains:

- stable ID and statement;
- MUST, SHOULD, or OPTIONAL;
- evidence references;
- observable acceptance condition;
- verification method;
- owner surface and lifecycle status.

Use a numeric threshold only when a source or measured baseline makes it meaningful. Preserve human
gates and non-goals. Record source artifact SHA-256 values.

## 2. Dispatch the architect

Give the read-only `architect` the validated evidence, draft Definition of Good, current-state receipts,
and constraints. The architect returns one coherent design, requirement mapping, interfaces, failure
behavior, operations, alternatives, risks, and human-owned forks.

The human decides product scope, permissions, cost, sensitive-data handling, and risk posture. The
architect decides technical coherence within the ratified boundary. OmniDex records the result; it
does not break the tie itself.

Write the approved technical result to `architecture.md`.

## 3. Build `traceability.json`

Trace:

- every active MUST to architecture elements, ticket IDs, or an explicit human gate;
- every ticket back to requirements and evidence;
- frontend states to backend/data ownership;
- security requirements to implementation and verification owners;
- shared contracts to every ticket that reads or changes them.

A missing owner or unresolved decision is a blocker, not a ticket.

## 4. Create executable tickets

Write one coherent work package per `tickets/<ticket-id>.json`, validating each against
`ticket.schema.json`. Tickets must include requirement/evidence references, user outcome, scope,
non-scope, files/surfaces, inputs, outputs, dependencies, shared contracts, acceptance checks,
capabilities, risk, rollback, owner, and human gates.

Builders never receive the original vague prompt as their work order. `required_capabilities` names
capabilities, not skill files.

## 5. Review and approval

Run one independent traceability/decomposition review. Repair once. If the same defect survives, return
`DEFINITION_REFRAME_REQUIRED`; do not start another consensus round.

Before build:

1. validate the project and every artifact;
2. set `definition-of-good.json` status to `AWAITING_HUMAN`;
3. set ledger stage `TICKETING`, status `AWAITING_HUMAN`;
4. present product/risk forks, Definition of Good, architecture, and tickets to the human;
5. after approval, set Definition status and ticket statuses to `APPROVED` and record the approval;
6. use `advance_stage.py` to enter `SEAM_REVIEW`.

`TICKETS_AWAITING_HUMAN_APPROVAL` is not a valid ledger stage and must never be written.

## Outputs

```text
definition-of-good.json
architecture.md
traceability.json
tickets/*.json
```

Hash and record each artifact with `record_artifact.py`. The next owner is the read-only Integration
Lead, not a builder.
