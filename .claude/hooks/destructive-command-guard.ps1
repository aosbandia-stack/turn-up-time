#requires -Version 5.1
# Narrow deterministic backstop, not a shell sandbox or approval verifier.
$ErrorActionPreference = 'Stop'
function Deny-Command {
    param([string]$Reason)
    @{
        hookSpecificOutput = @{
            hookEventName = 'PreToolUse'
            permissionDecision = 'deny'
            permissionDecisionReason = $Reason
        }
    } | ConvertTo-Json -Depth 6 -Compress | Write-Output
}
try {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { throw 'Missing tool event' }
    $event = $raw | ConvertFrom-Json -ErrorAction Stop
    if ($null -eq $event -or $null -eq $event.tool_input -or
        $event.tool_input.command -isnot [string] -or
        [string]::IsNullOrWhiteSpace($event.tool_input.command)) {
        throw 'Malformed command event'
    }
    $command = $event.tool_input.command
    $patterns = @(
        '(?i)(^|[;&|]\s*)rm\s+-(?:[^\s]*r[^\s]*f|[^\s]*f[^\s]*r)\b',
        '(?i)Remove-Item\b[^\r\n]*(?:-Recurse|-Force)[^\r\n]*(?:-Recurse|-Force)',
        '(?i)git\s+reset\s+--hard\b',
        '(?i)git\s+clean\s+-[^\s]*f[^\s]*d\b',
        '(?i)git\s+push\b[^\r\n]*(?:--force|-f\b)',
        '(?i)git\s+branch\s+-D\b',
        '(?i)\bDROP\s+TABLE\b',
        '(?i)\bTRUNCATE\s+(?:TABLE\s+)?\w+'
    )
    foreach ($pattern in $patterns) {
        if ($command -match $pattern) {
            Deny-Command 'Destructive command blocked. Run /guard-before-write and use an explicitly approved reversible path. Auto-accept is not authorization.'
            exit 0
        }
    }
} catch {
    Deny-Command 'Command guard could not validate its input. Stop and repair the hook; do not auto-accept an unvalidated command.'
}
exit 0
