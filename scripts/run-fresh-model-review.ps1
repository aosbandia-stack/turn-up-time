#requires -Version 5.1
[CmdletBinding()]
param(
    [decimal]$MaxBudgetUsd = 5.00,
    [int]$MaxTurns = 20,
    [string]$OutputPath = 'docs/FRESH-MODEL-REVIEW.md'
)
$ErrorActionPreference = 'Stop'
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    throw 'Claude Code CLI was not found on PATH.'
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python was not found on PATH.'
}

& python .claude/scripts/validate_repo.py
if ($LASTEXITCODE -ne 0) { throw 'Repository validator is RED; do not spend a model review yet.' }
& python .claude/scripts/run_seeded_evals.py
if ($LASTEXITCODE -ne 0) { throw 'Seeded process evals are RED; do not spend a model review yet.' }

$commit = (& git rev-parse HEAD).Trim()
$branch = (& git branch --show-current).Trim()
$prompt = @"
Review this repository cold using the fresh-workflow-reviewer agent contract. Do not edit files.
Reviewed branch: $branch
Reviewed commit: $commit

Run the deterministic validator and seeded evals yourself. Inspect the actual final tree. Trace the
conveyor from intake through workflow closeout, including artifact schemas and state transitions.
Verify the single constitution, funnel routing, role tool permissions and full role profiles, loop exits
and escalation, capability provider resolution, ticket and finding traceability, fresh final release
judge, install/uninstall safety, and all markers in docs/REVIEW-REPORT.md. Reproduce high-risk positive
and negative controls. Do not trust the existing report or builder summary. Return GREEN or RED with
exact file paths, commands, evidence, untested surfaces, and minimum repairs.
"@

$result = & claude -p --agent fresh-workflow-reviewer --max-budget-usd $MaxBudgetUsd --max-turns $MaxTurns --output-format text $prompt
if ($LASTEXITCODE -ne 0) { throw "Fresh model review failed with exit code $LASTEXITCODE" }

$header = @"
# Fresh model review

- Branch: `$branch`
- Commit: `$commit`
- Generated: $((Get-Date).ToUniversalTime().ToString('o'))

"@
($header + ($result -join "`n")) | Set-Content -Path $OutputPath -Encoding UTF8
Write-Host "Fresh model review written to $OutputPath"
