---
name: omnidex
description: Evidence compiler and ticket factory. Consumes approved intake, audited discovery evidence, and current-state receipts; produces the Definition of Good, one coherent architecture, traceability, and executable tickets. It does not conduct discovery, build code, or converge through a multi-round opinion panel.
disable-model-invocation: true
---

# /omnidex

OmniDex begins only after `EVIDENCE_READY`. Its job is compilation, architecture handoff, and ticket
quality—not research theater.

## Preconditions

Require:

- `intake-readiness.json` with READY status;
- all profile-required evidence packs;
- `evidence/premise-verdict.json` with `EVIDENCE_READY`;
- current-state receipts and ledger artifact hashes;
- no unresolved human-owned decision required by a MUST.

## 1. Compile `definition-of-good.json`

For every requirement record:

```text
id
statement
priority: MUST | SHOULD | OPTIONAL
evidence_refs
acceptance: type + check + expected
owner_surface
ticket_ids
```

Also preserve critical journeys, non-goals, and human gates. A number is used only when sourced or
measured and meaningful. Otherwise use an observable check, calibrated rubric, or human gate.

The human approves the Definition of Good before architecture is treated as final.

## 2. Dispatch the Architect

The read-only Architect receives the approved Definition of Good, evidence, constraints, and current
system. It returns `architecture.md` and `ARCHITECTURE_READY` or `ARCHITECTURE_BLOCKED`.

Human owns product scope, permitted behavior, sensitive data, cost, risk posture, and material product
tradeoffs. Architect owns technical coherence inside those boundaries. Turn Up Time records decisions;
it cannot overrule either authority.

## 3. Produce `traceability.json`

Prove:

- every MUST maps to design and at least one ticket or explicit human gate;
- every ticket maps to approved requirements and evidence;
- every critical journey has frontend, backend, test, and recovery ownership where applicable;
- every security/privacy requirement has an owner and proof;
- no unresolved decision is disguised as implementation.

## 4. Produce executable tickets

Each `tickets/<ticket-id>.json` must validate against `ticket.schema.json` and declare requirement/evidence
refs, user outcome, scope/non-scope, inputs/outputs, dependencies, shared contracts, owned/shared files,
acceptance checks, capabilities, risk, rollback, and production owner.

Builders receive the ticket and controlling artifacts, not the original vague prompt or OmniDex
conversation.

## 5. Ticket approval and seam review

The human approves tickets. Then the read-only Integration Lead performs PRE_BUILD review and writes
`integration/pre-build-verdict.json`.

No build begins until:

```text
Definition of Good: APPROVED
Tickets: APPROVED
Traceability: complete
Pre-build seam verdict: SEAMS_SOUND
validate_project.py --stage BUILD: GREEN
```

## Revision loop

One premise/traceability/seam repair pass is allowed because it receives a concrete finding. If the
same structural defect survives, return `OMNIDEX_REFRAME_REQUIRED`; do not restart multi-round consensus.

## Outputs

- `definition-of-good.json`
- `architecture.md`
- `traceability.json`
- `tickets/*.json`
- `integration/pre-build-verdict.json`
- ledger artifact hashes, approvals, and stage receipt

## Boundaries

Do not research broadly, implement code, run product closeout, or certify release. Do not force
consensus when the correct result is a human fork or architecture block.
