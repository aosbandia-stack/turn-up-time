---
name: turn-up-time
description: Root control plane for software work. Classifies the task, resolves human-owned ambiguity, selects discovery depth, coordinates runtime-owned ledger operations, dispatches independent roles, and enforces evidence-backed stage transitions. It does not research, architect, implement, or certify release.
disable-model-invocation: false
---

# /turn-up-time

Turn Up Time is the only automatic entry point for software work. It is a control role in the root
session, not a subagent. Classify, sequence, dispatch, record through the runtime, and escalate.
Do not conduct specialist research, author architecture, implement, or certify your own release.

## Reconcile and classify

Inspect repository root, branch, dirty state, relevant commits, runtime/build identity, existing
project ledgers, approved artifacts, and active ownership. Separate OBSERVED, VERIFIED, INFERRED,
PROPOSED, and UNKNOWN. Do not create a new project around work already shipped or in flight.

- **Tier A — Answer:** read, answer, cite. No project workspace or agents.
- **Tier B — Fix:** bounded known change. Read, edit, verify, report. No discovery fleet.
- **Tier C — Build:** a new capability, material product/business fork, or coordination as a work product.

File count and a desired minimum number of spawns do not classify the task. Uncertainty, risk, and
real dependencies do. Preserve in-flight work when Tier B escalates; freeze further writes, capture
checks/dirty state, and later mark the work KEEP, ADAPT, or REPLACE. It is not automatically approved.

## Scaffold and intake

For a new Tier C project, use `scaffold_project.py` with project ID, profile, objective, and a planned
whole-project spawn ceiling. The ceiling includes discovery, build, assurance, and repair work; it
is not a target. Do not overwrite an initialized project to reset it.

Workspace: `.claude/projects/<project-id>/` with intake, evidence, Definition of Good, architecture,
traceability, tickets, receipts, integration, closeout, release, improvements, and project ledger.
Only the runtime writes an initialized ledger. Agents return artifacts to the root, never racing state.

Resolve facts from evidence before asking questions. `/grill-me` is only for human-owned ambiguity
that changes the user/job, product boundary, permitted behavior, data, cost/risk, or material tradeoff.
Validate intake. Discovery starts at READY or READY_WITH_DEFERRED_RISK with recorded risk and the
signed intake approval. A supplied approver name is not authorization.

## Discovery and definition

Choose the smallest appropriate independent discovery profile:

- lite: Product/Domain + Combined Engineering, then Premise Auditor;
- standard: Product/Domain + Frontend/Experience + Backend/Systems + Security/Privacy, then Premise Auditor;
- full: standard plus at most two justified specialists/challenges.

A profile is coverage, not a reason to consume a budget. STANDARD_PROFILE_REQUIRED upgrades lite
when needed. Each spawn must buy independent evidence or verification. Reserve budget through the
runtime before dispatch and record its actual completion outcome afterward.

Research produces schema-valid packs. A fresh Premise Auditor returns EVIDENCE_READY or
EVIDENCE_BLOCKED. Repeats target named UNKNOWN/CONFLICTED MUST claims and require new evidence.
Invoke `/omnidex` for the Definition of Good, architecture, and executable tickets. The human signs
the corresponding approval requests. Run stage validation, then the read-only Integration Lead;
BUILD requires PRE_BUILD SEAMS_SOUND.

## Build, verify, and release

Invoke `/boil-the-ocean` on approved nonoverlapping tickets. Resolve each capability using
`resolve_capabilities.py`; missing providers block or route to `/plug-it-in`. Prefer one capable
builder when work does not genuinely divide. Keep independent verification.

Record the assembled build through `set_build_identity`. Every required acceptance check must have
an independent structured PASS, exact build identity, and a real content-addressed evidence file.
Recheck the assembled build with Integration Lead. The same seam after two repair waves escalates.

Run `/easily-irritated`, then `/production-audit` and a fresh release judge. Require a parsed
release-compatible closeout packet and separate audit/judge packets tied to the same build. Signed
release approval does not itself run deployment. `/guard-before-write` still governs consequences.
Close workflow through `/its-not-you-its-me` or record NO_WORKFLOW_CHANGE_PROPOSED. Global changes
need human approval and seeded evaluation.

## Runtime contract

Use the installed `turn-up-time-graph` CLI or PowerShell wrapper. Every signal has a stable event ID.
Never hash artifacts into the ledger yourself, append stage-history rows, or type an approval into it.

Metadata operations use `signal --event record_artifact|reserve_spawn|complete_spawn|set_build_identity`
with `--data-file` (project-relative JSON, recommended for PowerShell) or `--data-json`. They do not
advance a stage. After metadata/artifacts are complete, use `request-approval` for a gated transition;
the owner signs outside worker authority. Submit the matching `signal` with `--approval-ref`.

The runtime validates prerequisites, verifies the signature, locks the project, persists the intent,
and updates ledger, events, and checkpoint. Missing validators fail closed. Repeat an interrupted
operation with its SAME event ID and payload; use `recover` when required. Do not manufacture a new
ID to evade a failed check. `status` and `history` expose the current state and audit trail.

After compaction or a new session, inspect ledger, artifact hashes, checkpoint, branch, dirty state,
and build identity. Rerun only premises whose substrate changed. Unrecorded drift stops work;
conversation memory cannot overrule current code, approved artifacts, or the ledger.

The source repository's `docs/HARDENING.md` specifies payloads, signature provisioning, evidence
formats, and migration. A trust file editable by the worker is not an authority boundary. TUT is not
yet a worker supervisor or OS sandbox; do not claim work continues merely because a graph exists.

Terminal outputs: DONE, BLOCKED_BY_PRODUCT_DECISION, BLOCKED_BY_EVIDENCE,
BLOCKED_BY_ARCHITECTURE, BLOCKED_BY_ENVIRONMENT, BLOCKED_BY_RELEASE, CANCELLED.
