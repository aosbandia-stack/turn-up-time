---
name: boil-the-ocean
description: Ticket execution engine. Resolves approved ticket capabilities, assigns non-overlapping work packages to implementation agents, runs ticket-local checks until evidence is green, and hands the assembled result to integration. It does not research, redefine scope, or certify release.
disable-model-invocation: true
---

# /boil-the-ocean

Boil the ocean you were handed: complete depth inside the approved ticket, no horizontal scope
invention.

## Entry gate

Require all of the following:

- ledger stage `SEAM_REVIEW` or `BUILD` and a valid project workspace;
- approved Definition of Good, architecture, traceability, and tickets;
- `integration/prebuild-verdict.json` with `SEAMS_SOUND`;
- named repository and build identity;
- clean or explicitly preserved working state;
- no unresolved human gate for the ticket.

Run `validate_project.py` before dispatch. Advance to BUILD only through `advance_stage.py`.

## Capability resolution

For each ticket, run:

```text
python .claude/scripts/resolve_capabilities.py <capability...> --stage BUILD --project-root <repo-root>
```

Attach the `CAPABILITIES_READY` receipt to the worker brief. On `CAPABILITY_UNKNOWN`,
`CAPABILITY_CONFLICT`, `CAPABILITY_STAGE_MISMATCH`, or `CAPABILITY_PROVIDER_MISSING`, stop the ticket.
Route an uninstalled or unsuitable provider through `/plug-it-in`; never silently omit it or substitute a
similarly named skill.

## Dispatch

- One `implementation-engineer` per independent work package.
- Never assign overlapping files, data ownership, singleton writers, migrations, or shared high-risk
  surfaces concurrently.
- Respect ticket dependencies. Parallelism is secondary to independence and clear ownership.
- The worker receives the approved ticket, referenced requirements/evidence, shared contracts,
  capability receipt, current build identity, and rollback path—not the full orchestrator conversation.

## Ticket execution loop

The implementation engineer:

1. reads the actual files, callers, tests, and contracts;
2. sets ticket status to IN_PROGRESS through the root ledger writer;
3. implements the complete approved outcome, including applicable errors, states, observability, and
   rollback support;
4. runs every acceptance check and required live/browser verification;
5. records exact changed files, commands, decisive evidence, capability receipt, and build identity;
6. repairs concrete failures;
7. returns `TICKET_EVIDENCE_GREEN`, a named blocker, or escalation.

The same acceptance failure after two materially different repairs returns
`TICKET_OR_ARCHITECTURE_ESCALATION`. It does not receive a third speculative repair.

## Scope and mutation controls

Work outside the ticket becomes a finding. Missing work inside the approved user outcome returns to the
PM for ticket correction. Consequential, destructive, external, credential, production, or bulk-data
actions require `/guard-before-write` even when the ticket is approved.

## Ticket completion

The root validates the receipt, updates the ticket to `TICKET_EVIDENCE_GREEN`, records/hashes it, and
runs `validate_project.py`. Builders never set VERIFIED, integrated, release-ready, or deployed.

## Assembly and integration

After every ticket is evidence-green:

1. advance to INTEGRATION;
2. assemble the exact release candidate and record one build identity;
3. dispatch the read-only Integration Lead;
4. write `integration/postbuild-verdict.json`;
5. route `INT-nnn` repairs to the original work package owner.

Integration gets at most two repair waves. The same remaining seam returns to OmniDex/architecture.
Only postbuild `SEAMS_SOUND` may enter Easily Irritated.
