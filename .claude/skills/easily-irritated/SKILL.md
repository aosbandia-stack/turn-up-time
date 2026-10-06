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
The root requests closeout bookkeeping through the runtime; specialists do not edit the ledger.

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

Write `closeout/terminal-state.json` using `terminal-state.schema.json`: exact build, reviewer/time,
scenario proof, open risks and round history. Keep finding dispositions in the linked evidence. After
final product repairs, Turn Up Time loads `/swiper-dont-swpe-me` to extend this same packet with cleanup
and IT handoff proof. Use `completion: null` until completion is evidenced. `RELEASE_READY` does not
itself authorize deployment; release entry requires the finished current cleanup packet.

## Visual closeout

Resolve each approved UI surface's platform, purpose and flags through the registry, including its
actual assurance adapter. Impeccable is the default instruction baseline; legacy web aliases remain
supported. Do not auto-load marketing Taste or optional 21st generation.
Visual work begins only after S0/S1 workflow blockers and major interaction/IA decisions are stable.
Use one batched desktop/mobile pass and at most one confirmation pass. Compare actual route content
against the approved design and shared tokens/components, including loading/empty/error/success.
Record real screenshots and browser outputs in verification receipts named `ui:<route>:<viewport>`
and keyboard proof named `keyboard:<route>` for every declared route. Evaluate behavior, visual
fidelity and independent usability judgment separately. Never refresh screenshot baselines or delete
failing checks just to pass. Re-run accessibility and the full journey after visual changes.

Native surfaces use the same proof IDs with actual native captures/input-test outputs from their
declared adapter; do not relabel browser screenshots as native execution. Apply the project guide's
typography, spacing, color, hierarchy, density, states and components consistently across surfaces.

## Optional bounded design loop

The ordinary one-batch/one-confirmation visual flow remains the default. If approved
`ui.design_loop` is present, its `max_rounds` is the same overall round budget above, not an extra
polish allowance. In each round a fresh read-only evaluator receives the exact build, locked rubric
and guide plus actual UI evidence, without builder explanations. Record a verification receipt with
`check_id: design-evaluation`, a `design_evaluation` object, independently attributed criterion
scores and hard-gate results, and hashes of the actual captures/outputs supporting each result.

Use `closeout/terminal-state.json.round_history` for those ordered receipt references and set
`design_stop_reason`. A historical FAIL remains valid evidence; only the final exact build may
qualify with PASS. Every declared criterion must meet its anchored minimum, every hard gate must
PASS, and UNKNOWN cannot pass. Never average away a failed critical criterion. No regrading the
same unchanged content, swapping rubrics/guides, or reusing an evaluator until a lucky grade appears.

Continue only after an authorized changed build and while the shared round, elapsed-time and
stagnation budgets permit it. Any criterion/gate regression stops the loop. If a cost ceiling is
configured, record actual cumulative usage with unit and evidence; missing cost is unknown, not
zero. The validator checks these records; it does not launch or terminate workers.

Stop with THRESHOLD_MET, ROUND_LIMIT, TIME_LIMIT, COST_LIMIT, STAGNATION, REGRESSION, ENVIRONMENT or
DECISION. Only THRESHOLD_MET supports release entry. Other reasons return the existing blocked/max
rounds terminal state and a concrete next decision. Builders repair authorized findings but cannot
alter the rubric or certify themselves. Swiper still runs after the final repairs on the final build.

## Boundaries

Do not invent a new product, design system, feature set, or architecture. Do not use “no complaints,”
an average score, or reviewer fatigue as a release gate. Do not exceed `max_rounds`; surface the block.
