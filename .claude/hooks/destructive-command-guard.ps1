#requires -Version 5.1
$ErrorActionPreference = 'Continue'
try {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
    $event = $raw | ConvertFrom-Json -ErrorAction Stop
    $cmd = ''
    if ($null -ne $event.tool_input) { $cmd = ($event.tool_input | ConvertTo-Json -Depth 10 -Compress) }
    $patterns = @('rm -rf','rm -fr','git reset --hard','git clean -fd','git push --force','git push -f','git branch -D')
    foreach ($pattern in $patterns) {
        if ($cmd.IndexOf($pattern, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            $out = @{
                hookSpecificOutput = @{
                    hookEventName = 'PreToolUse'
                    permissionDecision = 'deny'
                    permissionDecisionReason = "Destructive command blocked. Run /guard-before-write and use a reversible alternative or explicit human-approved path. Pattern: $pattern"
                }
            } | ConvertTo-Json -Depth 6 -Compress
            Write-Output $out
            exit 0
        }
    }
} catch { }
exit 0
