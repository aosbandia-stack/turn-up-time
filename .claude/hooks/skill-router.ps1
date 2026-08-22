#requires -Version 5.1
# Advisory UserPromptSubmit router. One prompt gets at most one control-plane route,
# plus the independent irreversible-action signal. It never invokes specialist stages directly.
$ErrorActionPreference = 'Continue'
try {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { return }
    $event = $raw | ConvertFrom-Json -ErrorAction Stop
    $prompt = "$($event.prompt)"
    if ([string]::IsNullOrWhiteSpace($prompt)) { return }
    $p = $prompt.ToLowerInvariant()

    # Explicit slash commands are already a human routing decision.
    if ($p -match '^\s*/[a-z0-9-]+') { return }

    $route = $null
    $reason = $null
    $guard = $false

    if ($p -match '(?i)(delete|drop\s+table|truncate|purge|wipe|rm\s+-rf|reset\s+--hard|force[- ]?push|deploy|go\s+live|publish|send\s+(an\s+)?email|bulk\s+(update|delete)|schema\s+migration|production\s+flag|rotate\s+credentials)') {
        $guard = $true
    }

    if ($p -match '(?i)\b(add|install|plug\s*[- ]?in|integrate)\b.{0,80}\b(skill|agent|provider|plugin)\b') {
        $route = 'plug-it-in'
        $reason = 'Evaluate capability, placement, authority, conflicts, evals, and removal before installation.'
    }
    elseif ($p -match '(?i)(close\s*out\s+the\s+workflow|workflow\s+retrospective|improve\s+the\s+workflow|what\s+should\s+the\s+workflow\s+learn|it.?s\s+not\s+you)') {
        $route = 'its-not-you-its-me'
        $reason = 'Convert project traces into evidence-backed improvement proposals; never auto-promote policy.'
    }
    elseif ($p -match '(?i)\b(resume|continue\s+from|pick\s+up\s+where|where\s+did\s+we\s+leave)\b') {
        $route = 'turn-up-time'
        $reason = 'Resume from the project ledger and drift-check current repository/build state.'
    }
    elseif ($p -match '(?i)\b(build|design|implement|create|develop|automate|refactor|fix|repair|ship|set\s+up|wire\s+up)\b') {
        $route = 'turn-up-time'
        $reason = 'One control plane classifies Tier A/B/C and loads only justified stages and capabilities.'
    }

    if ($null -eq $route -and -not $guard) { return }
    $lines = New-Object 'System.Collections.Generic.List[string]'
    if ($route) { $lines.Add("Workflow router: adopt /$route. $reason") | Out-Null }
    if ($guard) { $lines.Add('Consequential-action signal: /guard-before-write must produce PROCEED before the named action.') | Out-Null }

    $out = @{
        hookSpecificOutput = @{
            hookEventName = 'UserPromptSubmit'
            additionalContext = ($lines -join "`n")
        }
    } | ConvertTo-Json -Depth 6 -Compress
    Write-Output $out
} catch {
    # Advisory router fails open. Deterministic deny rules still protect destructive commands.
}
