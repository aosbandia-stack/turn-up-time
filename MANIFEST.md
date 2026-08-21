# Manifest

Turn Up Time is a clean-room successor to `agentic-engineering-workflow`. It carries forward only the
mechanisms required by the evidence-to-ship conveyor.

## Current source inventory

| Surface | Count | Purpose |
|---|---:|---|
| `.claude/skills/*/SKILL.md` | 10 | 9 user-facing stages/controls plus the internal eval provider |
| `.claude/agents/*.md` | 17 | 1 production role and 16 read-only assurance roles |
| `.claude/schemas/*.json` | 11 | machine contracts for every load-bearing handoff |
| `.claude/templates/*.json` | 9 | schema-valid project artifacts/examples |
| `.claude/scripts/*.py` | 6 | validation, scaffolding, capability resolution, evals, and cold review |
| `.claude/hooks/*.ps1` | 3 | single funnel, destructive-command backstop, optional notification |
| `.claude/capabilities/registry.json` | 1 | provider placement and conflict registry |
| `.github/workflows/validate.yml` | 1 | Linux contract/eval review plus Windows PowerShell/install smoke |

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

## Role model

- Control roles live in the root session and are not agent files.
- `implementation-engineer` is the only general production agent with Edit/Write.
- All researchers, architects, auditors, triage, integration, verification, and judge roles are
  mechanically read-only.

## Deliberately not copied

- The legacy eight-phase Engineering Loop.
- The 12-class router.
- Automatic OmniDex R0-R3 consensus rounds.
- Default builder fan-out and unlimited judge loops.
- Twin-nem/fleet coordination as a default dependency.
- Large vendored design packages or multiple competing frontend constitutions.
- Duplicate user/project copies of the same core workflow.
- Taggy-specific paths, data, employer content, or protected-file names.
- Legacy command archives and dormant hooks.
- Automatic workflow mutation from continuous-learning output.
- Loose YAML handoff templates that could not be schema validated.

## Optional providers referenced but not bundled

- `impeccable`
- `e2e-testing`
- `ai-regression-testing`

They enter only through `/plug-it-in` and `.claude/capabilities/registry.json`.
