# Turn Up Time — Canonical Operating Contract

This is the one constitution for this repository. Skills elaborate a stage; schemas and scripts
enforce it. No skill, hook, agent, README, provider, or runtime may silently create a competing
workflow.

## 1. One funnel

Software build, design, implementation, automation, refactor, and fix requests enter
`/turn-up-time`. The root session classifies the task and loads the smallest valid process.

The prompt router may also signal `/guard-before-write`, `/plug-it-in`, or
`/its-not-you-its-me` for their narrow purposes. It must not route ordinary work directly to
OmniDex, Boil, frontend providers, or reviewer fleets.

## 2. Task tiers

- **Tier A — Answer:** read and answer. No project artifacts or agents.
- **Tier B — Fix:** bounded known change. Read, edit, verify, report. No discovery panel.
- **Tier C — Build:** a new capability, material product/business fork, or coordination is itself
  work.

File count does not select Tier C. Risk selects assurance and human gates. Start low; Tier B may
escalate in place when a real fork appears. Existing work is preserved but remains provisional until
labeled `KEEP`, `ADAPT`, or `REPLACE`.

## 3. Conveyor and ownership

```text
/turn-up-time             control plane and ledger
  → /grill-me             human-owned ambiguity only
  → discovery agents      independent evidence packs
  → premise-auditor       EVIDENCE_READY / EVIDENCE_BLOCKED
  → /omnidex + architect  Definition of Good, architecture, tickets
  → integration-lead      PRE_BUILD SEAMS_SOUND
  → /boil-the-ocean       ticket execution and build receipts
  → integration-lead      POST_BUILD SEAMS_SOUND
  → /easily-irritated     independent product closeout
  → /production-audit     operational release evidence
  → fresh-release-judge   independent final judgment
  → /guard-before-write   consequential action gate
  → /its-not-you-its-me   workflow improvement proposals
```

The root session is the only project-ledger writer.

## 4. Official executable topology

For Tier C, `runtime/src/turn_up_time_graph/topology.py` is the only executable source of legal
stages, transition events, loop ceilings, and human gates. `CLAUDE.md` owns principles and authority;
the topology owns legal movement; skills own node behavior; schemas own artifact shape.

The LangGraph runtime is a hard control shell around the gauntlet, not a replacement for it:

- agents reason freely inside bounded research, architecture, implementation, and assurance nodes;
- only the graph may advance a Tier C ledger stage;
- loop edges require new evidence, a changed artifact, a fresh evaluator, or a human decision;
- human-owned transitions require an explicit approver;
- checkpoint/ledger drift blocks resume;
- SQLite stores runtime cursor and interrupts, never hidden business truth;
- `project-ledger.json` remains the approved human-readable state;
- `events.jsonl` records each legal edge exactly once.

Tier A and Tier B remain usable without the optional Python runtime. Tier C requires the graph runtime
once enabled as the official project control path.

## 5. Loop contract

A loop repeats only when the next pass receives new evidence, a changed artifact, a fresh independent
evaluator, or a human decision.

- Clarification exits when intake is ready/deferred-with-risk/blocked.
- Discovery exits at `EVIDENCE_READY` or `EVIDENCE_BLOCKED`; repeats target named gaps only.
- OmniDex gets one structural repair; repeated failure means reframe.
- Ticket implementation repeats concrete checks; the same failure after two materially different
  repairs escalates.
- Integration gets at most two repair waves before architecture escalation.
- Easily Irritated obeys `max_rounds` and explicit terminal states.
- Visual polish gets one batched pass and at most one confirmation.
- Release is a gate, not a design loop.
- Workflow improvements are promoted, rejected, deferred, piloted, or retired—never accumulated by
  default.

Re-reading the same prompt with the same evidence is rumination, not loop engineering.

## 6. Separation of duties

Role class is enforced by agent tools:

- **Control:** root-session skills. Coordinate; no specialist production or self-certification.
- **Production:** `implementation-engineer` may Edit/Write only an approved ticket's owned scope.
- **Assurance:** researchers, architect, premise auditor, integration lead, auditors, triage,
  verifiers, and judges have no Edit/Write.

The PM does not research, architect, implement, triage, or certify. The architect does not make
product policy. Auditors do not repair. Builders do not independently verify themselves.

## 7. Human-owned decisions

Escalate when a choice changes:

- primary user, product scope, or desired outcome;
- what users are permitted to do;
- cost or risk posture;
- sensitive data, retention, or model/external egress;
- irreversible behavior;
- acceptance of a material product tradeoff or release risk.

Technical coherence within a ratified boundary belongs to the architect. The PM can sequence or
escalate; it cannot overrule the architect or human.

## 8. Evidence contract

Research claims use:

```text
SUPPORTED | CONFLICTED | UNKNOWN | NOT_APPLICABLE
MUST | SHOULD | OPTIONAL
```

No MUST remains silently unknown. A source must exist, support the claim, be authoritative enough,
be current enough, and apply to this project. Competitor behavior is not user evidence. Use a number
only when meaningful and sourced/measured; otherwise use an observable check, calibrated rubric, or
human gate.

## 9. Stage transition contract

Tier C state lives under `.claude/projects/<project-id>/`. Before the root signals a transition:

1. validate required artifacts against their schemas;
2. run `validate_project.py --stage <target>`;
3. verify the prior stage's explicit verdict;
4. include controlling receipt references and new-evidence identifiers where required;
5. obtain the named human approval for gated edges;
6. call the installed graph runtime with a stable project thread ID;
7. let the runtime atomically update the ledger and append the graph event;
8. verify checkpoint and ledger hashes still align.

Agent prose cannot advance a stage. Direct manual ledger edits require reconciliation before resume.

## 10. Capability routing

Tickets request capabilities, not hard-coded skill stacks. Resolve project registry first, then user
registry, then bundled registry. Load only the minimum conflict-free provider plan just in time.

Providers are implementation libraries, not constitutions. Every provider declares authority, stage,
inputs, outputs, dependencies, conflicts, evals, load policy, and removal contract. Missing optional
providers block or trigger `/plug-it-in`; they are not silently replaced.

## 11. Release and mutation

Release requires:

- exact build identity across all receipts;
- approved Definition of Good and ticket evidence;
- POST_BUILD `SEAMS_SOUND`;
- Easily Irritated terminal state compatible with release;
- production-audit SHIP/SHIP_WITH_ACCEPTED_RISK;
- fresh-release-judge GREEN;
- human accepted-risk/release approval where required;
- `/guard-before-write` receipt before consequential action.

Auto-accept never overrides human accountability.

## 12. Workflow improvement

`/its-not-you-its-me` may collect and research process defects. No observer, continuous-learning
system, reviewer, or agent may alter this constitution, topology, core skills, hooks, schemas, or
registry automatically. Promotion requires human approval and a seeded failure that proves the change
catches the original defect without unacceptable ceremony.
