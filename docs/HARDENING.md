# Runtime hardening and migration

This source reconciles the runtime hardening with the Swiper completion contracts. The v1.0.0 release
tag and existing installations are not rewritten by a source integration. Test a disposable project before
upgrading an in-flight one. A stronger model is not a replacement for these checks.

## What this implements

The runtime is the only supported writer of an initialized project ledger. Skills
request metadata operations or legal stage transitions; they do not edit the
ledger. `topology.py` still owns business-stage movement. Metadata operations can
revisit the same stage without changing its history or granting approval.

Each operation uses an explicit event ID, an OS-level per-project writer lock,
and a SQLite write-ahead journal. The journal records the validated intent before
projecting the ledger and logical append-only JSONL history. Recovery finishes
that intent and restores its checkpoint update; it does not rerun an agent, a
payment, a merge, or a deployment. Unknown ledger drift stops recovery rather
than overwriting it. Identical retries return the prior outcome; conflicting
reuse of the ID fails.

Missing validators, failed validators, and validation timeouts stop advancement.
Entering integration and subsequent release stages also requires a current,
runtime-derived Git/workspace identity. Stopping at BLOCKED remains possible
without complete product artifacts.

## Trust boundary: read this before enabling unattended work

This is NOT an OS sandbox, autonomous worker daemon, or hosted approval service.
An unrestricted process under the owner's OS account can edit Python, replace
trust configuration, change its home directory, or write files directly. File
hashes and signatures do not remove that authority. The supported protection
requires a trusted controller with protected runtime, validators, ledger, and
trust configuration; untrusted workers must not be able to write those paths.

Keep the Ed25519 private signing key outside the worker's account/container. The
worker only sees a read-only public trust file and signed approval envelopes.
Do not mount production credentials into a coding worker. Do not treat a Git
worktree, absence of Edit/Write tools, or the command regex guard as a sandbox.
The guard is a narrow backstop and now denies malformed input instead of silently
allowing it. External effects still need a separate controlled execution path.

The installer does not create a signing key, public trust configuration, worker
isolation, or a release authorization. `-EnableAutoAccept` remains an explicit
opt-in, not the recommended initial installation command.

## Owner-signed approvals

A name supplied through `--approved-by` is only a display identity. A human-gated
transition also requires `--approval-ref` naming a project-relative JSON envelope.
The signature binds the event ID, gate, source/target stages, approver, absolute
workspace location, ledger hash, code identity, receipt references, and evidence
manifest, including both project capability readiness and registry files. Changing any of these requires a fresh approval. Expiry is at most 24
hours. Each trusted key lists its permitted gates; keys and individual approvals
can be revoked.

The controller reads `.claude/turn-up-time-trust.json` under the **OS account's**
home — resolved from the POSIX password database or the Windows process token,
never from `HOME` or `USERPROFILE`. An earlier build resolved it with
`Path.home()`, which expands those variables; a process could therefore point
`HOME` at a directory holding its own trust file, name its own key as the owner,
and have a forged approval accepted on any gate, including `RELEASE`, without
modifying a single protected file. See `docs/SECURITY-BOUNDARY.md`.

To keep the trust file somewhere protected (for example root-owned under `/etc`),
set `TURN_UP_TIME_TRUST_FILE` to its absolute path. The runtime refuses that
override when the file's permissions grant write to the account running the
controller, so it cannot be redirected at a file the caller just wrote. That
raises the cost of substitution; under a single OS account it is not isolation.

A trusted operator provisions the trust file, not a ticket or worker. Format:

```json
{
  "keys": {
    "owner-2026": {
      "public_key": "BASE64_OF_RAW_32_BYTE_ED25519_PUBLIC_KEY",
      "approver": "Owner",
      "gates": ["INTAKE", "DEFINITION", "TICKETS", "RELEASE", "ACCEPTED_RISK"],
      "revoked": false
    }
  },
  "revoked_approvals": []
}
```

The public key must correspond to the owner's separately provisioned Ed25519
private key. No example key in a test is an operator key. The owner-only signer
accepts a PEM private key and refuses to overwrite an existing envelope. It lives
in root `scripts/`, outside the worker skills/scripts installer copy set.

PowerShell example after provisioning that trust boundary:

```powershell
$repo = 'C:\work\my-app'
$project = Join-Path $repo '.claude\projects\pilot'
$graph = Join-Path $HOME '.claude\scripts\turn-up-time-graph.ps1'
New-Item -ItemType Directory -Force (Join-Path $project 'approvals') | Out-Null
& $graph request-approval --repo-root $repo --project-dir $project `
  --event intake_ready --event-id pilot-intake-001 --approved-by Owner |
  Set-Content -Encoding UTF8 (Join-Path $project 'approvals\intake-request.json')
```

The owner inspects that request outside worker authority, then signs it:

```text
python scripts/sign_approval.py --request intake-request.json --private-key owner-key.pem --key-id owner-2026 --approver Owner --output intake-signed.json
```

Return only the signed envelope to `approvals/intake-signed.json` in the project.
Then submit the exact action:

```powershell
& $graph signal --repo-root $repo --project-dir $project `
  --event intake_ready --event-id pilot-intake-001 --approved-by Owner `
  --approval-ref approvals/intake-signed.json
```

A retry uses the SAME event ID and arguments. Approval files live in `approvals/`,
not `receipts/` or `release/`, to avoid a circular signature dependency. Record
metadata and complete the artifact packet before requesting approval. Requests
approve stage bookkeeping, not arbitrary external deployment commands.

## Bookkeeping without direct ledger edits

Submit control operations using `signal --event <operation> --event-id <stable-id>`.
Payloads can use `--data-json` or a project-relative `--data-file`. Prefer files in
PowerShell 5.1 to avoid native argument-quoting ambiguities. `requests/` is a useful
location for those payloads. Each operation accepts only its documented fields.

| Operation | Payload | Effect |
|---|---|---|
| `record_artifact` | `{"path":"intake-readiness.json","schema":"intake-readiness.schema.json"}` | Hash actual bytes and record CURRENT metadata; does not approve content. |
| `reserve_spawn` | `{"spawn_id":"T1-builder","role":"implementation-engineer","role_class":"production","reason":"Implement approved T1"}` | Reserve one spawn before dispatch; reject exhausted budget, duplicate ID, or production outside BUILD/CLOSEOUT. |
| `complete_spawn` | `{"spawn_id":"T1-builder","outcome":"SUCCEEDED","artifact_refs":["receipts/T1.json"]}` | Record completion or FAILED/CANCELLED/TIMED_OUT/INTERRUPTED; never refund consumed work. |
| `set_build_identity` | `{}` | Compute assembled Git/workspace identity; never accept a caller-invented identity. |
| `amend_spawn_budget` | `{"expected_limit":75,"new_limit":85,"reason":"Owner-approved continuation","owner_decision_ref":"receipts/owner-budget.json","owner_decision_sha256":"<actual SHA-256>"}` | Strictly increase the exact old limit; keep used/spawn history intact. Requires the registered CURRENT owner receipt described below. Records old/new/used/reason/decision hash in the event and durable journal. |
| `migrate_ledger_compatibility` | `{"profile":"ledger-v2-risk-severity-v1","expected_ledger_sha256":"<current SHA-256>","backup_ref":".runtime/backups/before-repair/manifest.json","backup_sha256":"<actual SHA-256>"}` | Normalize only known uppercase risk severity labels in ledger v2. Requires a complete current runtime backup. Records every changed field; never changes a decision, approval, stage, definition or evidence artifact. |

Example with `requests/reserve.json` containing the reserve payload above:

```powershell
& $graph signal --repo-root $repo --project-dir $project `
  --event reserve_spawn --event-id pilot-T1-reserve-001 `
  --data-file requests/reserve.json
```

These are accounting and control APIs, not worker launch commands. A future
supervisor must reserve first, launch within isolation, and record the real run
outcome. The project spawn ceiling covers ALL roles and repair attempts. Plan a
sufficient explicitly approved total during intake; do not edit an initialized
ledger to silently raise the ceiling or reset consumption.

For a budget amendment the owner must already have explicitly approved the exact increase. Record
the actual conversation evidence and its provenance in a new receipt, without rewriting historical
proposals or pretending it is cryptographically signed:

```json
{
  "status": "OWNER_APPROVED_IN_CONVERSATION",
  "ownerMessage": "Approved!",
  "authorization": {
    "project_id": "pilot",
    "operation": "amend_spawn_budget",
    "old_limit": 75,
    "new_limit": 85
  }
}
```

Additional top-level provenance is allowed; the `authorization` object must match these exact keys,
types, project and old/new limits. Register the receipt through `record_artifact` first. The operation
checks CURRENT status and both registered/actual hashes under the writer lock, and accepts only
integer increases through 2147483647. The caller cannot supply a new used count. A metadata receipt
is an auditable assertion of already-obtained owner authority, not an identity or signature verifier;
the operator remains responsible for truthful transcription. It cannot authorize any human-gated
stage transition. Approval signature provisioning and verification are unchanged.

## Evidence that can advance a stage

Approved, not-yet-built tickets may retain null evidence. EVIDENCE_GREEN tickets
must have one structured PASS result for every unique acceptance ID. Each result
contains `check_id`, `status`, `build_identity`, `evaluator_role: assurance`,
`evaluator_id`, `evidence_ref`, and `evidence_sha256`. Acceptance evidence must
refer to that same project-local Swiper verification receipt. Its schema, project/check/build identity,
PASS and hashed underlying outputs must also validate. Missing, modified, duplicate, unknown,
failed, or stale-build results block integration. Re-run acceptance against the
assembled build, not different per-worker builds.

Closeout continues to use `terminal-state.schema.json` and the existing Swiper project gate, not a
second raw packet. It binds the current product, installed instruction snapshot, caller checks,
action-specific approved removal guards, owned risks, changed-build reproof and IT handoff. The same
terminal packet gains scope-appropriate completion proof before DONE. Use the current schema/example;
a generic `evidence` array is not a substitute. Production-audit and final-judge components use
canonical `status`, exact build and current receipt evidence. Accepted risks require the existing
human approval and, at the corresponding runtime gate, a valid signed envelope.

These checks establish integrity and cross-artifact consistency. An evaluator
label is not proof of a separately isolated evaluator. The controller/verifier
must produce the actual evidence; builders must not control their own grader.
Current code identity covers Git HEAD and tracked/untracked nonignored files,
excluding project/runtime metadata and Python bytecode caches. It does not attest
an entire deployment image, ignored dependencies, environment, or external data.
Code symlinks and submodules currently fail closed pending an explicit policy.

## Recovery and migration

Use `recover --repo-root ... --project-dir ...`, followed by `status`, then retry
the identical event. Preserve both `.claude/runtime/turn-up-time-checkpoints.sqlite`
and project `.runtime/operations.sqlite` with the ledger and event log. Take
backups while the controller is stopped. Never delete the journal to reset loop
counts, or restore a ledger alone and call it a consistent recovery.

For the bounded ledger-v2 compatibility repair, first quiesce other controllers and run `recover`.
Use `compatibility-plan --repo-root ... --project-dir ...` for a pure read-only list of exact field
changes and the current raw ledger hash. `backup-project --repo-root ... --project-dir ...
--backup-id before-repair` then creates read-only, fsynced copies and a hash manifest under project
`.runtime/backups/before-repair/`. It never overwrites an existing capture. The capture includes the
ledger, event log, all project artifacts and runtime files except nested backups/writer.lock, plus
the repository checkpoint database when present. SQLite uses its online backup API so committed WAL
contents are retained; its sidecars are represented by that database snapshot. Before migration the
runtime checks the exact inventory and all copied hashes, current non-SQLite source hashes, and the
current logical SQLite contents against the snapshot. A partial, stale, modified or incomplete
capture fails closed. Keep runtime backups out of Git; they may contain sensitive project state.

Immediately submit `migrate_ledger_compatibility` with the returned ledger/manifest hashes. Do not
write request files or record other artifacts between capture and migration: the complete inventory
and source checks deliberately reject such changes. Use `--data-json` prepared before capture or
an already-existing request file. Its one profile changes only HIGH/MEDIUM/LOW/CRITICAL to their
lowercase spelling; unknown values and no-op migrations fail. Decision status WITHDRAWN is now
represented directly in the ledger schema and means retracted, non-authoritative history. It is
distinct from RESOLVED and has no effect on signed stage approvals. Re-run the real target validator
after repair; incompatible definitions and evidence must still be authored and reapproved normally.

Exact migration/amendment event retries use the existing durable idempotency journal, including
projection-interruption recovery. A fresh event ID is not a substitute for retry/recover. Backups
are recovery evidence, not an automatic rollback command: restore an entire coherent capture at its
original paths only through an explicitly authorized recovery that preserves later consumed work.
Persisted checkpoints bind absolute repository/project paths. CLI resume/recover rejects a copied
checkpoint whose paths differ, before invoking graph nodes that could write the original workspace.
For a disposable test copy, retain the original checkpoint as evidence and create a fresh isolated
checkpoint from the copied project's retained operation journal. Never rewrite checkpoint paths.

Back up an existing installation and active project state before upgrading.
Existing stage names/topology and ledger schema remain unchanged. Event history
adds CONTROL_OPERATION. Old EVIDENCE_GREEN receipts containing strings or empty
results must be regenerated from real verification. Existing human-gated CLI
calls need signed approval and a stable event ID. Existing raw ledger edits are
not automatically imported or treated as approved. If migration detects drift,
stop and reconcile it with the owner rather than suppressing the error.

## Verification and remaining pilot

The test suite includes positive and negative evidence controls, forged/stale
approvals, duplicate/conflicting event IDs, interrupted projection recovery,
actual CLI process termination and restart, and installed-command bookkeeping.
The old minimal graph unit fixture uses explicit test-only doubles; the CLI
integration tests use real schemas and Ed25519 verification with disposable keys.
Linux and Windows CI retain JUnit results. Missing PowerShell skips only the hook
tests on hosts where it is unavailable; Windows runs them.

A real paid-model Tier C feature pilot, full worker supervisor, production sandbox,
owner approval UI, and ROI comparison are NOT implemented or proven by these unit
and integration tests. Do not label a disposable CLI fixture a shipped app.
See [PILOT.md](PILOT.md) for the acceptance contract for that next operational test.
