#requires -Version 5.1
$ErrorActionPreference = 'Continue'
try {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { return }
    $event = $raw | ConvertFrom-Json -ErrorAction Stop
    $prompt = "$($event.prompt)"
    if ([string]::IsNullOrWhiteSpace($prompt)) { return }
    $p = $prompt.ToLowerInvariant()

    $route = $null
    $reason = $null
    $guard = $false

    if ($p -match '^\s*/') {
        return
    }
    if ($p -match '(delete|drop table|truncate|purge|wipe|rm -rf|reset --hard|force[- ]push|deploy|go live|publish|send email|bulk update|migration)') {
        $guard = $true
    }
    if ($p -match '(add|install|plug in|plug-in).*(skill|agent|provider)') {
        $route = 'plug-it-in'
        $reason = 'A new capability must be placed, conflict-checked, evaluated, and made removable.'
    }
    elseif ($p -match '(close out the workflow|workflow retrospective|improve the workflow|what should the workflow learn|its not you|it.s not you)') {
        $route = 'its-not-you-its-me'
        $reason = 'Collect and validate process improvements without auto-mutating the constitution.'
    }
    elseif ($p -match '(resume|continue from|pick up where|where did we leave)') {
        $route = 'turn-up-time'
        $reason = 'Resume from the project ledger and run drift checks before acting.'
    }
    elseif ($p -match '(build|design|implement|create|make|automate|refactor|fix|repair|develop|ship|set up|wire up)') {
        $route = 'turn-up-time'
        $reason = 'One control plane classifies Tier A/B/C and loads only justified stages and capabilities.'
    }

    if ($null -eq $route -and -not $guard) { return }
    $lines = New-Object System.Collections.Generic.List[string]
    if ($route) { $lines.Add("Workflow router: invoke /$route. $reason") | Out-Null }
    if ($guard) { $lines.Add('Irreversible-action signal detected: /guard-before-write must run before the consequential action.') | Out-Null }
    $out = @{
        hookSpecificOutput = @{
            hookEventName = 'UserPromptSubmit'
            additionalContext = ($lines -join "`n")
        }
    } | ConvertTo-Json -Depth 6 -Compress
    Write-Output $out
} catch {
    # Advisory router: fail open, never block the prompt.
}
