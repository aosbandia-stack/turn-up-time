---
name: boil-the-ocean
description: Ticket execution engine. Resolves approved ticket capabilities, assigns non-overlapping work packages to implementation agents, runs ticket-local checks until evidence is green, and hands assembled work to integration. It does not research, redefine scope, or certify release.
disable-model-invocation: true
---

# /boil-the-ocean

Boil the ocean you were handed: complete depth inside the approved ticket, no horizontal scope
invention.

## Precondition

Require:

- human-approved tickets;
- `SEAMS_SOUND`;
- named build identity;
- clean or explicitly preserved working state;
- capability registry resolution with no conflicts (project registry first, then user registry).

## Dispatch

One implementation engineer per independent work package. Do not assign overlapping files or a shared
writer concurrently. Sequential dependencies remain sequential. Parallelism is secondary to clear
ownership.

## Ticket loop

1. Read the ticket, acceptance checks, contracts, and required capabilities.
2. Load only the minimum registered providers.
3. Implement the complete ticket, including errors and edge states inside scope.
4. Run deterministic checks and any required live/browser check.
5. Record the deciding evidence, changed files, and build identity.
6. Repair failures.

The same acceptance failure after two materially different repairs is not an invitation to keep
trying. Return `TICKET_OR_ARCHITECTURE_ESCALATION` with evidence.

## Scope control

Work discovered outside the ticket is recorded as a finding. Do not silently add it. A missing piece
inside the approved outcome is not optional; escalate it to the PM for ticket repair.

## Completion

A builder may return:

- `TICKET_EVIDENCE_GREEN`
- `BLOCKED_BY_DEPENDENCY`
- `BLOCKED_BY_DECISION`
- `TICKET_OR_ARCHITECTURE_ESCALATION`

The builder never sets release-ready or verified status.

After assembly, send the integrated result to the read-only Integration Lead. Integration repair gets
at most two waves before returning to OmniDex.
