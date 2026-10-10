# Codex adapter

Turn Up Time's source-owned Codex installer provides namespaced skills and roles, a pinned source
snapshot, and a separate Python runtime per generation. It preserves the canonical workflow's task
tiers, authority and approval boundaries. It does not install Claude hooks or alter Codex tool approvals.

## Requirements and commands

Use Python 3.11 or newer. Installation creates a virtual environment and installs the runtime's existing
dependencies plus PyYAML. That step requires package access or an existing pip cache. Source and Codex
home paths may contain spaces; quote them in your shell. No dependency lock policy is introduced here.

```text
python scripts/codex_installer.py plan --source <repository> --codex-home <codex-home>
python scripts/codex_installer.py install --source <repository> --codex-home <codex-home> --apply
python scripts/codex_installer.py update --source <repository> --codex-home <codex-home> --apply
python scripts/codex_installer.py verify --codex-home <codex-home>
python scripts/codex_installer.py rollback --codex-home <codex-home> --apply
```

The default command is `plan`. Omitting `--apply` from a mutation prints its plan without writing files
or installing packages. `--source` defaults to the script's repository and `--codex-home` defaults to
`CODEX_HOME`, then the user's `.codex` directory. Verification is always read-only.

After installation, open a fresh Codex task and check available skills and role types. Use
`$turn-up-time`, its `tut-*` skills, and `tut_*` roles within this workflow. Existing unrelated skills
remain available. Default routing is an owned block in global `AGENTS.md`; repository constraints and
higher-priority instructions remain authoritative.

## Activation and recovery

A candidate generation contains a source snapshot and runtime environment. Project ledgers, runtime
checkpoints, audit runs, caches and local logs are excluded from that snapshot. Candidate topology and
repository validation run before global activation. The installer records source/runtime file hashes,
Python/package versions, generated-file ownership, and checksummed recovery copies.

Concurrent installer commands are excluded by a process lock. If a process is killed, inspect the PID
in `.installer.lock` and confirm it is no longer running before removing that stale lock. Do not remove
a live process lock. Recovery then uses the durable journal and checks for conflicting later edits.

Every active write is preceded by durable backups and an operation journal. The global routing block
is written after the wrappers, and the active manifest commits last. An ordinary activation failure
restores the prior files. A process interruption leaves a journal; `rollback --apply` restores that
interrupted operation if no later user edits conflict. Verification reports an interrupted journal.

Updates replace only files owned by the current manifest. Unrelated edits outside the global routing
block are preserved. Modified owned wrappers or a modified routing block stop activation/rollback.
Rollback preflights all affected files and backups, and preserves dependencies as a unit on conflict;
it returns a nonzero `PARTIAL_ROLLBACK` result. Reconcile the reported user edits before retrying.
The installer never deletes retained source/runtime generations or project state.

Rollback also verifies the previous generation's recorded source/runtime inventory before activating it;
a tampered inactive generation blocks rollback. A successful rollback restores the exact previous
manifest, wrappers and runtime selection. Rolling
back the first installation removes its active manifest, allowing installation again. Unrelated global
instruction edits made after installation survive rollback. Missing or changed backups block rollback.

The earlier profile-local installer format is accepted by `update`: unchanged owned files are migrated
into the generation scheme, and rollback restores the prior manifest and files. Restoring a legacy generation explicitly reports `restored_integrity: LEGACY_UNVERIFIED`.
Legacy manifests cannot prove runtime/source integrity and verify as `LEGACY_UNVERIFIED`. A modified legacy global instructions
file requires explicit reconciliation because the old format recorded only a whole-file hash.

## What verification proves

`VERIFIED` means that the managed files, source snapshot and runtime payload match their recorded
hashes, and that agent configuration parses with the expected read-only assurance declaration.
It is an installation-integrity result, not a release verdict or end-to-end workflow certification.

The report always separates:

- `CONFIG_VALID` / `CONFIG_INVALID`: role file syntax and declared authority.
- `DISCOVERY_UNVERIFIED`: whether the current Codex task actually exposes each role.
- `EFFECTIVE_SANDBOX_UNVERIFIED`: whether current runtime permissions enforce the role's boundary.

A fresh-task role inventory and a bounded effective-permission probe are required before claiming
runtime role enforcement. A TOML parser or skill-discovery response cannot prove those properties.
If a required role is unavailable, disclose the limitation; do not silently substitute a writable agent
and claim enforced independent assurance. Installation does not modify approval or permission settings.

## Adapter regression checks

```text
python -m pytest scripts/tests/test_codex_installer.py -q
```

Tests use isolated temporary homes and an injected runtime builder. They exercise ownership, migration,
source/runtime tampering, snapshot exclusions, generated-template consistency, failure recovery,
modified routing blocks, backup loss and rollback/reinstallation. They do not install into the real
user profile. A real candidate-runtime smoke is additionally needed to test packaging and graph
transitions; runtime tests and fresh independent review remain separate requirements.
