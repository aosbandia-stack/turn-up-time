# Turn Up Time — Canonical Operating Contract

This file is the one constitution for this repository. Skills elaborate it; they do not contradict or
supersede it. `AGENTS.md` is a compatibility pointer, not a second rule set.

## 1. Route through one control plane

For software build, design, implementation, automation, refactor, or fix requests, invoke or adopt
`/turn-up-time`. The root session classifies the task and selects the smallest valid process.

Do not route ordinary prompts directly to OmniDex, Boil, Impeccable, E2E, or reviewer fleets. Turn Up
Time loads them only when the project stage or an approved ticket requires their capability.

## 2. Task tiers

- **Tier A — Answer:** read and answer. No planning files or subagents.
- **Tier B — Fix:** bounded known change. Read, edit, verify, report. No discovery panel.
- **Tier C — Build:** new capability, material product fork, or coordination is itself work.

File count is not the Tier C trigger. Risk selects assurance and human gates; it does not by itself add
a project-management layer.

## 3. Loop contract

A loop may repeat only after new evidence, a changed artifact, a fresh independent evaluator, or a
human decision. Each loop has an exit and an escalation.

- Clarification ends when `intake-readiness.json` is ready or blocked.
- Discovery ends at `EVIDENCE_READY` or `EVIDENCE_BLOCKED`.
- OmniDex gets one repair cycle; repeated failure means reframe.
- Ticket implementation repeats concrete checks; the same failure after two materially different
  repairs escalates.
- Integration gets at most two repair waves before architecture escalation.
- Easily Irritated uses `max_rounds` and explicit terminal states.
- Visual polish uses one batched pass and at most one confirmation pass.
- Release is a gate, not a design loop.

## 4. Separation of duties

Authority is enforced by tool access, not good intentions.

- **Control roles:** root-session Turn Up Time, Grill Me, and release coordination.
- **Production roles:** implementation engineers may Edit/Write only for approved tickets.
- **Assurance roles:** researchers, premise auditor, architect, integration lead, auditors, triage,
  ticket verifier, and release judges have no Edit or Write.

The PM does not research, architect, implement, or certify. The architect does not make business
policy. Auditors do not repair. Builders do not verify their own material changes as the sole evidence.

## 5. Human-owned decisions

Escalate when a choice changes:

- product scope, primary user, or desired outcome;
- what users are permitted to do;
- cost or risk posture;
- sensitive data handled, retained, or sent externally/to a model;
- irreversible behavior;
- accepted tradeoffs among materially different product outcomes.

Technical coherence within a ratified boundary belongs to the architect. The PM cannot overrule the
architect; it may only escalate a fork.

## 6. Evidence contract

Research coverage is labeled:

- `SUPPORTED`
- `CONFLICTED`
- `UNKNOWN`
- `NOT_APPLICABLE`

and prioritized:

- `MUST`
- `SHOULD`
- `OPTIONAL`

No `MUST` may remain silently unknown. `evidence-pack.schema.json` mechanically rejects an
`EVIDENCE_READY` pack containing an UNKNOWN or CONFLICTED MUST. Use numeric thresholds only when a
meaningful source or measured baseline exists; otherwise use an observable test, calibrated rubric, or
human gate.

## 7. Project state and artifacts

Tier C work lives under `.claude/projects/<project-id>/`. The root session is the designated ledger
writer. The ledger is authoritative across compaction and sessions.

Canonical artifacts are JSON unless the artifact is inherently prose:

```text
project-ledger.json
intake-readiness.json
evidence/*.json
definition-of-good.json
architecture.md
traceability.json
tickets/*.json
integration/*-verdict.json
closeout/*.json
release/*.json
```

Schemas live under `.claude/schemas/`. Record durable artifact hashes in the ledger with
`record_artifact.py`. Change stages only through `advance_stage.py`; it validates the target state and
rolls back an invalid transition.

Existing work preserved during Tier B → C escalation is provisional until labeled `KEEP`, `ADAPT`, or
`REPLACE`.

## 8. Capability routing

Tickets request capabilities, not hard-coded skill stacks. Resolve providers from project
`.claude/capabilities/registry.json`, then user `~/.claude/capabilities/registry.json`, with project
entries taking precedence. Load the minimum provider set just in time.

`resolve_capabilities.py` fails closed on unknown capabilities, conflicts, stage mismatch, and missing
providers. Do not silently substitute Taste, Impeccable, E2E, or another similar skill. `/plug-it-in`
controls new providers.

## 9. Stage gates

The conveyor is:

```text
INTAKE → DISCOVERY → EVIDENCE_REVIEW → DEFINITION → TICKETING → SEAM_REVIEW
→ BUILD → INTEGRATION → CLOSEOUT → RELEASE → WORKFLOW_CLOSEOUT → DONE
```

`validate_project.py` enforces the required intake, evidence, premise verdict, approved Definition of
Good, approved tickets, pre/post integration verdicts, closeout verdict, production audit, fresh final
judge, spawn budget, build identity, and artifact hashes for the current stage.

## 10. Release and mutation

Run `/production-audit` before production/public release and dispatch a separate
`fresh-release-judge`. Only a GREEN final judge may proceed.

Run `/guard-before-write` before destructive, externally consequential, deployment, production-flag,
credential, bulk-data, or irreversible actions. Human approval is required for actions the human
remains accountable for. Auto-accept does not override the guard.

## 11. Workflow improvement

`/its-not-you-its-me` may collect, research, and propose improvements, but no observation system,
reviewer, or agent may modify the constitution automatically. Promotion requires human approval,
seeded failure and negative-control evals, a rollback, and a review date.
