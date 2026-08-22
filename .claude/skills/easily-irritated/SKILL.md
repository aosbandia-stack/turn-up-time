---
name: easily-irritated
description: Bounded independent product closeout. Runs fresh role-based journeys against the exact integrated build, validates findings through separate triage, routes authorized repairs to separate engineers, verifies fixes independently, and returns an explicit terminal state. It does not rediscover or redesign the product.
disable-model-invocation: true
argument-hint: 'project="<id>" mode=lite|standard|full max_rounds=4 repairs=off|authorized'
---

# /easily-irritated

Easily Irritated verifies the product the evidence contract asked for. It is not a late discovery team
or a reason to polish forever.

## Preconditions

Require:

- approved Definition of Good and critical journeys;
- all tickets `EVIDENCE_GREEN`;
- POST_BUILD `SEAMS_SOUND`;
- exact integrated build identity;
- approved synthetic/deidentified test data and environment;
- selected mode, repair authority, and `max_rounds` (default 4).

If the build cannot be tied to its identity, exploratory evidence may be collected but no release
state can close.

## Roles and separation

Core fresh audit team:

- `irritated-domain-user`
- `functional-qa`
- `ux-accessibility-reviewer`

Conditional:

- `security-performance-reviewer` when the approved contract or changed surface warrants it.

Then:

- `triage-lead` validates findings;
- `implementation-engineer` repairs authorized tickets;
- `ticket-verifier` verifies each repair.

Auditors and verifiers are read-only. Triage does not implement. Builders do not verify themselves.
The root session is the only closeout-ledger writer.

## Round loop

For each round up to `max_rounds`:

1. Spawn a fresh audit team with persona, journey, build identity, allowed evidence, and no prior
   findings or engineer explanation.
2. Collect independent findings conforming to `finding.schema.json`.
3. Triage validates reproducibility, rejects false positives/environment errors, deduplicates,
   classifies, sets severity/owner, and writes observable acceptance.
4. When `repairs=authorized`, dispatch fresh engineers only for authorized VALIDATED findings.
5. Dispatch fresh ticket verifiers from the original finding and acceptance—not the repair summary.
6. Re-run the locked full journey from a clean start on the changed build.
7. Record coverage, new material findings, reopened findings, verified findings, blockers, and build
   identity; evaluate the stop contract.

A new round requires a changed build or a newly ratified scenario. Re-running the same team against the
same artifact is not new evidence.

## Severity and stop contract

A materially clean round introduces no new validated S0, S1, or S2. S3/S4 craft observations stay
visible and require disposition but do not automatically restart the engineering loop.

Terminal states:

- `RELEASE_READY`
- `YELLOW_ACCEPTANCE_REQUIRED`
- `BLOCKED_BY_DECISION`
- `BLOCKED_BY_ENVIRONMENT`
- `MAX_ROUNDS_REACHED`
- `AUDIT_ONLY_COMPLETE`

Write `closeout/terminal-state.json` with build identity, scenario/coverage refs, counts by disposition,
open risks, terminal state, and round history. `RELEASE_READY` does not itself authorize deployment.

## Visual closeout

For product interfaces and dashboards, resolve `frontend-operate`; do not auto-load marketing Taste.
Visual work begins only after S0/S1 workflow blockers and major interaction/IA decisions are stable.
Use one batched desktop/mobile pass and at most one confirmation pass. Re-run accessibility and the
full journey after visual changes.

## Boundaries

Do not invent a new product, design system, feature set, or architecture. Do not use “no complaints,”
an average score, or reviewer fatigue as a release gate. Do not exceed `max_rounds`; surface the block.
