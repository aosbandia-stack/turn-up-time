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

File count and desired agent count do not select Tier C. Risk selects assurance and human gates.
Start low; Tier B may escalate in place when a real fork appears. Existing work is preserved but
remains provisional until labeled `KEEP`, `ADAPT`, or `REPLACE`. Do not manufacture parallel work.

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

The root session is the sole coordinator of ledger operations. After initial scaffolding, only the
runtime writes `project-ledger.json`; neither root nor workers edit it directly.

## 4. Official executable topology

For Tier C, `runtime/src/turn_up_time_graph/topology.py` is the only executable source of legal
business stages, transition events, loop ceilings, and human gates. `CLAUDE.md` owns principles and
authority; the topology owns legal movement; skills own node behavior; schemas own artifact shape.

The LangGraph runtime controls the gauntlet, not specialist judgment:

- agents reason freely inside bounded research, architecture, implementation, and assurance nodes;
- only the graph may advance a Tier C ledger stage;
- metadata operations may revisit the same stage, never change stage or grant approval;
- loop edges require new evidence, a changed artifact, a fresh evaluator, or a human decision;
- human-owned transitions require an owner-signed, action-bound approval, not just a name;
- unrecorded checkpoint/ledger drift blocks resume; journal-proven interruptions are recoverable;
- SQLite records checkpoint state and a durable operation journal, not unapproved product choices;
- `project-ledger.json` remains the approved human-readable state;
- `events.jsonl` records legal edges and metadata operations once per stable event ID.

Tier A and Tier B remain usable without the optional Python runtime. Tier C requires the graph runtime
once enabled as the official project control path. This runtime is not an OS sandbox or worker daemon.

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

Role tool profiles are necessary but are not an operating-system security boundary:

- **Control:** root-session skills. Coordinate; no specialist production or self-certification.
- **Production:** `implementation-engineer` may Edit/Write only an approved ticket's owned scope.
- **Assurance:** researchers, architect, premise auditor, integration lead, auditors, triage,
  verifiers, and judges have no Edit/Write.

The PM does not research, architect, implement, triage, or certify. The architect does not make
product policy. Auditors do not repair. Builders do not independently verify themselves.
Workers must not control the verifier, signing key, trust file, runtime, or ledger. Arbitrary shell
access under the owner's OS account can bypass application controls; do not represent it as isolated.

## 7. Human-owned decisions

Escalate when a choice changes:

- primary user, product scope, or desired outcome;
- what users are permitted to do;
- cost or risk posture;
- sensitive data, retention, or model/external egress;
- irreversible behavior;
- acceptance of a material product tradeoff or release risk.

Technical coherence within a ratified boundary belongs to the architect. The PM can sequence or
escalate; it cannot overrule the architect or human. Approval is bound to exact inputs and expires;
it does not carry forward to a changed build or authorize a different external operation.

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

EVIDENCE_GREEN requires a structured PASS for each acceptance check, independently attributed,
bound to the assembled build, and backed by a project-local file whose SHA-256 matches. An evaluator
label alone does not prove independence. The trusted verifier must produce the evidence. Release
closeout is parsed and checked; the mere existence of a terminal-state file is not success.

## 9. Stage transition contract

Tier C state lives under `.claude/projects/<project-id>/`. Before the root signals a transition:

1. validate required artifacts against their schemas and semantic evidence checks;
2. run `validate_project.py --stage <target>`; missing validation blocks advancement;
3. verify the prior stage's explicit verdict;
4. register controlling artifacts through `record_artifact`, not direct ledger edits;
5. obtain a signed approval for gated edges after inputs and metadata are stable;
6. call the installed graph runtime with a stable project thread ID and explicit event ID;
7. let the runtime journal the intent, project ledger/event updates, and checkpoint the result;
8. verify checkpoint and ledger hashes still align.

Use `reserve_spawn` before dispatch, `complete_spawn` for the real outcome, and
`set_build_identity` for the assembled code. None of these operations grants stage or release
authority. Retry with the same event ID and payload. Use `recover` for journal-proven interruptions;
never reset loop counts or erase state to make an operation pass. Agent prose cannot advance a stage.
See [the migration and command contract](docs/HARDENING.md).

## 10. Capability routing

Tickets request capabilities, not hard-coded skill stacks. Resolve project registry first, then user
registry, then bundled registry. Load only the minimum conflict-free provider plan just in time.

Providers are implementation libraries, not constitutions. Every provider declares authority, stage,
inputs, outputs, dependencies, conflicts, evals, load policy, and removal contract. Missing optional
providers block or trigger `/plug-it-in`; they are not silently replaced.

## 11. Release and mutation

Release requires:

- exact current assembled build identity across all receipts;
- approved Definition of Good and ticket evidence;
- POST_BUILD `SEAMS_SOUND`;
- parsed Easily Irritated terminal state compatible with release;
- separate production-audit SHIP/SHIP_WITH_ACCEPTED_RISK packet;
- separate fresh-release-judge GREEN packet;
- signed human accepted-risk/release approval where required;
- `/guard-before-write` receipt before consequential action.

Auto-accept never overrides human accountability. The command guard is only a narrow backstop.
A graph transition records a release decision; it does not itself execute or authorize arbitrary
network commands, deployments, or financial side effects.

## 12. Workflow improvement

`/its-not-you-its-me` may collect and research process defects. No observer, continuous-learning
system, reviewer, or agent may alter this constitution, topology, core skills, hooks, schemas, or
registry automatically. Promotion requires human approval and a seeded failure that proves the change
catches the original defect without unacceptable ceremony. Compare owner attention, elapsed time,
verified outcomes, defects, and measured usage cost; do not optimize for agent count.
