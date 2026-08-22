# Turn Up Time v1.0.0

Released August 22, 2026.

Turn Up Time v1.0.0 is the first official release of the LangGraph-backed evidence-to-ship workflow.
LangGraph is the deterministic Tier C control shell beneath the existing skills and agents; it does
not replace their research, architecture, implementation, integration, or assurance judgment.

## What is official

The workflow remains:

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

The executable authority order is:

```text
CLAUDE.md
      ↓
runtime/src/turn_up_time_graph/topology.py
      ↓
skills and agents
      ↓
JSON Schemas
      ↓
project-ledger.json
      ↓
SQLite checkpoint
      ↓
events.jsonl
```

## Runtime and recovery

v1.0.0 adds:

- one executable source of legal stages, edges, repair loops, and human gates;
- typed runtime state with Pydantic-backed event signals;
- local asynchronous SQLite checkpointing with stable graph thread IDs;
- checkpoint/ledger stage and hash alignment protection;
- atomic `project-ledger.json` transitions;
- append-only, idempotent `events.jsonl` history;
- required evidence deltas on repair edges;
- deterministic Mermaid and JSON rendering from the executable topology;
- topology validation, signaling, status, history, and render commands.

## Bounded loops

The topology enforces explicit ceilings for:

- product-boundary returns to Intake;
- targeted discovery and premise repair;
- pre-build ticket repair;
- architecture reframing;
- post-build integration repair;
- Easily Irritated closeout repair;
- release repair.

When a loop ceiling is exhausted, the graph blocks or escalates rather than silently restarting the
same review panel.

## Installation safety

The Windows PowerShell 5.1 installer now:

- previews by default;
- accepts `-EnableGraphRuntime`;
- requires Python 3.11 or newer;
- installs the runtime into `~/.claude/runtime/turn-up-time/`;
- pins compatible LangGraph, SQLite-checkpoint, and async-SQLite dependencies;
- validates the installed topology before recording success;
- records created, overwritten, and preserved artifacts;
- records file hashes, runtime ownership hashes, backups, and exact target paths;
- preserves unrelated hooks, deny rules, and an existing notification provider.

The uninstaller restores overwritten artifacts and removes the owned virtual environment only when
its marker and installation hash still match. Modified files or runtime contents are preserved and
reported instead of being destroyed.

## Validation evidence

The release runtime was merged through [PR #4](https://github.com/aosbandia-stack/turn-up-time/pull/4).
Its final candidate tree was `b59c91441fd2c63969f5bf3ac4349254ef971061`, and the signed squash commit
`752521b58f8cdbc958f092c5fd3affdb0a4bef26` contains that exact same tree.

The final candidate passed:

- [Validate workflow #260](https://github.com/aosbandia-stack/turn-up-time/actions/runs/32583708587):
  repository contracts, seeded process failures, deterministic cold review, capability resolution,
  project scaffolding, Windows PowerShell parsing, router and destructive-command guard checks, and
  hash-safe installation/uninstallation;
- [Cold graph review #6](https://github.com/aosbandia-stack/turn-up-time/actions/runs/32583708602):
  fresh graph-specific structural and behavioral review;
- [Validate graph runtime #41](https://github.com/aosbandia-stack/turn-up-time/actions/runs/32583708593):
  runtime dependency installation, Python compilation, the full runtime test suite, executable
  topology validation, generated-artifact schema validation and freshness, plus graph-enabled Windows
  installation, installed-runtime verification, settings preservation, and clean uninstall.

See [GRAPH-REVIEW-REPORT.md](GRAPH-REVIEW-REPORT.md) for the release audit summary.

## Install v1.0.0

```powershell
git clone https://github.com/aosbandia-stack/turn-up-time.git
cd turn-up-time
.\scripts\install.ps1 -EnableNotifications -EnableAutoAccept -ReplaceGlobalConstitution -EnableGraphRuntime
.\scripts\install.ps1 -Apply -EnableNotifications -EnableAutoAccept -ReplaceGlobalConstitution -EnableGraphRuntime
& "$HOME\.claude\scripts\turn-up-time-graph.ps1" validate-topology
```

For an existing clone:

```powershell
git switch main
git pull --ff-only origin main
```

Then run the preview, apply, and verification commands above.

## Scope of the release claim

v1.0.0 is technically validated and release-ready. It does not claim that a synthetic suite proves
business ROI, cycle-time reduction, or rework reduction. That evidence requires a genuine Tier C
pilot carried from Intake through workflow closeout.

The deterministic cold reviews are not represented as an independent Claude-model judgment. No fresh
external-model review was run as part of the corrective release work, and this release does not claim
otherwise.
