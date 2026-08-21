---
name: plug-it-in
description: Safe skill intake and placement. Inspects a proposed skill, identifies the exact capability it adds, classifies its authority and workflow stage, detects overlap and conflicts, requires an eval and rollback, and updates the canonical capability registry only after human approval.
disable-model-invocation: true
---

# /plug-it-in

Use when the human wants to add, install, replace, or pilot a skill/provider. A skill does not become
part of the conveyor merely because it looks useful.

## Inspect before asking

Read the complete proposed skill and its scripts, hooks, dependencies, setup, permissions, egress,
external services, license, update behavior, and uninstall path. Compare it with:

- project `.claude/capabilities/registry.json`;
- user `~/.claude/capabilities/registry.json`;
- installed skills/providers;
- the canonical workflow and existing provider conflicts.

Answer what the files already reveal. Ask only unresolved placement questions.

## Placement questions

1. What exact capability are we buying?
2. Which stages may consume it?
3. Is its authority control, production, assurance, or reference?
4. Is it default, conditional, manual-only, or a project-scoped pilot?
5. What artifacts does it consume and produce?
6. What tools, data, network access, credentials, hooks, and dependencies does it require?
7. What overlaps, replaces, or conflicts with it?
8. What seeded eval and control prove improvement?
9. What context, latency, maintenance, and monetary cost does it add?
10. How is it disabled and removed without deleting product work?

## Outcomes

- `INSTALL_AS_PROVIDER`
- `MERGE_INTO_PROVIDER`
- `REFERENCE_PACK_ONLY`
- `MANUAL_ONLY`
- `PROJECT_SCOPED_PILOT`
- `REJECT`
- `REPLACE_EXISTING_PROVIDER`

## Registry contract

After human approval, update the applicable `registry.json` entry and validate it against
`capability-registry.schema.json`. Every entry declares:

```text
provider
bundled
stages
mode when applicable
authority
consumes
produces
conflicts
eval
uninstall
```

Conflicts use `capability:<name>` or `provider:<name>` tokens. Project registry entries override user
entries; the override must be explicit in the proposal.

## Installation and proof

1. Back up any replaced provider or settings file.
2. Install only to the approved project/user scope.
3. Resolve the capability through:

```text
python .claude/scripts/resolve_capabilities.py <capability> --stage <stage> --project-root <repo>
```

4. Run the declared seeded eval and negative control.
5. Run `validate_repo.py` and `run_seeded_evals.py` for global workflow changes.
6. Record provider version, installed paths/hashes, eval result, conflicts, and uninstall receipt.

If resolution returns `CAPABILITY_PROVIDER_MISSING`, `CAPABILITY_CONFLICT`,
`CAPABILITY_STAGE_MISMATCH`, or `CAPABILITY_UNKNOWN`, the provider is not active. Do not silently
substitute another skill.

## Boundaries

- No install, hook registration, permission change, or registry mutation without human approval.
- Assurance providers must be mechanically read-only.
- Do not hard-code provider names throughout core stage skills; tickets request capabilities.
- Do not make a large vendor package always-loaded merely because it contains useful references.
- Do not delete an old provider until rollback and migrated consumers are verified.
