# Installation

The repository works as a project-scoped Claude Code configuration when cloned. The optional installer
copies the canonical skills, agents, hooks, capability registry, schemas, and templates to
`~/.claude/` for use across projects.

The installer is dry-run by default, backs up conflicts, and does not delete existing settings.

```powershell
./scripts/install.ps1
./scripts/install.ps1 -Apply
```

Options:

```powershell
./scripts/install.ps1 -Apply -EnableNotifications
./scripts/install.ps1 -Apply -EnableAutoAccept
```

`-EnableAutoAccept` sets `permissions.defaultMode` to `acceptEdits` but preserves deny rules and does
not auto-approve destructive actions. Review the generated settings diff before applying.

To replace an existing contradictory global constitution after reviewing the backup plan:

```powershell
./scripts/install.ps1 -Apply -ReplaceGlobalConstitution
```

The installer writes `~/.claude/turn-up-time-install-manifest.json`. The uninstaller uses that exact
file list rather than guessing what it installed.

Existing notification scripts are preserved. `-EnableNotifications` registers the existing provider
when present and installs the bundled fallback only when none exists. Runtime validators, schemas,
profiles, and eval fixtures are installed alongside the skills.

## Cold model review

After installation, run the fresh reviewer as a completely separate Claude Code session:

```powershell
./scripts/run-fresh-model-review.ps1
```

This uses `claude -p --agent fresh-workflow-reviewer`, caps turns and budget, and writes the verdict to
`docs/FRESH-MODEL-REVIEW.md`. The reviewer is read-only by frontmatter. The CLI pattern is supported by
current Claude Code custom-agent and CLI documentation.
