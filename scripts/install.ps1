#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$EnableNotifications,
    [switch]$EnableAutoAccept,
    [switch]$ReplaceGlobalConstitution
)
$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ClaudeHome = if ($env:TURN_UP_TIME_CLAUDE_HOME) { $env:TURN_UP_TIME_CLAUDE_HOME } else { Join-Path $env:USERPROFILE '.claude' }
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$BackupRoot = Join-Path $ClaudeHome ("turn-up-time-backup-$Stamp")
$ManifestPath = Join-Path $ClaudeHome 'turn-up-time-install-manifest.json'
$Plan = New-Object 'System.Collections.Generic.List[string]'
$FileRecords = New-Object 'System.Collections.Generic.List[object]'

function Ensure-Directory {
    param([string]$Path)
    if (-not [string]::IsNullOrWhiteSpace($Path) -and -not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Get-Sha256 {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-RelativeToHome {
    param([string]$Path)
    return $Path.Substring($ClaudeHome.Length).TrimStart([char[]]@([char]92, [char]47))
}

function Backup-Target {
    param([string]$Target)
    if (-not (Test-Path -LiteralPath $Target)) { return $null }
    $relative = Get-RelativeToHome $Target
    $backup = Join-Path $BackupRoot $relative
    Ensure-Directory (Split-Path -Parent $backup)
    Copy-Item -LiteralPath $Target -Destination $backup -Force
    return $backup
}

function Ensure-Property {
    param($Object, [string]$Name, $Value)
    if ($null -eq $Object.PSObject.Properties[$Name]) {
        $Object | Add-Member -MemberType NoteProperty -Name $Name -Value $Value
    }
}

function Remove-HookCommand {
    param($Groups, [string]$Needle)
    $result = @()
    foreach ($group in @($Groups)) {
        if ($null -eq $group) { continue }
        $kept = @()
        foreach ($hook in @($group.hooks)) {
            $command = "$($hook.command)"
            if ($command.IndexOf($Needle, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
                $kept += $hook
            }
        }
        if ($kept.Count -gt 0) {
            $copy = [ordered]@{}
            foreach ($property in $group.PSObject.Properties) {
                if ($property.Name -ne 'hooks') { $copy[$property.Name] = $property.Value }
            }
            $copy['hooks'] = @($kept)
            $result += [pscustomobject]$copy
        }
    }
    return ,$result
}

function Add-HookGroup {
    param($Groups, [string]$Matcher, [string]$Command, [int]$Timeout, [bool]$Async = $false)
    $hook = [ordered]@{ type = 'command'; command = $Command; timeout = $Timeout }
    if ($Async) { $hook['async'] = $true }
    $group = [ordered]@{ hooks = @([pscustomobject]$hook) }
    if (-not [string]::IsNullOrWhiteSpace($Matcher)) { $group['matcher'] = $Matcher }
    return @($Groups) + @([pscustomobject]$group)
}

$copySpecs = @(
    @{ Source = Join-Path $RepoRoot '.claude\skills'; Target = Join-Path $ClaudeHome 'skills' },
    @{ Source = Join-Path $RepoRoot '.claude\agents'; Target = Join-Path $ClaudeHome 'agents' },
    @{ Source = Join-Path $RepoRoot '.claude\hooks'; Target = Join-Path $ClaudeHome 'hooks' },
    @{ Source = Join-Path $RepoRoot '.claude\capabilities'; Target = Join-Path $ClaudeHome 'capabilities' },
    @{ Source = Join-Path $RepoRoot '.claude\schemas'; Target = Join-Path $ClaudeHome 'schemas' },
    @{ Source = Join-Path $RepoRoot '.claude\templates'; Target = Join-Path $ClaudeHome 'templates' },
    @{ Source = Join-Path $RepoRoot '.claude\evals'; Target = Join-Path $ClaudeHome 'evals' },
    @{ Source = Join-Path $RepoRoot '.claude\profiles'; Target = Join-Path $ClaudeHome 'profiles' },
    @{ Source = Join-Path $RepoRoot '.claude\scripts'; Target = Join-Path $ClaudeHome 'scripts' }
)

foreach ($entry in $copySpecs) {
    foreach ($file in @(Get-ChildItem -Path $entry.Source -Recurse -File)) {
        $relative = $file.FullName.Substring($entry.Source.Length).TrimStart([char[]]@([char]92, [char]47))
        $target = Join-Path $entry.Target $relative
        if ($relative -ieq 'fresh_review.py') {
            $Plan.Add("SKIP source-only cold reviewer $target") | Out-Null
            continue
        }
        if ($relative -ieq 'notify.ps1' -and -not $EnableNotifications) {
            $Plan.Add("SKIP optional notification provider $target") | Out-Null
            continue
        }
        if ($relative -ieq 'notify.ps1' -and (Test-Path -LiteralPath $target)) {
            $Plan.Add("KEEP existing notification provider $target") | Out-Null
            continue
        }

        $preexisting = Test-Path -LiteralPath $target
        $Plan.Add("COPY $($file.FullName) -> $target" + $(if ($preexisting) { ' (backup first)' } else { '' })) | Out-Null
        if ($Apply) {
            Ensure-Directory (Split-Path -Parent $target)
            $backup = Backup-Target $target
            Copy-Item -LiteralPath $file.FullName -Destination $target -Force
            $FileRecords.Add([pscustomobject][ordered]@{
                path = $target
                installed_sha256 = Get-Sha256 $target
                preexisting = [bool]$preexisting
                backup_path = $backup
            }) | Out-Null
        }
    }
}

$SettingsPath = Join-Path $ClaudeHome 'settings.json'
$RouterCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\hooks\skill-router.ps1"'
$GuardCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\hooks\destructive-command-guard.ps1"'
$NotifyCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\hooks\notify.ps1"'
$Plan.Add('REPLACE any existing skill-router.ps1 hook row with the Turn Up Time router; preserve unrelated prompt hooks') | Out-Null
$Plan.Add('REPLACE any existing destructive-command-guard.ps1 hook row; preserve unrelated Bash guards') | Out-Null
if ($EnableNotifications) { $Plan.Add('ADD notification Stop hook only when no notify.ps1 hook already exists') | Out-Null }
if ($EnableAutoAccept) { $Plan.Add('SET permissions.defaultMode=acceptEdits; preserve deny rules') | Out-Null }
if ($ReplaceGlobalConstitution) { $Plan.Add('BACKUP and replace ~/.claude/CLAUDE.md') | Out-Null }

if (-not $Apply) {
    Write-Host 'DRY RUN - no files changed. Re-run with -Apply after reviewing:'
    $Plan | ForEach-Object { Write-Host $_ }
    exit 0
}

Ensure-Directory $ClaudeHome
$SettingsBackup = Backup-Target $SettingsPath
if (Test-Path -LiteralPath $SettingsPath) {
    $settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
} else {
    $settings = [pscustomobject]@{}
}
Ensure-Property $settings 'hooks' ([pscustomobject]@{})
Ensure-Property $settings.hooks 'UserPromptSubmit' @()
Ensure-Property $settings.hooks 'PreToolUse' @()
Ensure-Property $settings.hooks 'Stop' @()

$settings.hooks.UserPromptSubmit = Remove-HookCommand $settings.hooks.UserPromptSubmit 'skill-router.ps1'
$settings.hooks.UserPromptSubmit = Add-HookGroup $settings.hooks.UserPromptSubmit '' $RouterCommand 20
$settings.hooks.PreToolUse = Remove-HookCommand $settings.hooks.PreToolUse 'destructive-command-guard.ps1'
$settings.hooks.PreToolUse = Add-HookGroup $settings.hooks.PreToolUse 'Bash' $GuardCommand 20

$NotificationAdded = $false
if ($EnableNotifications) {
    $existingStop = ($settings.hooks.Stop | ConvertTo-Json -Depth 30 -Compress)
    if ($existingStop.IndexOf('notify.ps1', [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
        $settings.hooks.Stop = Add-HookGroup $settings.hooks.Stop '' $NotifyCommand 10 $true
        $NotificationAdded = $true
    }
}

Ensure-Property $settings 'permissions' ([pscustomobject]@{})
$PreviousDefaultMode = $null
if ($null -ne $settings.permissions.PSObject.Properties['defaultMode']) {
    $PreviousDefaultMode = "$($settings.permissions.defaultMode)"
}
$DefaultModeChanged = $false
if ($EnableAutoAccept) {
    if ($null -eq $settings.permissions.PSObject.Properties['defaultMode']) {
        $settings.permissions | Add-Member -MemberType NoteProperty -Name defaultMode -Value 'acceptEdits'
    } else {
        $settings.permissions.defaultMode = 'acceptEdits'
    }
    $DefaultModeChanged = $true
}
$settings | ConvertTo-Json -Depth 50 | Set-Content -LiteralPath $SettingsPath -Encoding UTF8

$Constitution = [ordered]@{ replaced = $false; path = $null; installed_sha256 = $null; preexisting = $false; backup_path = $null }
if ($ReplaceGlobalConstitution) {
    $globalClaude = Join-Path $ClaudeHome 'CLAUDE.md'
    $preexisting = Test-Path -LiteralPath $globalClaude
    $backup = Backup-Target $globalClaude
    Copy-Item -LiteralPath (Join-Path $RepoRoot 'CLAUDE.md') -Destination $globalClaude -Force
    $Constitution = [ordered]@{
        replaced = $true
        path = $globalClaude
        installed_sha256 = Get-Sha256 $globalClaude
        preexisting = [bool]$preexisting
        backup_path = $backup
    }
}

$manifest = [ordered]@{
    schema_version = 2
    installed_at = (Get-Date).ToUniversalTime().ToString('o')
    source = $RepoRoot
    backup_root = $BackupRoot
    files = $FileRecords.ToArray()
    settings = [ordered]@{
        path = $SettingsPath
        backup_path = $SettingsBackup
        router_command = $RouterCommand
        guard_command = $GuardCommand
        notification_command = $NotifyCommand
        notification_added = $NotificationAdded
        default_mode_before = $PreviousDefaultMode
        default_mode_changed = $DefaultModeChanged
    }
    constitution = $Constitution
}
$manifest | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8

Write-Host "Applied Turn Up Time. Backup: $BackupRoot"
Write-Host "Install manifest: $ManifestPath"
$Plan | ForEach-Object { Write-Host $_ }
