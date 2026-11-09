# Register a daily Windows Task Scheduler task that runs scripts\run_job_boards_locally.ps1.
# Run once from an elevated or normal PowerShell:  powershell -ExecutionPolicy Bypass -File scripts\register_windows_task.ps1
# Remove later with:  Unregister-ScheduledTask -TaskName "JobAggregator-JobBoards" -Confirm:$false

param(
    [string]$Time = "20:15",                         # local time; before the cloud run at 20:47 IST
    [string]$TaskName = "JobAggregator-JobBoards"
)

$repo = Split-Path -Parent $PSScriptRoot
$script = Join-Path $repo "scripts\run_job_boards_locally.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
# Run when the PC is on; if the time was missed (PC asleep or off), run as soon as possible afterwards.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Fetch Indeed, Naukri and Glassdoor jobs from this PC's home IP" -Force
Write-Output "Registered '$TaskName' daily at $Time"
