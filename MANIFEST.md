# Manifest

Turn Up Time is a clean-room successor to `agentic-engineering-workflow`. It intentionally carries
forward only the mechanisms needed by the evidence-to-ship conveyor.

## Inventory

| Surface | Count | Purpose |
|---|---:|---|
| Core skills | 10 | 9 user-facing workflow/control skills + internal Eval Harness |
| Role agents | 17 | Discovery, architecture, production, integration, QA, triage, verification, review |
| JSON schemas | 9 | Registry, intake, evidence, DoG, ticket, ledger, finding, verdict, improvement |
| Runtime/review scripts | 8 | Scaffold, validate, advance, record, resolve, repo evals, cold review |
| Hooks | 3 | Single router, destructive command guard, notification fallback |
| Capability profiles | 1 | Dashboard/product-interface profile |
| GitHub workflows | 1 | Linux static/evals/review + Windows PS5.1/install/uninstall |

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

## Canonical machine artifacts

- `.claude/capabilities/registry.json`
- `.claude/schemas/*.json`
- `.claude/templates/*.json`
- `.claude/projects/<project-id>/project-ledger.json`
- `.claude/projects/<project-id>/intake-readiness.json`
- project evidence, Definition of Good, tickets, findings, verdicts, and release receipts

YAML is used only where it is the native configuration format, such as GitHub Actions and the readable
process-eval catalog. There is no second YAML capability registry.

## Deliberately not copied

- Legacy eight-phase Engineering Loop.
- Twelve-class router and direct routing to downstream skills.
- Default OmniDex multi-round consensus.
- Default builder fan-out on ordinary fixes.
- Twin-nem/fleet coordination as a default dependency.
- Large vendored design packages.
- Duplicate user/project copies of the same skill.
- Taggy-specific paths, data, protected-file names, and company content.
- Legacy command archives and dormant hooks.
- Automatic workflow mutation from continuous-learning output.

## Optional providers referenced but not bundled

- `impeccable`
- `e2e-testing`
- `ai-regression-testing`

They are installed and routed separately through `/plug-it-in` and the capability registry. Missing
providers block ticket dispatch rather than silently degrading the ticket.
