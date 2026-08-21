param([string]$Title = 'Claude Code', [string]$Message = 'Turn complete. Ready for input.')
try {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
    Add-Type -AssemblyName System.Drawing -ErrorAction Stop
    [System.Windows.Forms.NotifyIcon]$notification = New-Object System.Windows.Forms.NotifyIcon
    $notification.Icon = [System.Drawing.SystemIcons]::Information
    $notification.BalloonTipTitle = $Title
    $notification.BalloonTipText = $Message
    $notification.Visible = $true
    $notification.ShowBalloonTip(5000)
    Start-Sleep -Milliseconds 800
    $notification.Dispose()
} catch {
    try { [Console]::Beep(880,150) } catch { }
}
