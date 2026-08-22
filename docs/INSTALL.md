# Installation and removal

The repository runs project-scoped as cloned. The optional installer copies the canonical skills,
agents, hooks, capability registry, schemas, templates, profiles, evals, and runtime scripts to
`~/.claude/`.

## Preview first

```powershell
./scripts/install.ps1
```

Dry-run is the default. It prints every copy and settings change without writing.

## Apply

```powershell
./scripts/install.ps1 -Apply
```

Optional conveniences:

```powershell
./scripts/install.ps1 -Apply -EnableNotifications -EnableAutoAccept
```

Replace the old global constitution only after reviewing the backup plan:

```powershell
./scripts/install.ps1 -Apply -EnableNotifications -EnableAutoAccept -ReplaceGlobalConstitution
```

## What installation does

- backs up every conflicting target before replacement;
- installs only the Turn Up Time source surfaces;
- replaces any prior `skill-router.ps1` hook row with the single Turn Up Time router while preserving
  unrelated prompt hooks;
- replaces only the Turn Up Time destructive-command guard row;
- preserves an existing notification provider and adds the bundled fallback only when requested and
  absent;
- preserves existing permission deny rules;
- sets `permissions.defaultMode=acceptEdits` only when explicitly requested;
- records every installed file, its SHA-256, whether it preexisted, and its backup path;
- records targeted settings changes and global-constitution replacement in
  `~/.claude/turn-up-time-install-manifest.json`.

`TURN_UP_TIME_CLAUDE_HOME` may point installation at a temporary directory for testing.

## Validate the installed workflow

From the source checkout:

```powershell
python .claude/scripts/validate_repo.py
python .claude/scripts/run_seeded_evals.py
python .claude/scripts/fresh_review.py
```

A separate Claude Code model review can be run after installation:

```powershell
./scripts/run-fresh-model-review.ps1
```

That command uses the read-only `fresh-workflow-reviewer`. It is intentionally separate from the
builder session and tells the reviewer to reproduce high-risk checks rather than trust the stored
report.

## Uninstall safely

Preview:

```powershell
./scripts/uninstall.ps1
```

Apply:

```powershell
./scripts/uninstall.ps1 -Apply
```

The uninstaller:

- removes or restores only files whose current hash still matches the installed hash;
- prints `SKIP MODIFIED` and preserves any file changed after installation;
- restores preexisting files from their exact backup;
- removes only Turn Up Time router/guard/notification hook rows;
- restores the previous default permission mode only when it was not subsequently changed;
- restores the global constitution only when its current hash still matches the installed copy;
- retains the manifest when modified artifacts were skipped so recovery information is not lost.

It never guesses ownership from a path name.
