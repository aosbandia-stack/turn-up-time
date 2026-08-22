#requires -Version 5.1
# Deterministic backstop for a narrow set of commands that must never be auto-accepted.
# The broader decision remains in /guard-before-write.
$ErrorActionPreference = 'Continue'
try {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
    $event = $raw | ConvertFrom-Json -ErrorAction Stop
    $command = ''
    if ($null -ne $event.tool_input -and $null -ne $event.tool_input.command) {
        $command = "$($event.tool_input.command)"
    }
    if ([string]::IsNullOrWhiteSpace($command)) { exit 0 }

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
            $out = @{
                hookSpecificOutput = @{
                    hookEventName = 'PreToolUse'
                    permissionDecision = 'deny'
                    permissionDecisionReason = 'Destructive command blocked. Run /guard-before-write, produce a schema/receipt-backed PROCEED decision, and use an approved reversible path.'
                }
            } | ConvertTo-Json -Depth 6 -Compress
            Write-Output $out
            exit 0
        }
    }
} catch { }
exit 0
