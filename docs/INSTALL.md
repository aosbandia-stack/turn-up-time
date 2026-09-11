# Installation and removal

The repository supports project-scoped use. The optional installer copies canonical skills,
agents, hooks, capability registry, schemas, templates, profiles, evals, and runtime wrapper scripts to
`~/.claude/`. The LangGraph runtime is opt-in and uses its own virtual environment.

Before upgrading an active project, read [HARDENING.md](HARDENING.md). Human gates now require
signed approval, not a typed name; existing green receipts may need real reverification. Back up
an existing installation and stopped project state first. No merge, local upgrade, signing key,
trust file, or worker sandbox is implied by a source change.

## Preview first

Dry-run prints the plan without writing files. The recommended initial profile does not enable
auto-accept:

```powershell
.\scripts\install.ps1 `
  -EnableNotifications `
  -ReplaceGlobalConstitution `
  -EnableGraphRuntime
```

## Apply after reviewing the plan

```powershell
.\scripts\install.ps1 -Apply -EnableNotifications -ReplaceGlobalConstitution -EnableGraphRuntime
```

Python 3.11+ is required. To select an interpreter:

```powershell
$env:TURN_UP_TIME_PYTHON = 'C:\path\to\python.exe'
```

Without `-EnableGraphRuntime`, the installer copies skills and controls but does not create the
runtime virtual environment. `-EnableAutoAccept` is a separate explicit switch that sets acceptEdits;
it does not grant human approval or provide isolation. The command guard is only a narrow backstop.

## Installation behavior

The installer backs up conflicting targets, records created/overwritten/preserved files and their
SHA-256 hashes, keeps unrelated hooks and existing deny rules, and preserves an existing notification
provider. It replaces only its own router/guard hook rows. Global constitution replacement happens
only when requested. The graph option installs the runtime and validates topology, with a recorded
ownership marker and manifest under `~/.claude/turn-up-time-install-manifest.json`.

`TURN_UP_TIME_CLAUDE_HOME` can target a temporary home for installation tests. The public approval
trust file is separately provisioned in the trusted controller's home; a project cannot select its
own authority key. The root `scripts/sign_approval.py` owner utility is not copied into worker skills.
Source documentation remains in this checkout; retain its path with the installation record.

## Verify

From the source checkout with development dependencies installed:

```powershell
python .claude/scripts/validate_repo.py
python .claude/scripts/run_seeded_evals.py
python .claude/scripts/fresh_review.py
python -m pytest -q runtime/tests
& "$HOME\.claude\scripts\turn-up-time-graph.ps1" validate-topology
```

The full runtime tests require the installed runtime and its dev dependencies. GitHub Actions runs
Linux and Windows tests, including actual CLI interruption/recovery and malformed-input guard tests.
A separate model review can be requested with `scripts/run-fresh-model-review.ps1`; it uses the
read-only fresh-workflow-reviewer. This is distinct from deterministic tests and was not implicitly
run by installing the package.

For a new project, plan the total spawn ceiling, including research, implementation, verification,
and repairs. For example, a deliberately approved ceiling of 12 can be supplied at scaffolding:

```powershell
python .claude/scripts/scaffold_project.py pilot --profile lite --spawn-budget 12 --objective 'Approved pilot outcome'
```

Twelve is an example ceiling, not a measured optimum or target. The signed intake binds the actual
ledger including that limit. Legacy profile defaults remain available but may be too small for a
complete build. `--force` can reuse only an empty directory; it cannot reset an existing project.

## Uninstall safely

```powershell
.\scripts\uninstall.ps1
.\scripts\uninstall.ps1 -Apply
```

The first command previews. Apply removes or restores only files whose current hashes still match
installation ownership. Modified files print SKIP MODIFIED and remain. Preexisting files restore
from exact backups. Only TUT hook rows are removed; permission mode/global constitution are restored
only if still unchanged since installation. The owned graph environment is removed/restored only
when marker and hash match; a changed environment prints SKIP MODIFIED GRAPH RUNTIME. The manifest
remains when changes were skipped, preserving recovery information. Ownership is never guessed
from a filename. Back up active project ledgers, journals, checkpoints, and evidence separately.
