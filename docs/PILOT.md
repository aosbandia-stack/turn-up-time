# One-worker operational pilot

Run this only after the hardened runtime passes CI and the owner has provisioned
a protected controller, trust file, and signing path. Do not begin by creating a
fleet or installing multiple competing orchestration frameworks.

## Starting scope

Choose one reversible app feature in a disposable worktree and nonproduction
environment. A useful example is an approval action whose state survives refresh.
One builder implements; a separate verifier owns the acceptance checks. The
business outcome and permissions are approved before work starts. Neither worker
can modify the grader, controller, trust file, or ledger directly.

The execution backend must demonstrate: reserve-before-launch, clean workspace
creation, task identity, timeout and cancellation, process-tree termination,
interrupted-run detection, explicit restart policy, captured stdout/stderr,
resource usage, artifact collection, and cleanup that preserves unmerged work.
A resumed transition must never automatically repeat a merge or deployment.

A supervisor is not integrated in this candidate. Evaluate one backend against
these requirements before adopting it. Do not claim one is better because its
README lists more agents. Do not combine a second planner with TUT's authority.

## Acceptance checks

The user clicks Approve; the authorized state changes; a refreshed session sees
the persisted result. Also test double submission, forbidden approval, backend
write failure, loading/error feedback, and the intended mobile viewport. The
verifier must first demonstrate that a deliberately broken implementation fails.
Evidence identifies the exact assembled code and environment. The owner sees a
compact decision packet only for a true scope, risk, or release decision.

## Compare processes rather than model brands

Use 10-20 representative tasks as an initial diagnostic sample, not a definitive
benchmark. Run a single-agent baseline and the smallest appropriate TUT workflow
from equivalent starting commits and environments. Keep acceptance criteria,
model settings, and available tools comparable; randomize order and repeat some
tasks to reveal variability. Reserve separate tasks when tuning the workflow.

Record one JSONL row per attempt with task_id, arm, start_commit, environment_id,
model/provider/version, success (independent grader), elapsed_seconds, owner_minutes,
usage_cost_usd (null when unavailable), repair_count, escaped_defects, and evidence_ref.
Never report unmeasured costs as zero. Preserve failures and cancellations, not
only successful runs. Do not claim ROI from a deterministic CLI fixture.

Keep stages that reduce failures or owner attention; remove duplicate review that
adds time without a measurable benefit. Expand to multiple builders only after
single-worker cancellation, recovery, evidence capture, and verification pass.
