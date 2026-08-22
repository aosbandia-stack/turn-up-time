# Official LangGraph runtime

Turn Up Time uses LangGraph as a deterministic control shell beneath the existing evidence-to-ship
gauntlet. LangGraph does not replace `/turn-up-time`, the discovery roles, OmniDex, Boil the Ocean,
Easily Irritated, Production Audit, or Its Not You, Its Me.

## Authority

1. `CLAUDE.md` defines invariant principles and human ownership.
2. `runtime/src/turn_up_time_graph/topology.py` is the only executable source of legal stages,
   transitions, bounded loops, and human gates.
3. Skills define what each node does.
4. JSON Schemas define durable artifact contracts.
5. `project-ledger.json` is the approved human-readable business state.
6. SQLite stores graph cursor, pending interrupt, loop counters, and recovery state.
7. `events.jsonl` is the append-only transition history.

The runtime refuses to resume when the checkpoint and ledger disagree.

## Installation

```powershell
.\scripts\install.ps1 `
  -Apply `
  -EnableNotifications `
  -EnableAutoAccept `
  -ReplaceGlobalConstitution `
  -EnableGraphRuntime
```

The installer requires Python 3.11 or newer, creates an isolated virtual environment under
`~/.claude/runtime/turn-up-time/`, installs the pinned runtime package, validates the topology, and
records an ownership marker in the install manifest.

To select a specific Python executable:

```powershell
$env:TURN_UP_TIME_PYTHON = '<absolute-path-to-python.exe>'
```

## Commands

Use the installed wrapper:

```powershell
& "$HOME\.claude\scripts\turn-up-time-graph.ps1" validate-topology
& "$HOME\.claude\scripts\turn-up-time-graph.ps1" render --repo-root C:\path\to\repo
& "$HOME\.claude\scripts\turn-up-time-graph.ps1" status --repo-root C:\path\to\repo --project-dir C:\path\to\repo\.claude\projects\project-id
& "$HOME\.claude\scripts\turn-up-time-graph.ps1" signal --repo-root C:\path\to\repo --project-dir C:\path\to\repo\.claude\projects\project-id --event intake_ready --approved-by Harold
& "$HOME\.claude\scripts\turn-up-time-graph.ps1" history --repo-root C:\path\to\repo --project-dir C:\path\to\repo\.claude\projects\project-id
```

## Bounded loops

The executable topology enforces these ceilings:

- product-boundary return to Intake: 2;
- targeted discovery-premise repair: 2;
- pre-build ticket seam repair: 1;
- architecture reframe: 1;
- post-build integration repair: 2;
- Easily Irritated repair: 4;
- release repair: 2.

Loop edges that claim new evidence require a non-empty `evidence_delta` in the signal payload.

## Current execution boundary

The graph controls legal transitions, approvals, persistence, recovery, and history. Claude Code
skills and agents still perform the research, architecture, implementation, integration review,
product closeout, and release review. This preserves agent judgment inside bounded nodes while making
the overall process mechanically enforceable.
