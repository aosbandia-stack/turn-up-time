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
- deployment target and configuration identity.

## Audit lenses

1. **Repository/release state:** branch, SHA/artifact, dirty state, CI, package/build identity.
2. **Functional evidence:** critical journeys, regression results, closeout blockers, accepted risks.
3. **Security/privacy:** applicable authn/authz, secrets, input/upload/content boundaries, data egress,
   dependency and supply-chain risk.
4. **Data integrity:** migrations, backfills, idempotency, retries, concurrency, rollback/recovery.
5. **Operations:** startup/env validation, health/dependency checks, logs/traces/metrics, alert/owner,
   degraded behavior, incident and support path.
6. **Deployment:** exact steps, staged rollout where needed, rollback trigger and command.
7. **Real environment:** one load-bearing live smoke against the candidate in the intended boundary.

Do not run unapproved state-changing checks. Use `/guard-before-write` for consequential actions.

## Output

Write `release/production-audit.json` containing:

```text
project_id
build_identity
verdict: SHIP | SHIP_WITH_ACCEPTED_RISK | BLOCK
checks and evidence refs
blockers
accepted-risk candidates
missing evidence
rollback assessment
```

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
