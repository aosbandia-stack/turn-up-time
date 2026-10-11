# Bandia coordinator: provider bundle to verified application

This runbook connects the source-owned provider generation to an existing local Studio
Task and worktree. It requires the matching Studio runtime/CLI build with TUT task binding
and bundle delivery support. Local fixture success does not establish a running installed
Studio, live external-provider access, owner signing enrollment, or release approval.

## 1. Stage and verify the complete generation

Run from this workflow repository using Python 3.11+ with its declared dependencies
(including jsonschema). Paths below are examples; the controller chooses the actual
task worktree, project directory, coordinator handle, and Run. The project must be inside
the existing local worktree. Never borrow another Run's coordinator authority.

```powershell
$workflowRoot = 'C:/Users/Bandi/turn-up-time-gauntlet-20261010'
$providerHome = "$workflowRoot/.claude/runtime/provider-candidate"
$generation = 'gauntlet-20261010-v4'
python "$workflowRoot/scripts/provider_install.py" stage --home $providerHome --generation $generation --apply
python "$workflowRoot/scripts/provider_install.py" verify-generation --home $providerHome --generation $generation
```

Stage downloads reviewed immutable source blobs when needed; it never executes upstream
installers. The tested v4 generation contains 23 packages and 555 assets. Staging does not
select a global generation or prove external runtime readiness. Preserve an existing
generation ID; changed content needs a new ID. The legacy installation is not overwritten.

## 2. Reserve the real Task ID and prepare trusted inputs

Use the CLI matching the running Studio: `orca` for the installed runtime or `orca-dev`
for its development runtime. These commands require the current Run's authenticated
coordinator. Source checkout presence alone does not make either runtime available.

```powershell
$orca = 'orca-dev'
$coordinator = '<current-coordinator-handle>'
$runId = '<current-run-id>'
& $orca orchestration task-create --spec 'Reserved for approved TUT bundle' --from $coordinator --run $runId --json
```

Take the actual returned Task ID; do not invent or replace it. Before dispatch, the
controller writes `authorization.json` and `brief.txt` into the selected project. The
authorization is a trusted controller input, not a worker-authored claim. Its required fields:

```json
{
  "schema_version": 1,
  "generation_id": "gauntlet-20261010-v4",
  "project_id": "<project-directory-basename>",
  "task_id": "<actual-Studio-task-id>",
  "build_identity": "<approved-current-build>",
  "stage": "BUILD",
  "role": "implementation-engineer",
  "capability_ids": ["backend-architecture", "ponytail-implementation"],
  "registry_sha256": "<reviewed-generation-registry-SHA256>",
  "lock_sha256": "<reviewed-generation-lock-SHA256>",
  "environment": "local:win32"
}
```

The hashes come from the approved generation's exact `registry.json` and
`provider-lock.json` bytes. The selected capability IDs must include the complete resolver
closure. They cannot be expanded by the worker. Control capabilities such as cleanup
ownership and irreversible-write guards are restricted to controller roles
(`turn-up-time`, `root`, or `controller`); they do not grant approval for an action.

For UI work, optionally add strict `ui_surfaces` entries to this authorization:

```json
{
  "ui_surfaces": [{
    "id": "app", "platform": "web", "purpose": "operate",
    "stack": "react-tailwind", "flags": ["21st-catalog"],
    "verification_capabilities": []
  }]
}
```

That example's closure includes `frontend-operate` when explicitly requested, plus
`ui-operate`, `browser-e2e`, and `21st-catalog`. The existing resolver owns expansion and
platform/stack compatibility. Do not drop the browser requirement to make assembly pass.

External capabilities additionally need an actual current `capability-readiness` record
with matching project/environment, required checks, and hashed evidence. Studio derives
its trusted environment as `local:${process.platform}`: `local:win32`, `local:linux`, or
`local:darwin`. The manifest carries the earliest selected receipt expiry per provider;
Studio rechecks expiry and environment before effects. Fresh metadata is not a substitute
for actual tool access, runtime connectivity, permitted egress, or entitlement.

## 3. Assemble, then export the coordinator binding

All assembler evidence paths are **project-relative**. Studio's `manifestPath` is
**worktree-relative**. `export-task` performs this conversion with containment, regular-file,
symlink/reparse, hash, and task-context checks. It writes a new export file; it never binds
the Task or launches a worker.

```powershell
$worktreeRoot = '<approved-existing-local-worktree-absolute-path>'
$projectRoot = "$worktreeRoot/.claude/projects/<project-directory-basename>"
$authPath = "$projectRoot/authorization.json"
$build = '<approved-current-build>'
python "$workflowRoot/.claude/scripts/assemble_worker_bundle.py" assemble --home $providerHome --project $projectRoot --authorization $authPath --role implementation-engineer --stage BUILD --build-identity $build --capability backend-architecture --capability ponytail-implementation --output manifest.json
```

For external selections, supply `--readiness <actual-readiness-file>` and the appropriate
capability arguments. Any missing requirement yields `BLOCKED` and no manifest. Record
the exact `manifest.sha256` from the successful response in controller state; do not later
replace it with a worker-supplied digest.

```powershell
$manifestHash = '<manifest.sha256-from-successful-assembly>'
python "$workflowRoot/.claude/scripts/assemble_worker_bundle.py" export-task --worktree $worktreeRoot --project $projectRoot --authorization $authPath --manifest manifest.json --manifest-sha256 $manifestHash --brief-file brief.txt --output coordinator-export.json
$export = Get-Content "$projectRoot/coordinator-export.json" -Raw | ConvertFrom-Json
```

The export contains exactly `schema_version`, `task_spec`, and `worker_start_params`.
`task_spec` has the strict `tut-worker-task-v1` kind, brief, and pinned authorization.
`worker_start_params` contains `task` and `tutCapabilityBundle`; the latter contains the
converted manifest path, raw-byte hash, role, and capability IDs. The controller retains
the export hash returned by the CLI. Changed requirements or content require a new
reviewed artifact and Task binding; existing export files are never overwritten by this CLI.

## 4. Bind through the authenticated coordinator, then launch

```powershell
$taskSpecJson = $export.task_spec | ConvertTo-Json -Depth 50 -Compress
$bundleJson = $export.worker_start_params.tutCapabilityBundle | ConvertTo-Json -Depth 20 -Compress
$taskId = $export.worker_start_params.task
& $orca orchestration tut-task-bind --task $taskId --task-spec $taskSpecJson --from $coordinator --run $runId --json
& $orca orchestration worker-start --task $taskId --agent codex --worktree '<existing-worktree-selector>' --from $coordinator --run $runId --tut-capability-bundle $bundleJson --json
```

The binder permits the current Run coordinator to bind an undispatched Task and refuses
replacement of existing TUT authority. The worker runtime negotiates bundle support and
validates the stored Task binding before dispatch or terminal creation. Only an existing
local worktree is supported. Remote delivery and old runtimes without the capability block.
The normal graph's signed stage requirements remain applicable outside the recorded local
bootstrap exception. Task binding is not an owner signature or deployment authorization.

Capture the actual worker-start response and durable dispatch evidence. Studio passes
the verified instruction bytes through the common delivery path for both structured and
terminal transports, with instruction bytes included in the prompt budget. Its delivery
receipt binds the actual Task, dispatch, generation, and instruction/manifest hashes.
A successful delivery receipt means delivery, not provider application or accepted work.

## 5. Validate actual provider application separately

Produce one application receipt per selected provider under
`worker-provider-receipt.schema.json`. Each receipt binds the actual Task/dispatch/build,
generation, manifest hash, capability IDs, and instruction hash. All evidence uses
`{ "path": "<project-relative-file>", "sha256": "<exact-file-hash>" }` references.

For `APPLIED`, invocation records must bind the controller-known worker identity and
context; nonempty outputs must be consumed by every contract in that provider's
`required_outputs`; an independent evaluator must verify those exact invocation, output,
and consumption artifacts. The controller supplies evaluator identity and keeps verification
artifacts outside worker authority. Hashes establish integrity, not authorship or honesty.
The concrete record fields are enforced by `validate_receipt` in the assembler module.

```powershell
python "$workflowRoot/.claude/scripts/assemble_worker_bundle.py" validate-receipt --project $projectRoot --authorization $authPath --manifest manifest.json --manifest-sha256 $manifestHash --receipt '<provider-application-receipt.json>' --dispatch-id '<actual-dispatch-id>' --worker-id '<controller-known-worker-id>' --evaluator-id '<independent-evaluator-id>'
```

Missing contracts, empty outputs, wrong context, self-verification, stale hashes, or
unconsumed outputs cannot pass. `FAILED` and `BLOCKED` receipts remain unaccepted. The
gauntlet and release judge consume this evidence under their existing requirements.

## Reproduce the source fixture and local contract checks

```powershell
python runtime/tests/test_worker_bundle.py
python runtime/tests/generate_worker_bundle_fixture.py --home .claude/runtime/provider-candidate --generation gauntlet-20261010-v4 --output-dir runtime/tests/fixtures/worker-bundle-crosslanguage --replace-fixture
```

The fixture generator verifies the actual complete staged generation, runs the real
`assemble` and `export-task` CLIs for a clearly synthetic Task, and records raw manifests,
exports, source hashes, and command provenance. Studio's cross-language integration tests
consume those exact generated bytes. This does not execute a live agent or qualify an
external service. `--replace-fixture` is confined to the generator's five named test files
and rejects unmanaged destination files.

## Activation and remaining live prerequisites

Whole-release activation requires the agreed complete qualification, including actual
worker use, external providers, owner-controlled trust/signing where required, and the
current gauntlet/audit verdict. Spending, publication, deployment, and global activation
retain their existing owner approval requirements. A locally assembled bundle cannot
grant any of those permissions.

After those requirements are satisfied, the existing installer supports `select --home
<home> --generation <id> --apply` and `rollback --home <home> --apply`. Validate the approved
target home and generation first. These are separate managed selection operations; the
coordinator sequence above does not perform them. Existing jobs stay pinned to their
recorded generation. A rollback to no managed generation leaves the legacy installation
untouched and makes default managed-generation selection unavailable. Already authorized
explicit generation pins remain resolvable for staging and existing jobs. The controller
must enforce activation policy when selecting generations for new jobs.
