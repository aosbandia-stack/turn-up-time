#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$ForceModified,
    [switch]$RestoreSettingsBackup
)
$ErrorActionPreference = 'Stop'
$ClaudeHome = Join-Path $env:USERPROFILE '.claude'
$ManifestPath = Join-Path $ClaudeHome 'turn-up-time-install-manifest.json'
if (-not (Test-Path $ManifestPath -PathType Leaf)) { throw "Install manifest not found: $ManifestPath" }
$Manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
$Skipped = New-Object System.Collections.Generic.List[string]

function Get-Sha256 {
    param([string]$Path)
    if (-not (Test-Path $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
}

function Remove-InstalledArtifact {
    param([object]$Record, [string]$Label)
    $path = [string]$Record.path
    if (-not (Test-Path $path -PathType Leaf)) {
        Write-Host "MISSING $Label $path"
        return
    }
    $current = Get-Sha256 $path
    $installed = [string]$Record.installedSha256
    $modified = -not [string]::IsNullOrWhiteSpace($installed) -and $current -ne $installed
    if ($modified -and -not $ForceModified) {
        Write-Host "SKIP MODIFIED $Label $path"
        $Skipped.Add($path) | Out-Null
        return
    }

    if (-not $Apply) {
        if ($Record.previousExisted -and $Record.backupPath) { Write-Host "WOULD RESTORE $Label $path" }
        else { Write-Host "WOULD REMOVE $Label $path" }
        return
    }

    if ($Record.previousExisted -and $Record.backupPath -and (Test-Path $Record.backupPath -PathType Leaf)) {
        Copy-Item $Record.backupPath $path -Force
        Write-Host "RESTORED $Label $path"
    } else {
        Remove-Item $path -Force
        Write-Host "REMOVED $Label $path"
    }
}

function Remove-HookCommand {
    param([object]$Settings, [string]$EventName, [string]$Needle)
    if (-not $Settings.PSObject.Properties['hooks']) { return }
    if (-not $Settings.hooks.PSObject.Properties[$EventName]) { return }
    $keptRows = New-Object System.Collections.Generic.List[object]
    foreach ($row in @($Settings.hooks.$EventName)) {
        $keptHooks = New-Object System.Collections.Generic.List[object]
        foreach ($hook in @($row.hooks)) {
            $command = "$($hook.command)"
            if ($command.IndexOf($Needle, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
                $keptHooks.Add($hook) | Out-Null
            }
        }
        if ($keptHooks.Count -gt 0) {
            $row.hooks = @($keptHooks)
            $keptRows.Add($row) | Out-Null
        }
    }
    $Settings.hooks.$EventName = @($keptRows)
}

foreach ($record in @($Manifest.files)) {
    Remove-InstalledArtifact $record 'file'
}
if ($null -ne $Manifest.constitution) {
    Remove-InstalledArtifact $Manifest.constitution 'constitution'
}

$settingsRecord = $Manifest.settings
$settingsPath = if ($settingsRecord.path) { [string]$settingsRecord.path } else { Join-Path $ClaudeHome 'settings.json' }
if ($RestoreSettingsBackup) {
    if (-not $settingsRecord.backupPath -or -not (Test-Path $settingsRecord.backupPath -PathType Leaf)) {
        throw 'No settings backup is available.'
    }
    if ($Apply) {
        Copy-Item $settingsRecord.backupPath $settingsPath -Force
        Write-Host "RESTORED full settings backup $settingsPath"
    } else {
        Write-Host "WOULD RESTORE full settings backup $settingsPath (this discards later settings changes)"
    }
} elseif (Test-Path $settingsPath -PathType Leaf) {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    Remove-HookCommand $settings 'UserPromptSubmit' 'skill-router.ps1'
    Remove-HookCommand $settings 'PreToolUse' 'destructive-command-guard.ps1'
    if ($settingsRecord.notificationHookEnabled) { Remove-HookCommand $settings 'Stop' 'notify.ps1' }

    if ($settingsRecord.autoAcceptEnabled -and $settings.PSObject.Properties['permissions'] -and $settings.permissions.PSObject.Properties['defaultMode']) {
        if ($settings.permissions.defaultMode -eq 'acceptEdits') {
            if ($null -ne $settingsRecord.previousDefaultMode -and -not [string]::IsNullOrWhiteSpace("$($settingsRecord.previousDefaultMode)")) {
                $settings.permissions.defaultMode = $settingsRecord.previousDefaultMode
            } else {
                $settings.permissions.PSObject.Properties.Remove('defaultMode')
            }
        } else {
            Write-Host 'KEEP settings defaultMode because it changed after installation.'
        }
    }
    if ($Apply) {
        $settings | ConvertTo-Json -Depth 50 | Set-Content -Path $settingsPath -Encoding UTF8
        Write-Host "REMOVED Turn Up Time hook rows from $settingsPath"
    } else {
        Write-Host "WOULD REMOVE Turn Up Time hook rows from $settingsPath"
    }
}

if ($Apply) {
    if ($Skipped.Count -eq 0) {
        Remove-Item $ManifestPath -Force
        Write-Host 'Uninstall complete; manifest removed.'
    } else {
        Write-Host "Uninstall incomplete: $($Skipped.Count) modified file(s) were preserved. Manifest retained. Re-run with -ForceModified only after review."
    }
} else {
    Write-Host 'DRY RUN — no files or settings changed.'
}
