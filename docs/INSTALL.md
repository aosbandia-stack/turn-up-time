# Installation and removal

The repository runs project-scoped as cloned. The optional installer copies the canonical skills,
agents, hooks, capability registry, schemas, templates, profiles, evals, and runtime wrapper scripts to
`~/.claude/`. The LangGraph runtime is opt-in and is installed into its own virtual environment.

Turn Up Time's [BOT](../.claude/skills/turn-up-time/references/BOT.md),
[PERSONALITY](../.claude/skills/turn-up-time/references/PERSONALITY.md) and optional
[executive review example](../.claude/skills/turn-up-time/assets/executive-review.html) travel with the
skill through the existing recursive resource copy. They add communication guidance, not another
skill, runtime dependency or approval mechanism. Existing modified-file protection still applies.

The optional [provider routing reference](../.claude/skills/turn-up-time/references/PROVIDER-ROUTING.md)
also travels with the skill. Its pinned mappings do not copy/install upstream packages, enable hooks,
configure Bandia or launch scanners. Use `/plug-it-in` for a scoped provider pilot, inspect supporting
references and pins, and collect actual environment readiness/use proof for full audits. Source-only
audit and isolated target execution are different modes; a worktree is not an OS sandbox.

## Preview first

Dry-run is the default. The following command prints the complete plan without writing files:

```powershell
.\scripts\install.ps1 `
  -EnableNotifications `
  -ReplaceGlobalConstitution `
  -EnableGraphRuntime
```

## Apply the complete workflow

```powershell
.\scripts\install.ps1 `
  -Apply `
  -EnableNotifications `
  -ReplaceGlobalConstitution `
  -EnableGraphRuntime
```

Use a single line when copying through a system that may alter PowerShell backticks:

```powershell
.\scripts\install.ps1 -Apply -EnableNotifications -ReplaceGlobalConstitution -EnableGraphRuntime
```

The graph runtime requires Python 3.11 or newer. To select a specific interpreter:

```powershell
$env:TURN_UP_TIME_PYTHON = 'C:\path\to\python.exe'
```

Without `-EnableGraphRuntime`, the installer applies the skills, agents, router, schemas, and safety
controls but does not create the LangGraph virtual environment.

## What installation does

- backs up every conflicting target before replacement;
- records copied files as `created` or `overwritten` and records preserved conflicting providers;
- replaces any prior `skill-router.ps1` hook row with the single Turn Up Time router while preserving
  unrelated prompt hooks;
- replaces only the Turn Up Time destructive-command guard row;
- preserves an existing notification provider and adds the bundled fallback only when requested and
  absent;
- preserves existing permission deny rules;
- sets `permissions.defaultMode=acceptEdits` only when explicitly requested;
- records every installed file, its SHA-256, whether it preexisted, and its backup path;
- optionally creates an isolated virtual environment under
  `~/.claude/runtime/turn-up-time/`, installs the pinned runtime package, validates the executable
  topology, and records a runtime ownership marker;
- records targeted settings changes, graph-runtime ownership, and global-constitution replacement in
  `~/.claude/turn-up-time-install-manifest.json`.

`TURN_UP_TIME_CLAUDE_HOME` may point installation at a temporary directory for testing.

## Verify the installed workflow

From the source checkout:

```powershell
python .claude/scripts/validate_repo.py
python .claude/scripts/run_seeded_evals.py
python .claude/scripts/fresh_review.py
```

Verify the installed graph runtime:

```powershell
& "$HOME\.claude\scripts\turn-up-time-graph.ps1" validate-topology
```

A separate Claude Code model review can be run after installation:

```powershell
.\scripts\run-fresh-model-review.ps1
```

That command uses the read-only `fresh-workflow-reviewer`. It is intentionally separate from the
builder session and tells the reviewer to reproduce high-risk checks rather than trust a stored
report.

## Uninstall safely

Preview:

```powershell
.\scripts\uninstall.ps1
```

Apply:

```powershell
.\scripts\uninstall.ps1 -Apply
```

The uninstaller:

- removes or restores only files whose current hash still matches the installed hash;
- prints `SKIP MODIFIED` and preserves any file changed after installation;
- restores preexisting files from their exact backup;
- removes only Turn Up Time router, guard, and notification hook rows;
- restores the previous default permission mode only when it was not subsequently changed;
- restores the global constitution only when its current hash still matches the installed copy;
- removes or restores the owned graph virtual environment only when both its marker and installation
  hash still match;
- prints `SKIP MODIFIED GRAPH RUNTIME` rather than deleting a changed runtime;
- retains the manifest when modified artifacts were skipped so recovery information is not lost.

It never guesses ownership from a path name.

## Active project migration

This candidate changes Definition of Good to version 2 and capability registries to version 3. Do not
silently reinterpret an active project's old approvals. Pin the prior workflow for historical runs or
migrate a copy, retain the old records, and reapprove changed requirements/tickets through Turn Up Time.

1. Add the DoG's UI applicability/reason, execution environment, deployment scope and maintainability
   fields from the new example. For UI add one authoritative design reference, shared ownership,
   route states, desktop/mobile and keyboard expectations, and a first vertical journey. For non-UI
   declare actual command/integration proof; never invent UI or deployment work.
2. Create schema-valid traceability against real architecture headings, requirement/ticket IDs and
   acceptance check IDs. Link actual acceptance/journey receipts before INTEGRATION. POST_BUILD seams
   now require the exact reviewed build identity.
3. Add `provider_kind` to registry entries. Gather required external readiness probes in the declared
   project/environment, then record actual-use outputs separately. No missing selected provider may
   remain READY. Installation alone does not prove the bots used it.
4. After final product repair, load the installed Swiper instructions. Extend the existing closeout
   packet with cleanup, caller checks, rollback, handoff and current proof. `cleanup.instruction`
   records the known installed source path/hash and a baseline `cleanup-instructions` receipt with
   the captured bytes. It verifies integrity, not model cognition. Unknown callers/dependencies and
   INVESTIGATE actions link `risk_ref` to an existing `open_risks` entry, retaining the action owner.
   REMOVE/CONSOLIDATE actions require baseline `guard_ref` and resulting-build `execution_ref`, both
   bound to the exact path/decision through `cleanup_action`. The guard carries PROCEED and required
   APPROVED authority with `by`/`at`; capture its six checks as hashed outputs. Guard time must precede
   execution. Existing authorization is valid evidence; never fabricate approval or label it
   NOT_REQUIRED. Known KEEP/NO_CHANGE need no removal guard. Migrate legacy ad hoc packets with the
   consumed terminal/verification schemas and preserve historical findings.
5. Produce production-audit and final-judge packets with canonical `status` and their schema fields.
   Renaming a field alone does not recreate stale evidence or authorize release. Complete the same
   terminal packet's `completion` only for the scope actually verified.
6. Run `validate_project.py --stage <next-target>` and repair its named failures. Run repository,
   seeded and runtime tests before rollout. Preview installation and review the diff before applying.

Templates show shape, not evidence: replace placeholder hashes/builds/times with observed outputs.
The existing installer discovers the new skill and helper scripts; there is no second installation
path. Global installation and Windows provider wiring require validation in that actual environment.

UI contracts now also require `ui.surfaces` when UI is applicable: platform, purpose, stack, route
coverage, flags, change scope, research disposition and verification capabilities. Map all expanded
capabilities to approved tickets. Keep non-UI `surfaces: []` and `design_loop: null`; neither optional
21st nor an evaluator loop is required. Narrow refinements can use REUSE_GUIDE. For new/material
directions, place bounded comparable observations and their evidence/rationale in the existing design
guide; see [the UI contract](ARCHITECTURE.md#ui-surfaces-and-provider-flags) for the exact shape.

Project overrides must retain selector semantics and compatibility. Native work must name a real
external native assurance adapter. The 21st flags declare optional source mappings, not installed
tools: verify the actual provider, tool access, generation entitlement, stack adapter when needed,
and fresh project/environment probe before use; retain actual invocation/output receipts afterward.
Do not auto-install upstream hooks/binaries or invoke paid generation while migrating metadata.

Opt into `design_loop` only with approved anchors, hard gates, fixed guide/rubric hashes and shared
round/time/stagnation/optional cost budgets. Preserve failed historical evaluation receipts in the
existing terminal `round_history`, then record `design_stop_reason`. The final exact build must meet
every threshold. Ordinary UI closeout retains one batched pass plus confirmation. Reapprove changed
contracts; do not copy historical PASS labels into new receipts.

## Runtime hardening migration

This source integrates the durable runtime with Swiper's existing proof contracts. Read
[HARDENING.md](HARDENING.md) and [SECURITY-BOUNDARY.md](SECURITY-BOUNDARY.md) before upgrading an active
project. Preserve its ledger, event log, graph checkpoint and `.runtime/operations.sqlite` together.
The scaffold refuses to overwrite initialized state, even with `--force`.

The runtime alone writes initialized ledgers. Use metadata operations for artifacts, spawn reservation/
completion and derived assembled identity. Gated transitions require an expiring owner-signed
`--approval-ref`; a typed approver name is insufficient. Provision the trust file and signing key
through the trusted operator, outside worker authority. Installation supplies neither keys nor an OS
sandbox. Auto-accept remains an explicit optional flag.

Regenerate old string `check_results` from independent verification: one structured PASS per acceptance
ID, assurance evaluator identity, exact assembled build, evidence_ref and its SHA-256. That reference
must be the same schema-checked Swiper verification receipt referenced by the acceptance check, not
an alternate raw-output format. Existing Swiper instruction, risk, removal guard, cleanup, release and
completion requirements remain in force. Both project capability files are included in signed
manifests; changing either after approval requires a renewed signature.
