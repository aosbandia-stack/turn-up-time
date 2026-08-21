---
name: eval-harness
description: Internal evaluation provider. Defines deterministic, rule-based, browser, model-based, and human graders before implementation; records baselines; and runs seeded process failures for workflow changes.
disable-model-invocation: true
---

# Eval Harness

This is a capability provider, not a second workflow constitution.

## Contract

Each eval records:

```text
id
behavior under test
seed or input
expected outcome
prohibited outcome
grader type and command/rubric
baseline
result and evidence
```

Prefer deterministic code graders. Use browser/E2E graders for journeys, model graders only for
open-ended behavior with a calibrated rubric, and human graders for product/risk decisions.

## Before implementation

- Define capability and regression behavior from approved requirements.
- Include at least one control that must fail; an always-green grader is not evidence.
- Store project evals under the project workspace or the product's normal test tree.
- Version baselines with the behavior they grade.

## Workflow changes

A proposed workflow control must reproduce a seeded failure before the change, pass after the change,
and include a control showing the evaluator is capable of failing. Run:

```text
python .claude/scripts/run_seeded_evals.py
python .claude/scripts/validate_repo.py
```

`/its-not-you-its-me` may propose new evals, but human approval is required before the workflow changes.

## Output

Return the eval definition, grader command/rubric, baseline identity, result, decisive evidence,
regressions, and limitations. Do not use pass@k language unless multiple independent trials were
actually run.
