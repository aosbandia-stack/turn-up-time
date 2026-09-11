# Turn Up Time

**An evidence-to-ship engineering gauntlet for Claude Code, governed by an executable LangGraph
control shell.**

> **Latest published release: Turn Up Time v1.0.0.** See the
> [release notes](docs/RELEASE-NOTES-v1.0.0.md),
> [release validation report](docs/GRAPH-REVIEW-REPORT.md), and
> [installation guide](docs/INSTALL.md).
>
> **Unreleased hardening:** signed approvals, runtime-owned bookkeeping, evidence integrity,
> and journal-backed recovery change the operational contract. Read
> [the migration guide](docs/HARDENING.md) before upgrading an active project.
> The v1.0.0 tag and existing local installations are not changed by this branch.

Turn Up Time aims to build the right thing earlier and repair less later. It replaces overlapping
routers, planning rituals, and reviewer loops with one conveyor, one project ledger, bounded loops,
and one legal business-stage topology.

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
/production-audit + fresh release judge + release gate
      ↓
/its-not-you-its-me
```

LangGraph controls transitions, human gates, loop ceilings, checkpoint recovery, and history.
Specialist skills and agents still do the engineering work. This is not a worker daemon or an
operating-system sandbox.

## Operating rule

> **Loop where evidence changes. Gate where authority changes. Stop where the same failure repeats.
> Never loop merely because another agent is available.**

A repeat must buy new evidence, changed artifacts, independent evaluation, or a human decision.
Re-reading the same prompt and evidence is rumination, not progress.

## What is included

- 9 user-facing skills plus 1 internal eval provider; 17 role-specific agent profiles.
- One prompt router and a capability registry for optional providers.
- Schema-backed project, evidence, ticket, finding, and release contracts.
- Semantic checks for acceptance coverage, evidence hashes, dependency cycles, file ownership,
  closeout contents, and exact assembled build identity.
- A LangGraph runtime with SQLite checkpoints, operation journal, exclusive project writer,
  explicit retry IDs, and controlled artifact/spawn/build bookkeeping.
- Owner-signed, expiring approvals bound to the action, code, ledger, and evidence.
- Deterministic workflow checks and regression tests, including actual process-death recovery.
- A dry-run-first installer with backup, ownership manifest, modified-file protection, and uninstall.

Tool profiles, hashes, and signatures do not make arbitrary owner-account shell access safe.
Signing keys and trust configuration need a real protected-controller/worker boundary. No key,
worker sandbox, paid agent service, or autonomous supervisor is provisioned by installation.

## Task shapes

| Tier | Shape | Process |
|---|---|---|
| **A — Answer** | Lookup, explanation, read-only question | Read, answer, cite. No graph. |
| **B — Fix** | Bounded known change | Read, edit, verify, report. No discovery fan-out. |
| **C — Build** | New capability, material product fork, or real coordination | Graph-backed workflow sized lite/standard/full. |

Risk, uncertainty, and dependencies determine process—not file count or a desired minimum agent
count. Prefer one capable builder plus independent verification when work does not truly divide.

## Discovery profiles

| Profile | Coverage |
|---|---|
| **Lite** | Product/Domain + Combined Engineering, then Premise Auditor |
| **Standard** | Product/Domain + Frontend/Experience + Backend/Systems + Security/Privacy, then Premise Auditor |
| **Full** | Standard plus up to two justified specialists/challenges |

A spawn must buy independent evidence or verification. Plan the whole-project ceiling, including
build/review/repair work; the ceiling is not a target. Track reservations through the runtime.

## Install

Clone or update the repository, then preview without auto-accept:

```powershell
.\scripts\install.ps1 `
  -EnableNotifications `
  -ReplaceGlobalConstitution `
  -EnableGraphRuntime
```

After reviewing the plan and migration requirements, apply:

```powershell
.\scripts\install.ps1 `
  -Apply `
  -EnableNotifications `
  -ReplaceGlobalConstitution `
  -EnableGraphRuntime
```

Python 3.11+ is required for the isolated runtime under `~/.claude/runtime/turn-up-time/`.
`-EnableAutoAccept` remains a separate explicit opt-in; it is not a substitute for human approval.

```powershell
& "$HOME\.claude\scripts\turn-up-time-graph.ps1" validate-topology
```

See [installation](docs/INSTALL.md), [runtime commands](docs/GRAPH-RUNTIME.md), and
[approval/evidence migration](docs/HARDENING.md). Signed human gates fail closed until the trusted
operator provisions a public trust file and an owner-only signing path.

## Core commands

`/turn-up-time` coordinates classification and runtime state; `/omnidex` compiles approved evidence
into architecture and tickets; `/boil-the-ocean` executes approved work; `/easily-irritated` independently
checks the product; `/production-audit` checks release readiness; `/its-not-you-its-me` proposes measured
workflow improvements. Conditional controls are `/grill-me`, `/guard-before-write`, and `/plug-it-in`.

Runtime commands include `signal`, `request-approval`, `recover`, `status`, and `history`.
Metadata signals `record_artifact`, `reserve_spawn`, `complete_spawn`, and `set_build_identity` replace
direct edits to an initialized ledger. Every signal uses a stable event ID; a retry reuses it.

## Source of truth and execution boundary

Current code/runtime evidence and approved project artifacts outrank conversation memory. The
runtime is the only supported ledger writer. Only the business graph advances a stage. A journal
can finish a previously validated operation, not authorize a new one. Unrecorded drift blocks work.
A structurally valid verdict without current supporting evidence is not a release decision.

Large design/testing packages remain optional capability providers, loaded only when approved work
requires them. Providers are libraries, not competing constitutions. See
[architecture](docs/ARCHITECTURE.md) for ownership and handoffs.

The next operational proof is a real one-builder/one-verifier feature pilot and comparison with a
simpler baseline. [The pilot contract](docs/PILOT.md) defines the evidence and measurements; passing
runtime tests alone does not establish app quality, unattended execution, or return on investment.
