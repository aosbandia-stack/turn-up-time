---
name: guard-before-write
description: Reversibility and accountability gate before destructive, external, production, credential, bulk-data, deployment, or otherwise hard-to-undo actions. Requires blast radius, backup, dry-run, count reconciliation, rollback, and human authorization where accountability remains human-owned.
disable-model-invocation: true
---

# /guard-before-write

All required checks must pass:

1. **Blast radius:** exact objects and count.
2. **Restorable backup:** location and restore command.
3. **Dry-run/sample:** real diff or preview.
4. **Count reconciliation:** expected versus actual.
5. **Rollback:** tested or credibly executable.
6. **Authority:** explicit human approval for external, destructive, production, credential, or
   irreversible action.

If a check cannot be satisfied, stop and surface what is missing. Auto-accept does not override this
skill. A normal edit inside an approved ticket is not automatically destructive; deployment and
external side effects are.
