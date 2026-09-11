---
name: boil-the-ocean
description: Ticket execution engine. Resolves approved capabilities, dispatches implementations only after runtime budget reservation, collects build evidence, assembles the build, and returns it to independent Integration Lead. It does not redefine scope or certify release.
disable-model-invocation: true
---

# /boil-the-ocean

Complete vertical depth inside approved tickets, without horizontal scope invention.

## Preconditions and capability resolution

Require approved Definition of Good and tickets, PRE_BUILD SEAMS_SOUND, target-stage validation,
clean or explicitly preserved worktree state, a named worktree/branch, rollback, and resolved human
gates. Resolve capabilities deterministically. Unknown/conflicted/missing required providers block;
missing optional providers route to `/plug-it-in`, not silent substitution. Load only selected modes.

## Dispatch and accounting

Prefer one capable builder when work does not genuinely divide. Otherwise assign one implementation
engineer to each independent nonoverlapping package. Dependencies stay sequential; shared files need
one writer. Reserve each spawn with the runtime's `reserve_spawn` operation BEFORE dispatch. A failed
reservation means no worker starts. Do not edit the project ledger or increase its ceiling yourself.

After real completion, use `complete_spawn` with SUCCEEDED, FAILED, CANCELLED, TIMED_OUT, or
INTERRUPTED and actual artifact references. Failed or interrupted work still consumed the reservation.
These operations record accounting; they do not launch, isolate, or supervise a worker. The selected
execution backend must provide those functions. Do not claim a worktree is a security sandbox.

## Ticket loop

1. Recheck current state, approved ownership, and acceptance criteria.
2. Implement the entire approved ticket, including in-scope errors and recovery.
3. Run targeted checks and collect raw deciding outputs and changed-file manifests.
4. Have an independent verifier evaluate the acceptance contract, not just the builder's summary.
5. Repair concrete failures and reverify. Two materially different repairs failing the same check
   produce TICKET_OR_ARCHITECTURE_ESCALATION.

A builder's test output is evidence, not independent certification. Every EVIDENCE_GREEN acceptance
ID needs exactly one structured PASS, evaluator_role assurance, evaluator_id, build_identity,
evidence_ref, and the actual evidence file SHA-256. No empty results, null acceptance evidence,
free-text 'passed', duplicate checks, or obsolete build identity qualifies.

## Scope and assembly

Missing work inside the approved outcome returns for ticket repair; adjacent scope becomes a finding.
New dependencies, protected files, destructive actions, external effects, and architecture changes
remain gates. `/guard-before-write` governs consequential operations.

Assemble one build, then use runtime `set_build_identity`. Re-run each ticket's acceptance against
that assembled identity; per-worker green results do not automatically prove the combined build.
Register receipts through `record_artifact`. Dispatch the read-only Integration Lead for POST_BUILD
SEAMS_SOUND. Route findings to the original owner with the original brief, diff, finding, and checks.
At most two integration repair waves; the same seam afterward produces ARCHITECTURE_ESCALATION.

Outputs: schema-valid tickets and structured build receipts, exact assembled identity, changed-file
and dependency manifests, POST_BUILD verdict, and runtime-recorded build-stage evidence.

Builders never independently mark VERIFIED, SEAMS_SOUND, RELEASE_READY, GREEN, or SHIP. Boil does not
research broadly, invent scope, rewrite the Definition of Good, or provide final product/release judgment.
