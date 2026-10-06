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

The root session is the sole project-ledger writer. Agents return artifacts; they never race project
state.

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

The ledger records the artifact path, SHA-256, status, schema, approval, stage verdict, and receipt
references before advancing.

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
