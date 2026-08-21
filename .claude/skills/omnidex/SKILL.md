---
name: omnidex
description: Evidence compiler and ticket factory. Consumes approved discovery packs and current-state receipts, produces one Definition of Good, a coherent architecture, a traceability matrix, and executable tickets. It does not conduct discovery, build code, or converge by multi-round consensus.
disable-model-invocation: true
---

# /omnidex

## Inputs

- ratified Intake Readiness Card;
- current-state receipts;
- approved product, frontend, backend, and security evidence packs;
- Premise Auditor verdict;
- project ledger and constraints.

If evidence is not ready, stop. Do not fill gaps with first-principles confidence.

## 1. Compile the Definition of Good

For every requirement record:

```text
id
source/evidence
priority: MUST|SHOULD|OPTIONAL
acceptance condition
verification method
owner surface
```

A requirement may use a number only when the number is meaningful and sourced or measured.

## 2. Architecture

Dispatch the read-only `architect`. It proposes one coherent architecture and shows how each MUST is
satisfied. Product, scope, permission, cost, and risk forks go to the human. Technical coherence stays
with the architect.

## 3. Tickets

Create one ticket per coherent work package using `ticket.schema.json`. Every ticket must carry:

- requirement IDs and evidence references;
- user outcome;
- scope and explicit non-scope;
- inputs, outputs, dependencies, and shared contracts;
- required capabilities;
- deterministic and/or experiential acceptance checks;
- risk, rollback, and owner role.

Builders never receive the original vague prompt as their work order.

## 4. Traceability

Prove:

- every MUST maps to one or more tickets or an explicit human gate;
- every ticket maps back to approved requirements;
- security requirements have owners;
- frontend states have backend ownership;
- no unresolved decision is disguised as an implementation ticket.

## 5. Revision limit

Run one premise/traceability review. Repair once. If the same defect survives, stop and reframe the
architecture or evidence; do not begin a debate loop.

## Outputs

```text
definition-of-good.yaml
architecture.md
traceability.yaml
tickets/*.yaml
```

Set ledger stage to `TICKETS_AWAITING_HUMAN_APPROVAL`. Build begins only after approval and
`SEAMS_SOUND` from the Integration Lead.
