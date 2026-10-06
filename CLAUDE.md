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
  → /swiper-dont-swpe-me  bounded repository cleanup and IT handoff (same CLOSEOUT)
  → /production-audit     operational release evidence
  → fresh-release-judge   independent final judgment
  → /guard-before-write   consequential action gate
  → /its-not-you-its-me   workflow improvement proposals
```

The root session is the only control requester. The runtime is the only supported writer of an
initialized project ledger; skills and agents submit operations rather than editing it directly.

## 4. Official executable topology

For Tier C, `runtime/src/turn_up_time_graph/topology.py` is the only executable source of legal
stages, transition events, loop ceilings, and human gates. `CLAUDE.md` owns principles and authority;
the topology owns legal movement; skills own node behavior; schemas own artifact shape.

The LangGraph runtime is a hard control shell around the gauntlet, not a replacement for it:

- agents reason freely inside bounded research, architecture, implementation, and assurance nodes;
- only the graph may advance a Tier C ledger stage;
- loop edges require new evidence, a changed artifact, a fresh evaluator, or a human decision;
- human-owned transitions require an owner-signed, expiring approval bound to the exact event,
  ledger, code identity and evidence manifest, including project capability readiness and registry;
- checkpoint/ledger drift blocks resume;
- SQLite stores runtime cursor and interrupts, never hidden business truth;
- `project-ledger.json` remains the approved human-readable state;
- a per-project writer lock and durable journal precede ledger/event projection;
- `events.jsonl` records stage edges and metadata operations exactly once for a stable event ID;
- identical retries return the prior result; conflicting payload reuse fails and recovery retains counters.

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
- Visual polish gets one batched pass and at most one confirmation by default. An explicitly
  approved design loop shares Easily Irritated's overall round budget, pins guide/rubric before
  building, requires fresh independent evidence on changed content, and stops on regression,
  stagnation or configured elapsed/cost limits. A score never overrides a hard gate or criterion floor.
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
5. request and obtain the signed human approval envelope for gated edges; a name is not authorization;
6. call the installed graph runtime with a stable project thread ID;
7. let the runtime persist intent, project ledger/events, and reconcile the checkpoint;
8. verify checkpoint and ledger hashes still align.

Agent prose cannot advance a stage. Use `record_artifact`, `reserve_spawn`, `complete_spawn` and
`set_build_identity` for metadata without changing a stage. Reserve before dispatch, complete from
actual outcomes, and never refund consumed work or silently raise an initialized budget. Derive the
current assembled identity through the runtime. Direct edits cause drift; recovery must not erase it.

## 10. Capability routing

Tickets request capabilities, not hard-coded skill stacks. Resolve project registry first, then user
registry, then bundled registry. Load only the minimum conflict-free provider plan just in time.

Every selected capability and its dependencies are required even when its provider is not bundled.
Instruction-only providers require readable installed instructions. External tools also require a
current project/environment readiness probe; integration requires actual invocation/output evidence.
Installed, usable, and used are distinct claims. The resolver never executes registry shell commands.

Providers are implementation libraries, not constitutions. Every provider declares authority, stage,
inputs, outputs, dependencies, conflicts, evals, load policy, and removal contract. Missing optional
providers block or trigger `/plug-it-in`; they are not silently replaced.

UI surfaces declare platform, purpose, stack and optional flags. The existing resolver expands that
registry-backed selection into required ticket capabilities. Web requires browser assurance; native
requires a real configured native adapter. Impeccable is the default design instruction baseline;
21st catalog/generation stay optional and require actual external readiness/use and compatible stack.
Provider provenance does not authorize installation, paid calls or external egress. The approved
project guide and its shared components govern implementation and grading.

## 11. Release and mutation

Release requires:

- exact build identity across all receipts;
- approved Definition of Good and exactly one independent structured PASS per acceptance check,
  hashing its schema-checked Swiper verification receipt and the underlying actual outputs;
- POST_BUILD `SEAMS_SOUND`;
- Easily Irritated terminal state compatible with release, followed by `/swiper-dont-swpe-me`;
- current cleanup, dependency/external-caller, rollback and IT handoff evidence;
- production-audit SHIP/SHIP_WITH_ACCEPTED_RISK;
- fresh-release-judge GREEN;
- human accepted-risk/release approval where required;
- `/guard-before-write` receipt before consequential action.

Auto-accept never overrides human accountability. A changed candidate invalidates affected ticket,
integration, journey, visual, cleanup and release evidence. Refresh those checks before judging it.

`DONE` reports the approved scope. Candidate-only work ends at CANDIDATE_VERIFIED. Deployment work
requires the approved exact candidate, target/environment, guard and execution receipt, live checks,
and rollback/handoff owners. Graph events and worker reservations do not prove launch, supervision,
deployment or live success. Completion lives in the existing closeout terminal packet.

## 12. Workflow improvement

`/its-not-you-its-me` may collect and research process defects. No observer, continuous-learning
system, reviewer, or agent may alter this constitution, topology, core skills, hooks, schemas, or
registry automatically. Promotion requires human approval and a seeded failure that proves the change
catches the original defect without unacceptable ceremony.

## 13. Trust and recovery boundary

Missing, failing or timed-out validators block advancement. Default trust/validator roots come from
the OS account, not HOME or USERPROFILE. A writable explicit trust-file override is denied; an
explicit validator installation override remains operator-controlled configuration. Protect runtime,
validators, trust and ledger from workers, and keep signing keys outside worker authority. Same-account
shell access is not isolated by a worktree, hashes, tool labels or the advisory command guard.

Use the same event ID/payload when retrying an interrupted operation and `recover` when required.
The journal replays bookkeeping, not external deployment or other side effects. See the source
repository's `docs/HARDENING.md` and `docs/SECURITY-BOUNDARY.md` for supported limits.
