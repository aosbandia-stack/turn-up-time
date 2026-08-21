---
name: production-audit
description: Evidence-based release-readiness audit. Checks current build identity, CI/tests, auth, data integrity, migrations, dependencies, operations, observability, rollback, and critical user journeys. Returns SHIP, SHIP_WITH_ACCEPTED_RISK, or BLOCK.
disable-model-invocation: true
---

# /production-audit

## Establish the release surface

Record branch/SHA, dirty state, deployment target, configuration identity, migrations, external
integrations, and the critical user journey.

## Required lenses

- build, type, lint, test, and ticket evidence;
- authentication and authorization where applicable;
- secrets, input/upload boundaries, and dependency risk;
- migrations, idempotency, retries, and data recovery;
- startup, environment validation, logging, traces, metrics, and incident ownership;
- deploy and rollback instructions;
- desktop/mobile or relevant environment journey smoke.

Green CI is evidence, not production readiness by itself.

## Verdicts

- `SHIP`
- `SHIP_WITH_ACCEPTED_RISK`
- `BLOCK`

A blocked verdict lists the minimum repair and verification required. A release does not reopen product
design. Before deploy or other irreversible action, invoke `/guard-before-write`.
