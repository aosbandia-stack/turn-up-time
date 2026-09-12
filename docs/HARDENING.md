# Runtime hardening and migration

This branch is an unreleased hardening candidate. The v1.0.0 release tag and the
owner's existing installation are unchanged. Test a disposable project before
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
manifest. Changing any of these requires a fresh approval. Expiry is at most 24
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

## Evidence that can advance a stage

Approved, not-yet-built tickets may retain null evidence. EVIDENCE_GREEN tickets
must have one structured PASS result for every unique acceptance ID. Each result
contains `check_id`, `status`, `build_identity`, `evaluator_role: assurance`,
`evaluator_id`, `evidence_ref`, and `evidence_sha256`. Acceptance evidence must
refer to that same project-local file. Missing, modified, duplicate, unknown,
failed, or stale-build results block integration. Re-run acceptance against the
assembled build, not different per-worker builds.

Closeout is parsed, not merely checked for existence. Minimal release-compatible
packet fields are:

```json
{
  "terminal_state": "RELEASE_READY",
  "build_identity": "RUNTIME_DERIVED_IDENTITY",
  "open_risks": [],
  "evidence": [{"path": "receipts/journey.json", "sha256": "ACTUAL_SHA256"}]
}
```

Retain the existing scenario/coverage references, finding dispositions, and round
history too. YELLOW_ACCEPTANCE_REQUIRED needs explicitly accepted risks before
release. The separate production-audit and final-judge JSON packets must contain
`status` and the same `build_identity`; the summary cannot substitute for them.
Release evidence references are real project-local files, not prose citations.

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
