# Gauntlet and bounded triage

This is an opt-in component of the existing Turn Up Time controller, closeout loop and signed
stage gates. It neither launches a replacement controller nor grants approval. A component pass
is not release readiness. The current TypeSafe adapter is optional and has **only fixture contract
tests**, not live accuracy/latency qualification. All external providers remain subject to current
capability readiness and approved egress/cost settings.

## Run the synthetic examples

From the repository root with the workflow Python environment (including jsonschema) available:

```powershell
python .claude/scripts/gauntlet_examples.py local-synthetic-gauntlet
python .claude/scripts/triage_decision.py local-synthetic-gauntlet/triage/input.json --project-root local-synthetic-gauntlet
$gauntletDigest = (Get-FileHash local-synthetic-gauntlet/gauntlet/contract.json -Algorithm SHA256).Hash.ToLowerInvariant()
$verifierDigest = (Get-FileHash local-synthetic-gauntlet/evidence/attestation.json -Algorithm SHA256).Hash.ToLowerInvariant()
python .claude/scripts/gauntlet_contract.py --project-root local-synthetic-gauntlet --project-id synthetic --build candidate --contract-sha256 $gauntletDigest --round-event round-1 --round-event round-2 --assurance-id verifier --assurance-proof "verifier=evidence/attestation.json@$verifierDigest"
python .claude/scripts/gauntlet_contract.py --project-root local-synthetic-gauntlet --project-id synthetic --build candidate --contract-sha256 $gauntletDigest --results gauntlet/required-skip.json --round-event round-1 --round-event round-2 --assurance-id verifier --assurance-proof "verifier=evidence/attestation.json@$verifierDigest"
```

The valid gauntlet returns `COMPONENT_PASS`, exit 0, with a denominator of one. The required-skip
case returns `BLOCKED`, exit 2. Triage returns a bounded repair recommendation; it performs no
dispatch. Every example approval and receipt is explicitly synthetic. Generating a fixture is not
evidence of a real model, app, browser, independent reviewer or approval. Prebuilt synthetic inputs
also live under `docs/fixtures/gauntlet/synthetic/`.

In production, `--contract-sha256` must come from the independently approved Definition of Good,
not be recalculated from whatever matrix a worker supplies. The CLI's project/build, assurance IDs,
and round-event arguments are trusted controller inputs, not assertions accepted from a worker.
The CLI is a diagnostic verifier; the existing signed stage transition remains authoritative.

## Lock completion before evaluation

1. Persist `gauntlet/contract.json` conforming to `gauntlet-contract.schema.json`. It enumerates all
   MUST requirements, stable check/journey/state/surface identities, required flags, expected behavior,
   mandatory finding IDs, the original failure and immutable repair acceptance, and shared round budget.
2. Add one MUST requirement to the normal Definition of Good with `acceptance.check` equal to
   `gauntlet-contract`, `acceptance.type` equal to `deterministic`, and `acceptance.expected` equal to
   `sha256:<raw UTF-8 contract file digest>`. Retain all existing definition fields, traceability and
   approvals. Approval of this definition locks the matrix independently of results. Every other MUST
   requirement must occur in the contract; no new root fields are added to existing schemas.
3. Record results in `gauntlet/results.json`, including every declared check exactly once. The validator
   computes required counts from the pinned matrix. Required FAIL, SKIPPED, BLOCKED or UNKNOWN cannot
   count as completion. PASS requires a hashed existing verification receipt with matching check,
   project and final candidate, whose real evidence files also match their hashes.
4. Persist current finding-v2 snapshots in `closeout/findings/<id>.json`. Include every snapshot as a
   hashed result reference. If the existing `closeout/findings.jsonl` is used, snapshots must exactly
   match the latest record per ID, including rejected or deferred findings. Do not replace or discard
   the original log. Any S0/S1/S2 or declared mandatory finding requires VERIFIED status plus original
   failure replay and affected required journey evidence on the final candidate.
5. Repairs must retain the locked acceptance hash and original FAIL receipt. A current PASS replay
   and all affected journeys must be supplied. The verifier must be an assurance dispatch ID from the
   existing ledger, different from the locked implementer and contract author. A normal receipt with
   check ID `gauntlet-verifier:<dispatch ID>` must bind the exact replay hash and current candidate.
   Its path must be registered in that completed assurance dispatch's ledger `artifact_refs`, and
   its hash must already be recorded by the controller in ledger `artifacts` with CURRENT/APPROVED
   status and schema `verification-receipt.schema.json`. The check uses this recorded hash, never
   a hash calculated from potentially replaced attestation bytes. Missing recording blocks. The
   diagnostic CLI instead requires a controller-supplied `--assurance-proof verifier=path@sha256`.
   A verifier name alone cannot pass. The root persists assurance-returned artifacts and provenance;
   the existing worker/runtime boundary must enforce identity, artifact ownership and ledger access.
6. `budget.event_ids` must exactly match terminal `round_history`, preserve the locked baseline prefix,
   and stay within the same max-rounds budget. A final passing round may use the last available round;
   unresolved work does not become complete when the budget is exhausted. No per-provider extra rounds.
7. Put a normal verification receipt at `gauntlet/verification.json` with check ID `gauntlet-contract`,
   matching final project/build, status PASS and a hashed reference to `gauntlet/results.json`.
   Include this receipt in the existing terminal packet's `evidence_refs`. Existing `check_closeout`
   recomputes the component checks; writing a PASS receipt alone cannot pass the gate.

Approval/versioning of changed requirements or coverage remains human-owned. Ordinary newly
discovered defects use append-only repair obligations without changing the approved matrix:

1. Triage validates a finding-v2 observation against an existing requirement. Root records a
   `gauntlet-repair-obligation.schema.json` artifact before dispatching the authorized repair. It
   binds project and unchanged contract digest, original finding and FAIL receipt hashes, original
   build, unchanged acceptance hash, requirement IDs, implementer dispatch ID/owner role, affected
   locked check IDs, existing repair-authority reference and recording timestamp.
2. Root uses the existing runtime artifact-recording operation to register the obligation's path,
   raw SHA256, CURRENT/APPROVED status and schema in ledger `artifacts`. The production dispatch
   names that path in its existing `artifact_refs`; its role and time must match the obligation.
   Recording is performed by the controller before repair, not self-authorized by the engineer.
3. The closeout hook loads **every** recorded obligation from trusted ledger artifacts. Results
   cannot choose a subset. Obligations append to historical locked repair cases and cannot overwrite
   one another, discard history via status changes, widen requirements, reduce required checks or
   restart budgets. The original finding, authority and failure evidence must agree.
4. After targeted repair, the current finding must retain its acceptance/requirements and be
   independently verified. Existing replay, affected journey and recorded assurance attestation
   checks apply. Replay and assurance attestation timestamps must follow production completion,
   and attestation cannot precede the replay. Affected journey proofs must also follow repair
   completion. Missing/altered obligations, missing findings or missing repairs block completion.

The diagnostic CLI can load these controller-owned bindings with
`--controller-ledger project-ledger.json`; the caller must supply the trusted complete ledger.
The integration hook always uses the existing project ledger. Signed graph validation remains
responsible for controller authority and ledger integrity; workers may not mutate those records.
Cleanup changing the candidate still requires fresh affected proof. Existing production audit and
fresh judge checks remain authoritative.

### Retain and validate false positives and duplicates

A current `REJECTED` or `SUPERSEDED` status never removes work by itself. Root records original
finding-v2 observations immutably in the existing ledger artifact index before triage and preserves
the finding log. Historical material observations remain material even if a worker lowers severity.

For a legitimate false positive or duplicate, the completed independent triage-lead dispatch returns
a `gauntlet-finding-disposition.schema.json` artifact with project/build/contract identity, original
finding hash, rejection or duplicate action, hashed evidence, substantive rationale, affected locked
check IDs, dispatch ID and checked time. Root records its hash/schema/status in the existing ledger
and links its path in that triage dispatch's `artifact_refs`. An engineer's status change or unrecorded
disposition cannot satisfy this provenance requirement.

- Rejection retains the finding as `REJECTED` / `NOT_RUN`; no repair verification is invented.
- A duplicate remains `SUPERSEDED` / `SUPERSEDED` and links directly to a surviving canonical finding.
  Chains, self-links and missing targets are rejected. The canonical finding must cover the duplicate's
  requirements, and all declared affected checks remain in required coverage. A material duplicate
  makes its canonical finding mandatory even if the canonical's severity is lower. An unresolved
  canonical finding still blocks closure.
- Original fields, including severity, requirement bindings, acceptance and observations, remain
  unchanged except disposition status fields. Recorded dispositions cannot erase a locked mandatory
  case or an already authorized repair obligation; those require an explicit controller escalation.

Dispositions must be revalidated after a candidate changes. Append a new disposition with a
`supersedes` reference containing the previous disposition's exact path and hash; initial entries
use null. Keep every prior artifact and record in the ledger (CURRENT/APPROVED), with its original
triage provenance. The validator checks the entire chain, forbids forks/cycles/missing predecessors,
and uses its single latest disposition for the current candidate. This preserves history without
reusing an old candidate's triage judgment. The same `--controller-ledger` CLI option loads all
recorded obligations, dispositions and original finding snapshots.

## Triage contract

`triage-input.schema.json` embeds finding v2 and references a hashed `triage-policy` and prior
`triage-authority` artifact. The input must match the current candidate and known requirements;
finding evidence must be present and hashed. Authority references existing approval, exact finding,
candidate, requirements and allowed owner roles. This validator checks scope but does not issue or
cryptographically authenticate a new grant: root must still enforce its existing approval gates.

Deterministic policy can route an already validated finding to an explicitly declared owner without
a model call. Two failed repair attempts refer to the architect; product questions refer to the owner;
new scope refers to the architect. Missing evidence or authority blocks repair routing. Unresolved
semantic ownership is PENDING for the explicitly selected reasoning fallback, or BLOCKED. PENDING
means a real separate reasoning judgment is still needed, never that one was simulated.

The decision schema includes `LINK_DUPLICATE` and `REJECT_WITH_EVIDENCE`. The fast model adapter does
not emit either automatically: the existing independent human/reasoning triage role retains those
judgments and supplies the controller-recorded disposition contract above. It must preserve source
evidence and affected journeys. A model confidence score cannot hide a material defect.

### Optional TypeSafe Jev owner selection

Assumption: the proposed Jev means TypeSafe AI. Invocation requires explicit `provider.mode=jev`,
`permit_egress=true`, `permit_cost=true`, exact `jev-X.Y.Z` revision, and the exact permitted field
set `expected, observed, impact, recovery, type, severity, requirement_ids`. Only these fields leave
the machine as named JSON state. No raw evidence files, keys, paths or arbitrary input fields are sent.
The key is read from `TYPESAFE_API_KEY` only after configuration and qualification pass; keys and
server error bodies are never emitted. No auto retry, redirect, custom host or hidden model fallback.

The current policy must explicitly allow `owner-routing` and pin the qualification artifact hash in
`qualification_refs`. A qualification binds provider, exact revision, decision class and evaluated
probability threshold to evidence of actual held-out tests. Its `policy_sha256` is SHA256 of sorted,
compact JSON of the policy **excluding `qualification_refs`**; this avoids a circular hash. The input
and output still bind the complete raw policy file hash, including those qualification refs.
Qualification evidence must be independently accepted; a schema-valid fixture is never enough.

The question offers only currently authorized candidate owners plus a no-match option. Response
model, question IDs, type, option IDs, probability range/normalization and configured threshold must
match. Timeouts, malformed output, missing keys, model drift and insufficient probability return the
selected PENDING/BLOCKED fallback. A successful response remains a recommendation to the control
plane. It does not verify a repair, change severity, approve scope or release.

Primary upstream protocol source inspected October 10, 2026:
https://docs.typesafe.ai/introduction/quickstart (POST `https://api.typesafe.ai/v1/systemone`, Bearer
auth, typed choice criteria and `answers` response). This is a documentation snapshot observation,
not a live compatibility certification. Provider pinning is owned by the provider package; the
adapter requires an explicit model revision and rejects `jev-latest`. No paid/live requests were run.

## Skill/provider placement

- Root `/turn-up-time` owns scope, approvals, build identity, shared budget and dispatch.
- `/boil-the-ocean` gives scoped engineers the resolved `ponytail-implementation` method. Optional
  `code-symbol-analysis` identifies affected callers and `dependency-docs` supplies versioned API docs.
- Existing triage-lead uses `typed-decision-guidance`; `fast-triage-decision` is a separately ready,
  optional external capability. Its absence must not pretend a Jev judgment happened.
- `/easily-irritated` owns fresh reviews, the existing targeted repair loop, independent verification,
  complete journey replay and terminal packet. Gauntlet checks add fixed coverage evidence.
- Swiper owns cleanup scope; `ponytail-review` supplies review/simplification guidance. Impeccable,
  21st.dev and relevant frontend providers operate only inside approved polish scope.
- `/its-not-you-its-me` and `/eval-harness` consume rework evidence to propose/test a new process version.
  The running gauntlet never rewrites its own success criteria to obtain a pass.

Run scoped regression tests with `python -m pytest runtime/tests/test_triage_decision.py
runtime/tests/test_gauntlet_contract.py runtime/tests/test_evidence_contracts.py -q`. The tests cover
seeded omissions, tampering, stale candidate, required skips, independent repair proof, authority,
uncertainty and mocked provider failures. They establish local component behavior only.
