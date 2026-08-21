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
$prompt = @'
Review this repository cold using the fresh-workflow-reviewer agent contract. Do not edit files.
Run the deterministic validator, seeded evals, PowerShell parser checks available on this machine,
and inspect the actual final tree. Verify the single constitution, funnel routing, separation of duties,
loop exits and escalation, capability-provider contracts, project artifact traceability, install safety,
and all markers in docs/REVIEW-REPORT.md. Return GREEN or RED with exact file paths and commands.
Do not trust the existing review report; reproduce high-risk checks yourself.
'@
$result = & claude -p --agent fresh-workflow-reviewer --max-budget-usd $MaxBudgetUsd --max-turns $MaxTurns --output-format text $prompt
if ($LASTEXITCODE -ne 0) { throw "Fresh model review failed with exit code $LASTEXITCODE" }
$result | Set-Content -Path $OutputPath -Encoding UTF8
Write-Host "Fresh model review written to $OutputPath"
