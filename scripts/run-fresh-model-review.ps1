#requires -Version 5.1
[CmdletBinding()]
param(
    [decimal]$MaxBudgetUsd = 8.00,
    [int]$MaxTurns = 30,
    [string]$OutputPath = 'docs/FRESH-MODEL-REVIEW.md'
)
$ErrorActionPreference = 'Stop'
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    throw 'Claude Code CLI was not found on PATH.'
}
$prompt = @'
Review this repository cold using the fresh-workflow-reviewer role. Do not edit files and do not trust
existing review conclusions. Inspect the current commit and reproduce the highest-risk checks.

Required work:
1. Run validate_repo.py, run_seeded_evals.py, and fresh_review.py.
2. Trace one Tier C project end to end through intake, discovery, premise verdict, Definition of Good,
   ticketing, pre-build seam review, build receipts, post-build seam review, closeout, production audit,
   final judge, release verdict, and workflow closeout. Identify any missing or contradictory handoff.
3. Verify all assurance agents are read-only and all 17 profiles have mission, inputs, method, output,
   stop/escalation, and prohibited behavior.
4. Exercise capability resolution for success, dependency, unknown capability, missing optional
   provider, and conflict.
5. Scaffold a project and prove invalid stage transitions fail.
6. Inspect installer/uninstaller for dry-run, targeted settings merge, backups, duplicate-router
   removal, hash-safe uninstall, and notification/auto-accept preservation.
7. Inspect docs/counts/links, schemas/examples, secret/machine-path exposure, and CI coverage.

Return GREEN, RED, or BLOCKED with commands, exact outputs, file paths, severity, untested surfaces,
and residual risk. A persuasive README is not evidence.
'@
$result = & claude -p --agent fresh-workflow-reviewer --max-budget-usd $MaxBudgetUsd --max-turns $MaxTurns --output-format text $prompt
if ($LASTEXITCODE -ne 0) { throw "Fresh model review failed with exit code $LASTEXITCODE" }
$result | Set-Content -Path $OutputPath -Encoding UTF8
Write-Host "Fresh model review written to $OutputPath"
