#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$EnableNotifications,
    [switch]$EnableAutoAccept,
    [switch]$ReplaceGlobalConstitution,
    [switch]$EnableGraphRuntime
)
$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ClaudeHome = if ($env:TURN_UP_TIME_CLAUDE_HOME) { $env:TURN_UP_TIME_CLAUDE_HOME } else { Join-Path $env:USERPROFILE '.claude' }
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$BackupRoot = Join-Path $ClaudeHome ("turn-up-time-backup-$Stamp")
$ManifestPath = Join-Path $ClaudeHome 'turn-up-time-install-manifest.json'
$Plan = New-Object 'System.Collections.Generic.List[string]'
$FileRecords = New-Object 'System.Collections.Generic.List[object]'
$PreservedRecords = New-Object 'System.Collections.Generic.List[object]'

function Ensure-Directory {
    param([string]$Path)
    if (-not [string]::IsNullOrWhiteSpace($Path) -and -not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Get-Sha256 {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-RelativeToHome {
    param([string]$Path)
    return $Path.Substring($ClaudeHome.Length).TrimStart([char[]]@([char]92, [char]47))
}

function Get-DirectorySha256 {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return $null }
    $root = (Resolve-Path -LiteralPath $Path).Path
    $rows = New-Object 'System.Collections.Generic.List[string]'
    foreach ($file in @(Get-ChildItem -LiteralPath $root -Recurse -File | Sort-Object FullName)) {
        $relative = $file.FullName.Substring($root.Length).TrimStart([char[]]@([char]92, [char]47))
        if ($relative -ieq 'runtime-manifest.json') { continue }
        if ($relative -match '(^|[\\/])__pycache__([\\/]|$)') { continue }
        if ($relative -match '\.pyc$') { continue }
        $rows.Add("$relative|$(Get-Sha256 $file.FullName)") | Out-Null
    }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes([string]::Join("`n", $rows.ToArray()))
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash($bytes)
        return ([System.BitConverter]::ToString($hash)).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Backup-Target {
    param([string]$Target)
    if (-not (Test-Path -LiteralPath $Target -PathType Leaf)) { return $null }
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

function Resolve-GraphPython {
    if (-not [string]::IsNullOrWhiteSpace($env:TURN_UP_TIME_PYTHON)) {
        if (-not (Test-Path -LiteralPath $env:TURN_UP_TIME_PYTHON -PathType Leaf)) {
            throw "TURN_UP_TIME_PYTHON does not exist: $env:TURN_UP_TIME_PYTHON"
        }
        return $env:TURN_UP_TIME_PYTHON
    }
    foreach ($name in @('python.exe', 'python3.exe', 'python3', 'python')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $command) { return $command.Source }
    }
    throw 'Python 3.11 or newer is required. Install Python or set TURN_UP_TIME_PYTHON to python.exe.'
}

function Install-GraphRuntime {
    $runtimeSource = Join-Path $RepoRoot 'runtime'
    if (-not (Test-Path -LiteralPath (Join-Path $runtimeSource 'pyproject.toml') -PathType Leaf)) {
        throw "Graph runtime source is missing: $runtimeSource"
    }
    $runtimeHome = Join-Path $ClaudeHome 'runtime\turn-up-time'
    $markerPath = Join-Path $runtimeHome 'runtime-manifest.json'
    $preexisting = Test-Path -LiteralPath $runtimeHome -PathType Container
    $backup = $null
    if ($preexisting) {
        $backup = Join-Path $BackupRoot 'runtime\turn-up-time'
        Ensure-Directory (Split-Path -Parent $backup)
        Copy-Item -LiteralPath $runtimeHome -Destination $backup -Recurse -Force
    }

    try {
        if (Test-Path -LiteralPath $runtimeHome) {
            Remove-Item -LiteralPath $runtimeHome -Recurse -Force
        }
        Ensure-Directory (Split-Path -Parent $runtimeHome)

        $python = Resolve-GraphPython
        $versionText = "$(& $python -c 'import sys; print("{0}.{1}.{2}".format(*sys.version_info[:3]))')".Trim()
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($versionText)) {
            throw "Unable to read Python version from $python"
        }
        try { $pythonVersion = [version]$versionText }
        catch { throw "Unrecognized Python version from $python`: $versionText" }
        if ($pythonVersion -lt [version]'3.11') {
            throw "Python 3.11 or newer is required; found $pythonVersion at $python"
        }

        $venvOutput = & $python -m venv $runtimeHome 2>&1
        $venvCode = $LASTEXITCODE
        $venvOutput | ForEach-Object { Write-Host $_ }
        if ($venvCode -ne 0) { throw "Failed to create graph runtime virtual environment at $runtimeHome" }

        $venvPython = Join-Path $runtimeHome 'Scripts\python.exe'
        if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
            $venvPython = Join-Path $runtimeHome 'bin\python'
        }
        if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
            throw "Virtual environment Python is missing under $runtimeHome"
        }

        $pipOutput = & $venvPython -m pip install --disable-pip-version-check --no-input $runtimeSource 2>&1
        $pipCode = $LASTEXITCODE
        $pipOutput | ForEach-Object { Write-Host $_ }
        if ($pipCode -ne 0) { throw 'Failed to install the Turn Up Time graph runtime and pinned dependencies.' }

        $validationOutput = & $venvPython -m turn_up_time_graph.cli validate-topology 2>&1
        $validationCode = $LASTEXITCODE
        $validationOutput | ForEach-Object { Write-Host $_ }
        if ($validationCode -ne 0) { throw 'Installed graph runtime failed topology validation.' }

        $installedHash = Get-DirectorySha256 $runtimeHome
        $installId = [guid]::NewGuid().ToString()
        $marker = [ordered]@{
            schema_version = 1
            install_id = $installId
            runtime_version = '1.0.0'
            installed_at = (Get-Date).ToUniversalTime().ToString('o')
            home = $runtimeHome
            venv_python = $venvPython
            installed_sha256 = $installedHash
            source = $runtimeSource
        }
        $marker | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $markerPath -Encoding UTF8
        $markerHash = Get-Sha256 $markerPath

        return [pscustomobject][ordered]@{
            enabled = $true
            install_id = $installId
            version = '1.0.0'
            home = $runtimeHome
            marker_path = $markerPath
            marker_sha256 = $markerHash
            venv_python = $venvPython
            installed_sha256 = $installedHash
            preexisting = [bool]$preexisting
            backup_path = $backup
        }
    } catch {
        if (Test-Path -LiteralPath $runtimeHome) {
            Remove-Item -LiteralPath $runtimeHome -Recurse -Force
        }
        if ($preexisting -and $backup -and (Test-Path -LiteralPath $backup -PathType Container)) {
            Ensure-Directory (Split-Path -Parent $runtimeHome)
            Copy-Item -LiteralPath $backup -Destination $runtimeHome -Recurse -Force
        }
        throw
    }
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
        if ($relative -ieq 'fresh_graph_review.py') {
            $Plan.Add("SKIP source-only graph reviewer $target") | Out-Null
            continue
        }
        if ($relative -ieq 'notify.ps1' -and -not $EnableNotifications) {
            $Plan.Add("SKIP optional notification provider $target") | Out-Null
            continue
        }
        if ($relative -ieq 'notify.ps1' -and (Test-Path -LiteralPath $target)) {
            $Plan.Add("KEEP existing notification provider $target") | Out-Null
            $PreservedRecords.Add([pscustomobject][ordered]@{ path = $target; reason = 'existing notification provider' }) | Out-Null
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
                action = $(if ($preexisting) { 'overwritten' } else { 'created' })
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
if ($EnableGraphRuntime) { $Plan.Add('CREATE isolated Python 3.11+ graph runtime under ~/.claude/runtime/turn-up-time and record runtime-manifest.json') | Out-Null }

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

$GraphRuntime = [pscustomobject][ordered]@{
    enabled = $false
    install_id = $null
    version = $null
    home = $null
    marker_path = $null
    marker_sha256 = $null
    venv_python = $null
    installed_sha256 = $null
    preexisting = $false
    backup_path = $null
}
if ($EnableGraphRuntime) {
    $GraphRuntime = Install-GraphRuntime
}

$manifest = [ordered]@{
    schema_version = 3
    installed_at = (Get-Date).ToUniversalTime().ToString('o')
    source = $RepoRoot
    backup_root = $BackupRoot
    files = $FileRecords.ToArray()
    preserved_files = $PreservedRecords.ToArray()
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
    graph_runtime = $GraphRuntime
}
$manifest | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8

Write-Host "Applied Turn Up Time. Backup: $BackupRoot"
Write-Host "Install manifest: $ManifestPath"
if ($GraphRuntime.enabled) { Write-Host "Graph runtime: $($GraphRuntime.home)" }
$Plan | ForEach-Object { Write-Host $_ }
