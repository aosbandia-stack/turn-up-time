# Turn Up Time

**An evidence-to-ship engineering gauntlet for Claude Code.**

Turn Up Time is a compact software-delivery workflow designed to make agents define the right product
earlier, repair less later, and improve the workflow only when evidence justifies it. It replaces a
large collection of overlapping routers, planning rituals, reviewer loops, and style skills with one
control plane, versioned artifacts, bounded loops, and a plug-in capability registry.

```text
/turn-up-time
      ↓
Discovery Gauntlet
      ↓
/omnidex
      ↓
Integration Lead
      ↓
/boil-the-ocean
      ↓
/easily-irritated
      ↓
/production-audit + fresh release judge + release guard
      ↓
/its-not-you-its-me
```

## Operating rule

> **Loop where evidence changes. Gate where authority changes. Stop where the same failure repeats.
> Never loop merely because another agent is available.**

A repeat pass must receive at least one of:

- new evidence;
- a changed artifact;
- a fresh independent evaluator;
- a human decision resolving a real fork.

Re-reading the same prompt with the same evidence is rumination, not loop engineering.

## What ships

- **10 skills**: 9 user-facing workflow/control skills plus the internal Eval Harness.
- **17 role-specific agents**, with assurance roles mechanically read-only.
- **9 machine-readable schemas** for the registry, intake, evidence, Definition of Good, tickets,
  project state, findings, stage verdicts, and workflow improvements.
- **8 runtime/review scripts** for scaffolding, stage validation/advancement, artifact receipts,
  capability resolution, repository validation, seeded evals, and cold review.
- One prompt router that sends software work to `/turn-up-time` instead of competing workflows.
- A capability registry for plug-and-play providers such as Impeccable, E2E Testing, and AI regression
  testing without making them always-loaded dependencies.
- A dry-run-first installer, backup/restore manifest, modified-file-safe uninstaller, notification
  preservation, auto-accept compatibility, and deterministic destructive-command guard.
- Linux and Windows PowerShell 5.1 validation in GitHub Actions.

## Three task shapes

| Tier | Shape | Process |
|---|---|---|
| **A — Answer** | Lookup, explanation, read-only question | Read, answer, cite. No workflow. |
| **B — Fix** | Bounded change whose shape is known | Read, edit, verify, report. No discovery fan-out. |
| **C — Build** | New capability, material product fork, or coordination is work | Full conveyor, sized lite/standard/full. |

File count does not determine the tier. Risk selects assurance and human gates. Coordination and
unresolved product design select Tier C.

## Discovery profiles

| Profile | Use | Independent roles |
|---|---|---|
| **Lite** | Small, genuinely compressible capability | Product/Domain + Combined Engineering + Premise Auditor |
| **Standard** | New app or significant feature | Product/Domain + Frontend/Experience + Backend/Systems + Security/Privacy + Premise Auditor |
| **Full** | Novel, high-risk, enterprise, regulated | Standard + up to three justified specialists/challenges |

The spawn budget is a ceiling, not a target. Each spawn must buy independent information or
verification.

## Quick start

Clone the repository, then install validator dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

Run the repository checks:

```powershell
python .claude/scripts/validate_repo.py
python .claude/scripts/run_seeded_evals.py
python .claude/scripts/fresh_review.py
```

Preview global installation:

```powershell
./scripts/install.ps1
```

When `~/.claude/CLAUDE.md` already exists, installation requires an explicit choice:

```powershell
./scripts/install.ps1 -Apply -ReplaceGlobalConstitution
# or
./scripts/install.ps1 -Apply -KeepGlobalConstitution
```

To preserve the conveniences Harold values:

```powershell
./scripts/install.ps1 `
  -Apply `
  -ReplaceGlobalConstitution `
  -EnableNotifications `
  -EnableAutoAccept
```

The installer backs up conflicts, merges hook rows instead of replacing settings, registers both the
single router and destructive-command guard, preserves an existing notification provider, records
installed hashes, and writes an exact uninstall manifest.

## Core commands

- `/turn-up-time` — root control plane and stage manager.
- `/omnidex` — compiles approved evidence into the Definition of Good, architecture, traceability, and
  executable tickets.
- `/boil-the-ocean` — resolves capabilities and executes approved tickets completely.
- `/easily-irritated` — independent product friction, consistency, repair, and journey closeout.
- `/production-audit` — operational readiness followed by a separate fresh release judge.
- `/its-not-you-its-me` — workflow self-improvement with human approval and seeded evals.

Conditional support:

- `/grill-me` — resolves only human-owned ambiguity.
- `/guard-before-write` — reversibility/accountability gate for consequential actions.
- `/plug-it-in` — places new skill providers safely and removably.

## Project state

Create a Tier C workspace:

```powershell
python .claude/scripts/scaffold_project.py my-project --profile standard --objective "Build ..."
```

Validate it at any point:

```powershell
python .claude/scripts/validate_project.py my-project
```

Stage changes are validated and atomic:

```powershell
python .claude/scripts/advance_stage.py my-project --to DISCOVERY
```

The project ledger and artifact hashes outrank conversation memory. Builders never receive the vague
original prompt as their ticket.

## Capability providers

Tickets request capabilities such as `frontend-operate` or `browser-e2e`. The deterministic resolver
checks project overrides, user defaults, provider installation, allowed stages, and conflicts:

```powershell
python .claude/scripts/resolve_capabilities.py frontend-operate browser-e2e --stage BUILD
```

A missing or conflicting provider blocks execution and routes through `/plug-it-in`; there is no silent
fallback.

See [the architecture](docs/ARCHITECTURE.md), [installation guide](docs/INSTALL.md), and
[review report](docs/REVIEW-REPORT.md).
