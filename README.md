# Turn Up Time

**An evidence-to-ship engineering gauntlet for Claude Code, governed by an executable LangGraph
control shell.**

> **Current release: Turn Up Time v1.0.0.** See the
> [release notes](docs/RELEASE-NOTES-v1.0.0.md),
> [graph validation report](docs/GRAPH-REVIEW-REPORT.md), and
> [installation guide](docs/INSTALL.md).

Turn Up Time is designed to make agents build the right thing earlier, repair less later, and improve
the workflow only when evidence justifies it. It replaces overlapping routers, planning rituals,
reviewer loops, and style constitutions with one conveyor, one project ledger, bounded local loops,
and one legal stage topology.

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
/swiper-dont-swpe-me (same CLOSEOUT stage)
      ↓
/production-audit + fresh release judge + release gate
      ↓
/its-not-you-its-me
```

LangGraph sits beneath that conveyor. It controls legal transitions, human interrupts, loop ceilings,
checkpoint/resume, and event history. It does not replace the specialist skills and agents.

## Operating rule

> **Loop where evidence changes. Gate where authority changes. Stop where the same failure repeats.
> Never loop merely because another agent is available.**

A repeat is justified only by new evidence, a changed artifact, a fresh independent evaluator, or a
human decision. Re-reading the same prompt with the same evidence is rumination.

## What ships

- 10 user-facing skills plus 1 internal eval provider.
- 17 role-specific agents, with assurance roles mechanically read-only.
- One prompt router that sends ordinary software work to `/turn-up-time`.
- A plug-and-play capability registry for optional specialist providers.
- Machine-readable contracts for intake, evidence, Definition of Good, tickets, seams, findings,
  release, ledger, workflow improvements, graph topology, and graph events.
- Deterministic project validation and seeded workflow-failure evals.
- A pinned LangGraph runtime with local SQLite checkpointing.
- A dry-run-first installer with backup, ownership manifest, modified-file protection, and reversible
  uninstall.

## Task shapes

| Tier | Shape | Process |
|---|---|---|
| **A — Answer** | Lookup, explanation, read-only question | Read, answer, cite. No project graph. |
| **B — Fix** | Bounded change whose shape is already known | Read, edit, verify, report. No discovery fan-out. |
| **C — Build** | New capability, material product fork, or coordination is itself work | Full graph-backed conveyor, sized lite/standard/full. |

File count does not decide the tier. Risk selects assurance. Coordination and unresolved product
design select Tier C.

## Discovery profiles

| Profile | When | Independent roles |
|---|---|---|
| **Lite** | Small new capability | Product/Domain + combined engineering + Premise Auditor |
| **Standard** | New web app or significant feature | Product/Domain + Frontend/Experience + Backend/Systems + Security/Privacy + Premise Auditor |
| **Full** | Novel, high-risk, enterprise, regulated | Standard team + up to two justified specialists + architecture challenge |

A spawn is not a goal. It must buy independent information or independent verification.

## Official topology

The authority chain is:

```text
CLAUDE.md
  constitutional principles and human ownership
        ↓
runtime/src/turn_up_time_graph/topology.py
  only executable source of legal stages, edges, loops, and gates
        ↓
.claude/skills and .claude/agents
  node behavior and role boundaries
        ↓
.claude/schemas
  artifact contracts
        ↓
project-ledger.json
  approved human-readable project state
        ↓
SQLite checkpoint + events.jsonl
  runtime recovery and append-only execution history
```

The graph runtime blocks illegal transitions, loop exhaustion, unsigned/stale human approvals,
missing evidence deltas, missing validators, stale assembled builds, and checkpoint/ledger drift.
Per-project locks and durable journaled intents support stable-ID retries and process-death recovery.
It records work; it does not launch workers, provide OS isolation, or deploy applications.

## Install

Clone or update the repository, then preview:

```powershell
.\scripts\install.ps1 `
  -EnableNotifications `
  -ReplaceGlobalConstitution `
  -EnableGraphRuntime
```

The preview changes nothing. After reviewing it, apply:

```powershell
.\scripts\install.ps1 `
  -Apply `
  -EnableNotifications `
  -ReplaceGlobalConstitution `
  -EnableGraphRuntime
```

The graph runtime requires Python 3.11 or newer and is installed into an isolated virtual environment
under `~/.claude/runtime/turn-up-time/`.

Verify:

```powershell
& "$HOME\.claude\scripts\turn-up-time-graph.ps1" validate-topology
```

See [docs/INSTALL.md](docs/INSTALL.md), [docs/GRAPH-RUNTIME.md](docs/GRAPH-RUNTIME.md), and
[the hardening/migration guide](docs/HARDENING.md) for signed approval provisioning. Auto-accept is an
explicit optional setting; installation does not provision signing keys or worker isolation.

## Core commands

- `/turn-up-time` — control plane, classification, state, and stage signaling.
- `/omnidex` — compiles approved evidence into architecture and executable tickets.
- `/boil-the-ocean` — executes approved tickets completely.
- `/easily-irritated` — independent product-friction and consistency closeout.
- `/swiper-dont-swpe-me` — bounded repository cleanup and IT handoff after final product repairs.
- `/production-audit` — release readiness and operational risk.
- `/its-not-you-its-me` — workflow self-improvement with approval and seeded evals.

Conditional controls:

- `/grill-me` — resolves only human-owned ambiguity.
- `/guard-before-write` — reversibility gate for destructive or externally consequential actions.
- `/plug-it-in` — safely places a new provider into the capability registry.

## Source-of-truth order

1. Current repository and runtime evidence.
2. Active `project-ledger.json`.
3. Human-ratified intake and Definition of Good.
4. Approved architecture and tickets.
5. Recorded evidence packs and receipts.
6. SQLite checkpoint cursor, only when aligned with the ledger.
7. Handoffs and summaries.
8. Conversation memory.

A conversation cannot overrule the ledger. A checkpoint cannot overrule a changed ledger. A summary
cannot overrule the code.

## Optional providers

Large design and testing packages are not vendored into the core. Tickets request capabilities such as
`frontend-operate` or `browser-e2e`; the registry maps them to approved providers. `/plug-it-in`
evaluates placement, overlap, authority, conflicts, evals, cost, and removal before activation.

UI work declares each surface's platform, stack and purpose before building:

| Purpose | Design emphasis |
| --- | --- |
| `operate` | Clear actions, feedback, recovery and useful density |
| `persuade` | Message hierarchy, credible evidence and a clear next action |
| `read` | Legibility, navigation, content hierarchy and reading rhythm |
| `experience` | Interaction and pacing, with accessible input and motion |

The approved project guide governs all four. Impeccable supplies the default instruction baseline;
`polish`, `21st-catalog` and `21st-generate` are explicit optional flags. Web requires browser proof;
native requires a real native assurance adapter. 21st needs compatible output, tool access and actual
invocation evidence; generation also needs entitlement. A registry entry does not install or invoke
a provider. Narrow refinements reuse the incumbent guide; new directions need bounded evidenced
comparables. An opt-in design loop pins anchored criteria and budgets inside Easily Irritated; its
ordinary one-batch/one-confirmation flow stays the default.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full ownership and loop model.
