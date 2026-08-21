---
name: turn-up-time
description: Root control plane for software work. Classifies the task, resolves human-owned ambiguity, selects discovery depth, maintains the project ledger, dispatches roles, enforces stage transitions, and tracks spawn budget. Does not research, architect, implement, or certify release.
disable-model-invocation: false
---

# /turn-up-time

Adopt this skill in the root session for software build, design, fix, refactor, or automation work.

## Boundaries

You coordinate. You do not conduct specialist research, author the architecture, implement production
code, or certify your own project.

## Step 1 — Reconcile current state

Inspect repository root, branch, dirty state, recent relevant commits, existing implementation,
active project ledger, and any approved parent artifact. Separate `OBSERVED`, `VERIFIED`, `INFERRED`,
`PROPOSED`, and `UNKNOWN`.

## Step 2 — Classify

- Tier A: read-only answer.
- Tier B: bounded change with known shape.
- Tier C: new capability, material product fork, or coordination is a work product.

Risk selects assurance; file count does not select the tier.

If a Tier B task discovers a design fork, adopt Tier C in place. Preserve current work, freeze further
writes, create a bootstrap receipt, and later disposition existing work as `KEEP`, `ADAPT`, or
`REPLACE`.

## Step 3 — Intake readiness

Create or update `intake-readiness.yaml`. Resolve from repo/conversation where possible. Invoke
`/grill-me` only for human-owned unknowns:

```text
primary user
primary job/outcome
product boundary
what users may do
material data/risk choice
non-goals
```

After six questions, summarize remaining forks and ask whether to continue, defer, or block.

## Step 4 — Profile and ledger

For Tier C create the project workspace:

```text
.claude/projects/<project-id>/
  project-ledger.json
  intake-readiness.yaml
  evidence/
  definition-of-good.yaml
  architecture.md
  traceability.yaml
  tickets/
  receipts/
  integration/
  closeout/
  release/
```

The root session is the designated ledger writer. Then choose:

- lite: `product-domain-researcher` + `combined-engineering-researcher` + `premise-auditor`;
- standard: 5;
- full: 6–8, with every additional role justified.

Record the proposed budget. The human may veto it. If the projected Tier C project uses fewer than three independent spawns, reconsider whether Tier B is sufficient.

## Step 5 — Discovery

Standard profile dispatches in parallel:

- `product-domain-researcher`
- `frontend-experience-researcher`
- `backend-systems-researcher`
- `security-privacy-researcher`

Then dispatch `premise-auditor` serially. Discovery may loop only on specific `UNKNOWN` or
`CONFLICTED` MUST items. A silent MUST-level unknown produces `EVIDENCE_BLOCKED`. Proceed only on
`EVIDENCE_READY` or a human-approved explicit risk recorded in the ledger.

## Step 6 — Definition and tickets

Invoke `/omnidex` with the Intake Card, evidence packs, premise verdict, and current-state receipts.
Stop for human approval on material business forks and before build.

## Step 7 — Seam check

Send approved tickets to `integration-lead`. No build begins before `SEAMS_SOUND`.

## Step 8 — Build and integrate

Invoke `/boil-the-ocean`. Dispatch independent tickets only. Prevent overlapping ownership. Track
spawns by department and ticket. The same acceptance failure after two materially different repairs
returns to OmniDex or the architect.

After assembly, run the Integration Lead again. Two failed repair waves force architecture escalation.

## Step 9 — Closeout and release

Run `/easily-irritated` at the selected mode, then `/production-audit`. Invoke
`/guard-before-write` for deployment or other irreversible actions. Record build identity and release
receipt.

## Step 10 — Workflow improvement

Run `/its-not-you-its-me` or append candidates to the improvement queue. No candidate changes the
workflow without human approval and a seeded eval.

## Resume contract

The ledger is authoritative after compaction or a new session. Re-read it, compare repo/build identity,
and rerun only affected premises. Conversation memory never silently overrides ledger state.
