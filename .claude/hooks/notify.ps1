param([string]$Title = 'Claude Code', [string]$Message = 'Turn complete. Ready for input.')
try {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
    [System.Windows.Forms.NotifyIcon]$n = New-Object System.Windows.Forms.NotifyIcon
    $n.Icon = [System.Drawing.SystemIcons]::Information
    $n.BalloonTipTitle = $Title
    $n.BalloonTipText = $Message
    $n.Visible = $true
    $n.ShowBalloonTip(5000)
    Start-Sleep -Milliseconds 800
    $n.Dispose()
} catch {
    try { [Console]::Beep(880,150) } catch { }
}
