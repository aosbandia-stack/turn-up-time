---
name: plug-it-in
description: Safe skill/provider intake and placement. Inspects a proposed package, identifies the exact capability it adds, classifies authority and stage, detects overlap/conflicts and data/tool risk, requires eval and removal contracts, pilots when appropriate, and updates the registry only after human approval.
disable-model-invocation: true
---

# /plug-it-in

Skills are implementation providers, not new constitutions. Add capability without adding routing
confusion or permanent context cost.

## 1. Inspect before asking

Read the proposed skill/package, dependencies, install scripts, hooks, tools, model/data egress,
configuration, generated files, update behavior, size, license, and referenced standards. Compare it
against project registry first, user registry second, and installed providers.

Do not run unpinned install commands or external scanners during evaluation.

## 2. Placement contract

Resolve only unanswered questions:

1. What exact capability are we buying?
2. Which stages consume it?
3. Is it `control`, `production`, `assurance`, or `reference`?
4. Is load policy core, conditional, signal-triggered, manual-only, or project pilot?
5. What artifacts/data/tools does it consume and produce?
6. What existing provider overlaps, conflicts, or should be replaced?
7. What transitive capabilities does it require?
8. What seeded eval proves it adds value and catches a real failure?
9. What context, dependency, security, latency, and maintenance cost does it add?
10. How is it removed without deleting product evidence or user work?

Assurance providers may not have Edit/Write. A provider that combines review and repair must be split
or classified as production with a separate verifier.

## 3. Outcomes

- `INSTALL_AS_PROVIDER`
- `MERGE_INTO_PROVIDER`
- `REFERENCE_PACK_ONLY`
- `MANUAL_ONLY`
- `PROJECT_SCOPED_PILOT`
- `REJECT`
- `REPLACE_EXISTING_PROVIDER`

Default to a project pilot when evidence is promising but not yet sufficient for global installation.

## 4. Approval, registration, and validation

Before mutation, present exact files/hooks/settings/dependencies, conflict/removal plan, eval, and
rollback. Obtain human approval and run `/guard-before-write` when installation changes external,
credential, global, or protected state.

Register a provider as installed only after installation is real. Source-level optional mappings may
be declared beforehand; they must stay unavailable until the resolver proves the installed inputs.
Validate `registry.json` against the capability schema,
run `resolve_capabilities.py` for success and conflict cases, run repository validation/seeded evals,
and record the provider version/hash. Registry version 3 requires `provider_kind`: instruction-only
or external. External providers need a project/environment smoke probe that checks the actual
configuration/authentication/entitlement boundary before use. Save a short-lived readiness receipt
(maximum 24 hours) with hashed outputs. Record later invocation and output evidence separately.
Never execute commands supplied by registry data; select an approved probe deliberately. Presence of
a provider or a successful smoke probe does not prove task invocation. The optional 21st source
mappings do not claim a working adapter or permission to invoke it in the target environment.

UI mappings declare selector platform/purpose/flag, supported platforms and stack compatibility.
Preserve selector semantics when overriding a project provider. Native assurance must be external
and platform-compatible. The 21st generation flag requires tool access and entitlement checks;
catalog and generation both require current probe and actual use evidence. React/Tailwind output
compatibility is not permission to inject it into native or incumbent stacks. A nonstandard mapping
needs an explicit reviewed `stack_adapter_ref`. Source/ref/license metadata is provenance only:
inspect hosted service terms, selected catalog-item licenses, egress and cost separately. Never
auto-download upstream hooks/binaries or run paid generation from a registry flag.

## 5. Review and retirement

A project pilot has an owner, success measure, cost measure, and review date. `/its-not-you-its-me`
handles global promotion or retirement; usage alone is not proof of value.

## Boundaries

Do not hard-code provider names into core stage skills, install multiple competing frontend
constitutions, silently enable hooks/telemetry, or treat discoverability as permission to install.
