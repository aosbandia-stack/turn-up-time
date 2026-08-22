# Manifest

Turn Up Time is the clean, official successor to `agentic-engineering-workflow`. It carries forward
only the mechanisms needed by the evidence-to-ship gauntlet and its executable graph control shell.

## Core skills

1. `turn-up-time`
2. `grill-me`
3. `omnidex`
4. `boil-the-ocean`
5. `easily-irritated`
6. `production-audit`
7. `its-not-you-its-me`
8. `plug-it-in`
9. `guard-before-write`
10. `eval-harness` (internal provider)

## Core roles

The repository contains 17 role profiles. Production authority is limited to
`implementation-engineer`; research, architecture, integration, audit, triage, verification, and
judgment roles are read-only by tool contract.

## Durable contracts

The `.claude/schemas/` directory contains the project, evidence, ticket, seam, finding, release,
capability, improvement, workflow-graph, and graph-event contracts. Templates under
`.claude/templates/` provide schema-valid starting artifacts.

## Official graph runtime

`runtime/` is the pinned Python 3.11+ LangGraph execution controller. It provides:

- one executable stage topology;
- bounded loop counters;
- explicit human gates;
- local SQLite checkpointing;
- checkpoint/ledger alignment checks;
- atomic ledger transitions;
- append-only idempotent events;
- topology validation, signaling, status, history, and Mermaid/JSON rendering;
- isolated runtime tests.

The installer creates an owned virtual environment under `~/.claude/runtime/turn-up-time/` only when
`-EnableGraphRuntime` is requested.

## Deliberately not copied or vendored

- The legacy eight-phase Engineering Loop.
- The 12-class router.
- Default OmniDex multi-round consensus.
- Default builder fan-out on ordinary fixes.
- Twin-nem and fleet coordination as a default dependency.
- Large vendored design packages.
- LangGraph source, SDKs, server, CLI, prebuilt agents, or cloud tracing.
- Duplicate global/project copies of the same skill.
- Taggy-specific paths, data, protected-file names, and company content.
- Legacy command archives and dormant hooks.
- Automatic workflow mutation from continuous-learning output.

## Optional capability providers

The core registry may reference providers such as Impeccable, E2E Testing, and AI Regression Testing.
They are not bundled. `/plug-it-in` evaluates and installs them separately.

## Third-party dependencies

The optional runtime installs `langgraph==1.2.11` and
`langgraph-checkpoint-sqlite==3.1.1` from PyPI under their MIT licenses. See
`THIRD_PARTY_NOTICES.md`.
