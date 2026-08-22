# Installation and removal

The repository runs project-scoped as cloned. The optional installer copies the canonical skills,
agents, hooks, capability registry, schemas, templates, profiles, evals, and runtime wrapper scripts to
`~/.claude/`. The LangGraph runtime is opt-in and is installed into its own virtual environment.

## Preview first

Dry-run is the default. The following command prints the complete plan without writing files:

```powershell
.\scripts\install.ps1 `
  -EnableNotifications `
  -EnableAutoAccept `
  -ReplaceGlobalConstitution `
  -EnableGraphRuntime
```

## Apply the complete workflow

```powershell
.\scripts\install.ps1 `
  -Apply `
  -EnableNotifications `
  -EnableAutoAccept `
  -ReplaceGlobalConstitution `
  -EnableGraphRuntime
```

Use a single line when copying through a system that may alter PowerShell backticks:

```powershell
.\scripts\install.ps1 -Apply -EnableNotifications -EnableAutoAccept -ReplaceGlobalConstitution -EnableGraphRuntime
```

The graph runtime requires Python 3.11 or newer. To select a specific interpreter:

```powershell
$env:TURN_UP_TIME_PYTHON = 'C:\path\to\python.exe'
```

Without `-EnableGraphRuntime`, the installer applies the skills, agents, router, schemas, and safety
controls but does not create the LangGraph virtual environment.

## What installation does

- backs up every conflicting target before replacement;
- records copied files as `created` or `overwritten` and records preserved conflicting providers;
- replaces any prior `skill-router.ps1` hook row with the single Turn Up Time router while preserving
  unrelated prompt hooks;
- replaces only the Turn Up Time destructive-command guard row;
- preserves an existing notification provider and adds the bundled fallback only when requested and
  absent;
- preserves existing permission deny rules;
- sets `permissions.defaultMode=acceptEdits` only when explicitly requested;
- records every installed file, its SHA-256, whether it preexisted, and its backup path;
- optionally creates an isolated virtual environment under
  `~/.claude/runtime/turn-up-time/`, installs the pinned runtime package, validates the executable
  topology, and records a runtime ownership marker;
- records targeted settings changes, graph-runtime ownership, and global-constitution replacement in
  `~/.claude/turn-up-time-install-manifest.json`.

`TURN_UP_TIME_CLAUDE_HOME` may point installation at a temporary directory for testing.

## Verify the installed workflow

From the source checkout:

```powershell
python .claude/scripts/validate_repo.py
python .claude/scripts/run_seeded_evals.py
python .claude/scripts/fresh_review.py
```

Verify the installed graph runtime:

```powershell
& "$HOME\.claude\scripts\turn-up-time-graph.ps1" validate-topology
```

A separate Claude Code model review can be run after installation:

```powershell
.\scripts\run-fresh-model-review.ps1
```

That command uses the read-only `fresh-workflow-reviewer`. It is intentionally separate from the
builder session and tells the reviewer to reproduce high-risk checks rather than trust a stored
report.

## Uninstall safely

Preview:

```powershell
.\scripts\uninstall.ps1
```

Apply:

```powershell
.\scripts\uninstall.ps1 -Apply
```

The uninstaller:

- removes or restores only files whose current hash still matches the installed hash;
- prints `SKIP MODIFIED` and preserves any file changed after installation;
- restores preexisting files from their exact backup;
- removes only Turn Up Time router, guard, and notification hook rows;
- restores the previous default permission mode only when it was not subsequently changed;
- restores the global constitution only when its current hash still matches the installed copy;
- removes or restores the owned graph virtual environment only when both its marker and installation
  hash still match;
- prints `SKIP MODIFIED GRAPH RUNTIME` rather than deleting a changed runtime;
- retains the manifest when modified artifacts were skipped so recovery information is not lost.

It never guesses ownership from a path name.
