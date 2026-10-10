#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$GraphArguments
)
$ErrorActionPreference = 'Stop'
$ClaudeHome = if ($env:TURN_UP_TIME_CLAUDE_HOME) { $env:TURN_UP_TIME_CLAUDE_HOME } else { Join-Path $env:USERPROFILE '.claude' }
$InstalledHome = Split-Path -Parent $PSScriptRoot
$SharedMarker = Join-Path $InstalledHome 'turn-up-time-install-manifest.json'
$SharedInstall = (Test-Path -LiteralPath (Join-Path $InstalledHome 'turn-up-time-promotion.json') -PathType Leaf)
if ((Test-Path -LiteralPath $SharedMarker -PathType Leaf) -and ((Get-Content -LiteralPath $SharedMarker -Raw | ConvertFrom-Json).state -eq 'shared-release')) { $SharedInstall = $true }
if ($SharedInstall) { $ClaudeHome = $InstalledHome }
$MarkerPath = Join-Path $ClaudeHome 'runtime\turn-up-time\runtime-manifest.json'
if (-not (Test-Path -LiteralPath $MarkerPath -PathType Leaf)) {
    throw 'Turn Up Time graph runtime is not installed. Re-run install.ps1 with -EnableGraphRuntime.'
}
$Runtime = Get-Content -LiteralPath $MarkerPath -Raw | ConvertFrom-Json
$Python = "$($Runtime.venv_python)"
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Turn Up Time graph runtime Python is missing: $Python"
}
& $Python (Join-Path $PSScriptRoot 'promotion_admission.py') --home $ClaudeHome
if ($LASTEXITCODE -ne 0) { throw 'Turn Up Time promotion admission is blocked; recover the shared release before launching.' }
if ($SharedInstall) { $env:TURN_UP_TIME_CLAUDE_HOME = $ClaudeHome }
& $Python -m turn_up_time_graph.cli @GraphArguments
exit $LASTEXITCODE
