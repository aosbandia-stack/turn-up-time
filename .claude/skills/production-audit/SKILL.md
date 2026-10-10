---
name: production-audit
description: Evidence-based release-readiness audit of the exact candidate build. Checks CI/tests, auth, data integrity, migrations, dependencies, operations, observability, rollback, and critical journeys, then supplies the production-audit component of the release verdict. It does not deploy or replace the final fresh judge.
disable-model-invocation: true
---

# /production-audit

Production audit answers “what could fail in the real environment?” Green CI is evidence, not the
whole answer.

## Preconditions

Require:

- exact release-candidate build identity;
- approved Definition of Good;
- all tickets evidence green;
- POST_BUILD `SEAMS_SOUND`;
- Easily Irritated terminal packet;
- completed `/swiper-dont-swpe-me` cleanup and IT handoff on that candidate;
- the declared completion scope, and deployment target/configuration identity when deployment is in scope.

For selected audit capabilities, load
[provider routing](../turn-up-time/references/PROVIDER-ROUTING.md) and review current-candidate use,
coverage, output validation and finding disposition. A requested audit must have run before
INTEGRATION; stale or missing proof returns for scoped work and revalidation, not a release-only
waiver. Installed instructions or readiness flags alone do not prove an audit succeeded.

## Audit lenses

1. **Repository/release state:** branch, SHA/artifact, dirty state, CI, package/build identity.
2. **Functional evidence:** critical journeys, regression results, closeout blockers, accepted risks.
3. **Security/privacy:** applicable authn/authz, secrets, input/upload/content boundaries, data egress,
   dependency and supply-chain risk.
4. **Data integrity:** migrations, backfills, idempotency, retries, concurrency, rollback/recovery.
5. **Operations:** startup/env validation, health/dependency checks, logs/traces/metrics, alert/owner,
   degraded behavior, incident and support path.
6. **Deployment:** exact steps, staged rollout where needed, rollback trigger and command.
7. **Real environment:** one load-bearing smoke in the intended boundary. Candidate-only scope uses
   its declared test environment and makes no live deployment claim. Deployment scope requires actual
   execution and subsequent live proof before DONE; release readiness precedes that action.

Do not run unapproved state-changing checks. Use `/guard-before-write` for consequential actions.

## Output

Write `release/production-audit.json` using `production-audit.schema.json` and its example:

```text
schema_version: 1
project_id
build_identity
status: SHIP | SHIP_WITH_ACCEPTED_RISK | BLOCK
reviewer
checked_at
evidence_refs: verification receipt paths
blockers: explicit unresolved failures or missing evidence
accepted_risks: explicit owned risks
```

The canonical field is `status`; a legacy `verdict` field is rejected, including conflicting copies.
Receipts use `verification-receipt.schema.json`, name the exact project/build and hash their actual
outputs. Include rollback and operational evidence there. Component judgment must follow final
cleanup on the same candidate.

Then dispatch the independent `fresh-release-judge`. The root composes both results into the
schema-valid `release-verdict.json`.

## Verdict rules

- `BLOCK` for a failed MUST, unknown build, unsafe migration, missing high-impact rollback, unresolved
  S0/S1/S2 closeout blocker, or critical security/data issue.
- `SHIP_WITH_ACCEPTED_RISK` only when risks are explicit, owned, and human-approved where required.
- `SHIP` only when no blocker remains and the fresh final judge is capable of reproducing the
  load-bearing evidence.

## Boundaries

Do not deploy, repair product code, invent a score that hides a blocker, reopen product design, or
stand in for the final judge/human release authority.
