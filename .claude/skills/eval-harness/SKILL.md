---
name: eval-harness
description: Internal evaluation provider. Defines deterministic, live, experiential, model-based, and human graders before implementation; records baselines and controls; and runs seeded process failures for workflow changes.
disable-model-invocation: true
---

# Eval Harness

## Purpose

Turn acceptance from prose into reproducible evidence. Use the cheapest decisive grader that can
actually prove the claim.

## Eval contract

Every eval records:

```text
id
behavior under test
source requirement
seed/input
expected outcome
prohibited outcome
grader type
command or scenario
control that must fail
baseline
result and artifact/build identity
```

Grader types:

- deterministic code/schema/command;
- live boundary or browser journey;
- experiential rubric with anchored examples;
- fresh model grader for open-ended output;
- human gate for policy, taste, risk, or accountability that cannot be delegated.

## Rules

1. Define capability and regression evals before implementation.
2. Prefer deterministic graders; do not use a model to discover what a shell command proves.
3. Every new control has a seeded failure that is RED before the control and GREEN after it.
4. A happy-path-only test is not a control; include a known-bad case.
5. Record exact build/prompt/model/config identity for non-deterministic behavior.
6. Re-run release-critical regression checks more than once when stability, not one lucky pass, is the
   requirement.
7. A score never overrides a critical failed requirement.

## Workflow-change gate

`/its-not-you-its-me` may propose a rule only with a seeded failure, expected benefit, ceremony cost,
new risks, and rollback. The eval harness reports evidence; it does not promote policy.
