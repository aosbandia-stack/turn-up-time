---
name: turn-up-time
description: Root control plane for software work. Classifies the task, resolves human-owned ambiguity, selects discovery depth, maintains the project ledger, dispatches roles, enforces stage transitions, and tracks spawn budget. Does not research, architect, implement, or certify release.
disable-model-invocation: false
---

# /turn-up-time

Adopt this skill in the root session for software build, design, implementation, automation, refactor,
or fix work. It is the only automatic entry point into the conveyor.

## Control-plane boundaries

The root session coordinates, records, and escalates. It does not conduct specialist research, author
the architecture, implement production code, validate its own findings, or certify release.

The project ledger is authoritative. Agents return structured results to the root; the root is the only
ledger writer.

## 1. Reconcile current state

Before classifying:

- identify repository root, branch, HEAD, dirty state, active work, and runtime/build identity;
- inspect existing implementation, tests, plans, and relevant recent commits;
- locate an active `.claude/projects/<project-id>/project-ledger.json`;
- separate `OBSERVED`, `VERIFIED`, `INFERRED`, `PROPOSED`, and `UNKNOWN`.

A summary or conversation cannot overrule current code, runtime, or the ledger.

## 2. Classify the task

- **Tier A — Answer:** read and answer. No project workspace or agents.
- **Tier B — Fix:** bounded change whose shape is known. Read, edit, verify, report. No discovery panel,
  OmniDex, or Easily Irritated by default.
- **Tier C — Build:** new capability, material product fork, or coordination is itself a work product.

File count does not decide the tier. Risk selects assurance and human gates.

When Tier B reveals a material fork, adopt Tier C in place. Preserve current work, freeze further
writes, record the escalation, and later disposition existing work as `KEEP`, `ADAPT`, or `REPLACE`.

## 3. Create the Tier C workspace

Run:

```text
python .claude/scripts/scaffold_project.py <project-id> --profile <lite|standard|full> --objective "<objective>"
```

This creates the authoritative ledger, intake card, and stage directories. Immediately run:

```text
python .claude/scripts/validate_project.py <project-id>
```

Do not create placeholder evidence, tickets, or verdicts before their stage begins.

## 4. Intake and conditional grilling

Resolve `intake-readiness.json` from current evidence and the conversation. Invoke `/grill-me` only for
human-owned unknowns:

- primary user and job;
- desired outcome and product boundary;
- what users are permitted to do;
- sensitive data, external/model egress, cost, or risk choice;
- non-goals and materially different product interpretations.

Advance only when the card validates and its status is `INTAKE_READY` or
`INTAKE_READY_WITH_DEFERRED_RISK`:

```text
python .claude/scripts/advance_stage.py <project-id> --to DISCOVERY
```

## 5. Select a discovery profile and budget

- **Lite:** `product-domain-researcher`, `combined-engineering-researcher`, then
  `premise-auditor`. Budget 3.
- **Standard:** `product-domain-researcher`, `frontend-experience-researcher`,
  `backend-systems-researcher`, `security-privacy-researcher`, then `premise-auditor`. Budget 5.
- **Full:** Standard plus no more than three justified specialists or architecture challenges. Default
  ceiling 8.

A spawn must buy independent evidence or independent verification. Record role, stage, reason,
start time, and result in the ledger. If the lite engineer returns `STANDARD_PROFILE_REQUIRED`, update
the profile and budget before continuing.

## 6. Discovery and premise audit

Run the independent research lanes in parallel. The root writes their returned JSON to:

```text
evidence/product.json
evidence/engineering.json        # lite only
evidence/frontend.json           # standard/full
evidence/backend.json            # standard/full
evidence/security.json            # standard/full
```

Every pack must validate against `evidence-pack.schema.json`. Research loops only on named UNKNOWN or
CONFLICTED MUST items and only when a new source, probe, or human decision is available.

Then dispatch `premise-auditor` cold. Write its `stage-verdict.schema.json` output to
`evidence/premise-verdict.json`. Advance through `EVIDENCE_REVIEW` to `DEFINITION` only on
`EVIDENCE_READY` or a human-approved, explicitly recorded deferred risk.

Hash durable artifacts with:

```text
python .claude/scripts/record_artifact.py <project-id> <name> <relative-path>
```

## 7. Definition, architecture, and tickets

Invoke `/omnidex` with the ratified intake, current-state receipts, evidence packs, premise verdict,
and ledger. OmniDex writes:

```text
definition-of-good.json
architecture.md
traceability.json
tickets/*.json
```

The human approves product/risk forks, the Definition of Good, and executable tickets. OmniDex then
sets ledger stage `TICKETING`, status `AWAITING_HUMAN`; after approval, use `advance_stage.py` to enter
`SEAM_REVIEW`.

## 8. Seam review, build, and integration

Dispatch `integration-lead` against the approved tickets. The root writes
`integration/prebuild-verdict.json`. Build does not begin before `SEAMS_SOUND`.

Invoke `/boil-the-ocean`. Before each ticket, resolve capabilities through
`resolve_capabilities.py`. Prevent overlapping ownership and track every spawn. After all tickets are
`TICKET_EVIDENCE_GREEN`, advance to `INTEGRATION`, assemble the candidate, and dispatch the Integration
Lead again. Write `integration/postbuild-verdict.json`.

The same ticket failure after two materially different repairs, or the same seam after two repair
waves, returns to OmniDex/architecture rather than looping.

## 9. Product closeout and release

On postbuild `SEAMS_SOUND`, advance to `CLOSEOUT` and invoke `/easily-irritated`. It writes validated
findings and `closeout/verdict.json`.

On `RELEASE_READY` or human-accepted yellow, advance to `RELEASE` and invoke `/production-audit`.
Release requires:

- `release/production-audit.json`;
- a cold `fresh-release-judge` verdict at `release/final-judge.json`;
- `/guard-before-write` before deployment or another consequential action;
- `release/receipt.json` with exact build identity and result.

## 10. Workflow closeout

Run `/its-not-you-its-me` or explicitly record why no workflow closeout is warranted. Improvement
candidates never modify the constitution automatically.

## Resume contract

After compaction or a new session, read the ledger first, compare repository/build identity and artifact
hashes, run `validate_project.py`, and refresh only premises whose substrate changed. Conversation
memory never silently overrides project state.
