---
name: eval-harness
description: Internal evaluation provider. Defines deterministic, rule-based, model-based, browser, and human graders before implementation; records baselines; and runs seeded process failures for workflow changes.
disable-model-invocation: true
---

# Eval Harness

Use deterministic graders wherever possible. Use model or human grading only for behavior that cannot
be captured reliably by code.

Each eval declares:

```text
id
behavior under test
seed/input
expected outcome
prohibited outcome
grader
baseline
result
```

Workflow changes require a seeded failure that is RED before the control and GREEN after it. A test
that never fails is not evidence that the control works.
