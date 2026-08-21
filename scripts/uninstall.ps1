#requires -Version 5.1
param(
    [switch]$Apply,
    [switch]$RestoreSettings,
    [switch]$RestoreConstitution
)
$ErrorActionPreference = 'Stop'
$home = Join-Path $env:USERPROFILE '.claude'
$manifestPath = Join-Path $home 'turn-up-time-install-manifest.json'
if (-not (Test-Path $manifestPath)) { throw "Install manifest not found: $manifestPath" }
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
foreach ($path in @($manifest.files)) {
    $prefix = 'WOULD REMOVE '
    if ($Apply) {
        if (Test-Path $path) { Remove-Item $path -Force }
        $prefix = 'REMOVED '
    }
    Write-Host ($prefix + $path)
}
if ($RestoreSettings -and $manifest.backupRoot) {
    $backup = Join-Path $manifest.backupRoot 'settings.json'
    if (Test-Path $backup) {
        if ($Apply) { Copy-Item $backup (Join-Path $home 'settings.json') -Force }
        $prefix = 'WOULD RESTORE '; if ($Apply) { $prefix = 'RESTORED ' }; Write-Host ($prefix + 'settings.json')
    }
}
if ($RestoreConstitution -and $manifest.backupRoot) {
    $backup = Join-Path $manifest.backupRoot 'CLAUDE.md'
    if (Test-Path $backup) {
        if ($Apply) { Copy-Item $backup (Join-Path $home 'CLAUDE.md') -Force }
        $prefix = 'WOULD RESTORE '; if ($Apply) { $prefix = 'RESTORED ' }; Write-Host ($prefix + 'CLAUDE.md')
    }
}
if ($Apply) { Remove-Item $manifestPath -Force }
Write-Host 'Hook rows added to settings are removed by restoring the settings backup; otherwise remove them manually.'
