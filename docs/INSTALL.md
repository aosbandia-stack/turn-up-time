# Installation

The repository works immediately as a project-scoped Claude Code configuration when cloned. The
optional installer copies the canonical skills, agents, hooks, registry, schemas, templates, profiles,
evals, and runtime scripts to `~/.claude/` for use across projects.

## Validate first

```powershell
python -m pip install -r requirements-dev.txt
python .claude/scripts/validate_repo.py
python .claude/scripts/run_seeded_evals.py
python .claude/scripts/fresh_review.py
```

## Preview

```powershell
./scripts/install.ps1
```

Dry run is the default. It lists copies, settings merges, notification behavior, and the constitution
decision without changing anything.

## Apply

When a global `~/.claude/CLAUDE.md` already exists, choose explicitly:

```powershell
./scripts/install.ps1 -Apply -ReplaceGlobalConstitution
```

or:

```powershell
./scripts/install.ps1 -Apply -KeepGlobalConstitution
```

Keeping an old global constitution is supported for project-scoped pilots, but that file may still
contradict Turn Up Time outside repositories whose local `CLAUDE.md` is authoritative.

Enable the conveniences intentionally:

```powershell
./scripts/install.ps1 `
  -Apply `
  -ReplaceGlobalConstitution `
  -EnableNotifications `
  -EnableAutoAccept
```

`-EnableAutoAccept` sets `permissions.defaultMode` to `acceptEdits`. Existing deny rules remain, and the
installer registers `destructive-command-guard.ps1` under `PreToolUse` for Bash. Auto-accept never
overrides `/guard-before-write` or a deterministic deny.

`-EnableNotifications` preserves an existing `~/.claude/hooks/notify.ps1`. The bundled fallback is
copied only when no provider exists, then registered as a Stop hook.

## What the installer preserves

- existing settings and unrelated hook rows;
- an existing notification provider;
- every overwritten file under a timestamped backup root;
- previous global constitution when replaced;
- previous auto-accept default mode;
- an install manifest containing every installed path, installed SHA-256, prior-file state, and backup
  path.

The manifest is `~/.claude/turn-up-time-install-manifest.json`.

## Uninstall

Preview:

```powershell
./scripts/uninstall.ps1
```

Apply targeted removal:

```powershell
./scripts/uninstall.ps1 -Apply
```

The uninstaller:

- restores a backed-up file when Turn Up Time replaced it;
- removes a file that Turn Up Time created;
- prints `SKIP MODIFIED` and preserves any installed file whose hash changed after installation;
- retains the manifest when modified files remain;
- removes only Turn Up Time hook rows and restores the previous auto-accept mode when safe.

After reviewing modified files, force their removal/restoration explicitly:

```powershell
./scripts/uninstall.ps1 -Apply -ForceModified
```

Restoring the entire settings backup can discard later settings changes and is therefore separate:

```powershell
./scripts/uninstall.ps1 -Apply -RestoreSettingsBackup
```

## Project workflow

Create and validate a Tier C workspace:

```powershell
python .claude/scripts/scaffold_project.py budgeting-app --profile standard --objective "Build a household budgeting app"
python .claude/scripts/validate_project.py budgeting-app
```

Advance only through the stage command:

```powershell
python .claude/scripts/advance_stage.py budgeting-app --to DISCOVERY
```

Record durable artifacts:

```powershell
python .claude/scripts/record_artifact.py budgeting-app product-evidence evidence/product.json
```

Resolve ticket capabilities before dispatch:

```powershell
python .claude/scripts/resolve_capabilities.py frontend-operate browser-e2e --stage BUILD
```

## Cold model review

After installation, a separate Claude Code session can review the repository:

```powershell
./scripts/run-fresh-model-review.ps1
```

It launches the read-only `fresh-workflow-reviewer` agent with capped turns and budget and tells the
reviewer not to trust the existing report. The deterministic reviewer remains independently available
through `python .claude/scripts/fresh_review.py`.
