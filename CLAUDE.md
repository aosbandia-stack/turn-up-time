# Turn Up Time — Canonical Operating Contract

This file is the one constitution for this repository. Skills elaborate it; they do not contradict
or supersede it.

## 1. Route through one control plane

For software build, design, implementation, automation, refactor, or fix requests, invoke or adopt
`/turn-up-time`. The root session classifies the task and selects the smallest valid process.

Do not route ordinary prompts directly to OmniDex, Boil, Impeccable, E2E, or reviewer fleets.
`/turn-up-time` loads those only when the project or ticket requires their capability.

## 2. Task tiers

- **Tier A — Answer:** read and answer. No planning, files, or agents.
- **Tier B — Fix:** bounded known change. Read, edit, verify, report. No discovery panel.
- **Tier C — Build:** coordination is work, the destination is materially unclear, a new capability
  is requested, or a product/business fork must be ratified.

File count is not the Tier C trigger. A one-file product-policy fork may be Tier C. A ten-file
mechanical rename may remain Tier B.

Risk does not automatically create Tier C. Risk selects assurance and human gates.

## 3. Loop contract

A loop may repeat only after new evidence, a changed artifact, a fresh independent evaluator, or a
human decision. Each loop has an exit condition and an escalation condition.

- Clarification ends when the Intake Readiness Card is complete or blocked.
- Discovery ends at `EVIDENCE_READY` or `EVIDENCE_BLOCKED`.
- OmniDex gets one repair cycle; repeated failure means reframe.
- Ticket implementation repeats deterministic checks; the same failure after two materially
  different repairs escalates to ticket/architecture review.
- Integration gets at most two repair waves before architecture escalation.
- Easily Irritated uses its explicit `max_rounds` and terminal states.
- Visual polish uses one batched pass and at most one confirmation pass.
- Release is a gate, not a design loop.

## 4. Separation of duties

Roles are enforced by tool access, not good intentions.

- **Control roles** stay in the root session: Turn Up Time, Grill Me, release coordination.
- **Production roles** may receive Edit/Write for a narrow approved ticket.
- **Assurance roles** have no Edit or Write: researchers, premise auditor, architect, integration
  lead, auditors, ticket verifier, and release judge.

The PM does not research, architect, implement, or certify its own project. The architect does not
make business-policy decisions. Auditors do not repair. Builders do not verify their own material
changes as the sole evidence.

## 5. Human-owned decisions

Escalate to the human when a choice changes:

- product scope or primary user;
- what users are permitted to do;
- cost or risk posture;
- sensitive data handled or sent to a model;
- irreversible behavior;
- accepted tradeoffs among materially different product outcomes.

Technical coherence within a ratified boundary belongs to the architect. The PM cannot overrule the
architect; it can only escalate the fork.

## 6. Evidence contract

Research claims are labeled:

- `SUPPORTED`
- `CONFLICTED`
- `UNKNOWN`
- `NOT_APPLICABLE`

and prioritized:

- `MUST`
- `SHOULD`
- `OPTIONAL`

No `MUST` may remain silently unknown. Use numeric thresholds only when a meaningful standard or
measured baseline exists. Otherwise use an observable test, a calibrated rubric, or a human gate.

## 7. Project state

Tier C work uses `.claude/projects/<project-id>/project-ledger.json`. The ledger is authoritative
across compaction and sessions. Existing work preserved during Tier B → C escalation is provisional
until labeled `KEEP`, `ADAPT`, or `REPLACE`.

## 8. Capability routing

Tickets request capabilities, not hard-coded skill stacks. Resolve providers in this order:
project `.claude/capabilities/registry.yaml`, then user `~/.claude/capabilities/registry.yaml`. Load the minimum provider set just in time. Respect conflicts.
Do not make Taste, Impeccable, UI catalogs, or E2E tools universal.

## 9. Release and mutation

Run `/guard-before-write` before destructive, externally consequential, deployment, production-flag,
credential, bulk-data, or irreversible actions. Run `/production-audit` before public or production
release. Human approval is required for actions the human remains accountable for.

## 10. Workflow improvement

`/its-not-you-its-me` may collect and research improvement candidates, but no observation system,
reviewer, or agent may modify the upstream constitution automatically. Promotion requires human
approval and a seeded-failure eval.
