---
name: easily-irritated
description: Bounded independent product closeout. Tests the finished build against the approved Definition of Good and critical journeys, validates friction with evidence, routes repairs to separate engineers, verifies tickets independently, and returns an explicit release state.
disable-model-invocation: true
argument-hint: 'project="<id>" mode=lite|standard|full max_rounds=4 repairs=off|authorized'
---

# /easily-irritated

This stage checks consistency, friction, recovery, accessibility, integration, and craft. It does not
redesign the product or invent new product requirements.

## Inputs

- approved Definition of Good;
- critical journeys and state matrix;
- ticket acceptance criteria;
- current build identity;
- known risks and deferred decisions.

## Roles

Core audit team:

- `irritated-domain-user`
- `functional-qa`
- `ux-accessibility-reviewer`

Conditional:

- `security-performance-reviewer`

Triage and repair:

- `triage-lead`
- `implementation-engineer`
- `ticket-verifier`
- `fresh-release-judge`

Auditors and verifiers are read-only. Triage does not implement. Builders do not verify themselves.

## Round

1. Spawn a fresh audit team with no prior finding list or engineer explanation.
2. Collect evidence-backed findings tied to journey steps and approved requirements.
3. Triage validates, rejects false positives, deduplicates, sets severity, owner, and acceptance test.
4. When repairs are authorized, fresh engineers repair only validated tickets.
5. Fresh ticket verifiers rerun the original reproduction and adjacent behavior.
6. Run the full critical journey from a clean state with a fresh team.
7. Evaluate the stop contract.

## Stop contract

A round is materially clean when it introduces no new validated S0, S1, or S2. Craft findings remain
visible but do not automatically restart the full engineering loop.

Terminal states:

- `RELEASE_READY`
- `YELLOW_ACCEPTANCE_REQUIRED`
- `BLOCKED_BY_DECISION`
- `BLOCKED_BY_ENVIRONMENT`
- `MAX_ROUNDS_REACHED`
- `AUDIT_ONLY_COMPLETE`

No unbounded retries. Fresh rounds must receive a changed build or they are not justified.

## Visual provider rule

For dashboards and product interfaces, request `frontend-operate` through the registry. Do not load a
marketing-page Taste skill by default. Visual polish gets one batched desktop/mobile pass and at most
one confirmation pass.
