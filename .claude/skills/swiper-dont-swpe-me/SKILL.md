---
name: swiper-dont-swpe-me
description: Bounded repository cleanup and IT handoff inside Turn Up Time CLOSEOUT, after final product repairs and before release judgment. Preserves behavior, proves dependency and external caller safety before removal, and refreshes evidence after changes. Use for a repository cleanup or the final maintainability pass.
disable-model-invocation: false
argument-hint: 'project="<id>" scope=changed|full'
---

# /swiper-dont-swpe-me

Make the approved product easier to understand and maintain. This is a control procedure inside the
existing CLOSEOUT stage, not another architecture, product audit, or release authority. Turn Up Time
must read this installed `SKILL.md` before use and retain its path/hash in cleanup evidence. A slash
mention, installed directory, or recorded event does not prove that instructions were loaded.
`cleanup.instruction` binds the known source/installed path and SHA-256 to a `cleanup-instructions`
verification receipt on the baseline build. Capture the read instruction bytes in its hashed outputs.
The validator resolves the source from its own installed root, never an arbitrary claimed path.
Matching bytes prove snapshot integrity, not model cognition or truthful tool invocation.

## Entry and scope

Require the approved Definition of Good, ticket ownership, exact integrated build, completed product
repairs, current POST_BUILD seam verdict, and rollback. Default to the changed files and their affected
callers. `scope=full` inventories the whole repository only when the user requested that scope. For a
standalone cleanup, route through Turn Up Time and choose the smallest valid tier before edits.

## Inventory before removal

For each candidate record its purpose, owner, and disposition: `KEEP`, `REMOVE`, `CONSOLIDATE`, or
`INVESTIGATE`. Check references, imports, dynamic discovery, build/package manifests, CI, deployment,
scheduled jobs, external callers and operator instructions. Search absence alone does not prove a file
unused. Ask the system owner about callers outside the checkout; unknown callers mean KEEP or
INVESTIGATE. Age, a PowerShell extension, low coverage, and a desired file count are never deletion
proof. Preserve generated/vendor boundaries and required root manifests.

For PowerShell inspect dot-sourcing, module exports, scope, parameter/return contracts, task scheduler,
remote execution, execution policy and supported PowerShell versions. Pin applicable analyzer/Pester
checks to the project. Avoid accidental script-to-module or language migrations.

## Bounded change and proof

1. Capture the exact baseline, behavior checks and recoverable version or backup.
2. Batch mechanical cleanup by one reason; separate behavior changes into new tickets.
3. Dispatch the existing implementation owner for authorized file changes. Use `/guard-before-write`
   before removal or another consequential action. Every REMOVE or CONSOLIDATE records an action-bound
   `guard_ref` on the baseline and `execution_ref` on the resulting build. Both receipts name the exact
   path and decision in `cleanup_action`. The guard includes PROCEED and required, named, time-stamped
   human approval in `guard`; NOT_REQUIRED cannot waive destructive authority. Its hashed outputs
   retain all six guard checks. Approval and guard must precede the action. Existing scoped user
   authorization may supply that approval; do not invent it. Auditors do not repair their own findings.
4. Keep one canonical implementation or document, stable entry points, explicit generated/temporary
   locations, and links from existing navigation. Avoid a new checklist document for each finding.
5. Verify the changed build independently: affected acceptance checks, callers, integration, journeys,
   visual/keyboard checks when applicable, then cleanup proof. Changed build identity invalidates old
   proof. A later repair repeats the affected proof and cleanup before fresh release judgment.
6. Give IT the actual entry points, layout, setup/run/test commands, configuration ownership, deployment
   and rollback path, known limitations, and maintenance owner. Check that instructions work from a
   clean checkout. Reuse README/runbooks; do not duplicate them into another report tree.

## Output and stop

Extend `closeout/terminal-state.json` using `terminal-state.schema.json`. Its `cleanup` records scope,
baseline/current build, actions with dependency and external-caller proof, rollback, evidence receipts,
reproof and handoff reference. Receipts follow `verification-receipt.schema.json` and hash the actual
outputs. `NO_CHANGE` is a valid evidence-backed result. `CHANGED` requires a new build identity and
fresh reproof. Every INVESTIGATE or UNKNOWN dependency/caller action supplies `risk_ref` matching an
entry in the existing `open_risks`; its action owner remains responsible. Release validation carries
those risks into explicit accepted-risk approval. Known KEEP and NO_CHANGE need no removal guard.

Receipt IDs are `cleanup-instructions`, `cleanup-guard:<path>` and `cleanup-execution:<path>`. Guard
receipts add `guard: {verdict, authority_required, authority_status, by, at}`. Both action receipts add
`cleanup_action: {path, decision}`. These extend the existing verification receipt, not another report
tree. Retain actual captured outputs and refresh affected proof when the candidate changes.

Do not claim release approval or deployment. Stop at a behavior fork, uncertain destructive action,
missing evidence, or the existing two-repair ceiling. The same terminal packet gains `completion`
proof only after the requested candidate or deployment outcome is actually verified.
