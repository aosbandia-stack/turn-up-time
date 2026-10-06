# Turn Up Time Architecture

## Conveyor ownership and handoffs

| Stage | Owner | Required inputs | Required output/verdict | May edit product? |
|---|---|---|---|---|
| INTAKE | `/turn-up-time` + conditional `/grill-me` | user ask, repo/runtime receipts | `intake-readiness.json`: READY / READY_WITH_DEFERRED_RISK / BLOCKED | No |
| DISCOVERY | selected research agents | approved intake, current-state receipts | profile-required schema-valid evidence packs | No |
| EVIDENCE_REVIEW | `premise-auditor` | all packs + intake | `premise-verdict.json`: EVIDENCE_READY / EVIDENCE_BLOCKED | No |
| DEFINITION | `/omnidex` + human approval | ready evidence | approved `definition-of-good.json` | No |
| TICKETING | Architect + `/omnidex` + human approval | approved DoG, architecture | `architecture.md`, `traceability.json`, approved tickets | No |
| SEAM_REVIEW | `integration-lead` | DoG, architecture, tickets, capability plans | PRE_BUILD `seam-verdict.json`: SEAMS_SOUND / BLOCKED | No |
| BUILD | `/boil-the-ocean` + implementation engineers | approved tickets, SEAMS_SOUND | ticket build receipts + assembled build identity | Ticket scope only |
| INTEGRATION | `integration-lead` | assembled build and receipts | POST_BUILD `seam-verdict.json`: SEAMS_SOUND / BLOCKED | No |
| CLOSEOUT | `/easily-irritated`, then `/swiper-dont-swpe-me` | exact build, DoG, journeys | One `terminal-state.json` with product, cleanup and handoff proof | Repair engineers only |
| RELEASE | `/production-audit`, fresh judge, guard | closeout packet, target environment | `release-verdict.json`: SHIP / SHIP_WITH_ACCEPTED_RISK / BLOCK | Operational action only after gate |
| WORKFLOW_CLOSEOUT | `/its-not-you-its-me` | project traces, rework, costs | proposal(s) or NO_WORKFLOW_CHANGE_PROPOSED | No automatic workflow edit |

The root requests control operations; only the runtime writes an initialized ledger. Agents return
artifacts and never race project state. A journal and exclusive writer lock precede projections;
recovery restores the recorded checkpoint update without repeating external work.

## Stage prerequisites

`validate_project.py` enforces the monotonic subset below:

```text
DISCOVERY       requires ready intake
EVIDENCE_REVIEW requires profile evidence packs
DEFINITION      requires EVIDENCE_READY
TICKETING       requires approved Definition of Good
SEAM_REVIEW     requires approved tickets, architecture/design/traceability, and usable capabilities
BUILD           requires PRE_BUILD SEAMS_SOUND
INTEGRATION     requires exact-build ticket/check/journey evidence and actual external-provider use
CLOSEOUT        requires POST_BUILD SEAMS_SOUND on the candidate
RELEASE         requires a current product, cleanup and handoff terminal packet
WORKFLOW_CLOSEOUT requires agreeing production-audit/final-judge components and release verdict
DONE            requires scope-appropriate completion proof in the same terminal packet
```

Runtime operations record artifact path/hash, reserve and complete spawns, and derive the assembled
build identity. Gated transitions require signed approvals binding code, ledger and the evidence
manifest, including `capability-readiness.json` and `capability-registry.json`. Metadata operations
cannot grant approval or change a stage.

## Project workspace

```text
.claude/projects/<project-id>/
  project-ledger.json
  intake-readiness.json
  evidence/
    product.json
    combined-engineering.json       # lite only
    frontend.json                    # standard/full
    backend.json                     # standard/full
    security.json                    # standard/full
    premise-verdict.json
  definition-of-good.json
  architecture.md
  traceability.json
  tickets/
    <ticket-id>.json
  receipts/
  integration/
    pre-build-verdict.json
    post-build-verdict.json
  closeout/
    terminal-state.json
    findings.jsonl
    verification.jsonl
  release/
    production-audit.json
    final-judge.json
    guard-receipt.json               # when required
    release-verdict.json
  improvements/
  requests/                         # metadata payloads
  approvals/                        # signed envelopes, excluded from signature manifest
  .runtime/operations.sqlite         # durable operation journal
```

## Loop map

| Loop | New input required | Exit | Escalation |
|---|---|---|---|
| Clarification | human answer | intake ready/deferred/blocked | six questions still leave a material fork |
| Discovery | new source/evidence for a named gap | EVIDENCE_READY/BLOCKED | unresolved MUST or human decision |
| OmniDex repair | concrete premise/traceability/seam finding | approved artifacts | same structural defect survives one repair |
| Ticket repair | failing acceptance check + changed implementation | EVIDENCE_GREEN | same failure survives two distinct repairs |
| Integration repair | changed assembled build | SEAMS_SOUND | same seam survives two waves |
| Closeout | changed build + fresh independent team | terminal state | max rounds or decision/environment block |
| Visual polish | new batched screenshots/journey evidence | confirmed pass | second pass reveals structural issue |
| Workflow improvement | new project evidence + seeded eval | promote/reject/defer/retire | no measurable benefit or excess ceremony |

## Discovery profiles

### Lite

`product-domain-researcher` + `combined-engineering-researcher`, then `premise-auditor`.
The combined lane must return `STANDARD_PROFILE_REQUIRED` when independent UI/backend/security work
cannot be responsibly compressed.

### Standard

Product/Domain, Frontend/Experience, Backend/Systems, and Security/Privacy in parallel, then Premise
Auditor serially.

### Full

Standard plus no more than two risk-justified specialists/challenges. The spawn budget is a ceiling,
not a target.

## Capability providers

`.claude/capabilities/registry.json` is schema-backed. `resolve_capabilities.py` expands dependencies,
rejects unknown capabilities and conflicts, and blocks every selected missing provider regardless of
bundling. Instruction-only providers require readable instructions; external tools also require a
current project/environment probe and separate actual-use proof at integration. Project registry overrides user registry, which overrides bundled defaults.

Providers are loaded only by approved tickets. `frontend-operate` maps dashboards/product interfaces
to Impeccable `operate`; marketing Taste rules are not a dashboard default.

### UI surfaces and provider flags

`ui.surfaces` in Definition of Good names `id`, `platform` (`web`/`native`), `purpose`
(`operate`/`persuade`/`read`/`experience`), `stack`, `routes`, `flags`, `change_scope`,
`research_disposition`, `research`, and `verification_capabilities`. Every declared route must be
covered. Registry `ui_selector` metadata expands platform/purpose/flags using the same function in
the CLI and project validator. Expanded direct/transitive capabilities must be ticketed; dropping a
flag from a ticket cannot drop its provider checks. Legacy web aliases remain valid.

The defaults select one Impeccable purpose capability and, for web, `browser-e2e`. Native needs an
explicit external assurance capability with `supported_platforms: ["native"]` and a real readiness/
use receipt; no React/browser adapter is inferred. A project override replaces the named capability,
including its selector/compatibility declaration, so retain that metadata when replacing providers.

`polish` selects installed polish instructions. `21st-catalog` and `21st-generate` are separate
external capabilities. Both require a successful `checks.tool_access` readiness probe; generation
also requires `checks.entitlement`. Both need actual invocation/output evidence at integration.
Default compatibility is `react-tailwind`; a reviewed nonstandard project mapping must declare its
compatible stack and resolve `stack_adapter_ref`. No 21st polish API is assumed. Pinned upstream
source/ref/license metadata records provenance, not installed version, permission to call paid tools,
or the license of hosted/catalog content. The 21st integration repository is ISC; hosted service and
individual catalog terms remain separate. No upstream hook or binary is downloaded automatically.

For example, an incumbent tool surface can declare:

```json
{"id":"main","platform":"web","purpose":"operate","stack":"react-tailwind",
 "routes":["/items"],"flags":["polish"],"change_scope":"REFINEMENT",
 "research_disposition":"REUSE_GUIDE","research":[],"verification_capabilities":[]}
```

CLI equivalent: `resolve_capabilities.py --ui-platform web --ui-purpose operate --ui-stack
react-tailwind --ui-flag polish`, plus the actual project/provider/readiness arguments. These are
Turn Up Time selectors, not invented provider command flags. `--ui-verification-capability` selects
a configured assurance adapter, especially for native. Readable instruction-only inputs, current
external readiness and actual use remain three distinct claims.

The authoritative `ui.design_reference` contains typography, spacing, color, hierarchy, density,
states, responsiveness, accessibility and component ownership. `NEW`/`REDESIGN` surfaces require
`COMPARABLES`: one to three records with `source`, OBSERVED/SUPPLIED `basis`, `observation`,
ADOPT/ADAPT/REJECT `disposition`, `rationale`, a `guide_ref` in that same guide, and hashed
`evidence_refs`. Supplied captures work offline; a missing source is not invented observation.
`REFINEMENT` may `REUSE_GUIDE` with no new research. Hashes establish evidence integrity, not honesty.

### Optional design evaluation contract

Ordinary UI closeout retains one batched visual pass plus one confirmation. Opting into
`ui.design_loop` uses Easily Irritated's existing overall `max_rounds` (default 4, declared in the
approved contract), not another allowance. The object records:

- `rubric_version`, `locked_at`, `guide_sha256`, `rubric_sha256`;
- `criteria`: unique `id`, `critical`, `minimum` (1–4), and project-specific `anchors` for all scores
  `"0"` through `"4"`; every minimum must pass, including each critical floor;
- named `hard_gates`, independent of judgment scores;
- positive `max_rounds`, `max_elapsed_seconds`, `max_stagnant_rounds`, and `cost_ceiling` (null, or
  positive `amount` and `unit`).

Hash the complete guide file, even when the reference includes a heading. Use
`project_contracts.rubric_digest(loop)` to SHA-256 the sorted compact JSON object excluding only its
own `rubric_sha256`; it includes anchors, thresholds, version, guide hash and budgets. Lock before
building. Amending the guide/rubric uses the existing definition approval path and invalidates grades.

Each ordered `terminal-state.round_history` reference is an existing verification receipt with
`check_id: "design-evaluation"`. Its `design_evaluation` names the locked hashes, `evaluator_role:
"assurance"`, a fresh `evaluator_id`, `started_at`, and criterion/hard-gate rows. Each row has `id`,
PASS/FAIL/UNKNOWN `status` and hashed `evidence_refs`; criteria also have ordinal `score` (null for
UNKNOWN). Receipt status agrees with all individual outcomes. No mean or total score is accepted.
The receipt's ordinary project/build/time/output fields still apply. These attributed claims require
actual captures/tests from independent review; they do not attest to model cognition or OS isolation.

Historical FAIL receipts are schema/hash-checked against their own builds. Only the final receipt
must PASS on the final build. Changed content and a fresh evaluator are required each round; changing
only the commit while retaining the same content hash is not a new candidate. Any criterion or gate
regression stops. Lack of improvement consumes the stagnation budget. Elapsed time includes gaps
between rounds. With a cost ceiling, every round needs actual `cumulative_cost`, matching `cost_unit`
and hashed `cost_evidence_refs`; unknown cost is not zero.

`design_stop_reason` is THRESHOLD_MET, ROUND_LIMIT, TIME_LIMIT, COST_LIMIT, STAGNATION, REGRESSION,
ENVIRONMENT or DECISION. Only THRESHOLD_MET supports release entry, and a later pass cannot erase an
earlier stop. Other reasons preserve failed history and use the existing blocked/max-round terminal
states. These checks consume recorded budgets, not a new evaluator service or worker termination
mechanism. The ordinary journey, UI/keyboard, Swiper and release checks remain required.

## Role authority

- Control roles live in the root session.
- The only general product writer is `implementation-engineer`, bounded to ticket file ownership.
- Every researcher, auditor, architect, integration lead, triage lead, verifier, and judge lacks
  Edit/Write tools.
- A fresh final judge is independent of production audit and product closeout.

## Resume and drift

On resume, read the ledger, compare branch/dirty state/build identity, and verify hashes of controlling
artifacts. Rerun only premises whose substrate changed. Conversation memory cannot overwrite ledger
state.

## Evidence and completion boundary

Versioned contracts are consumed by `validate_project.py`; the existing runtime calls that validator
for target stages. No new topology or supervisor is added. Readiness/use receipts distinguish presence,
usable tools and actual task execution. Local output hashes detect changes, not dishonest reporting or
remote authentication guarantees; independent reproduction and human authority still matter.

`verification-receipt.schema.json` links a check ID, project/build, PASS/FAIL, timestamp and hashed
output paths confined to the project. Acceptance IDs come from tickets; journey IDs come from DoG.
Cleanup uses `cleanup`, handoff uses `handoff`, per-file caller proof uses `dependencies:<path>` and
`external-callers:<path>`. UI proof uses `ui:<route>:<viewport>` and `keyboard:<route>`. Keep actual logs,
screenshots and reviewed source snapshots as evidence; never generate positive receipts from labels.

The same terminal packet gains `completion` at DONE. CANDIDATE_ONLY ends at CANDIDATE_VERIFIED with
handoff evidence. DEPLOYED requires named target/environment, approved exact release and guard proof,
`deployment-execution` and later `live-verification` receipts whose `context` matches that target,
plus rollback/handoff owners. A `deployment-guard` verification receipt preserves the actual
`/guard-before-write` PROCEED output as hashed evidence; it does not replace that authority decision.
Release approval, deployment execution and live success are separate
facts. Reservations, graph events and caller-reported outcomes do not supervise a worker or deploy it.

Source or cleanup repairs change build identity. Re-run affected ticket, seam, journey, UI, cleanup
and release proof before proceeding. Keep a no-change cleanup when the reviewed scope is already
maintainable; do not create churn to satisfy a quota.

## Reconciled runtime and ticket evidence

Structured ticket results identify one assurance evaluator and PASS per acceptance ID. Their
`evidence_ref` equals the acceptance check's reference and their SHA-256 hashes that existing Swiper
verification receipt. Its project/check/build/status and underlying output hashes are validated by the
same project gate. There is no second closeout/release validator. Assurance labels are attributed
claims; isolation and independent reproduction still require a trusted execution arrangement.

The runtime rejects missing validators and stale assembled identities from INTEGRATION onward.
Signatures bind both project capability files. OS-account home resolution protects default trust and
validator lookup from HOME/USERPROFILE substitution; explicit trusted operator overrides and the
remaining same-account limits are documented in [SECURITY-BOUNDARY.md](SECURITY-BOUNDARY.md).
