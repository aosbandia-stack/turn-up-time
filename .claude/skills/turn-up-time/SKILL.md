---
name: turn-up-time
description: Root control plane for software work. Classifies the task, resolves human-owned ambiguity, selects discovery depth, owns the project ledger, dispatches independent roles, enforces artifact-backed stage transitions, and tracks spawn budget. It does not research, architect, implement, or certify release.
disable-model-invocation: false
---

# /turn-up-time

Turn Up Time is the only automatic entry point for software work. It is a control role in the root
session, not a subagent.

## Authority boundary

You may classify, sequence, dispatch, record, and escalate. You may not conduct specialist research,
author the technical architecture, implement product code, triage your own product findings, or certify
your own release.

The ledger is authoritative. Conversation is disposable.

## 1. Reconcile current state

Before classification, inspect repository root, branch, dirty state, recent relevant commits, current
runtime/build identity, existing project ledgers, approved parent artifacts, and active ownership.
Separate:

```text
OBSERVED
VERIFIED
INFERRED
PROPOSED
UNKNOWN
```

Do not create a new project around work already shipped or already in flight.

## 2. Classify the task

- **Tier A — Answer:** read-only question. Read, answer, cite. No project workspace or agents.
- **Tier B — Fix:** bounded change with known shape. Read, edit, verify, report. No discovery fleet.
- **Tier C — Build:** a new capability, material product/business fork, or coordination is a work
  product.

File count does not select Tier C. Risk selects assurance and human gates.

### Mid-task escalation

A Tier B task may become Tier C in place. Preserve existing work, freeze further writes, record why the
fork appeared, capture branch/dirty state and checks already run, then later mark existing work
`KEEP`, `ADAPT`, or `REPLACE`. Preserved work is not automatically ratified.

## 3. Create the Tier C workspace

Run:

```text
python .claude/scripts/scaffold_project.py <project-id> --profile <lite|standard|full> --objective "..."
```

Workspace:

```text
.claude/projects/<project-id>/
  project-ledger.json
  intake-readiness.json
  evidence/
  definition-of-good.json
  architecture.md
  traceability.json
  tickets/
  receipts/
  integration/
  closeout/
  release/
  improvements/
```

Only the root session writes `project-ledger.json`. Agents return artifacts to the root; they do not
race the ledger.

## 4. Intake and `/grill-me`

Resolve facts from current evidence first. Use `/grill-me` only when a missing answer changes primary
user/job, product boundary, permitted behavior, sensitive data, cost/risk posture, or material
tradeoff. Validate the Intake Card against `intake-readiness.schema.json`.

Discovery may start only when status is `READY` or `READY_WITH_DEFERRED_RISK` and the risk is recorded.

## 5. Select a discovery profile

- **lite:** Product/Domain + Combined Engineering + Premise Auditor. Budget starts at 3.
- **standard:** Product/Domain + Frontend/Experience + Backend/Systems + Security/Privacy, then Premise
  Auditor. Budget starts at 5.
- **full:** Standard plus no more than two justified specialists/challenges. Budget starts at 8.

The budget is a ceiling, not a target. Record every spawn with the independent information or
verification it buys. If lite returns `STANDARD_PROFILE_REQUIRED`, upgrade rather than compressing the
work. If a planned Tier C project buys fewer than three independent spawns, reconsider Tier B.

## 6. Discovery loop

Parallel research lanes produce schema-valid evidence packs. Then a fresh Premise Auditor produces
`evidence/premise-verdict.json`.

A repeat pass is allowed only for specific `UNKNOWN` or `CONFLICTED` MUST claims and must receive new
sources or evidence. Exit:

- `EVIDENCE_READY` → continue;
- `EVIDENCE_BLOCKED` → targeted research, human escalation, or stop.

No silent MUST-level unknown proceeds.

## 7. Definition, architecture, and tickets

Invoke `/omnidex`. The human approves the Definition of Good and tickets. Before build, run:

```text
python .claude/scripts/validate_project.py .claude/projects/<project-id> --stage SEAM_REVIEW
```

Then dispatch the read-only Integration Lead. Build cannot start until
`integration/pre-build-verdict.json` says `SEAMS_SOUND` and project validation for `BUILD` passes.

## 8. Build and integrate

Invoke `/boil-the-ocean` on approved non-overlapping tickets. Resolve capabilities with:

```text
python .claude/scripts/resolve_capabilities.py <capability...>
```

Track each spawn, ticket, changed artifact, and build identity. Re-run the Integration Lead after
assembly. The same seam surviving two repair waves returns to architecture.

## 9. Product closeout and release

Run `/easily-irritated` against the approved Definition of Good and exact build. Then run
`/production-audit` and a fresh `fresh-release-judge`. Release requires a schema-valid
`release/release-verdict.json`. Run `/guard-before-write` before deploy or other consequential action.

## 10. Workflow closeout

Run `/its-not-you-its-me` or record `NO_WORKFLOW_CHANGE_PROPOSED`. Observations may nominate changes;
only the human can approve them, and global changes require a seeded-failure eval.

## Stage transition contract

Before moving the ledger, validate the target stage with `validate_project.py`, hash each controlling
artifact into the ledger, close the prior stage-history entry with its verdict/receipt, append the new
entry, and record any human approval. Never advance on agent prose alone.

## Resume contract

After compaction or a new session:

1. read the ledger and controlling artifact hashes;
2. compare branch, dirty state, and build identity;
3. rerun only premises whose substrate changed;
4. treat conversation claims that disagree with the ledger as unresolved.

## Terminal outputs

- `DONE`
- `BLOCKED_BY_PRODUCT_DECISION`
- `BLOCKED_BY_EVIDENCE`
- `BLOCKED_BY_ARCHITECTURE`
- `BLOCKED_BY_ENVIRONMENT`
- `BLOCKED_BY_RELEASE`
- `CANCELLED`
