# Architecture

## Conveyor ownership

| Stage | Owner | Required input | Durable output | Product edits? |
|---|---|---|---|---|
| Route/intake | `/turn-up-time` root skill | User ask + live repo state | Ledger + `intake-readiness.json` | No |
| Clarification | `/grill-me` root skill | Human-owned unknowns | Ratified intake | No |
| Discovery | Profile research agents | Intake + current-state receipts | `evidence/*.json` | No |
| Premise audit | `premise-auditor` | Valid evidence packs | `evidence/premise-verdict.json` | No |
| Definition/tickets | `/omnidex` + `architect` | Ready evidence + premise verdict | DoG + architecture + traceability + tickets | No |
| Seam review | `integration-lead` | Approved tickets/contracts | `integration/prebuild-verdict.json` | No |
| Build | `/boil-the-ocean` + implementation engineers | Approved tickets + capability receipts | Code + ticket receipts | Yes, ticket scope only |
| Integration | `integration-lead` | Assembled build + receipts | `integration/postbuild-verdict.json` | No |
| Product closeout | `/easily-irritated` team | Integrated build + DoG + journeys | Findings + `closeout/verdict.json` | Auditors no; repairers yes |
| Release | `/production-audit` + `fresh-release-judge` + guard | Closeout-ready build | Audit + final judge + guard/release receipts | Operational only |
| Workflow closeout | `/its-not-you-its-me` | Project traces | Improvement proposals | No automatic workflow edit |

## State machine

```text
INTAKE
  ↓
DISCOVERY
  ↓
EVIDENCE_REVIEW
  ↓
DEFINITION
  ↓
TICKETING
  ↓
SEAM_REVIEW
  ↓
BUILD
  ↓
INTEGRATION
  ↓
CLOSEOUT
  ↓
RELEASE
  ↓
WORKFLOW_CLOSEOUT
  ↓
DONE
```

`BLOCKED` is an explicit state, not a synonym for incomplete. `advance_stage.py` permits only declared
transitions, validates the proposed target, and restores the ledger when validation fails.

## Entry and exit gates

| Stage | Entry gate | Exit gate |
|---|---|---|
| Intake | Tier C classification | Valid ready intake or explicit product block |
| Discovery | Ready intake | Required evidence packs validate |
| Evidence Review | Evidence exists | Premise verdict `EVIDENCE_READY` or human-accepted named risk |
| Definition | Ready premise | Traceable DoG/architecture/tickets authored |
| Ticketing | Valid artifacts | Human-approved DoG and tickets |
| Seam Review | Approved DoG/tickets | Prebuild `SEAMS_SOUND` |
| Build | Prebuild sound | Every ticket `TICKET_EVIDENCE_GREEN` |
| Integration | Evidence-green tickets | Postbuild `SEAMS_SOUND` and one build identity |
| Closeout | Integrated candidate | Release-ready or human-accepted yellow |
| Release | Closeout-ready candidate | Production SHIP, final judge GREEN, guard and release receipt |
| Workflow Closeout | Release result | Proposals dispositioned or no-change rationale recorded |

`validate_project.py` checks these prerequisites, artifact schemas, hashes, build identity, and spawn
budget for the current stage.

## Artifact graph

```text
intake-readiness.json
        ↓
evidence/*.json ────────┐
        ↓                │
premise-verdict.json     │
        ↓                │
definition-of-good.json ←┘
        ↓
architecture.md + traceability.json
        ↓
tickets/*.json
        ↓
prebuild-verdict.json
        ↓
ticket receipts + code
        ↓
postbuild-verdict.json
        ↓
findings + closeout/verdict.json
        ↓
production-audit.json
        ↓
final-judge.json
        ↓
guard-receipt.json + release/receipt.json
        ↓
improvement proposals
```

The root session writes project state. Read-only agents return structured material; the root validates,
writes, hashes, and records it with `record_artifact.py`.

## Loop map

| Loop | New input required | Exit | Escalation |
|---|---|---|---|
| Clarification | Human answer | Intake ready/blocked | Six questions still leave material fork |
| Discovery | New source/probe/decision | Evidence ready | MUST remains conflicted/unknown |
| OmniDex repair | Traceability/decomposition finding | Approved artifacts | Same defect survives one repair |
| Ticket repair | Concrete failing check | Evidence green | Same failure survives two distinct repairs |
| Integration repair | Changed integrated build | Seams sound | Same seam survives two waves |
| EI audit/repair | Changed build + fresh team | Terminal state | Max rounds or decision/environment block |
| Visual polish | New screenshots | Confirmation pass | Second pass reveals structural issue |
| Workflow improvement | New project evidence | Promote/reject/defer/retire | No benefit or excessive ceremony |

## Discovery profiles

- **Lite:** Product/Domain, Combined Engineering, Premise Auditor.
- **Standard:** Product/Domain, Frontend/Experience, Backend/Systems, Security/Privacy, Premise Auditor.
- **Full:** Standard plus up to three justified specialist/challenge roles.

Every role writes the same evidence-pack contract. The lite combined researcher must return
`STANDARD_PROFILE_REQUIRED` when compression hides material independent complexity.

## Capability providers

The canonical registry is `.claude/capabilities/registry.json`. Project entries override user entries.
Each provider declares stage, authority, consumes/produces, conflicts, eval, and uninstall path.

`resolve_capabilities.py` fails closed on:

- unknown capability;
- provider or capability conflict;
- stage mismatch;
- missing provider skill.

Core workflow skills never hard-code a stack of frontend/design/test providers. The approved ticket asks
for a capability; the resolver selects the provider just in time.

## Separation of duties

- Control roles coordinate and write ledgers.
- Production roles edit only approved ticket scope.
- Assurance roles are read-only by frontmatter tool lists.
- Product/risk decisions remain human-owned.
- Architect owns technical coherence.
- Integration owns composition.
- Triage validates findings.
- Ticket verifiers retest repairs.
- The fresh release judge is distinct from Production Audit.

## Installation architecture

The installer:

- previews by default;
- requires an explicit keep/replace decision for an existing global constitution;
- backs up overwritten files;
- merges router, destructive guard, notification, and auto-accept settings;
- records installed hashes and prior files in an exact manifest.

The uninstaller preserves files changed after installation unless `-ForceModified` is explicit. It
removes only Turn Up Time hook rows by default and restores the full settings backup only when asked.
