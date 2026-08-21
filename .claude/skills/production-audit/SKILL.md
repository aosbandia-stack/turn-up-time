---
name: production-audit
description: Evidence-based release-readiness audit. Checks current build identity, CI/tests, auth, data integrity, migrations, dependencies, operations, observability, rollback, and critical journeys, then requires a separate fresh release judge before release.
disable-model-invocation: true
---

# /production-audit

Production Audit answers whether the approved release candidate is operationally safe to ship. It is
not the final independent release judge and does not reopen product design.

## Entry gate

Require:

- ledger stage `RELEASE`;
- closeout verdict `RELEASE_READY` or human-accepted yellow;
- exact release candidate build identity;
- approved Definition of Good, ticket receipts, integration verdicts, and open risks;
- deployment target, configuration identity, migration/dependency changes, and rollback plan.

Run `validate_project.py` before auditing.

## Required evidence

1. Repository, branch/SHA, dirty state, artifact/runtime identity, configuration, and deployment target.
2. Build, type, lint, test, ticket, integration, and critical-journey evidence.
3. Authentication, authorization, secrets, sensitive-data, input/upload, external-content, dependency,
   and model/tool boundaries that apply.
4. Data migrations, backfills, idempotency, retries, duplicate/out-of-order events, backup, and recovery.
5. Startup validation, health/dependency checks, logs, traces, metrics, alerts, support/incident owner,
   and degraded behavior.
6. Deployment sequence, rollback command/path, and evidence the rollback is credible.
7. One live smoke of the release-critical journey in the closest permitted environment.

Green CI alone is not production readiness. Missing evidence remains missing.

## Production-audit verdict

Write `release/production-audit.json` conforming to `stage-verdict.schema.json` with kind
`production-audit` and one status:

- `SHIP`
- `SHIP_WITH_ACCEPTED_RISK`
- `BLOCK`

Include exact build identity, evidence, blockers, accepted risks, reviewer, and timestamp. Accepted risk
must point to a human approval in the ledger.

## Independent final judgment

After a SHIP-capable production audit, dispatch the read-only `fresh-release-judge` with cold context.
It receives the original approved Definition of Good, tickets, evidence receipts, integrated journeys,
closeout verdict, production audit, current build, and rollback—not a persuasive summary.

Write its `stage-verdict.schema.json` output to `release/final-judge.json`. Only `GREEN` may proceed.
A RED verdict returns a requirement-linked punch list to the appropriate earlier owner.

## Release gate

Before deploy, publish, production flag, external mutation, credential change, or another hard-to-undo
action, invoke `/guard-before-write` and write `release/guard-receipt.json`.

After the approved action, write `release/receipt.json` with kind `release`, exact build identity,
result `RELEASED` or `NOT_RELEASED`, evidence, and rollback status. Then run `validate_project.py` before
marking DONE.

## Boundaries

- Do not deploy from this skill.
- Do not waive a blocker or human-owned risk.
- Do not let production audit grade itself as the fresh release judge.
- Do not reopen product scope during release.
