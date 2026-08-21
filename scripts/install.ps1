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
$ClaudeHome = Join-Path $env:USERPROFILE '.claude'
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$BackupRoot = Join-Path $ClaudeHome ("turn-up-time-backup-$Stamp")
$Plan = New-Object System.Collections.Generic.List[string]
$InstalledFiles = New-Object System.Collections.Generic.List[string]

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Force -Path $Path | Out-Null }
}

function Backup-File {
    param([string]$Target)
    if (-not (Test-Path $Target)) { return }
    $relative = $Target.Substring($ClaudeHome.Length).TrimStart('\\','/')
    $backup = Join-Path $BackupRoot $relative
    Ensure-Directory (Split-Path -Parent $backup)
    Copy-Item $Target $backup -Force
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
    $files = @(Get-ChildItem -Path $entry.Source -Recurse -File)
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($entry.Source.Length).TrimStart('\\','/')
        $target = Join-Path $entry.Target $relative

        if ($entry.Source -like '*\.claude\scripts' -and $relative -ieq 'fresh_review.py') {
            $Plan.Add("SKIP source-repository-only reviewer $target") | Out-Null
            continue
        }
        if ($relative -ieq 'notify.ps1' -and -not $EnableNotifications) {
            $Plan.Add("SKIP notification provider $target") | Out-Null
            continue
        }
        if ($relative -ieq 'notify.ps1' -and (Test-Path $target)) {
            $Plan.Add("KEEP existing notification provider $target") | Out-Null
            continue
        }

        $Plan.Add("COPY $($file.FullName) -> $target") | Out-Null
        if ($Apply) {
            Ensure-Directory (Split-Path -Parent $target)
            Backup-File $target
            Copy-Item $file.FullName $target -Force
            $InstalledFiles.Add($target) | Out-Null
        }
    }
}

$Plan.Add('MERGE UserPromptSubmit skill-router hook into ~/.claude/settings.json') | Out-Null
if ($EnableNotifications) { $Plan.Add('MERGE Stop notification hook without replacing an existing notify.ps1') | Out-Null }
if ($EnableAutoAccept) { $Plan.Add('SET permissions.defaultMode=acceptEdits while preserving deny rules') | Out-Null }
if ($ReplaceGlobalConstitution) { $Plan.Add('BACKUP and replace ~/.claude/CLAUDE.md with the canonical Turn Up Time constitution') | Out-Null }

if (-not $Apply) {
    Write-Host 'DRY RUN — no files changed. Re-run with -Apply after reviewing:'
    $Plan | ForEach-Object { Write-Host $_ }
    exit 0
}

Ensure-Directory $ClaudeHome
$settingsPath = Join-Path $ClaudeHome 'settings.json'
if (Test-Path $settingsPath) {
    Ensure-Directory $BackupRoot
    Copy-Item $settingsPath (Join-Path $BackupRoot 'settings.json') -Force
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
} else {
    $settings = [pscustomobject]@{}
}
if (-not $settings.PSObject.Properties['hooks']) { $settings | Add-Member NoteProperty hooks ([pscustomobject]@{}) }
if (-not $settings.hooks.PSObject.Properties['UserPromptSubmit']) { $settings.hooks | Add-Member NoteProperty UserPromptSubmit @() }
$routerCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\hooks\skill-router.ps1"'
$existingRouter = $settings.hooks.UserPromptSubmit | ConvertTo-Json -Depth 20 -Compress
if ($existingRouter -notlike '*skill-router.ps1*') {
    $settings.hooks.UserPromptSubmit = @($settings.hooks.UserPromptSubmit) + @([pscustomobject]@{ hooks = @([pscustomobject]@{ type='command'; command=$routerCommand; timeout=20 }) })
}
if ($EnableNotifications) {
    if (-not $settings.hooks.PSObject.Properties['Stop']) { $settings.hooks | Add-Member NoteProperty Stop @() }
    $notifyCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\hooks\notify.ps1"'
    $existingStop = $settings.hooks.Stop | ConvertTo-Json -Depth 20 -Compress
    if ($existingStop -notlike '*notify.ps1*') {
        $settings.hooks.Stop = @($settings.hooks.Stop) + @([pscustomobject]@{ hooks = @([pscustomobject]@{ type='command'; command=$notifyCommand; timeout=10; async=$true }) })
    }
}
if ($EnableAutoAccept) {
    if (-not $settings.PSObject.Properties['permissions']) { $settings | Add-Member NoteProperty permissions ([pscustomobject]@{}) }
    if ($settings.permissions.PSObject.Properties['defaultMode']) { $settings.permissions.defaultMode = 'acceptEdits' }
    else { $settings.permissions | Add-Member NoteProperty defaultMode 'acceptEdits' }
}
$settings | ConvertTo-Json -Depth 30 | Set-Content -Path $settingsPath -Encoding UTF8

if ($ReplaceGlobalConstitution) {
    $globalClaude = Join-Path $ClaudeHome 'CLAUDE.md'
    Backup-File $globalClaude
    Copy-Item (Join-Path $RepoRoot 'CLAUDE.md') $globalClaude -Force
}

$manifest = [ordered]@{
    installedAt = (Get-Date).ToUniversalTime().ToString('o')
    source = $RepoRoot
    backupRoot = $BackupRoot
    files = @($InstalledFiles)
    settingsPath = $settingsPath
    constitutionReplaced = [bool]$ReplaceGlobalConstitution
}
$manifestPath = Join-Path $ClaudeHome 'turn-up-time-install-manifest.json'
$manifest | ConvertTo-Json -Depth 10 | Set-Content -Path $manifestPath -Encoding UTF8

Write-Host "Applied. Backup: $BackupRoot"
Write-Host "Install manifest: $manifestPath"
$Plan | ForEach-Object { Write-Host $_ }
