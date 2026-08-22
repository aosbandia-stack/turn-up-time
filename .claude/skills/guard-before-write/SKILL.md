---
name: guard-before-write
description: Reversibility and accountability gate before destructive, external, production, credential, bulk-data, deployment, or otherwise hard-to-undo actions. Requires blast radius, backup, dry-run, count reconciliation, rollback, and the correct human authorization.
disable-model-invocation: true
---

# /guard-before-write

Auto-accept is convenience, not authority. This gate applies independently of task tier.

## Trigger

Run before:

- destructive or bulk file/data changes;
- schema migration or backfill;
- force/reset/clean operations;
- deploy, publish, release, feature-flag activation, or merge when consequential;
- external messages or state-changing API calls;
- credential/permission changes;
- protected-file or sensitive-data/model-egress operations;
- anything the project marks human-accountable or hard to reverse.

A normal edit inside an approved ticket is not automatically destructive.

## Six required checks

1. **Blast radius** — exact objects and expected count.
2. **Restorable backup** — location, integrity check, and restore command.
3. **Dry-run/sample** — real preview or small-N execution and diff.
4. **Count reconciliation** — expected versus actual, including an explanation for any difference.
5. **Rollback** — executable rollback and conditions under which it is used.
6. **Authority** — explicit human approval when the action is external, destructive, production,
   credentialed, sensitive-data related, or otherwise human-accountable.

## Output

Write or return a guard receipt:

```text
action
blast_radius
backup
sample_or_dry_run
expected_count
actual_count
rollback
authority_required
authority_status
verdict: PROCEED | BLOCK
```

Only `PROCEED` allows the named action, and the receipt does not authorize a different action or
larger scope.

## Stop

If any check cannot be satisfied, return `BLOCK`, state the failed check, and wait. Do not weaken the
gate by rewording the action or splitting a bulk change into hidden smaller calls.

## Prohibited

Do not auto-approve on behalf of the human, treat Git as a backup for uncommitted/external state, or
claim a dry-run when the command still has side effects.
