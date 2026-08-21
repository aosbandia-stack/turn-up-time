---
name: plug-it-in
description: Safe skill intake and placement. Inspects a proposed skill, identifies the exact capability it adds, classifies its authority and workflow stage, detects overlap and conflicts, requires an eval and rollback, and updates the capability registry only after human approval.
disable-model-invocation: true
---

# /plug-it-in

Use when the human says "add this skill," "install this dashboard skill," or wants a new capability
provider.

## Inspect before asking

Read the skill, dependencies, tool permissions, data egress, hooks, setup, size, and references. Compare
against the project registry first and the user registry second, plus installed providers.

Ask only unresolved placement questions:

1. What exact capability are we buying?
2. Which stage consumes it?
3. Is it control, production, assurance, or reference?
4. Default, conditional, manual-only, or project pilot?
5. What does it consume and produce?
6. What tools/data does it require?
7. What overlaps or conflicts?
8. What eval proves improvement?
9. What is the context/dependency cost?
10. How is it removed cleanly?

## Outcomes

- `INSTALL_AS_PROVIDER`
- `MERGE_INTO_PROVIDER`
- `REFERENCE_PACK_ONLY`
- `MANUAL_ONLY`
- `PROJECT_SCOPED_PILOT`
- `REJECT`
- `REPLACE_EXISTING_PROVIDER`

## Rules

- Skills request capabilities; workflow stages do not hard-code large skill stacks.
- Assurance providers must not receive Edit/Write.
- A provider must declare stage, mode, inputs, outputs, conflicts, eval, and uninstall path.
- No installation or registry mutation occurs without human approval.
- Run the validator and seeded evals after any registry change.
