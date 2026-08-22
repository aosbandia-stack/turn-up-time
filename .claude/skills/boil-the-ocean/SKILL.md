---
name: boil-the-ocean
description: Ticket execution engine. Resolves approved capabilities, dispatches one implementation engineer per non-overlapping work package, runs ticket-local checks to evidence green, assembles the build, and returns it to Integration Lead. It does not research, redefine scope, or certify release.
disable-model-invocation: true
---

# /boil-the-ocean

Boil the ocean you were handed: complete vertical depth inside approved tickets, no horizontal scope
invention.

## Preconditions

Require:

- approved Definition of Good and tickets;
- current `SEAMS_SOUND` PRE_BUILD verdict;
- target stage validation GREEN;
- clean or explicitly preserved worktree state;
- named branch/worktree and rollback;
- no unresolved human gate required by the ticket.

## Resolve capabilities

For each ticket, run the deterministic resolver. A ticket does not start when a capability is unknown,
conflicted, or a required bundled provider is missing. Optional providers that are not installed are
reported to Turn Up Time and handled through `/plug-it-in`; they are not silently substituted.

Load only the selected providers and modes. Do not stack multiple frontend constitutions.

## Dispatch

- One `implementation-engineer` per independent ticket or explicitly grouped non-overlapping tickets.
- No concurrent ownership of the same `owned_files` entry or shared writer.
- Dependencies remain sequential.
- Parallelism is secondary to clear ownership and independent attention.
- Record each spawn against the ledger budget before dispatch.

If the execution plan projects fewer than two independent production packages, solo ticket execution
is preferred; do not create a fleet for ceremony.

## Ticket loop

1. Re-run current-state probes and confirm file ownership.
2. Implement the complete approved ticket, including in-scope errors and recovery.
3. Run every acceptance check and required live/browser proof.
4. Record build identity, changed files, deciding outputs, and rollback in the ticket receipt.
5. Repair concrete failures.

A repeat is justified only by a failing check and a changed implementation. The same check surviving
two materially different repairs produces `TICKET_OR_ARCHITECTURE_ESCALATION`.

## Scope and change control

- Missing work inside the approved user outcome is returned for ticket repair; it is not optional.
- Adjacent work outside scope becomes a finding and is not implemented.
- New dependencies, protected files, destructive actions, external side effects, or architecture
  changes are gates, not silent builder choices.
- `/guard-before-write` governs consequential operations.

## Assembly and integration

After all tickets are `EVIDENCE_GREEN`, assemble one build identity and dispatch the read-only
Integration Lead for POST_BUILD review. Integration findings return to the original ticket owner with
the original brief, diff, finding, and acceptance. Each repair is a full-cost production spawn.

At most two integration repair waves are permitted. The same seam after two waves produces
`ARCHITECTURE_ESCALATION`.

## Outputs

- updated schema-valid tickets with build receipts;
- one assembled build identity;
- changed-file and dependency manifest;
- `integration/post-build-verdict.json`;
- build-stage ledger receipt.

## Boundaries

Builders never mark VERIFIED, SEAMS_SOUND, RELEASE_READY, GREEN, or SHIP. Boil does not run broad
research, invent tickets, rewrite the Definition of Good, or perform final product/release judgment.
