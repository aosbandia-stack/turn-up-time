# Turn Up Time

**An evidence-to-ship engineering gauntlet for Claude Code.**

Turn Up Time is a compact software-delivery workflow designed to help agents build the right thing
earlier, repair less later, and improve the workflow only when evidence justifies it. It replaces
competing routers, planning rituals, reviewer loops, and overlapping style constitutions with one
control plane, explicit handoff artifacts, and plug-in capability providers.

```text
/turn-up-time
      ↓
Discovery Gauntlet
      ↓
Premise Auditor
      ↓
/omnidex + Architect
      ↓
Integration Lead (pre-build)
      ↓
/boil-the-ocean
      ↓
Integration Lead (post-build)
      ↓
/easily-irritated
      ↓
/production-audit + Fresh Release Judge
      ↓
/guard-before-write
      ↓
/its-not-you-its-me
```

## Operating rule

> **Loop where evidence changes. Gate where authority changes. Stop where the same failure repeats.
> Never loop merely because another agent is available.**

A repeat pass must receive new evidence, a changed artifact, a fresh independent evaluator, or a human
decision. Re-reading the same prompt with the same context is rumination.

## What ships

- **9 user-facing skills plus 1 internal eval provider**—one job each.
- **17 agents**, with every assurance role mechanically read-only.
- **11 JSON schemas** for intake, discovery, definition, tickets, ledger, findings, integration,
  release, capabilities, and workflow improvement.
- A single prompt router that sends software work to `/turn-up-time` rather than competing workflows.
- A schema-backed capability registry and deterministic resolver.
- Project scaffolding and stage-aware transition validation.
- Seeded process evals, a deterministic cold reviewer, and Linux/Windows CI.
- Dry-run-first installation, backups, notification preservation, exact install manifests, and
  modified-file-safe uninstall.

## Task tiers

| Tier | Shape | Process |
|---|---|---|
| **A — Answer** | Lookup, explanation, read-only question | Read, answer, cite. No workflow. |
| **B — Fix** | Bounded change whose shape is known | Read, edit, verify, report. No discovery fleet. |
| **C — Build** | New capability, material product fork, or coordination is work | Artifact-backed conveyor, sized lite/standard/full. |

File count does not decide the tier. Risk selects assurance and human gates.

## Discovery profiles

| Profile | Use | Independent roles |
|---|---|---|
| **Lite** | Small new capability | Product/Domain + Combined Engineering + Premise Auditor |
| **Standard** | New web app or significant feature | Product/Domain + Frontend/Experience + Backend/Systems + Security/Privacy + Premise Auditor |
| **Full** | Novel, high-risk, regulated, enterprise | Standard + up to two justified specialists/challenges |

A spawn budget is a ceiling, not a target. Each spawn must buy independent information or
verification. Lite self-escalates when compression is unsafe.

## Quick start

Clone the repository and validate the workflow:

```powershell
python .claude/scripts/validate_repo.py
python .claude/scripts/run_seeded_evals.py
python .claude/scripts/fresh_review.py
```

Preview installation:

```powershell
./scripts/install.ps1
```

Apply after reviewing the plan:

```powershell
./scripts/install.ps1 -Apply
```

Preserve and enable the workflow conveniences explicitly:

```powershell
./scripts/install.ps1 -Apply -EnableNotifications -EnableAutoAccept -ReplaceGlobalConstitution
```

The installer backs up conflicts, replaces only the old Turn Up Time/legacy skill-router registration,
preserves unrelated hooks/settings, and records hashes for safe uninstall.

## Run a Tier C project

```powershell
python .claude/scripts/scaffold_project.py budget-app --profile standard --objective "Build a household budgeting app"
python .claude/scripts/validate_project.py .claude/projects/budget-app --stage INTAKE
```

Turn Up Time advances the project only when the target-stage validator is green and the controlling
artifact hashes/verdict are recorded in the ledger.

Resolve an approved ticket's capabilities:

```powershell
python .claude/scripts/resolve_capabilities.py frontend-operate browser-e2e
```

Missing optional providers are reported; they are never silently substituted. Use `/plug-it-in` to
pilot or install one.

## Core commands

- `/turn-up-time` — control plane, ledger, stage transitions, and budget.
- `/omnidex` — evidence compiler, architecture handoff, traceability, and ticket factory.
- `/boil-the-ocean` — approved ticket execution and build receipts.
- `/easily-irritated` — independent product-friction closeout.
- `/production-audit` — operational release evidence.
- `/its-not-you-its-me` — evidence-based workflow improvement.

Conditional support:

- `/grill-me` — human-owned ambiguity only.
- `/guard-before-write` — reversibility/accountability gate.
- `/plug-it-in` — safe provider placement, pilot, and retirement.

## Source-of-truth order

1. Current repository/runtime evidence.
2. Active project ledger and artifact hashes.
3. Human-approved intake and Definition of Good.
4. Approved architecture, traceability, and tickets.
5. Evidence packs and stage receipts.
6. Handoffs and summaries.
7. Conversation memory.

A conversation cannot overrule the ledger. A summary cannot overrule the code.

## Optional providers

Large design/testing packages are not vendored. Tickets request capabilities such as
`frontend-operate`, `browser-e2e`, or `ai-regression`; the registry maps them to providers such as
Impeccable, E2E Testing, or AI Regression Testing after `/plug-it-in` evaluation.

For dashboards and product interfaces, `frontend-operate` uses Impeccable's `operate` mode. A
marketing-page Taste skill is not loaded by default.

See [Architecture](docs/ARCHITECTURE.md), [Installation](docs/INSTALL.md), and
[Skill decisions](docs/SKILL-DECISIONS.md).
