#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$EnableNotifications,
    [switch]$EnableAutoAccept,
    [switch]$ReplaceGlobalConstitution,
    [switch]$KeepGlobalConstitution
)
$ErrorActionPreference = 'Stop'
if ($ReplaceGlobalConstitution -and $KeepGlobalConstitution) {
    throw 'Choose only one: -ReplaceGlobalConstitution or -KeepGlobalConstitution.'
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ClaudeHome = Join-Path $env:USERPROFILE '.claude'
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$BackupRoot = Join-Path $ClaudeHome ("turn-up-time-backup-$Stamp")
$Plan = New-Object System.Collections.Generic.List[string]
$InstalledFiles = New-Object System.Collections.Generic.List[object]

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Force -Path $Path | Out-Null }
}

function Get-Sha256 {
    param([string]$Path)
    if (-not (Test-Path $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
}

function Backup-Target {
    param([string]$Target)
    if (-not (Test-Path $Target -PathType Leaf)) { return $null }
    $relative = $Target.Substring($ClaudeHome.Length).TrimStart('\\','/')
    $backup = Join-Path $BackupRoot $relative
    Ensure-Directory (Split-Path -Parent $backup)
    Copy-Item $Target $backup -Force
    return $backup
}

function Ensure-Property {
    param([object]$Object, [string]$Name, [object]$Value)
    if (-not $Object.PSObject.Properties[$Name]) {
        $Object | Add-Member -MemberType NoteProperty -Name $Name -Value $Value
    }
}

function Add-HookIfMissing {
    param(
        [object]$Settings,
        [string]$EventName,
        [string]$Matcher,
        [string]$Command,
        [int]$Timeout,
        [bool]$Async = $false
    )
    Ensure-Property $Settings 'hooks' ([pscustomobject]@{})
    Ensure-Property $Settings.hooks $EventName @()
    $rows = @($Settings.hooks.$EventName)
    $serialized = $rows | ConvertTo-Json -Depth 50 -Compress
    $needle = [IO.Path]::GetFileName(($Command -replace '\\"','' -replace '"',''))
    if ($serialized.IndexOf($needle, [StringComparison]::OrdinalIgnoreCase) -ge 0) { return }

    $hook = [ordered]@{ type = 'command'; command = $Command; timeout = $Timeout }
    if ($Async) { $hook['async'] = $true }
    $row = [ordered]@{ hooks = @([pscustomobject]$hook) }
    if (-not [string]::IsNullOrWhiteSpace($Matcher)) { $row['matcher'] = $Matcher }
    $Settings.hooks.$EventName = @($rows) + @([pscustomobject]$row)
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
        $relative = $file.FullName.Substring($entry.Source.Length).TrimStart('\\','/')
        $target = Join-Path $entry.Target $relative
        if ($entry.Source -like '*\.claude\scripts' -and $relative -ieq 'fresh_review.py') {
            $Plan.Add("SKIP source-repository-only reviewer $target") | Out-Null
            continue
        }
        if ($relative -ieq 'notify.ps1' -and -not $EnableNotifications) {
            $Plan.Add("SKIP bundled notification provider $target") | Out-Null
            continue
        }
        if ($relative -ieq 'notify.ps1' -and (Test-Path $target)) {
            $Plan.Add("KEEP existing notification provider $target") | Out-Null
            continue
        }

        $Plan.Add("COPY $($file.FullName) -> $target") | Out-Null
        if ($Apply) {
            Ensure-Directory (Split-Path -Parent $target)
            $previousExisted = Test-Path $target -PathType Leaf
            $backup = Backup-Target $target
            Copy-Item $file.FullName $target -Force
            $InstalledFiles.Add([pscustomobject]@{
                path = $target
                installedSha256 = Get-Sha256 $target
                previousExisted = [bool]$previousExisted
                backupPath = $backup
            }) | Out-Null
        }
    }
}

$globalClaude = Join-Path $ClaudeHome 'CLAUDE.md'
$globalExists = Test-Path $globalClaude -PathType Leaf
if ($globalExists -and -not $ReplaceGlobalConstitution -and -not $KeepGlobalConstitution) {
    $Plan.Add('APPLY REQUIRES an explicit constitution choice: -ReplaceGlobalConstitution or -KeepGlobalConstitution') | Out-Null
}
elseif ($ReplaceGlobalConstitution -or (-not $globalExists -and -not $KeepGlobalConstitution)) {
    $Plan.Add("INSTALL canonical constitution -> $globalClaude") | Out-Null
}
else {
    $Plan.Add("KEEP existing constitution $globalClaude; project CLAUDE.md must remain authoritative where Turn Up Time is used") | Out-Null
}

$Plan.Add('MERGE UserPromptSubmit skill-router hook into ~/.claude/settings.json') | Out-Null
$Plan.Add('MERGE PreToolUse destructive-command-guard hook into ~/.claude/settings.json') | Out-Null
if ($EnableNotifications) { $Plan.Add('MERGE Stop notification hook without replacing an existing provider') | Out-Null }
if ($EnableAutoAccept) { $Plan.Add('SET permissions.defaultMode=acceptEdits while preserving deny rules and the destructive guard') | Out-Null }

if (-not $Apply) {
    Write-Host 'DRY RUN — no files changed. Review the plan, then re-run with -Apply:'
    $Plan | ForEach-Object { Write-Host $_ }
    exit 0
}

if ($globalExists -and -not $ReplaceGlobalConstitution -and -not $KeepGlobalConstitution) {
    throw 'Existing ~/.claude/CLAUDE.md found. Re-run with -ReplaceGlobalConstitution or -KeepGlobalConstitution.'
}

Ensure-Directory $ClaudeHome
$settingsPath = Join-Path $ClaudeHome 'settings.json'
$settingsBackup = $null
$settingsBeforeSha256 = $null
$previousDefaultMode = $null
if (Test-Path $settingsPath -PathType Leaf) {
    Ensure-Directory $BackupRoot
    $settingsBackup = Join-Path $BackupRoot 'settings.json'
    Copy-Item $settingsPath $settingsBackup -Force
    $settingsBeforeSha256 = Get-Sha256 $settingsPath
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
} else {
    $settings = [pscustomobject]@{}
}

$routerCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\hooks\skill-router.ps1"'
$guardCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\hooks\destructive-command-guard.ps1"'
Add-HookIfMissing $settings 'UserPromptSubmit' '' $routerCommand 20 $false
Add-HookIfMissing $settings 'PreToolUse' 'Bash' $guardCommand 20 $false

if ($EnableNotifications) {
    $notifyCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\hooks\notify.ps1"'
    Add-HookIfMissing $settings 'Stop' '' $notifyCommand 10 $true
}
if ($EnableAutoAccept) {
    Ensure-Property $settings 'permissions' ([pscustomobject]@{})
    if ($settings.permissions.PSObject.Properties['defaultMode']) {
        $previousDefaultMode = $settings.permissions.defaultMode
        $settings.permissions.defaultMode = 'acceptEdits'
    } else {
        $settings.permissions | Add-Member -MemberType NoteProperty -Name 'defaultMode' -Value 'acceptEdits'
    }
}
$settings | ConvertTo-Json -Depth 50 | Set-Content -Path $settingsPath -Encoding UTF8

$constitutionRecord = $null
if ($ReplaceGlobalConstitution -or (-not $globalExists -and -not $KeepGlobalConstitution)) {
    $backup = Backup-Target $globalClaude
    Copy-Item (Join-Path $RepoRoot 'CLAUDE.md') $globalClaude -Force
    $constitutionRecord = [pscustomobject]@{
        path = $globalClaude
        installedSha256 = Get-Sha256 $globalClaude
        previousExisted = [bool]$globalExists
        backupPath = $backup
    }
}

$manifest = [ordered]@{
    schemaVersion = 2
    installedAt = (Get-Date).ToUniversalTime().ToString('o')
    source = $RepoRoot
    backupRoot = $BackupRoot
    files = @($InstalledFiles)
    settings = [ordered]@{
        path = $settingsPath
        backupPath = $settingsBackup
        beforeSha256 = $settingsBeforeSha256
        installedSha256 = Get-Sha256 $settingsPath
        autoAcceptEnabled = [bool]$EnableAutoAccept
        previousDefaultMode = $previousDefaultMode
        notificationHookEnabled = [bool]$EnableNotifications
    }
    constitution = $constitutionRecord
}
$manifestPath = Join-Path $ClaudeHome 'turn-up-time-install-manifest.json'
$manifest | ConvertTo-Json -Depth 20 | Set-Content -Path $manifestPath -Encoding UTF8

Write-Host "Applied. Backup: $BackupRoot"
Write-Host "Install manifest: $manifestPath"
$Plan | ForEach-Object { Write-Host $_ }
