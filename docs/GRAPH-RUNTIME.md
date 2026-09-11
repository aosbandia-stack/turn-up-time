# Official LangGraph runtime

LangGraph is the control shell beneath the evidence-to-ship workflow. Specialist skills and agents
perform the work; the runtime controls legal stage movement, evidence/approval checks, persistence,
and recovery. It is not a worker daemon or OS sandbox.

## Authority and persistence

`CLAUDE.md` owns principles; `topology.py` owns business-stage transitions, gates, and loop ceilings;
skills own node behavior; schemas and semantic validators own artifact contracts. The root requests
ledger operations, but only the runtime writes the initialized ledger.

Metadata operations record artifacts, reserve/complete spawns, and derive assembled build identity.
They cannot change a stage or grant approval. They appear as CONTROL_OPERATION in the event history.
Business transitions remain EDGE_TRAVERSED and use the unchanged generated topology.

SQLite checkpoints record the graph cursor. A separate per-project `.runtime/operations.sqlite`
journal records each validated operation before the ledger and event-log projections. An exclusive
OS lock serializes project writes. The journal restores a missing checkpoint update after interruption;
unrecorded ledger changes stop recovery. Identical event IDs/payloads return the original outcome,
while conflicting reuse fails. JSONL is logically append-only with atomic file replacement, not
an unprotected physical append.

## Install

Preview first, without enabling auto-accept:

```powershell
.\scripts\install.ps1 -EnableNotifications -ReplaceGlobalConstitution -EnableGraphRuntime
```

After reviewing the plan, add `-Apply`. Python 3.11+ is required. The isolated runtime lives under
`~/.claude/runtime/turn-up-time/`. `TURN_UP_TIME_PYTHON` selects an explicit Python executable.
The installer does not provision signing keys or worker isolation. Read [HARDENING.md](HARDENING.md)
before upgrading an active project or configuring the owner approval boundary.

## Commands

```text
turn-up-time-graph validate-topology
turn-up-time-graph render --repo-root <repo>
turn-up-time-graph status --repo-root <repo> --project-dir <project>
turn-up-time-graph history --repo-root <repo> --project-dir <project>
turn-up-time-graph recover --repo-root <repo> --project-dir <project>
turn-up-time-graph signal --repo-root <repo> --project-dir <project> --event record_artifact --event-id <stable-id> --data-file requests/artifact.json
turn-up-time-graph request-approval --repo-root <repo> --project-dir <project> --event intake_ready --event-id <stable-id> --approved-by Owner
turn-up-time-graph signal --repo-root <repo> --project-dir <project> --event intake_ready --event-id <same-id> --approved-by Owner --approval-ref approvals/intake-signed.json
```

The PowerShell wrapper accepts the same arguments. `--data-file` is project-relative JSON and avoids
native PowerShell JSON quoting problems. A name alone does not approve a gated edge. The owner signs
the exact request outside the worker's authority; the controller verifies the signature, permitted
gate, expiry, code identity, ledger hash, and artifact manifest. Changed inputs need renewed approval.

## Bounded loops

The unchanged executable topology caps product-boundary return at 2, discovery-premise repair at 2,
pre-build seam repair at 1, architecture reframe at 1, integration repair at 2, product closeout repair
at 4, and release repair at 2. New-evidence edges require a nonempty evidence_delta. The root and
independent evaluator must confirm that the described evidence really changed; a nonempty string
alone is not a proof of novelty. Counters survive journal-backed recovery.

## Evidence and current boundary

Missing project validators block advancement. Green tickets require structured, content-addressed
acceptance results. Integration and release stages require the runtime-derived current assembled
build identity. Closeout and separate release audit/judge packets are parsed and cross-checked.

Current tests prove specific control-path behaviors, not production deployment or model quality.
The model-backed worker pilot and outcome benchmark are specified in [PILOT.md](PILOT.md); they are
not automatically performed by installing this runtime. Owner attention and verified task outcomes,
not agent count, determine whether the process should grow or shrink.
