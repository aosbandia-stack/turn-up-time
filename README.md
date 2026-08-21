# Turn Up Time

**An evidence-to-ship engineering gauntlet for Claude Code.**

Turn Up Time is a small, explicit software-delivery workflow designed to make agents build the
right thing earlier, repair less later, and improve the workflow only when evidence justifies it.
It replaces a large collection of overlapping routers, planning rituals, reviewer loops, and style
skills with one conveyor belt and a plug-in capability registry.

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
/production-audit + release gate
      ↓
/its-not-you-its-me
```

## The operating rule

> **Loop where evidence changes. Gate where authority changes. Stop where the same failure
> repeats. Never loop merely because another agent is available.**

A pass is worth buying only when it receives at least one of:

- new evidence;
- a changed artifact;
- a fresh independent evaluator;
- a human decision that resolves a real fork.

Re-reading the same prompt with the same evidence is not loop engineering. It is rumination.

## What ships in this repository

- **9 user-facing skills plus 1 internal eval provider**, each with one job.
- **17 role-specific agents**, with assurance roles mechanically read-only.
- A **single prompt router** that points build work to `/turn-up-time` rather than fanning out
  competing workflows.
- A **capability registry** for plug-and-play specialist skills such as Impeccable and E2E testing.
- Machine-readable schemas for the project ledger, evidence packs, tickets, findings, and
  workflow-improvement proposals.
- Seeded process evals and a deterministic validator.
- A dry-run-first installer that preserves existing notifications and permission settings unless
  explicitly asked to change them.

## The three task shapes

| Tier | Shape | Process |
|---|---|---|
| **A — Answer** | Lookup, explanation, read-only question | Read, answer, cite. No workflow. |
| **B — Fix** | Bounded change whose shape is already known | Read, edit, verify, report. No discovery fan-out. |
| **C — Build** | New capability, material product fork, or coordination is itself work | Full conveyor, sized lite/standard/full. |

**File count does not decide the tier.** Risk selects assurance gates. Coordination and unresolved
product design select Tier C.

## Discovery profiles

| Profile | When | Independent roles |
|---|---|---|
| **Lite** | Small new capability | Product/Domain + combined engineering + Premise Auditor |
| **Standard** | New web app or significant feature | Product/Domain + Frontend/Experience + Backend/Systems + Security/Privacy + Premise Auditor |
| **Full** | Novel, high-risk, enterprise, regulated | Standard team + up to two justified specialists + architecture challenge |

The spawn budget is not a target. Each spawn must buy independent information or independent
verification.

## Quick start

1. Clone this repository.
2. Run the validator:

   ```powershell
   python .claude/scripts/validate_repo.py
   python .claude/scripts/run_seeded_evals.py
   ```

3. Preview installation:

   ```powershell
   ./scripts/install.ps1
   ```

4. Apply after reviewing the plan:

   ```powershell
   ./scripts/install.ps1 -Apply
   ```

The installer backs up conflicting files and merges hook registrations without deleting your
existing notification or permission hooks.

## Core commands

- `/turn-up-time` — control plane and stage manager.
- `/omnidex` — compiles approved evidence into architecture and executable tickets.
- `/boil-the-ocean` — executes approved tickets completely.
- `/easily-irritated` — independent product-friction and consistency closeout.
- `/production-audit` — release readiness and operational risk.
- `/its-not-you-its-me` — workflow self-improvement with human approval and seeded evals.

Conditional support:

- `/grill-me` — resolves only human-owned ambiguity.
- `/guard-before-write` — reversibility gate for destructive or externally consequential actions.
- `/plug-it-in` — safely places a new skill into the capability registry.

## Source-of-truth order

1. Current repository and runtime evidence.
2. The active project ledger.
3. Human-ratified intake and Definition of Good.
4. Approved architecture and tickets.
5. Recorded evidence packs and receipts.
6. Handoffs and summaries.
7. Conversation memory.

A conversation cannot overrule the ledger. A summary cannot overrule the code.

## Design choices

The repository intentionally does **not** vendor large design packages. Frontend tickets request
capabilities such as `frontend-operate` or `browser-e2e`; the registry maps those capabilities to
optional providers such as Impeccable and E2E Testing. `/plug-it-in` evaluates new providers,
conflicts, cost, placement, evals, and rollback before activation.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full role and stage contract.
