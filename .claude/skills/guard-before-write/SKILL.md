---
name: guard-before-write
description: Reversibility and accountability gate before destructive, external, production, credential, bulk-data, deployment, or otherwise hard-to-undo actions. Requires blast radius, backup, dry-run, count reconciliation, rollback, and human authorization where accountability remains human-owned.
disable-model-invocation: true
---

# /guard-before-write

Auto-accept and an approved implementation ticket do not authorize consequential actions.

## Required checks

All six must pass:

1. **Blast radius:** name the exact objects, environment, and expected count.
2. **Restorable backup:** give its location, identity, and restore command; create it before mutation.
3. **Dry-run or sample:** run the real operation in preview/transaction/small-N mode and inspect the
   diff.
4. **Count reconciliation:** expected and observed counts must match; explain any zero or discrepancy.
5. **Rollback:** name the rollback owner, command/path, prerequisites, and how it was tested or verified.
6. **Authority:** obtain explicit human approval for external, production, credential, destructive,
   bulk-data, or irreversible action.

If any check fails, stop. “The command is probably safe” is not a receipt.

## Always applies to

- delete, purge, truncate, recursive remove, hard reset, force push, and branch deletion;
- database/schema migrations, backfills, bulk writes, and queue/state moves;
- deployment, publication, production flags, scheduled jobs, and go-live;
- external messages, charges, posts, or API mutations;
- credentials, secrets, access policy, protected data/model egress;
- overwrite of user-owned or protected artifacts without a clean restore path.

Normal edits inside an approved, reversible ticket do not require this gate merely because they write a
file.

## Receipt contract

Before action, write `release/guard-receipt.json` or the applicable project receipt using
`stage-verdict.schema.json` with kind `guard` and status `GUARD_GREEN` or `GUARD_BLOCKED`. Include:

- project/build identity;
- blast radius and expected count;
- backup and restore path;
- dry-run evidence and observed count;
- rollback evidence;
- explicit human approval reference;
- blockers, reviewer, and timestamp.

After the action, append the actual result to the release receipt. A preflight receipt does not prove
the mutation succeeded.

## Stop conditions

Stop when the affected set cannot be named, backup cannot be restored, preview does not exercise the
real operation, counts disagree, rollback is not credible, approval is absent, or the environment is
not the one named in the plan.

Do not route around the deterministic `destructive-command-guard.ps1`; it is the floor, while this
skill is the full evidence gate.
