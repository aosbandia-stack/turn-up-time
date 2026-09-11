# Turn Up Time Architecture

## Ownership and handoffs

| Stage | Owner | Required output | Product editing |
|---|---|---|---|
| INTAKE | Root control + conditional `/grill-me` | Ready intake and signed owner approval | No |
| DISCOVERY | Profile-selected research roles | Required evidence packs | No |
| EVIDENCE_REVIEW | Fresh Premise Auditor | EVIDENCE_READY or EVIDENCE_BLOCKED | No |
| DEFINITION | `/omnidex` + owner | Approved Definition of Good | No |
| TICKETING | Architect + `/omnidex` + owner | Architecture, traceability, approved tickets | No |
| SEAM_REVIEW | Integration Lead | PRE_BUILD SEAMS_SOUND | No |
| BUILD | `/boil-the-ocean` + scoped engineers | Independently verified ticket receipts and assembled build | Approved ticket scope |
| INTEGRATION | Integration Lead | POST_BUILD SEAMS_SOUND | No |
| CLOSEOUT | `/easily-irritated` team | Parsed terminal packet and verified findings | Separate authorized repair engineers |
| RELEASE | Production audit + fresh judge + owner | Matching audit/judge packets and signed release verdict | Separately gated operations only |
| WORKFLOW_CLOSEOUT | `/its-not-you-its-me` | Evidence-backed proposal or NO_WORKFLOW_CHANGE_PROPOSED | No automatic workflow edits |

The root coordinates state updates; the runtime writes the initialized ledger. Workers return
artifacts, not ledger edits. Assurance tool profiles are useful restrictions, not an OS sandbox.
Unattended workers must not control the runtime, trust configuration, ledger, signing key, or grader.

## Stage prerequisites

DISCOVERY requires ready intake; EVIDENCE_REVIEW requires profile evidence; DEFINITION requires
EVIDENCE_READY; TICKETING requires the approved Definition of Good; SEAM_REVIEW requires approved
schema-valid tickets, valid dependencies, and unique canonical file ownership. BUILD requires
PRE_BUILD SEAMS_SOUND. INTEGRATION requires complete structured evidence for every acceptance
check. CLOSEOUT requires POST_BUILD SEAMS_SOUND. Entering RELEASE requires a parsed compatible
closeout packet. The release verdict is produced inside RELEASE and checked before advancing to
WORKFLOW_CLOSEOUT or DONE—not required before its own stage can run.

Integration and subsequent stages compare the ledger's assembled identity to the actual workspace.
Receipt files must exist inside the project and match their recorded SHA-256. Release checks parse
separate production-audit/final-judge packets and require matching identity and compatible verdicts.
Signatures bind human decisions to exact action IDs, code, ledger, and evidence; a name is not proof.

## Control operations and persistence

`topology.py` remains the sole business-stage authority. `record_artifact`, `reserve_spawn`,
`complete_spawn`, and `set_build_identity` are metadata operations; they cannot change stage or
approve a gate. Reserve-before-dispatch is mandatory, and failed work does not refund spent budget.
These commands do not themselves launch or isolate a worker.

The exclusive project writer stores a validated intent in `.runtime/operations.sqlite` before
projecting ledger and events. SQLite checkpoints are separate. A missing checkpoint update is
recovered from its uniquely anchored journal successor without repeating the authorized action.
Conflicting event IDs, simultaneous writers, or unrelated ledger drift fail closed. JSONL remains
logically append-only, with atomic file replacement to avoid torn tails.

## Project workspace

```text
.claude/projects/<project-id>/
  project-ledger.json
  intake-readiness.json
  evidence/
  definition-of-good.json
  architecture.md
  traceability.json
  tickets/
  receipts/
  integration/
  closeout/
  release/
  improvements/
  requests/                  control-operation JSON payloads
  approvals/                 unsigned requests and owner-signed envelopes
  .runtime/operations.sqlite durable operation journal
  .runtime/writer.lock        stable OS-lock file; never delete during use
```

The repo-level checkpoint remains `.claude/runtime/turn-up-time-checkpoints.sqlite`. Back up both
stores together with ledger/evidence while stopped. Never erase a journal to reset loop ceilings.

## Loops, profiles, and providers

Preserve the existing bounded discovery, architecture, ticket, integration, closeout, visual, and
release loops. Every repeated review needs new evidence or a changed artifact; unchanged failure
escalates rather than commissioning another agent. Lite discovery combines engineering; standard
separates UI/backend/security; full adds at most two justified specialists. Profile selection is
based on needed coverage, not a minimum agent-count target.

Capability resolution expands dependencies, rejects conflicts, and checks provider availability.
Project registry overrides user registry, which overrides bundled defaults. Load only approved
providers. Dashboard/product work uses frontend-operate, not a marketing style constitution.

## Operational limit

Recovery and evidence checks are not a full autonomous execution service. Worker timeouts,
cancellation, isolated credential handling, live model execution, and the owner decision interface
require a chosen supervisor and a measured pilot. Do not stack a second planner on top of this
control authority. See [HARDENING.md](HARDENING.md) and [PILOT.md](PILOT.md).
