#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$GraphArguments
)
$ErrorActionPreference = 'Stop'
$ClaudeHome = if ($env:TURN_UP_TIME_CLAUDE_HOME) { $env:TURN_UP_TIME_CLAUDE_HOME } else { Join-Path $env:USERPROFILE '.claude' }
$MarkerPath = Join-Path $ClaudeHome 'runtime\turn-up-time\runtime-manifest.json'
if (-not (Test-Path -LiteralPath $MarkerPath -PathType Leaf)) {
    throw 'Turn Up Time graph runtime is not installed. Re-run install.ps1 with -EnableGraphRuntime.'
}
$Runtime = Get-Content -LiteralPath $MarkerPath -Raw | ConvertFrom-Json
$Python = "$($Runtime.venv_python)"
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Turn Up Time graph runtime Python is missing: $Python"
}
& $Python -m turn_up_time_graph.cli @GraphArguments
exit $LASTEXITCODE
