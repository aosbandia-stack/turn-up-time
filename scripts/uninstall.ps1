#requires -Version 5.1
[CmdletBinding()]
param([switch]$Apply)
$ErrorActionPreference = 'Stop'

$ClaudeHome = if ($env:TURN_UP_TIME_CLAUDE_HOME) { $env:TURN_UP_TIME_CLAUDE_HOME } else { Join-Path $env:USERPROFILE '.claude' }
$ManifestPath = Join-Path $ClaudeHome 'turn-up-time-install-manifest.json'
if (-not (Test-Path -LiteralPath $ManifestPath)) { throw "Install manifest not found: $ManifestPath" }
$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
$Skipped = New-Object 'System.Collections.Generic.List[string]'

function Get-Sha256 {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
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

foreach ($record in @($manifest.files)) {
    $path = "$($record.path)"
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host "ABSENT $path"
        continue
    }
    $current = Get-Sha256 $path
    if ($current -ne "$($record.installed_sha256)") {
        Write-Host "SKIP MODIFIED $path"
        $Skipped.Add($path) | Out-Null
        continue
    }
    if (-not $Apply) {
        if ($record.preexisting -and $record.backup_path) { Write-Host "WOULD RESTORE $path" }
        else { Write-Host "WOULD REMOVE $path" }
        continue
    }
    if ($record.preexisting -and $record.backup_path -and (Test-Path -LiteralPath $record.backup_path)) {
        Copy-Item -LiteralPath $record.backup_path -Destination $path -Force
        Write-Host "RESTORED $path"
    } else {
        Remove-Item -LiteralPath $path -Force
        Write-Host "REMOVED $path"
    }
}

$settingsPath = "$($manifest.settings.path)"
if (Test-Path -LiteralPath $settingsPath) {
    if (-not $Apply) {
        Write-Host "WOULD REMOVE Turn Up Time hook rows from $settingsPath"
    } else {
        $settings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
        if ($null -ne $settings.PSObject.Properties['hooks']) {
            if ($null -ne $settings.hooks.PSObject.Properties['UserPromptSubmit']) {
                $settings.hooks.UserPromptSubmit = Remove-HookCommand $settings.hooks.UserPromptSubmit 'skill-router.ps1'
            }
            if ($null -ne $settings.hooks.PSObject.Properties['PreToolUse']) {
                $settings.hooks.PreToolUse = Remove-HookCommand $settings.hooks.PreToolUse 'destructive-command-guard.ps1'
            }
            if ($manifest.settings.notification_added -and $null -ne $settings.hooks.PSObject.Properties['Stop']) {
                $settings.hooks.Stop = Remove-HookCommand $settings.hooks.Stop 'notify.ps1'
            }
        }
        if ($manifest.settings.default_mode_changed -and $null -ne $settings.PSObject.Properties['permissions']) {
            $currentMode = if ($null -ne $settings.permissions.PSObject.Properties['defaultMode']) { "$($settings.permissions.defaultMode)" } else { $null }
            if ($currentMode -eq 'acceptEdits') {
                if ([string]::IsNullOrWhiteSpace("$($manifest.settings.default_mode_before)")) {
                    $settings.permissions.PSObject.Properties.Remove('defaultMode')
                } else {
                    $settings.permissions.defaultMode = "$($manifest.settings.default_mode_before)"
                }
            } else {
                Write-Host "SKIP MODIFIED permissions.defaultMode=$currentMode"
                $Skipped.Add('settings.permissions.defaultMode') | Out-Null
            }
        }
        $settings | ConvertTo-Json -Depth 50 | Set-Content -LiteralPath $settingsPath -Encoding UTF8
        Write-Host "UPDATED $settingsPath"
    }
}

if ($manifest.constitution.replaced -and $manifest.constitution.path) {
    $path = "$($manifest.constitution.path)"
    if (Test-Path -LiteralPath $path) {
        $current = Get-Sha256 $path
        if ($current -ne "$($manifest.constitution.installed_sha256)") {
            Write-Host "SKIP MODIFIED $path"
            $Skipped.Add($path) | Out-Null
        } elseif (-not $Apply) {
            if ($manifest.constitution.preexisting) { Write-Host "WOULD RESTORE $path" }
            else { Write-Host "WOULD REMOVE $path" }
        } elseif ($manifest.constitution.preexisting -and $manifest.constitution.backup_path -and (Test-Path -LiteralPath $manifest.constitution.backup_path)) {
            Copy-Item -LiteralPath $manifest.constitution.backup_path -Destination $path -Force
            Write-Host "RESTORED $path"
        } else {
            Remove-Item -LiteralPath $path -Force
            Write-Host "REMOVED $path"
        }
    }
}

if ($null -ne $manifest.PSObject.Properties['graph_runtime'] -and $manifest.graph_runtime.enabled) {
    $runtime = $manifest.graph_runtime
    if (-not (Test-Path -LiteralPath $runtime.home -PathType Container)) {
        Write-Host "ABSENT GRAPH RUNTIME $($runtime.home)"
    } else {
        $markerSafe = Test-Path -LiteralPath $runtime.marker_path -PathType Leaf
        if ($markerSafe -and $runtime.marker_sha256) {
            $markerSafe = (Get-Sha256 $runtime.marker_path) -eq "$($runtime.marker_sha256)"
        }
        $runtimeSafe = (Get-DirectorySha256 $runtime.home) -eq "$($runtime.installed_sha256)"
        if (-not $markerSafe -or -not $runtimeSafe) {
            Write-Host "SKIP MODIFIED GRAPH RUNTIME $($runtime.home)"
            $Skipped.Add("graph_runtime:$($runtime.home)") | Out-Null
        } elseif (-not $Apply) {
            if ($runtime.preexisting -and $runtime.backup_path) {
                Write-Host "WOULD RESTORE GRAPH RUNTIME $($runtime.home)"
            } else {
                Write-Host "WOULD REMOVE GRAPH RUNTIME $($runtime.home)"
            }
        } else {
            Remove-Item -LiteralPath $runtime.home -Recurse -Force
            if ($runtime.preexisting -and $runtime.backup_path -and (Test-Path -LiteralPath $runtime.backup_path -PathType Container)) {
                New-Item -ItemType Directory -Force -Path (Split-Path -Parent $runtime.home) | Out-Null
                Copy-Item -LiteralPath $runtime.backup_path -Destination $runtime.home -Recurse -Force
                Write-Host "RESTORED GRAPH RUNTIME $($runtime.home)"
            } else {
                Write-Host "REMOVED GRAPH RUNTIME $($runtime.home)"
            }
        }
    }
}

if ($Apply -and $Skipped.Count -eq 0) {
    Remove-Item -LiteralPath $ManifestPath -Force
    Write-Host "REMOVED manifest $ManifestPath"
} elseif ($Skipped.Count -gt 0) {
    Write-Host "Manifest retained because modified artifacts were skipped: $ManifestPath"
}

if (-not $Apply) { Write-Host 'DRY RUN - re-run with -Apply to uninstall.' }
